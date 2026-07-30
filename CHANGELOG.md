# Changelog

This file records repository-level changes. Individual plugin versions remain
the source of truth for installed plugin releases.

## Unreleased

- Expanded `a-stock-data` from a six-command prototype to a complete
  52-command Codex surface covering the upstream ten-layer A-share toolkit,
  independent fallbacks, dependency diagnostics, structured errors, and
  bundled offline tests.
- Made the public `a-stock-data` plugin its own release source instead of
  vendoring an incomplete copy from the earlier Codex adaptation repository.
- Renamed third-party plugin IDs to clean product names and kept upstream
  ownership in metadata instead of exposing a maintenance prefix.
- Added four separately installable, commit-pinned upstream plugins for
  frontend design, programmatic SEO, UI/UX intelligence, and web design review.
- Added unified validation and local Codex installation entry points.
- Documented public/private boundaries, release checks, and upstream handling.
- Reused the existing pinned-upstream automation instead of introducing a
  second synchronization system.

## Maintenance baseline — 2026-07-29

- Established `agent-toolkit` as the public marketplace.
- Published the first-party `media-tools` plugin.
- Added marketplace validation and scheduled upstream update workflows.

Earlier repository history is preserved in Git and is not reconstructed here.
