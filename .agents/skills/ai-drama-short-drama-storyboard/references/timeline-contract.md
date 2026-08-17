# Timeline And Video Prompt Contract

Maintain scoped canonical shot plans and one current series aggregate. All timing fields are integer milliseconds. A v2 plan declares `scope`, `timeline_start_ms`, and `timeline_end_ms`; scoped plans use absolute series time. The series aggregate starts at `0` and ends at `target_runtime_ms`.

## Aggregate And Projection

Aggregate only confirmed episode-range plans with continuous, non-overlapping coverage from episode 1 through the configured episode count. Scene definitions with the same `scene_id` must be identical. Beat and shot IDs must be unique across scoped plans.

Aggregation creates a versioned series `shot-plan-vNNN.json` and registers it as the immutable canonical artifact. It also replaces root `shot-plan.json` as the current projection. The projection is not a second canonical revision: it must be byte-for-byte equivalent to the immutable snapshot and have the same SHA-256. Re-aggregation supersedes the prior series snapshot and invalidates affected downstream artifacts.

The aggregate must be a lossless ordered merge of scoped `scenes`, `beats`, and `shots`. It may coexist with its confirmed scoped inputs. Aggregation requires a confirmed series audit whose decision is `pass` or effectively authorized `accepted-with-risk`.

## Beats And Clips

A complete beat is an action or question plus its direct consequence or answer. Give all shots in an indivisible beat the same `beat_id`; do not split the beat merely to satisfy a clip limit.

The default generator maximum is `30000` ms. Cut only at shot and beat boundaries. When `generation_group` is present, every shot must declare one, groups must be contiguous, and one group is exactly one generator call. Never split a group or merge different groups. If a group exceeds the generator maximum, report the incompatibility instead of truncating it.

Generation groups are distinct from editing containers and final deliverables. Editing may combine generated calls according to `editing_policy` without redefining their generation groups or canonical timing.

For an unspecified 2-3 minute request, use `150000` ms. Accept any explicit positive master duration. The screenplay-stage duration tolerance does not relax exact storyboard, scoped boundary, aggregate, or delivery timing.

## V2 Shot Data

Every v2 beat includes `source_scene_ref`, `source_beat_range`, and `source_beats`. Every v2 shot includes `performance`, `dialogue`, `sound`, `generation_group`, and `prompt_ref` in addition to identity, scene, beat, timing, framing, angle, movement, transition, visual action, and assets. Optional inline `prompt`, negative constraints, and model parameters do not replace the governed prompt file referenced by `prompt_ref`.

The plan profile must match project configuration for clip maximum, audio, subtitles, aspect ratio, generator, editing, visual reset, and dialogue rate. Do not impose policy values that the user or configured target did not request.
