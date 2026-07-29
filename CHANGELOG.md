# Changelog

This file records repository-level changes. Individual plugin versions remain
the source of truth for installed plugin releases.

## Unreleased

- Added the Codex-native `a-stock-data` plugin with tested JSON commands for
  A-share quotes, reports, company information, news, and valuation math.
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
