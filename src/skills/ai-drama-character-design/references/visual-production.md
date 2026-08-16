# Character Visual Production

## Identity Lock

Hold stable: age impression, face and skull geometry, feature spacing, eye and skin color, hairline and hair structure, body proportions, persistent marks, non-human anatomy, art language, and declared asymmetry. Hold costume silhouette, layers, seams, color, patterns, hardware, wear, and accessories stable whenever the mode does not explicitly vary them.

Never beautify, age-shift, change ethnicity, alter body type, swap art styles, erase distinctive marks, or copy a public figure or protected character. Keep minors age-appropriate.

## Evidence Overlay

Use one legend across all plates:

- Solid treatment: `confirmed` (`已确认`).
- Short dashed or low-saturation translucent treatment: `inferred` (`保守推定`).
- Dash-dot plus `待确认`: `unknown`.

Do not let overlays hide facial features or critical silhouettes. Store the same evidence state in the project manifest; the picture is not the source of truth.

## Two-Pass Text

First generate artwork without text, IDs, arrows, UI, signatures, or watermarks. Then use deterministic layout to add simplified Chinese labels, the stable asset ID, panel names, guide lines, and evidence legend. Keep labels short and concrete. Proofread for wrong characters, pseudo-Chinese, duplicated text, incorrect IDs, and crossed leader lines.

If deterministic layout is unavailable, provide the unlettered image and `character-CHAR-NNN-labels-vNNN.txt`. Do not present it as a finished labeled plate.

## Prompt Construction

State the asset ID, character anchors, selected mode, panel count and order, projection/camera, pose or expression, background, lighting, materials, composition, and exclusions. Use physical descriptions instead of vague quality labels. Include the original references on every edit pass.

For `prompt-only`, include:

1. Source and evidence summary.
2. Immutable identity and continuity anchors.
3. Exact panel map and layout.
4. Positive prompt.
5. Negative constraints.
6. Resolution and aspect ratio.
7. Label text and placement plan.
8. Mode-specific QC checklist.

## Quality Gate

Inspect the final pixels, not just the prompt. Reject and repair when any of these occur:

- Face, age, body proportion, hairstyle, costume, material, or art-style drift.
- Incorrect left/right assignment, mirrored asymmetry, missing or duplicated accessories.
- Perspective in orthographic views, mismatched scale, landmark misalignment, or inconsistent pose.
- Anatomical errors, fused or extra limbs/digits, broken weight, impossible contact, or clipping.
- Missing panels, duplicated content, unreadable differences, crowded layout, or cropped body/props.
- Garment seams, patterns, closures, or prop parts that fail to continue across views.
- Wrong ID, bad Chinese, watermark, signature, unintended logo, second character, or story background.

Record unresolved failures and mark the project artifact `invalid` or `pending-confirmation`; never label a failed plate `confirmed`.
