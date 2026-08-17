# Evidence And Audit Contract

Separate observed fact, inference, proposal, and unknown. Never claim source fidelity when the canonical source is unavailable. A passing claim without locatable evidence is invalid.

## Canonical V2 Audit

Every formal v2 audit is JSON conforming to `audit-report.schema.json`. Markdown is only a human-facing derivative. An embedded `ai-drama-audit` marker is accepted only for v1 or standalone compatibility and cannot authorize v2 downstream work.

The canonical report binds exact scope and ordered target artifacts by `artifact_id`, path, and SHA-256. It records basis items, findings, required-element evidence, differences, decision, and limitations. Governed imports require `conformance` mode, exact scope, and exact target order and hashes.

Each finding has a unique `FIND-NNN`, severity `P0`, `P1`, or `P2`, category, title, nonempty evidence, judgment, impact, action, and acceptance condition. Evidence identifies a source, locator, optional minimum quote, and status `observed`, `inferred`, `proposed`, or `unknown`.

Each required element has a unique `REQ-NNN`, requirement, source reference, result, and nonempty evidence. Results are `pass`, `fail`, or `unverifiable`. Each difference records locator, baseline, implementation, authorization, and result.

## Severity And Decision

- `P0`: breaks a confirmed core, causal spine, rights boundary, ending, relationship, or critical continuity; blocks passage and cannot be risk-accepted.
- `P1`: material omission, motivation jump, severe pacing, production, dialogue, or format failure.
- `P2`: local optimization that does not independently block passage.

Decision is `pass`, `revise`, `blocked`, or `accepted-with-risk`. `pass` requires zero P0, fewer than three P1, and every required element passed. `accepted-with-risk` requires zero P0 and every required element passed; it also requires an independent effective audit checkpoint with risk-acceptance authorization. Risk acceptance cannot override P0 or missing required elements.

## Registered Summary

The audit artifact's `audit_result` is derived from the canonical arrays and contains exactly:

`p0_count`, `p1_count`, `p2_count`, `required_elements_total`, `required_elements_passed`, `decision`.

The counts and decision must match the canonical report. Do not add hand-entered totals or alternate severity names. Machine validation verifies structure, bindings, counts, and gates; it does not replace creative review of causality, character, pacing, clarity, production, rights, and continuity.

## Modes

- `diagnostic`: analyze supplied material; source fidelity may be unavailable.
- `conformance`: compare the governed target with registered sources and confirmed upstream artifacts.
- `revision`: produce a new target revision from confirmed findings; never overwrite the audited revision.

Mark the audit artifact invalid when cited evidence, target paths, or target hashes cannot be verified.
