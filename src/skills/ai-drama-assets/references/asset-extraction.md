# Asset Extraction Rules

## Inclusion Thresholds

Include an asset when it recurs, changes story causality, identifies a character or faction, anchors spatial continuity, or needs a stable image-generation reference. A prop that triggers, proves, enables, blocks, or resolves a key causal turn is included even if it appears only once. Exclude interchangeable crowds, ordinary background objects, and one-use items without visual or narrative significance unless the user requests exhaustive coverage.

### Characters

Include protagonists, antagonists, relationship pivots, information holders, recurring supporting roles, and visually distinctive non-human entities. Merge titles, nicknames, former names, and spelling variants as aliases.

Lock identity with age impression, face geometry, skin, eyes, hairline and hair structure, body silhouette, persistent marks, and exact non-human anatomy. Define non-human appendage counts, attachment points, symmetry, material, and terminal shape.

### Costumes and Character Variants

Create `COSTUME-NNN` for reusable clothing systems and reference it from character variants. Create a character variant only when clothing, grooming, age, health, transformation, or social identity changes enough to alter generation. Dirt, a removed accessory, or a momentary expression is normally a continuity state, not a variant.

Describe layers, silhouette, closure, seam logic, material, weave, color relationships, pattern placement, hardware, wear, climate response, and movement constraints. Preserve the base character's immutable identity in every variant.

### Scenes and Backgrounds

Include locations that host key action, recur, have distinctive geometry, or require spatial continuity. Use `SCENE-NNN` for the production space and `BG-NNN` only for a reusable distant environment, backdrop, or set extension.

Record boundary, elevation, entrances, windows, structural grid, functional zones, circulation, fixed furniture, hero objects, light sources, palette, materials, atmosphere, and scale references. Create a variant only when time, weather, damage, or reconfiguration materially changes the visible asset.

### Props and Motifs

Include a prop when it drives plot, signals identity, grants capability, carries evidence, or recurs. Plot-driving and evidence-bearing props do not need recurrence. Record silhouette, component connections, opening or articulation, material, fabrication, scale relative to a known object, handling points, load and wear points, storage position, and state changes.

Use `MOTIF-NNN` for recurring visual grammar such as a faction pattern, symbol family, color code, or fabrication signature. Link motifs to assets; do not duplicate their definitions inside every asset.

## Art Baseline

Resolve the following once per project or delivery:

- Era, region, climate, season, technology, and social hierarchy.
- Cultural sources and explicit exclusions.
- Primary, secondary, and accent color relationships.
- Material families, construction precision, maintenance, and aging.
- Rendering or capture language, contrast, grain, and light behavior.

Use the baseline to constrain additions, not to overwrite direct evidence.

## Evidence and Completion

Use source facts first. Infer only the smallest missing structure needed for function or reproducibility. Mark unknown hidden surfaces, exact geometry, undecidable left/right placement, and disputed details `unknown` (`待确认`).

For reference images, inspect the actual image. For text-only concept design, mark all newly invented identity, decoration, geometry, and materials as `inferred` (`保守推定`) or `unknown`; they become `confirmed` only after user approval.

## Originality and Safety

Do not imitate a living public figure, reproduce a protected character, or retain real brand marks unless the user has supplied authorized production material and explicitly needs fidelity. Translate inspiration into general era, craft, silhouette, material, and color constraints. Keep minors age-appropriate. Represent injury through story-required, non-exploitative visible facts.

## DNA Writing

Use observable, repeatable statements. Prefer "dark oxidized brass with polished contact edges" over "premium cinematic metal." Avoid generic quality tags, celebrity likeness, brand names, unexplained ornament, incompatible periods, and mutually exclusive rendering styles.
