#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

python3 "$repo_root/scripts/validate_marketplace.py" "$repo_root"

python3 - "$repo_root" <<'PY'
import ast
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(sys.argv[1])
errors = []

for path in sorted(root.rglob("*.py")):
    if ".git" in path.parts:
        continue
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        errors.append(f"invalid Python syntax: {path}: {exc}")

for path in sorted(root.rglob("*.svg")):
    if ".git" in path.parts:
        continue
    try:
        ET.parse(path)
    except ET.ParseError as exc:
        errors.append(f"invalid SVG XML: {path}: {exc}")

if errors:
    print("Additional validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("Python syntax and SVG XML are valid")
PY

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$repo_root/plugins/a-stock-data/skills/a-stock-data/scripts/build_upstream_module.py" \
  --check
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s "$repo_root/plugins/a-stock-data/skills/a-stock-data/scripts/tests" \
  -q
echo "A-share endpoint contracts and offline parsers are valid"

while IFS= read -r -d '' shell_script; do
  bash -n "$shell_script"
done < <(find "$repo_root" -path "$repo_root/.git" -prune -o -type f -name '*.sh' -print0)

echo "Shell syntax is valid"
