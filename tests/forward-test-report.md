# Forward Test Report

> Status: **STALE / LEGACY / NOT REVALIDATED**  
> Current forward/model evidence gate: **FAIL**  
> Last recorded historical activity: **2026-08-16**

No fresh isolated forward run has been completed against the current checkout or current release package. The prompts now use `<WORKSPACE_ROOT>` instead of the unavailable legacy host path, but changing prompt paths does not revalidate the historical outputs.

The deterministic release run recorded in [release-validation.md](release-validation.md) passed its own checks. That result is deliberately separate and does not change this forward gate.

## Historical Observations Only

The entries below preserve what earlier ephemeral agent runs reported. Every PASS is a historical observation, not a current certification, and should not be used as release approval for model behavior.

| Legacy group | Historical observation |
|:--|:--|
| Concept development | PASS was observed: a standalone response produced three directions, a recommendation, an 8-minute causal chain and explicit proposals without creating project state. |
| Mature story workflow | PASS was observed: `mature-r2` produced the planned artifact chain, an 18-shot `90000 ms` plan, legal clips and recorded checkpoints; its then-current validators passed. |
| Third-party originality | PASS was observed: `originality-r2/development-v001.md` rejected name/location substitution, retained abstract appeal and rebuilt concrete expression without claiming legal clearance. |
| Evidence audit | PASS was observed: `audit/audit-report-v001.md` cited exact severity findings and blocked formal shots and locked assets. |
| 135-second storyboard | PASS was observed: `storyboard-135` produced 27 shots on an exact `135000 ms` timeline and five complete-beat clips; its then-current timeline validation passed. |
| Visual generation and shot analysis | PASS was observed after iteration: the run generated and inspected a five-panel character image and probed a 3-second video with the expected frame and cut measurements. |

## Historical Release-Candidate Observations

These observations also came from the 2026-08-16 legacy campaign and remain unvalidated against the current package.

| Legacy group | Historical observation |
|:--|:--|
| Adversarial evidence audit | PASS was observed: an independent report blocked the screenplay and its then-current embedded audit parser accepted the recorded metadata and counts. |
| Authorized 30-second project | PASS was observed: the project recorded scoped artifacts and checkpoints, produced an exact `30000 ms` shot plan, and passed the then-current packaged validators. |
| Visual degradation and video analysis | PASS AFTER ITERATION was observed: the agent correctly used `prompt-only` when no image generator was callable, and fresh media probing plus contact-sheet checks passed after Markdown field preservation was fixed. |

## Historical Remediations

The legacy runs triggered changes that were subsequently incorporated into the repository:

- packaged `timeline_cli.py` was added wherever packaged validation imports it;
- development output gained a stable English filename rule;
- scoped automatic screenplay confirmation and audit acceptance were tightened;
- relative source paths were resolved from `--project-dir`;
- package replacement gained staged exchange and rollback behavior;
- shot-analysis Markdown retained canonical scene and asset IDs;
- presentation-only Markdown was prohibited from contradicting canonical JSON.

This list explains repository history; it does not prove those changes still pass an open-ended model workflow.

## Requirement To Clear The Gate

A replacement report must run the current raw prompts through fresh isolated agents using the current package, capture package identity and environment, preserve outputs and validator results, and distinguish model judgments from deterministic checks. Until that evidence exists, the forward/model gate remains **FAIL**.

Temporary outputs under ignored `tests/.forward-runs/`, when present, are working data and are not release evidence by themselves.
