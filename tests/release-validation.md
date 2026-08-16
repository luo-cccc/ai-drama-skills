# Release Validation

> Run date: **2026-08-16**  
> Scope: documentation refresh and deterministic release validation  
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
| Python suite | **86 tests passed; 0 failures; 0 errors; 0 skips** |
| `novel-characters` selftest | 307 assertions passed |
| `novel-outline` selftest | 220 assertions passed |
| `novel-art` selftest | 146 assertions passed |
| `novel-script` selftest | 153 assertions passed |
| `novel-storyboard` selftest | 191 assertions passed |
| Adapted Node total | **1017 assertions passed** |
| `synthetic-short` | project validator passed |
| `legacy-yiqiyang` | project validator passed |
| Schema enforcement lint | passed |
| Pinned upstream snapshot | **65 files verified**; upstream, adapted overlays and runtime hashes matched |
| Release inventory | **15 Skills; 450 manifest-listed files** |
| Isolated dist verification | both builds passed |
| Deterministic build | both complete package trees matched |
| Python cache pollution | disabled during verification; dist verifier confirmed package tree remained unchanged |

## Identities

- `vendor/shuohao/snapshot-manifest.json` SHA-256: `88dd4e58d7d30a32eba6f62c7a766db42394445e097f8f48952cca37d42e31dd`
- `dist/package-manifest.json` SHA-256: `7cb4fb0d101b4b855b661b00f162035fd09fe90e71ff8cb198459745227ababf`

The package manifest includes the shared delivery contract and, for every Skill carrying shuohao runtime material, upstream LICENSE, upstream NOTICE and the Forging modification addendum.

## Evidence Boundary

This PASS covers the executed checkout's deterministic code, documentation contracts, fixtures, schemas, snapshot integrity, package closure and reproducibility. It does not establish:

- fresh model behavior on the forward prompts;
- independent agent performance on the current package;
- image, video or audio generation quality;
- fidelity to a source that is not distributed;
- legal clearance for project content or generated media;
- a passing forward/model evidence gate.

The forward/model gate remains **FAIL** because [forward-test-report.md](forward-test-report.md) is **STALE / LEGACY / NOT REVALIDATED**. A replacement forward report must record its own package identity, prompt and fixture hashes, environment, outputs, validator results and limitations.
