#!/usr/bin/env python3
"""Validate an Agent Toolkit marketplace using only the Python standard library."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_SKILL_KEYS = {"name", "description"}
INSTALL_POLICIES = {"NOT_AVAILABLE", "AVAILABLE", "INSTALLED_BY_DEFAULT"}
AUTH_POLICIES = {"ON_INSTALL", "ON_USE"}
FORBIDDEN_NAMES = {"config.yaml", ".DS_Store"}
SECRET_PATTERNS = (
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
TEXT_SUFFIXES = {
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".toml",
    ".txt",
}


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"expected JSON object: {path}")
        return {}
    return value


def inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def parse_frontmatter(path: Path, errors: list[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append(f"missing YAML frontmatter: {path}")
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        errors.append(f"unterminated YAML frontmatter: {path}")
        return {}

    values: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(f"unsupported multiline frontmatter in {path}: {line}")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in values:
            errors.append(f"duplicate frontmatter key {key}: {path}")
        values[key] = value.strip().strip("\"'")

    extra = set(values) - ALLOWED_SKILL_KEYS
    if extra:
        errors.append(f"unsupported frontmatter keys {sorted(extra)}: {path}")
    if not values.get("name") or not values.get("description"):
        errors.append(f"frontmatter requires name and description: {path}")
    return values


def validate_skill(
    skill_dir: Path,
    seen_names: dict[str, Path],
    errors: list[str],
) -> None:
    frontmatter = parse_frontmatter(skill_dir / "SKILL.md", errors)
    name = frontmatter.get("name", "")
    if name and not SKILL_NAME.fullmatch(name):
        errors.append(f"invalid skill name {name!r}: {skill_dir}")
    if name and skill_dir.name != name:
        errors.append(f"skill folder/name mismatch: {skill_dir.name} != {name}")
    if name in seen_names:
        errors.append(f"duplicate skill name {name}: {seen_names[name]} and {skill_dir}")
    elif name:
        seen_names[name] = skill_dir

    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if openai_yaml.exists():
        metadata = openai_yaml.read_text(encoding="utf-8")
        if f"${name}" not in metadata:
            errors.append(f"default_prompt must mention ${name}: {openai_yaml}")


def validate_plugin(
    root: Path,
    entry: dict[str, Any],
    seen_names: dict[str, Path],
    errors: list[str],
) -> None:
    name = entry.get("name")
    source = entry.get("source", {})
    policy = entry.get("policy", {})
    expected_path = f"./plugins/{name}"
    if source != {"source": "local", "path": expected_path}:
        errors.append(f"invalid source for plugin {name}: expected {expected_path}")
    if policy.get("installation") not in INSTALL_POLICIES:
        errors.append(f"invalid installation policy for plugin {name}")
    if policy.get("authentication") not in AUTH_POLICIES:
        errors.append(f"invalid authentication policy for plugin {name}")
    if not entry.get("category"):
        errors.append(f"missing category for plugin {name}")

    plugin_dir = root / "plugins" / str(name)
    if not inside(root, plugin_dir):
        errors.append(f"plugin path escapes repository: {plugin_dir}")
        return
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path, errors)
    if not manifest:
        return
    if plugin_dir.name != name or manifest.get("name") != name:
        errors.append(f"plugin directory, entry, and manifest names must match: {name}")
    if not SEMVER.fullmatch(str(manifest.get("version", ""))):
        errors.append(f"invalid semver for plugin {name}: {manifest.get('version')}")

    required = ("description", "author", "interface")
    for key in required:
        if not manifest.get(key):
            errors.append(f"plugin {name} missing {key}")
    if not isinstance(manifest.get("author"), dict) or not manifest.get("author", {}).get("name"):
        errors.append(f"plugin {name} missing author.name")
    interface = manifest.get("interface", {})
    for key in (
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "capabilities",
        "defaultPrompt",
    ):
        if key not in interface:
            errors.append(f"plugin {name} missing interface.{key}")

    skills_path = plugin_dir / str(manifest.get("skills", "./skills/")).removeprefix("./")
    if not skills_path.is_dir():
        errors.append(f"plugin {name} has no skills directory: {skills_path}")
        return
    skill_dirs = sorted(path.parent for path in skills_path.glob("*/SKILL.md"))
    if not skill_dirs:
        errors.append(f"plugin {name} contains no Skills")
    for skill_dir in skill_dirs:
        validate_skill(skill_dir, seen_names, errors)


def validate_upstreams(root: Path, marketplace_name: str, errors: list[str]) -> None:
    sources_path = root / "upstreams" / "sources.json"
    lock_path = root / "upstreams" / "sources.lock.json"
    sources = load_json(sources_path, errors)
    lock = load_json(lock_path, errors)
    modules = sources.get("modules", [])
    locked = lock.get("modules", {})
    if not isinstance(modules, list) or not isinstance(locked, dict):
        errors.append("upstream manifests have invalid module shapes")
        return

    ids: set[str] = set()
    for module in modules:
        module_id = module.get("id")
        if not module_id or module_id in ids:
            errors.append(f"invalid or duplicate upstream id: {module_id}")
            continue
        ids.add(module_id)
        destination = root / str(module.get("destination", ""))
        if not inside(root, destination) or not (destination / "SKILL.md").exists():
            errors.append(f"invalid upstream destination for {module_id}: {destination}")
        if module.get("mode") != "vendor":
            errors.append(f"unsupported upstream mode for {module_id}")
        if module.get("updatePolicy") != "pull-request":
            errors.append(f"upstream {module_id} must use pull-request updates")
        locked_module = locked.get(module_id, {})
        if not COMMIT_SHA.fullmatch(str(locked_module.get("resolvedCommit", ""))):
            errors.append(f"upstream {module_id} is not locked to a commit")
        plugin = root / "plugins" / str(module.get("plugin", ""))
        if not (plugin / "THIRD_PARTY_NOTICES.md").exists():
            errors.append(f"upstream {module_id} missing THIRD_PARTY_NOTICES.md")

    extra_locks = set(locked) - ids
    if extra_locks:
        errors.append(f"lock file contains undeclared modules: {sorted(extra_locks)}")
    if marketplace_name == "agent-toolkit" and not (root / "LICENSE").exists():
        errors.append("public marketplace requires a root LICENSE")


def validate_tree(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            errors.append(f"symlinks are not allowed in marketplace archives: {path}")
            continue
        if path.name in FORBIDDEN_NAMES or "__pycache__" in path.parts:
            errors.append(f"forbidden generated or local file: {path}")
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        local_home_marker = "/" + "Users/"
        if local_home_marker in text:
            errors.append(f"local absolute path found in {path}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible credential found in {path}")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors: list[str] = []
    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
    marketplace = load_json(marketplace_path, errors)
    name = str(marketplace.get("name", ""))
    if not name:
        errors.append("marketplace name is required")
    if not marketplace.get("interface", {}).get("displayName"):
        errors.append("marketplace interface.displayName is required")
    entries = marketplace.get("plugins", [])
    if not isinstance(entries, list) or not entries:
        errors.append("marketplace must contain at least one plugin")
        entries = []

    plugin_names: set[str] = set()
    skill_names: dict[str, Path] = {}
    for entry in entries:
        plugin_name = entry.get("name")
        if plugin_name in plugin_names:
            errors.append(f"duplicate plugin name: {plugin_name}")
        plugin_names.add(plugin_name)
        validate_plugin(root, entry, skill_names, errors)

    declared_dirs = {path.name for path in (root / "plugins").iterdir() if path.is_dir()}
    undeclared = declared_dirs - plugin_names
    if undeclared:
        errors.append(f"plugin directories missing from marketplace: {sorted(undeclared)}")

    validate_upstreams(root, name, errors)
    validate_tree(root, errors)

    if errors:
        print("Marketplace validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        f"Marketplace {name} is valid: "
        f"{len(plugin_names)} plugins, {len(skill_names)} skills"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
