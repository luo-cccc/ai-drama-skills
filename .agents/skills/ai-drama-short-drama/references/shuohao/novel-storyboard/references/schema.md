# storyboard.json Contract

The kernel structure is `episode -> segment -> cut`.

- A **segment** is one video-generation call and never crosses a scene.
- A **cut** claims a contiguous inclusive script beat range and carries duration, framing, camera, characters, props, and frame prompt.
- A **frame** is one keyframe per cut: cut 1 at `0.00`, later cuts at their cumulative cut marks.
- `h3Prompt` is one prompt per segment.

## Mode Decision

### Standalone

Standalone may omit local optional fields and use kernel defaults:

```json
{
  "source": "example",
  "style": "realistic",
  "promptLang": "en",
  "params": {
    "maxSegmentSeconds": 15,
    "minCutSeconds": 2,
    "maxCutSeconds": 5,
    "maxOnScreen": 3,
    "tolerance": 0.15
  },
  "episodes": [{"ep": 1, "segments": []}]
}
```

Here `tolerance` is a standalone episode-integrity check against script `targetSeconds`. It is not formal production closure.

### Forging Governed

The Forging wrapper must inject and verify explicit governed fields before import, including:

```json
{
  "promptLang": "en",
  "style": "realistic",
  "aspectRatio": "9:16",
  "dialogueTag": "<d>[Chinese]",
  "episodes": [{"ep": 1, "segments": []}]
}
```

Values come from immutable prompt context/project profile, not this example. Governed mode must not default missing `promptLang`, `style`, `aspectRatio`, `dialogueTag`, generator limits, or target duration. The exact target is supplied by the wrapper and every episode must equal it after lossless conversion to integer milliseconds. `params.tolerance` cannot authorize governed import.

## Segment

| Field | Contract |
| --- | --- |
| `id` | `E01-01`, sequential; used as generation-group/file identity |
| `sceneIndex` | 1-based script scene occurrence; all cuts remain in this scene |
| `cuts` | ordered cuts; duration is derived from their sum |
| `h3Prompt` | one prompt whose structure follows [h3-prompt.md](h3-prompt.md) |
| `note` | optional production note |

In Forging, `id` maps to `generation_group`; it is not a narrative beat ID.

## Cut

| Field | Contract |
| --- | --- |
| `beats` | inclusive `[start, end]`; every script beat claimed exactly once, in order |
| `seconds` | positive duration within active cut limits; dialogue must fit |
| `size` | kernel framing enum |
| `camera` | approved H3 camera term |
| `characters` | upstream character IDs visible in this cut |
| `props` | upstream prop IDs visible in this cut |
| `frame` | prompt for this cut's keyframe, including required size/style terms |
| `note` | optional exception/explanation |

Governed conversion creates exactly one Forging beat and shot per cut. It stores absolute integer `start_ms/end_ms`, source scene/beat evidence, asset IDs, prompt reference, and generation group in canonical scoped `shot-plan` JSON.

## H3 And Dialogue

The alignment line and each cut timestamp derive from cut durations and must reconcile exactly. Dialogue is copied verbatim into the active dialogue tag:

- Standalone default may use `<d>[Chinese] ...</d>` when no other local choice is supplied.
- Governed mode uses the explicit profile-derived `dialogueTag`; hard-coded `[Chinese]` is invalid when it differs.

## Timing And Manifests

Standalone chain: dialogue duration `<= cut seconds <= maxCutSeconds`; segment sum `<= maxSegmentSeconds`; episode may use configured tolerance.

Governed chain: all durations convert losslessly to integer milliseconds; each episode and scope closes exactly at profile boundaries; later ranges use absolute series time. Each generation group is bound by Forging `generation-manifest` to prompt path/hash, shot IDs, beat IDs, asset IDs, and absolute range.

The standalone export `manifest.json` remains a local H3 file list and must not be presented as the Forging canonical generation manifest.
