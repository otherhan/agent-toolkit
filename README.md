# Agent Toolkit

A public Codex plugin marketplace for reusable first-party tools and reviewed third-party modules.

## Install

```bash
codex plugin marketplace add otherhan/agent-toolkit --json
codex plugin list --available --json
```

Install one plugin at a time:

```bash
codex plugin add media-tools@agent-toolkit --json
codex plugin add upstream-agent-browser@agent-toolkit --json
```

Refresh the Git-backed marketplace:

```bash
codex plugin marketplace upgrade agent-toolkit --json
```

Start a new Codex task after installing or updating a plugin so newly available Skills are discovered.

## Plugins

| Plugin | Ownership | Purpose |
| --- | --- | --- |
| `media-tools` | First-party | Local media processing and verification |
| `upstream-agent-browser` | Third-party mirror | Version-locked Agent Browser guidance from Vercel Labs |

Third-party modules are pinned to an upstream commit, retain attribution and licensing, and are updated through reviewed pull requests.

## Repository model

- `.agents/plugins/marketplace.json` is the marketplace catalog.
- `plugins/<name>/.codex-plugin/plugin.json` defines each installable plugin.
- `plugins/<name>/skills/` contains the plugin's Skills.
- `upstreams/sources.json` declares vendored upstream modules.
- `upstreams/sources.lock.json` records resolved upstream commits.
- `scripts/` validates the marketplace and synchronizes upstream modules.

## Validate

```bash
python3 scripts/validate_marketplace.py .
```

## License

The repository is licensed under Apache-2.0. Vendored components retain their own attribution; see each plugin's notices.
