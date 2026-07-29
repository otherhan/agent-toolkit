#!/usr/bin/env python3
"""Check and synchronize version-locked third-party Skills."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run(args: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def ensure_inside(root: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {path}") from exc


def refspec(ref: str) -> str:
    return ref if ref.startswith("refs/") else f"refs/heads/{ref}"


def resolve_commit(module: dict[str, Any]) -> str:
    output = run(
        ["git", "ls-remote", module["repository"], refspec(module["ref"])]
    )
    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError(
            f"expected one ref for {module['id']}, received {len(lines)}"
        )
    commit = lines[0].split()[0]
    if len(commit) != 40:
        raise RuntimeError(f"invalid commit returned for {module['id']}: {commit}")
    return commit


def normalize_frontmatter(skill_file: Path, transforms: dict[str, Any]) -> None:
    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise RuntimeError(f"missing frontmatter: {skill_file}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise RuntimeError(f"unterminated frontmatter: {skill_file}") from exc

    new_name = transforms.get("skillName")
    strip = set(transforms.get("stripFrontmatterKeys", []))
    normalized: list[str] = ["---"]
    found_name = False
    stripping_block = False
    for line in lines[1:end]:
        is_top_level = bool(line) and not line[0].isspace()
        key = line.split(":", 1)[0].strip() if ":" in line else ""
        if is_top_level:
            stripping_block = key in strip
        if stripping_block:
            continue
        if is_top_level and key == "name" and new_name:
            normalized.append(f"name: {new_name}")
            found_name = True
        else:
            normalized.append(line)
    if new_name and not found_name:
        normalized.insert(1, f"name: {new_name}")
    normalized.extend(["---", *lines[end + 1 :]])
    skill_file.write_text("\n".join(normalized) + "\n", encoding="utf-8")


def replace_strings(skill_file: Path, transforms: dict[str, Any]) -> None:
    replacements = transforms.get("replaceStrings", {})
    if not replacements:
        return
    text = skill_file.read_text(encoding="utf-8")
    for old, new in replacements.items():
        if old not in text:
            raise RuntimeError(
                f"replacement source not found in {skill_file}: {old!r}"
            )
        text = text.replace(old, new)
    skill_file.write_text(text, encoding="utf-8")


def strip_trailing_whitespace(staged: Path, transforms: dict[str, Any]) -> None:
    suffixes = set(transforms.get("stripTrailingWhitespaceSuffixes", []))
    if not suffixes:
        return
    for path in staged.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        normalized = "\n".join(line.rstrip() for line in text.splitlines())
        if text.endswith("\n"):
            normalized += "\n"
        path.write_text(normalized, encoding="utf-8")


def copy_overlay(root: Path, staged: Path, overlay: str | None) -> None:
    if not overlay:
        return
    overlay_path = root / overlay
    ensure_inside(root, overlay_path)
    if not overlay_path.is_dir():
        raise RuntimeError(f"overlay directory does not exist: {overlay_path}")
    for source in overlay_path.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(overlay_path)
        target = staged / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def replace_directory(destination: Path, staged: Path) -> None:
    backup = destination.with_name(f".{destination.name}.backup-{os.getpid()}")
    if backup.exists():
        raise RuntimeError(f"backup path already exists: {backup}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.rename(backup)
    try:
        shutil.copytree(staged, destination)
    except Exception:
        if destination.exists():
            shutil.rmtree(destination)
        if backup.exists():
            backup.rename(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def update_plugin_version(root: Path, module: dict[str, Any], commit: str) -> None:
    manifest_path = (
        root / "plugins" / module["plugin"] / ".codex-plugin" / "plugin.json"
    )
    manifest = load_json(manifest_path)
    base = str(manifest["version"]).split("+", 1)[0]
    manifest["version"] = f"{base}+upstream.{commit[:7]}"
    write_json(manifest_path, manifest)


def sync_module(
    root: Path,
    module: dict[str, Any],
    commit: str,
    apply: bool,
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"toolkit-{module['id']}-") as temp:
        checkout = Path(temp) / "checkout"
        run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                "--branch",
                module["ref"],
                module["repository"],
                str(checkout),
            ]
        )
        run(["git", "sparse-checkout", "set", module["sourcePath"]], cwd=checkout)
        resolved = run(["git", "rev-parse", "HEAD"], cwd=checkout)
        if resolved != commit:
            raise RuntimeError(
                f"upstream moved while syncing {module['id']}: {commit} -> {resolved}"
            )

        source = checkout / module["sourcePath"]
        staged = Path(temp) / "staged"
        shutil.copytree(source, staged)
        normalize_frontmatter(staged / "SKILL.md", module.get("transforms", {}))
        replace_strings(staged / "SKILL.md", module.get("transforms", {}))
        strip_trailing_whitespace(staged, module.get("transforms", {}))
        copy_overlay(root, staged, module.get("overlayPath"))

        if not apply:
            print(f"{module['id']}: would sync {commit}")
            return

        destination = root / module["destination"]
        ensure_inside(root, destination)
        replace_directory(destination, staged)
        update_plugin_version(root, module, commit)
        print(f"{module['id']}: synced {commit}")


def selected_modules(
    modules: list[dict[str, Any]],
    requested: str,
) -> list[dict[str, Any]]:
    if requested == "all":
        return modules
    selected = [module for module in modules if module.get("id") == requested]
    if not selected:
        raise ValueError(f"unknown upstream module: {requested}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("check", "sync"),
        help="Check for updates or synchronize vendored content",
    )
    parser.add_argument("module", nargs="?", default="all")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run the synchronization pipeline even when the lock is current",
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    sources_path = root / "upstreams" / "sources.json"
    lock_path = root / "upstreams" / "sources.lock.json"
    sources = load_json(sources_path)
    lock = load_json(lock_path)
    modules = selected_modules(sources.get("modules", []), args.module)

    results: list[dict[str, Any]] = []
    for module in modules:
        current = lock.get("modules", {}).get(module["id"], {}).get(
            "resolvedCommit"
        )
        latest = resolve_commit(module)
        results.append(
            {
                "id": module["id"],
                "current": current,
                "latest": latest,
                "updateAvailable": current != latest,
            }
        )

    if args.command == "check":
        if args.json:
            print(json.dumps({"modules": results}, indent=2))
        else:
            for result in results:
                state = "update available" if result["updateAvailable"] else "current"
                print(f"{result['id']}: {state} ({result['latest']})")
        return 2 if any(item["updateAvailable"] for item in results) else 0

    changed = False
    for module, result in zip(modules, results, strict=True):
        if not result["updateAvailable"] and not args.force:
            print(f"{module['id']}: already current")
            continue
        sync_module(root, module, result["latest"], args.apply)
        if args.apply:
            lock.setdefault("modules", {})[module["id"]] = {
                "resolvedCommit": result["latest"],
                "syncedAt": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
            }
            changed = True

    if changed:
        write_json(lock_path, lock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
