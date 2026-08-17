---
name: ai-drama-short-drama-outline
description: Run the governed shuohao outline kernel to create and import an outline skeleton checkpoint followed by a confirmed full series outline. Use only when explicitly invoked or delegated by ai-drama-short-drama for short-drama structure work.
---

# Short Drama Outline Kernel

1. Refuse work until a production brief is confirmed.
2. Read `references/short-drama-prompt-governance.md`, `references/shuohao/workflow.md`, and all directly required files it names.
3. Run `prompt-context --stage outline --scope series` before each generation pass.
4. Generate the fast skeleton first and pass the upstream `beats` validator.
5. Present cuts, merged characters, and major payoff episode positions for user confirmation.
6. Import the confirmed skeleton with `import-outline --kind skeleton --confirm --authorization ...`.
7. Generate the full outline, assigning a stable `C`-ID to every character (novel-derived characters reuse the cast name/aliases; only original characters mint new IDs), pass the full validator, then import it with `--kind series`. The canonical outline JSON carries beats, hook/suspense, and major payoff episode positions; in the outline report, plan each episode's drama contract — which suspense lines open, advance, resolve, or defer (with 1-3 screen-visible evidence carriers for advance/resolve), the outgoing pressure and handoff facts for the next episode, and payoff types that rotate. The per-episode contract fields are executed at the screenplay stage from these beats; see `references/episode-drama-contract.md`.
8. In conversion mode, require explicit mappings under 人物、场景、核心事件、结局、必保元素 plus a conflict conclusion. Stop on material conflict.

The confirmed `series-outline` is the structural source of truth. Markdown and HTML are derived reports. On series confirmation the CLI deterministically seeds `hook-ledger.json` from the outline's major beats; the ledger itself is machine-maintained.
