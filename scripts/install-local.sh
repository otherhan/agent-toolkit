#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/install-local.sh [--no-upgrade] [plugin ...]

Validate the repository, refresh its configured Git marketplace when needed,
and install selected plugins into local Codex. With no plugin arguments, all
plugins declared by this marketplace are installed.

Options:
  --no-upgrade  Skip marketplace upgrade.
  -h, --help    Show this help.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
marketplace_file="$repo_root/.agents/plugins/marketplace.json"
upgrade=true
plugins=()

while (($#)); do
  case "$1" in
    --no-upgrade)
      upgrade=false
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      plugins+=("$1")
      ;;
  esac
  shift
done

command -v codex >/dev/null 2>&1 || {
  echo "codex CLI is required but was not found in PATH." >&2
  exit 1
}

"$repo_root/scripts/validate.sh"

marketplace_name="$(
  python3 - "$marketplace_file" <<'PY'
import json
import sys
from pathlib import Path

print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["name"])
PY
)"

marketplaces_json="$(codex plugin marketplace list --json)"
source_type="$(
  printf '%s' "$marketplaces_json" |
    python3 -c '
import json
import sys

name = sys.argv[1]
data = json.load(sys.stdin)
match = next((item for item in data.get("marketplaces", []) if item.get("name") == name), None)
print(match.get("marketplaceSource", {}).get("sourceType", "") if match else "")
' "$marketplace_name"
)"

if [[ -z "$source_type" ]]; then
  echo "Adding local marketplace: $repo_root"
  codex plugin marketplace add "$repo_root" --json
  source_type="local"
fi

if [[ "$source_type" == "git" ]]; then
  if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
    echo "Refusing to install from Git while the source repository has uncommitted changes." >&2
    echo "Commit and push the changes first, then run this command again." >&2
    exit 2
  fi

  if upstream_ref="$(git -C "$repo_root" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null)"; then
    ahead_count="$(git -C "$repo_root" rev-list --count "$upstream_ref..HEAD")"
    if [[ "$ahead_count" != "0" ]]; then
      echo "Refusing to install from Git: local HEAD is $ahead_count commit(s) ahead of $upstream_ref." >&2
      echo "Push the commits first, then run this command again." >&2
      exit 2
    fi
  else
    echo "Refusing to install from Git because this branch has no configured upstream." >&2
    echo "Configure and push the branch first, then run this command again." >&2
    exit 2
  fi

  if [[ "$upgrade" == true ]]; then
    codex plugin marketplace upgrade "$marketplace_name" --json
  fi
fi

if ((${#plugins[@]} == 0)); then
  while IFS= read -r plugin_name; do
    plugins+=("$plugin_name")
  done < <(
    python3 - "$marketplace_file" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for plugin in data.get("plugins", []):
    print(plugin["name"])
PY
  )
fi

for plugin_name in "${plugins[@]}"; do
  codex plugin add "$plugin_name@$marketplace_name" --json
done

echo "Installed ${#plugins[@]} plugin(s) from $marketplace_name."
echo "Start a new Codex task before testing updated Skills."
