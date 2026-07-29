# Contributing

## Repository boundaries

- Put reusable, redistributable plugins in this public marketplace.
- Put personal, restricted, customer-specific, or secret-dependent workflows
  in `agent-toolkit-self`.
- Edit the source repository under `plugins/`; never edit
  `~/.codex/plugins/cache/` or marketplace snapshots under `~/.codex/.tmp/`.

## First-party plugins

Group closely related Skills into one domain plugin. Keep Skill instructions concise, avoid machine-specific paths, and include only the resources needed at runtime.

Every first-party plugin must:

1. Use the same normalized name for its folder, manifest, and marketplace entry.
2. Declare a focused purpose rather than a broad collection of unrelated tools.
3. Include accurate author, repository, interface, capability, and icon metadata.
4. Keep machine-specific paths, credentials, generated outputs, and caches out
   of Git.
5. Document optional dependencies and ask before installing them.

## Third-party plugins

Before vendoring upstream content:

1. Confirm the source repository and redistribution license.
2. Create a separate `upstream-<name>` plugin.
3. Add an entry to `upstreams/sources.json`.
4. Record the resolved commit in `upstreams/sources.lock.json`.
5. Preserve the upstream license and attribution.
6. Keep Codex-specific changes in declared transforms or overlays.
7. Require a reviewed pull request for every update.

Do not silently copy third-party Skills into a first-party plugin. The source,
license, resolved commit, and local adaptations must remain auditable.

## Validation

Run:

```bash
./scripts/validate.sh
```

Do not commit credentials, local configuration, generated caches, broken symlinks, or absolute home-directory paths.

## Release checklist

1. Make the smallest coherent plugin or maintenance change.
2. Update the affected plugin version when its installed content changes.
3. Add a concise entry under `Unreleased` in `CHANGELOG.md`.
4. Run `./scripts/validate.sh`.
5. Review `git diff` and confirm no private data or generated files are present.
6. Commit and push through a reviewed pull request.
7. Run `./scripts/install-local.sh <plugin>` after the change reaches the
   configured Git marketplace.
8. Start a new Codex task to verify newly discovered Skills.
