# Workflow Contract

Use named stages and never invent numeric Step aliases:

`intake -> development -> brief -> outline -> screenplay -> audit -> shots/assets -> complete`

## Routing

| Request | Route |
|:--|:--|
| Concept or incomplete premise | `development` |
| Mature story to screenplay | `brief -> outline -> screenplay -> audit` |
| Existing screenplay diagnosis | `audit` |
| Confirmed screenplay to shots | `shots` |
| Confirmed screenplay to assets | `assets` |
| Direct character, scene, storyboard, or video task | Matching domain skill |
| Video reverse analysis | Shot analysis, independent of screenplay stages |

Determine completeness from protagonist, goal or conflict, key relationship, ending direction, and tone. Do not use a word-count threshold.

## Checkpoints

Every checkpoint must name a stage, decision, nonempty authorization, continuous `sequence`, and nonempty `affects` list of existing artifact IDs. The checkpoint stage must match each affected artifact's owning stage. An `automatic` decision is valid only when project configuration enables `automatic_authorization`.

Authorization is effective per artifact, not per stage or conversation. The effective checkpoint is the affected artifact's checkpoint with the greatest valid `sequence`. Only effective `confirmed` or `automatic` decisions approve the artifact. A later `revise` or `rejected` decision revokes an earlier approval and is incompatible with confirmed status.

Pause after direction, production brief, scene outline, and each screenplay revision unless the user explicitly authorized automatic continuation. Approval must bind exact artifact IDs through `affects`; vague permission to continue does not approve a later revision. An automatically confirmed screenplay requires a valid covering audit.

Project-level briefs and outlines are singletons. Confirmed ranged artifacts must not overlap, except that a series audit or series shot plan may coexist with its episode-range inputs. Supersede an overlapping replacement before confirmation. A series audit and series aggregate must cover every episode without gaps.

## Delivery Tiers

- **Planning complete**: screenplay, valid series audit, scoped plans, immutable series aggregate, matching root projection, and locked required assets pass validation. `delivery_required=false`. This tier makes no media-generation claim.
- **Generation-ready**: each generation manifest depends on a confirmed shot plan; its groups exactly match the plan's generation groups, shot IDs, beat IDs, asset IDs, and time bounds; every prompt file exists and matches its declared SHA-256.
- **Media delivered**: `delivery_required=true` and a confirmed series `delivery-manifest` with status `complete` is required. All declared artifacts must be delivered with passing or not-applicable QC, all storyboard images must be present as declared, hashes must match, and `known_gaps` must be empty.

Do not use a higher tier label when only a lower tier is satisfied. See `delivery-contract.md` for delivery declaration and validation limits.

## Authority And Persistence

Apply this order when instructions conflict: safety and rights; explicit current user constraints; confirmed project state and effective checkpoints; canonical sources by registered authority; domain defaults.

Do not let downstream work silently change plot, dialogue meaning, relationships, ending, or locked continuity. Record sources, artifacts, decisions, dependencies, scope, and hashes durably; session memory is not authorization or provenance. JSON is authoritative over Markdown derivatives.
