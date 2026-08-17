# Release Validation

> Run date: **2026-08-18**
> Scope: integration cleanup (kernel rename, terminology unification, removal of legacy forward test assets)
> Result: **PASS for all recorded deterministic checks**

本文件记录当前文档、规范源、测试和发行包完成后的实际运行结果。它不把确定性工程验证扩展为模型、agent 或真实媒体的 forward evidence。

## Environment

| Tool | Version |
|:--|:--|
| Python | 3.14.6 |
| Node.js | 22.22.2 |
| FFmpeg | 9.0 full build |
| Pillow | 12.3.0 |

外部 sibling `../shuohao-skills-main` 可用，并参与 snapshot source、license 和 selftest 核对。

## Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p "test_*.py" -v

node engine/shuohao-adapted/skills/novel-characters/scripts/selftest.mjs
node engine/shuohao-adapted/skills/novel-outline/scripts/selftest.mjs
node engine/shuohao-adapted/skills/novel-art/scripts/selftest.mjs
node engine/shuohao-adapted/skills/novel-script/scripts/selftest.mjs
node engine/shuohao-adapted/skills/novel-storyboard/scripts/selftest.mjs

python scripts/validate_project.py examples/synthetic-short
python scripts/validate_project.py examples/legacy-yiqiyang
python scripts/sync_shuohao_snapshot.py --source ../shuohao-skills-main --check
python scripts/package_skills.py --output dist
python tests/verify_dist.py --dist dist
```

Schema keyword lint 也对 `schemas/*.json` 全部执行。dist 构建到两个独立目录，并比较所有相对路径和 SHA-256。

## Results

| Check | Result |
|:--|:--|
| Python suite | **141 tests passed; 0 failures; 0 errors; 0 skips** |
| `synthetic-short` | project validator passed |
| `legacy-yiqiyang` | project validator passed |
| Schema keyword lint | passed |
| Pinned upstream snapshot | **65 files verified** |
| Release inventory | **15 Skills; 489 manifest-listed files** |
| Isolated dist verification | passed |
| Deterministic build | both complete package trees matched |

## Identities

- `vendor/shuohao/snapshot-manifest.json` SHA-256: `02097a9e0afd0bce0f3dff9efea42f6307565bd29b5fc02aeee08a0f6a6e3822`
- `.agents/skills/package-manifest.json` SHA-256: `b0ba71c78424d3df6075e629b13c15f37b0b65284e17ccffb1f32cd6f829436b`

The package manifest includes the shared delivery contract and, for every Skill carrying shuohao runtime material, upstream LICENSE, upstream NOTICE and the Forging modification addendum.

## Evidence Boundary

This PASS covers the executed checkout's deterministic code, documentation contracts, fixtures, schemas, snapshot integrity, package closure and reproducibility. It does not establish:

- fresh model behavior on new prompts;
- independent agent performance on the current package;
- image, video or audio generation quality;
- fidelity to a source that is not distributed;
- legal clearance for project content or generated media.

Deterministic code, fixture evidence and release-run records are mechanically verifiable; model/agent behavior in open tasks is outside this repository's verification scope.
