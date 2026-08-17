# Screenplay Format

## Scene Headings

Use exactly:

```md
## 场 1｜内景 地点 - 时间
```

Keep scene numbers stable and continuous. A normal scene contains one continuous time and space.

Use `连续场组` when action moves continuously through adjacent spaces:

```md
## 场 5｜连续场组 会议室B -> 行政办公室 - 日
```

Use `交叉剪辑` for simultaneous parallel spaces:

```md
## 场 25｜交叉剪辑 出租车 / 公寓 - 夜
```

Mark each space change in the body with `**空间：名称**`. Do not use either form to hide a time jump that requires a new scene.

## Action And Dialogue

Write observable action in present tense. Keep one continuous action or visual change per paragraph. Convert internal states into behavior, silence, objects, sound, space, or an explicitly delimited subjective image.

Pronouns are allowed when their referent is unambiguous. Repeat names or IDs only when needed to protect execution clarity.

Write dialogue as:

```md
**姜宁**
时间到了。放下画笔。
```

Use `**姜宁（画外）**` for off-screen speech. Use Markdown block quotes for messages and screen text. Do not mix audit notes, camera plans, or author explanation into the screenplay.

## Scene Function

Each substantive scene must contain a goal, resistance, action, change, and exit logic. Dialogue should pursue, conceal, resist, or test something. Remove or merge scenes that only repeat information or emotional state.

