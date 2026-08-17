#!/usr/bin/env python3
"""Deterministic hook ledger for the governed short-drama pipeline.

The ledger is a machine-maintained canonical file: it is seeded from the
confirmed series outline's major beats, evolved deterministically by each
screenplay batch's contract hook actions, and read by completion and health
gates. Models never write the ledger directly; they only declare hook actions
in per-episode contracts and the evidence carriers must echo in the script.
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent

try:
    from script_quality import (
        _episode_character_names,
        hook_evidence_is_concrete,
        ordered_episodes,
        surface_of_episode,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(SCRIPTS_DIR))
    from script_quality import (
        _episode_character_names,
        hook_evidence_is_concrete,
        ordered_episodes,
        surface_of_episode,
    )


HOOK_TIMING_PROFILES: dict[str, dict[str, int]] = {
    "immediate": {"stale_dormancy": 1, "overdue_age": 3},
    "near-term": {"stale_dormancy": 2, "overdue_age": 5},
    "mid-arc": {"stale_dormancy": 4, "overdue_age": 8},
    "slow-burn": {"stale_dormancy": 5, "overdue_age": 12},
    "endgame": {"stale_dormancy": 6, "overdue_age": 16},
}
MAX_ACTIVE_HOOKS = 12
SEED_PLANT_WINDOW = 3


def next_hook_id(hooks: list[dict[str, Any]]) -> str:
    maximum = max(
        (int(match.group(1)) for hook in hooks if (match := re.fullmatch(r"H-(\d{3})", str(hook.get("hook_id", ""))))),
        default=0,
    )
    if maximum >= 999:
        raise ValueError("hook ID space exhausted")
    return f"H-{maximum + 1:03d}"


def timing_for_payoff_episode(episode: int, episode_count: int) -> str:
    ratio = episode / max(1, episode_count)
    if ratio <= 0.25:
        return "near-term"
    if ratio <= 0.5:
        return "mid-arc"
    if ratio <= 0.8:
        return "slow-burn"
    return "endgame"


def seed_hook_ledger(outline: dict[str, Any], project_id: str, episode_count: int) -> dict[str, Any]:
    """Seed the ledger from the outline's major beats.

    Major beats are the series' long-arc suspense lines: the outline's beat-gap
    rule guarantees each payoff is set up within three episodes, so the planted
    episode is a structural estimate (payoff minus the plant window, floored at
    one) that later advance/resolve actions refine with real evidence.
    """
    hooks: list[dict[str, Any]] = []
    for beat in outline.get("beats", []):
        if not isinstance(beat, dict) or beat.get("weight") != "major":
            continue
        payoff_episode = beat.get("episode")
        if not isinstance(payoff_episode, int) or payoff_episode < 1:
            continue
        planted = max(1, payoff_episode - SEED_PLANT_WINDOW)
        hooks.append({
            "hook_id": next_hook_id(hooks),
            "name": f"{beat.get('type', '悬念')}：{str(beat.get('setup', ''))[:20]}",
            "kind": "plot",
            "status": "open",
            "planted_episode": planted,
            "last_advanced_episode": planted,
            "timing": timing_for_payoff_episode(payoff_episode, episode_count),
            "target_payoff_episode": payoff_episode,
            "expected_payoff": str(beat.get("payoff", ""))[:80] or None,
            "evidence_history": [],
        })
    return {
        "schema_version": "1.0",
        "project_id": project_id,
        "ledger_version": 1,
        "hooks": hooks,
    }


# ------------------------------------------------------------- evidence echo

_CARRIER_SUFFIX = re.compile(
    r"(?:的|之)?(?:台词|对白|画面|动作|问话|沉默|眼神|神态|表情|反应|镜头|声音|音效|物件|道具"
    r"|信息|变化|状态|瞬间|样子|行为|场景|桥段|细节)$"
)
_STOP_CHARS = set("的了在是有和与及中上下对把被")


def evidence_echoes(surface: str, carrier: str) -> bool:
    """Whether a declared evidence carrier lands in the episode surface.

    A full-phrase echo counts immediately. Otherwise at least two meaningful
    contiguous fragments must land, so scattered shared characters or a name
    cannot prove that the promised action happened.
    """
    carrier = (carrier or "").strip()
    if not carrier:
        return False
    if carrier in surface:
        return True
    core = _CARRIER_SUFFIX.sub("", carrier).strip()
    if len(core) < 2:
        return False
    fragments = [
        core[index:index + 2]
        for index in range(len(core) - 1)
        if not any(char in _STOP_CHARS for char in core[index:index + 2])
    ]
    hits = sum(1 for fragment in fragments if fragment in surface)
    if hits >= max(1, min(2, len(fragments))):
        return True
    content_chars = [char for char in core if char not in _STOP_CHARS]
    if len(content_chars) < 3:
        return False
    for window_size in range(min(4, len(content_chars)), 1, -1):
        for index in range(len(content_chars) - window_size + 1):
            fragment = "".join(content_chars[index:index + window_size])
            if fragment in surface:
                return window_size >= 3 or len(content_chars) == 3
    return False


# -------------------------------------------------------------- derivation

def derive_hook_ledger(
    ledger: dict[str, Any], script: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Evolve the ledger deterministically from per-episode contract hook actions.

    Returns the next ledger and a list of hard errors. A failed derivation
    must not be committed.
    """
    current = {hook["hook_id"]: copy.deepcopy(hook) for hook in ledger.get("hooks", [])}
    errors: list[str] = []
    for episode in ordered_episodes(script):
        ep = episode.get("ep")
        label = f"第 {ep} 集"
        contract = episode.get("contract")
        if not isinstance(contract, dict):
            continue
        surface = surface_of_episode(episode)
        for action in contract.get("hookActions", []):
            if not isinstance(action, dict):
                continue
            kind = action.get("action")
            hook_id = str(action.get("hookId", "")).strip()
            carriers = [str(item).strip() for item in action.get("evidence", []) if str(item).strip()]
            note = str(action.get("description", "")).strip() or None

            if kind == "open":
                if hook_id != "[new]":
                    errors.append(f"{label}：open 动作的 hookId 必须是 [new]（收到 {hook_id}）")
                    continue
                new_id = next_hook_id(list(current.values()))
                current[new_id] = {
                    "hook_id": new_id, "name": note or f"第 {ep} 集新开悬念", "kind": "plot",
                    "status": "open", "planted_episode": ep, "last_advanced_episode": ep,
                    "timing": "mid-arc", "target_payoff_episode": None, "expected_payoff": None,
                    "evidence_history": [{"episode": ep, "action": "open", "carriers": carriers}],
                }
                continue

            if kind not in {"advance", "resolve", "defer"}:
                errors.append(f"{label}：未知 hook 动作 {kind}")
                continue
            target = current.get(hook_id)
            if target is None:
                errors.append(f"{label}：hook 动作引用了台账中不存在的 {hook_id}")
                continue
            if target["status"] == "resolved":
                errors.append(f"{label}：已收束的 hook {hook_id} 不能再次 advance/resolve/defer")
                continue
            if kind in {"advance", "resolve"}:
                if not 1 <= len(carriers) <= 3:
                    errors.append(f"{label}：hook {hook_id}（{kind}）必须声明 1-3 个证据载体")
                    continue
                character_names = _episode_character_names(episode)
                invalid = [
                    carrier for carrier in carriers
                    if not hook_evidence_is_concrete(carrier, character_names)
                ]
                if invalid:
                    errors.append(
                        f"{label}：hook {hook_id}（{kind}）的 evidence 不能用单字、角色名或角色 ID 充数："
                        f"{'、'.join(invalid)}"
                    )
                    continue
                missing = [carrier for carrier in carriers if not evidence_echoes(surface, carrier)]
                if missing:
                    errors.append(
                        f"{label}：hook {hook_id}（{kind}）承诺的证据载体未在正文落地：{'、'.join(missing)}"
                    )
                    continue
            if kind == "advance":
                target["status"] = "progressing"
            elif kind == "resolve":
                target["status"] = "resolved"
                target["resolved_episode"] = ep
            else:
                target["status"] = "deferred"
            target["last_advanced_episode"] = ep
            target["evidence_history"].append({
                "episode": ep, "action": kind, "carriers": carriers, "note": note,
            })

    next_ledger = {
        "schema_version": "1.0",
        "project_id": ledger.get("project_id"),
        "ledger_version": int(ledger.get("ledger_version", 0)) + 1,
        "hooks": sorted(current.values(), key=lambda hook: hook["hook_id"]),
    }
    return next_ledger, errors


# ---------------------------------------------------------------- health

def frontier_episode(ledger: dict[str, Any]) -> int:
    return max(
        (hook.get("last_advanced_episode", 0) for hook in ledger.get("hooks", [])),
        default=0,
    )


def hook_health(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    hooks = [hook for hook in ledger.get("hooks", []) if isinstance(hook, dict)]
    active = [hook for hook in hooks if hook.get("status") in {"open", "progressing"}]
    if len(active) > MAX_ACTIVE_HOOKS:
        warnings.append({
            "severity": "warning", "gate": "hook-capacity",
            "detail": f"活跃 hook 共 {len(active)} 个（上限 {MAX_ACTIVE_HOOKS}）。先推进、回收或延后既有债务，再开新坑",
        })
    frontier = frontier_episode(ledger)
    for hook in hooks:
        if hook.get("status") not in {"open", "progressing"}:
            continue
        dormancy = frontier - int(hook.get("last_advanced_episode", frontier))
        age = frontier - int(hook.get("planted_episode", frontier))
        profile = HOOK_TIMING_PROFILES.get(hook.get("timing", ""), HOOK_TIMING_PROFILES["mid-arc"])
        if dormancy >= profile["stale_dormancy"]:
            warnings.append({
                "severity": "warning", "gate": "hook-stale",
                "detail": f"{hook['hook_id']}「{hook.get('name', '')}」已 {dormancy} 集未推进（timing={hook.get('timing')}），进入休眠区",
            })
        if age >= profile["overdue_age"]:
            warnings.append({
                "severity": "warning", "gate": "hook-overdue",
                "detail": f"{hook['hook_id']}「{hook.get('name', '')}」已开 {age} 集未收束（timing={hook.get('timing')}），接近逾期",
            })
    opens = sum(
        1 for hook in hooks
        if any(entry.get("action") == "open" for entry in hook.get("evidence_history", []))
        and hook.get("planted_episode") == frontier
    )
    frontier_resolves = sum(
        1 for hook in hooks
        for entry in hook.get("evidence_history", [])
        if entry.get("action") == "resolve" and entry.get("episode") == frontier
    )
    older_debt = [hook for hook in active if hook.get("planted_episode", frontier) < frontier]
    if opens >= 2 and frontier_resolves == 0 and older_debt:
        warnings.append({
            "severity": "warning", "gate": "hook-burst",
            "detail": f"第 {frontier} 集新开 {opens} 个 hook 且零回收，同时存在更早的未收束债务。新开伏笔时尽量配套回收旧伏笔",
        })
    return warnings


def completion_debt(ledger: dict[str, Any], episode_count: int) -> list[dict[str, Any]]:
    """Unresolved hooks that block completion.

    Hooks planted in the final episode are exempt: they are the series-level
    emotional hook, and their adequacy is judged by the series audit's ending
    review, not by the ledger.
    """
    return [
        hook for hook in ledger.get("hooks", [])
        if hook.get("status") in {"open", "progressing", "deferred"}
        and int(hook.get("planted_episode", episode_count)) < episode_count
    ]
