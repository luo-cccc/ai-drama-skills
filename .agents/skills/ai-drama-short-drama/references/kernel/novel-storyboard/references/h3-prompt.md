# H3 Video Prompt Contract

One segment has one H3 prompt. Alignment text, picture order, and `[Shot k]` timestamps derive from the segment's cuts and are validated against them.

## Mode-Specific Language

### Standalone

The kernel may default `promptLang` to `en`. Dialogue keeps its source text and, when no local override exists, may use `<d>[Chinese] ...</d>`. Chinese prompt mode remains an explicit local option.

### Forging Governed

Prompt context/project profile must explicitly provide:

- prompt language;
- dialogue language and exact H3 dialogue tag;
- visual style and aspect ratio;
- generator/segment limit;
- exact episode duration.

Do not use standalone defaults in governed mode. The tag is derived from the profile, for example `profile.dialogue_language -> profile.h3.dialogue_tag`; never hard-code `[Chinese]` unless that is the explicit governed tag. Prompt prose uses the configured prompt language while dialogue remains verbatim in the configured dialogue language.

## Structure

English-mode skeleton:

```text
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 2) aligns with the 3.00-second mark of the target video; ….

integrated_multimodal_description:
[Shot 1] Anchor <Picture 1>, describe visible action, camera, performance, and tagged dialogue.
[Shot 2] At 00:03.000, cut to <Picture 2>: describe this cut only.

overall_soundscape: observable environment, action, and nonverbal sound.

non_diegetic_music: score direction, or N/A.
```

Chinese mode uses the matching Chinese alignment/field/shot tokens. Each shot stays on its own line. Cut `k >= 2` starts with the exact cumulative timestamp derived from prior cut durations.

## Dialogue

- Copy every claimed line exactly, including punctuation, into `<d>[Language] ...</d>`.
- Keep speaker identity, voice, pace, and emotion outside the `<d>` block.
- Keep a stable speaker label such as `(S1)` inside a segment when needed.
- For off-screen dialogue, state that it is off-screen and lips remain closed.
- Visible text and lyrics keep their source language; do not translate canonical content silently.

## Camera And Sound

Use the active camera vocabulary naturally, and place each cut's camera term inside that cut's own line. Soundscape is also an execution instruction: when visible action changes, reconcile its action sound. Keep dialogue/music out of `overall_soundscape` when their dedicated fields carry them.

## Frames And Aspect Ratio

`<Picture 1>` anchors the world at `0.00`; later pictures anchor their own cut marks. Frame composition and any generated raster must use the explicit active aspect ratio. Standalone may take a user-provided ratio; governed mode must use profile `aspect_ratio` and may not fall back to `16:9`.

## Closure And Delivery

H3 timestamps must reconcile with cut durations in both modes. In governed mode, their sum must also close the exact episode target after integer-millisecond conversion; `±15%` cannot pass this gate.

Standalone export produces a local prompt/frame manifest. Forging governed import separately creates the canonical generation manifest with prompt SHA-256, shots, beats, assets, generation group, and absolute timing. Actual generated media reaches verified delivery only after manifest registration and required QC.
