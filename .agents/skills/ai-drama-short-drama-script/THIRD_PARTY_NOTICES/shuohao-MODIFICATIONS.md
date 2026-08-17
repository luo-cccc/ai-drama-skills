# Modifications to shuohao-skills

This directory is the repository's adapted copy of the pinned `shuohao-skills` component. The corresponding unmodified snapshot is stored at `vendor/kernels/upstream/`. Identities for the pinned files and generated adapted/runtime component files are recorded in `vendor/kernels/snapshot-manifest.json`; this repository-authored statement is maintained outside that generated file set.

## Pinned Upstream

| Component | Version |
|:--|:--|
| `novel-characters` | 1.7.0 |
| `novel-outline` | 1.1.0 |
| `novel-art` | 1.1.0 |
| `novel-script` | 1.2.0 |
| `novel-storyboard` | 1.1.0 |

Upstream copyright and license terms remain in `LICENSE` and `NOTICE`. The repository adaptation is identified as version 1.0.0 in `FORGING-ADAPTATION.json`.

## Local Adaptations

- Public style identifiers and documentation are normalized to `realistic` and `hand-painted-cel`.
- Legacy imported style labels are normalized to the supported public identifier instead of being exposed as an additional public style.
- Adapted scripts and references are checked by the same five deterministic selftest programs used for the pinned engines.
- `novel-script` adds a non-blocking craft-hint pass (`craftReport`): delivery-as-strategy (delivery must name an executable strategy, not an emotion word) and action-surface tells (surprise-marker pileups, meta-narration). Hints surface in `checkup` and the rendered reports and never affect `validate` results or exit codes.
- The broader ai-drama-forging integration surrounds these engines with repository-specific scope, evidence, audit, transaction and timeline contracts.

The last item is primarily an integration boundary: it must not be read as a claim that the unmodified upstream project implements the repository's governance contracts.

## Derived Copies

`engine/runtime/` is a reduced execution projection generated from this adapted tree. It contains the five adapted runtime scripts and `FORGING-ADAPTATION.json`, without the complete upstream documentation, examples, assets or selftests.

Applicable packages under `dist/` copy selected runtime and reference material from the governed repository sources. Those packages include the shuohao Apache-2.0 license, NOTICE and snapshot manifest where the component is bundled. `dist/` is generated output and is not the source of record for modifications.

## Upstream NOTICE Typo

The upstream NOTICE names the sample story path as `skills/storycast/examples/渡口.txt`. In the pinned upstream snapshot, the file is located at `skills/novel-characters/examples/渡口.txt`. The NOTICE is retained verbatim to preserve upstream text; this note records the apparent path typo without changing the attribution or license coverage stated by upstream.

## Rights Boundary

These modifications are made under the Apache License 2.0 terms that accompany the identified shuohao files. That license applies to the shuohao component and modifications to it. It does not, by association, relicense other ai-drama-forging sources, user-provided stories, private project data, or generated media.
