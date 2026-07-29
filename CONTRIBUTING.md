# Contributing

## First-party plugins

Group closely related Skills into one domain plugin. Keep Skill instructions concise, avoid machine-specific paths, and include only the resources needed at runtime.

## Third-party plugins

Before vendoring upstream content:

1. Confirm the source repository and redistribution license.
2. Create a separate `upstream-<name>` plugin.
3. Add an entry to `upstreams/sources.json`.
4. Record the resolved commit in `upstreams/sources.lock.json`.
5. Preserve the upstream license and attribution.
6. Keep Codex-specific changes in declared transforms or overlays.
7. Require a reviewed pull request for every update.

## Validation

Run:

```bash
python3 scripts/validate_marketplace.py .
```

Do not commit credentials, local configuration, generated caches, broken symlinks, or absolute home-directory paths.
