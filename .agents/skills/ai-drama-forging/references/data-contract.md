# Structured Data Contract

JSON is canonical for project state, audit, assets, continuity, timed shots, generation inputs, and delivery declarations. Markdown, HTML, images, and root projections are derivatives unless a schema or registered artifact says otherwise.

## Canonical Files

- `project-state.json`: schema v2 project metadata, configuration, sources, artifact graph, checkpoints, and `project_revision`.
- `asset-manifest.json`: operational asset registry. New projects currently initialize and mutate schema v1.
- `continuity-ledger.json`: operational continuity event ledger. Its current schema is v1.
- scoped `shot-plan-vNNN.json`: canonical episode-range shot plans.
- series `shot-plan-vNNN.json`: immutable canonical series aggregate registered as a `shot-plan` artifact.
- root `shot-plan.json`: replaceable projection of the current series aggregate; its bytes and SHA-256 must match the immutable registered snapshot.
- `audit-vNNN.json`: canonical v2 formal audit.
- `generation-manifest-vNNN.json`: generation-group inputs and prompt hashes.
- `delivery-manifest-vNNN.json`: declared delivery contents, hashes, dimensions, durations, and QC states.

Write UTF-8 JSON with two-space indentation and a final newline. Use the project CLIs for mutation and atomic commit. Validate after every material update.

## Versions And Migration

Schema versions are per file type. A v2 `project-state.json` does not require a v2 asset manifest or continuity ledger. The current supported operational baseline is v2 project state with a v1 `asset-manifest.json` and v1 `continuity-ledger.json`.

Run `state_cli.py migrate-project --dry-run` before `--apply`. Migrating project state from v1 to v2:

- sets `schema_version` to `2.0` and `project_revision` to `1`;
- adds language, visual style, delivery, prompt-context, source trust, and rights defaults when absent;
- snapshots each valid confirmed artifact to a versioned immutable path unless it is already versioned or is the root `locked-assets` manifest;
- preserves the registered bytes and SHA-256;
- marks a confirmed artifact `invalid` when its path is unsafe, its file is missing, or its registered hash does not match;
- refuses a conflicting migration target instead of overwriting it.

Migration does not upgrade `asset-manifest.json` or `continuity-ledger.json`. Re-running migration on v2 is valid only when `project_revision` is a positive integer.

## Project State

Every available source records identity, authority, trust, rights, path, and SHA-256. Every artifact records identity, type, revision, status, path, dependencies, source references, optional scope, and SHA-256 when confirmed. Confirmed files must exist and match their registered hash.

Artifact status is `draft`, `pending-confirmation`, `confirmed`, `superseded`, or `invalid`. Dependencies must exist and remain usable. Never overwrite a confirmed artifact; register a new revision and supersede the replaced revision.

Use `SCN-NNN` only for screenplay scene occurrences registered in `project.scene_ids`. Use `CHAR-NNN`, `SCENE-NNN`, `PROP-NNN`, `MOTIF-NNN`, `COSTUME-NNN`, and `BG-NNN`, optionally with `-VNN`, for reusable production assets. Never recycle an ID or change it because a display name changes.

## Evidence And Locking

The operational v1 asset evidence levels are `confirmed`, `inferred`, and `unknown`. Lock status is `unlocked`, `partial`, `locked`, or `stale`. A `partial` or `locked` asset must list `locked_fields`; every locked field must have confirmed evidence, and visual DNA must be nonempty. A changed upstream artifact makes affected assets stale until reconciled.
