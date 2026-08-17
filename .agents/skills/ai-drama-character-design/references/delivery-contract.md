# Delivery Contract

Delivery claims are tiered. Never infer a higher tier from project completion, prompt availability, or manifest presence alone.

## Planning Complete

Planning completion requires the validated screenplay and series audit chain, continuous scoped shot plans, an immutable series aggregate with matching root projection, and locked assets required by the aggregate. It normally uses `delivery_required=false` and makes no claim that prompts were executed or media exists.

## Generation-Ready

A generation manifest is canonical v2 JSON conforming to `generation-manifest.schema.json`. It must depend on a confirmed shot plan. Its generator declaration fixes name, version, maximum segment duration, aspect ratio, prompt language, and dialogue language.

Each generation group must exactly match the dependent plan's group identity, ordered shot IDs, beat IDs, asset IDs, and start/end time. Its prompt path is relative to the manifest, the file must exist, and its SHA-256 must match. Generation readiness declares reproducible inputs; it does not claim a generation job ran or produced media.

## Media Delivered

A media delivery is canonical v2 JSON conforming to `delivery-manifest.schema.json`. It declares delivery identity, project, scope, status, rights summary, language profile, visual profile, artifacts, storyboard images, and known gaps. Rights declarations never claim legal clearance.

Use status precisely:

- `complete`: every listed artifact is `delivered`, each artifact QC is `pass` or `not-applicable`, all declared files exist and match their SHA-256, and `known_gaps` is empty.
- `partial`: some declared work is incomplete or omitted; record every material gap.
- `prompt-only`: prompts are delivered but generated media is not.
- `blocked`: delivery cannot proceed; record the blocker in `known_gaps`.
- `invalid`: declarations, files, hashes, or QC evidence are unreliable.

When project configuration sets `delivery_required=true`, completion requires a confirmed series `delivery-manifest` whose internal status is `complete`. A confirmed manifest with any other delivery status does not satisfy that gate.

## Validator Boundary

The project validator checks schema conformance, artifact registration and dependencies, declared status and QC fields, project-relative file existence, and SHA-256 equality. For a complete manifest it rejects undelivered artifacts, failed or unrun artifact QC, and known gaps.

The validator does not independently probe video, decode frames, measure duration or dimensions, run `ffprobe`, extract samples, or perform visual review. Values such as `duration_ms`, dimensions, and `qc_status` are declarations backed by prior tool or human evidence. Media probing and visual QC must be performed before the manifest is finalized; validation only verifies the resulting declarations and files.

Visual deliveries use `visual-delivery.schema.json` and its stronger per-output declared QC. Generated or edited visual output requires real files, matching hashes, deterministic QC declarations, passing visual review, and passing VR review for equirectangular output. Prompt-only visual status must not claim generated files.
