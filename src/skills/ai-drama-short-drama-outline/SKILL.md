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
7. Generate the full outline, reusing the stable `id` of each cast card for novel-derived characters and minting new ids only for original characters, pass the full validator, then import it with `--kind series`.
8. In conversion mode, require explicit mappings under 人物、场景、核心事件、结局、必保元素 plus a conflict conclusion. Stop on material conflict.

The confirmed `series-outline` is the structural source of truth. Markdown and HTML are derived reports.
