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
| `frontend-design` | Anthropic / Apache-2.0 | Distinctive production frontend design |
| `programmatic-seo` | Corey Haines / MIT | Scalable SEO page strategy and quality |
| `ui-ux-pro-max` | Next Level Builder / MIT | Searchable UI/UX design intelligence |
| `web-design-guidelines` | Vercel / MIT | Web interface review and accessibility checks |

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
./scripts/validate.sh
```

The validation entry point checks the marketplace catalog, plugin and Skill
layout, Python syntax, shell syntax, and SVG readability.

## Maintain

Work in this repository, not in the installed Codex cache:

```bash
git pull --ff-only
./scripts/validate.sh
git status
```

After committing and pushing a change, refresh the configured Git marketplace
and install one plugin or every plugin into the local Codex installation:

```bash
./scripts/install-local.sh media-tools
./scripts/install-local.sh
```

`install-local.sh` means “install into local Codex.” When this marketplace is
configured from GitHub, the script deliberately refuses dirty or unpushed
changes and installs from the refreshed Git snapshot.

See [CONTRIBUTING.md](CONTRIBUTING.md) for plugin ownership, third-party
vendoring, and release rules. Repository-level changes are recorded in
[CHANGELOG.md](CHANGELOG.md).

## Upstream maintenance

Third-party modules are declared in `upstreams/sources.json` and pinned in
`upstreams/sources.lock.json`:

```bash
python3 scripts/upstream.py check all
```

## License

The repository is licensed under Apache-2.0. Vendored components retain their own attribution; see each plugin's notices.
