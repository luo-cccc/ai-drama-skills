# Structured Data Contract

JSON is canonical for project state, audit, assets, continuity, timed shots, generation inputs, and delivery declarations. Markdown, HTML, images, and root projections are derivatives unless a schema or registered artifact says otherwise.

## Canonical Files

- `project-state.json`: schema v2 project metadata, configuration, sources, artifact graph, checkpoints, and `project_revision`.
- `asset-manifest.json`: operational asset registry. New projects currently initialize and mutate schema v1.
- `continuity-ledger.json`: operational continuity event ledger. Its current schema is v1.
- `hook-ledger.json` and `canon.json`: machine-maintained root projections for governed short-drama projects. Their authoritative bytes are immutable versioned snapshots `short-drama/governance/hook-ledger-vNNN.json` and `canon-vNNN.json`, registered as `hook-ledger` / `canon` artifacts; the root files must stay byte-identical to the current snapshot. `short-drama-engine.canonical_state` binds each snapshot artifact ID, path, SHA-256, revision, and derivation source.
- `canon-register-vNNN.json`: immutable inputs for each `canon register` operation, registered as `canon-register` artifacts so the canon history can be replayed deterministically.
- scoped `shot-plan-vNNN.json`: canonical episode-range shot plans.
- series `shot-plan-vNNN.json`: immutable canonical series aggregate registered as a `shot-plan` artifact.
- root `shot-plan.json`: replaceable projection of the current series aggregate; its bytes and SHA-256 must match the immutable registered snapshot.
- `audit-vNNN.json`: canonical v2 formal audit.
- `generation-manifest-vNNN.json`: generation-group inputs and prompt hashes.
- `delivery-manifest-vNNN.json`: declared delivery contents, hashes, dimensions, durations, and QC states.

Write UTF-8 JSON with two-space indentation and a final newline. Use the project CLIs for mutation and atomic commit. Validate after every material update.

## Governance Snapshots

The suspense ledger and canon are machine-maintained, and their history is immutable. Each mutation — hook seeding at confirmed series outline import, hook/canon evolution at confirmed screenplay import, canon register, and canon refresh — writes a versioned snapshot under `short-drama/governance/` and registers it as a `confirmed` `hook-ledger` / `canon` artifact. The previous snapshot of the same type is superseded; the root `hook-ledger.json` / `canon.json` remains a byte-identical projection of the current snapshot.

`short-drama-engine.canonical_state` records, for each of `hook_ledger` and `canon`, the current snapshot `artifact_id`, `snapshot_path`, `projection_path`, `sha256`, `revision`, and `depends_on`. The validator enforces that snapshot artifact, projection bytes, engine ref, and SHA-256 all agree, and it deterministically replays the derivation chain from confirmed inputs:

- hook ledger: seed from the confirmed series outline, then apply each confirmed screenplay in episode order;
- canon: walk snapshots in revision order, applying `merge_registered_canon` for a `canon-register` dependency, `derive_canon_updates` for a `screenplay` dependency, and `refresh_canon` otherwise.

A missing binding, a tampered snapshot or projection, or a derivation mismatch fails validation. `rebuild-governance --hook`/`--canon` deterministically rebuilds the hook ledger (and re-binds the canon projection) when state is missing or drifted.

## Episode Contract

Governed v2 short-drama projects with `episode_contract_required: true` embed a per-episode `contract` object in each screenplay batch JSON (`schemas/episode-contract.schema.json`). The contract rides with the screenplay file — one artifact, one scope, one SHA-256 binding — and is never a standalone canonical file. Its `handoffState` deterministically feeds the next batch's `previous_handoff` section in the script-stage prompt context; incoming state is a continuity boundary, not a creative choice.

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
