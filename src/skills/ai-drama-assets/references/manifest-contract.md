# Asset Manifest Contract

The repository schema is authoritative. Preserve unknown valid fields during a complete update.

## Versions And Migration

- Load the full existing manifest before allocation.
- A material delivery increments `manifest_version` exactly once and preserves every existing ID.
- v1 evidence records use `field`, `level`, `source_ref`, and `locator` with `confirmed`, `inferred`, or `unknown`.
- v2 claim records use `field` and `status`: `observed`, `inferred`, `proposed`, or `unknown`. `observed` requires source and locator; `proposed` requires `produced_by_artifact`; `unknown` requires a reason. Record derivation where available.
- Project migration is an explicit decision. The current `state_cli.py apply-manifest` path accepts schema `1.0` only: do not manually flip `asset-manifest.json` to `2.0`. Use v2 claim rows only after an approved compatible migration/write path exists. Never relabel v1 evidence as v2 provenance merely to obtain a lock.

## Canonical Semantics

`asset-manifest.json` contains only schema-valid project ID, schema/manifest versions, and asset rows. Each asset has stable ID, type, canonical name, aliases, lock state, locked fields, evidence/claims, and structured visual DNA.

Use `CHAR-001`, `SCENE-001`, `PROP-001`, `MOTIF-001`, `COSTUME-001`, and `BG-001`; use `-VNN` only for a reusable variant with a valid base and explicit delta. Store source hashes and artifact status in `project-state.json`, not as extra manifest properties.

## Update Procedure

1. Preserve IDs, aliases, history, and valid fields.
2. Append new IDs after the highest number for that type.
3. Reject duplicates, type changes, orphan variants, unsupported lock weakening, and locked fields without evidence.
4. Mark affected locks `stale` when supporting upstream content changes.
5. Apply the complete candidate with `state_cli.py apply-manifest --expected-version <current>`; never hand-edit the canonical file.
6. Validate before registering its exact hash. If validation fails, leave the previous manifest unchanged.

## Lock And Delivery Gates

A locked manifest is registered as artifact type `locked-assets`, canonical path `asset-manifest.json`, with its exact SHA-256 and exact confirmed screenplay/audit dependencies. Any later manifest change invalidates that confirmation until a new locked-assets artifact is authorized.

Prompts and preview images are not evidence. A DNA brief is planning-stage material, not delivered media. Generated visual media requires a separate `visual-delivery` with capability evidence, hashes, dimensions, and QC; project delivery requires the applicable delivery state in `delivery-contract.md`.

## Human Projection

Derive `asset-dna-vNNN.md` from the committed manifest. Group by type; show ID, name, evidence/claim status, lock state, immutable anchors, variant delta, and unresolved confirmations. Markdown is never the source of truth. A standalone manifest may use delivery-scoped `PROJECT-001`; state that its IDs are not project-global.
