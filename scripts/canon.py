#!/usr/bin/env python3
"""Deterministic canon for the governed short-drama pipeline.

Canon claims are story facts and world rules registered from development or
brief outputs. Per screenplay batch, deterministic claim gates protect the
audience-visible surface (leaks, prohibitions, unpaid bypasses) and canon
evolution settles claims whose facts land in the episode's authoritative
state. Models register claims and read the gates; they never hand-write
evolution results.
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent

try:
    from hook_ledger import evidence_echoes
    from script_quality import ordered_episodes, surface_of_episode
except ModuleNotFoundError:
    sys.path.insert(0, str(SCRIPTS_DIR))
    from hook_ledger import evidence_echoes
    from script_quality import ordered_episodes, surface_of_episode


_GENERALIZATION_SIGNALS = re.compile(r"配角|反派|组织|所有人|人人|每个人|任何人都|谁都|everyone|anyone")
_STRUCTURE_FIELDS = (
    "incomingState", "objective", "opposition", "causalEscalation",
    "localDramaticResult", "outgoingPressure", "handoffState",
    "emotionalHook", "endState",
)


def next_claim_id(claims: list[dict[str, Any]]) -> str:
    maximum = max(
        (int(match.group(1)) for claim in claims if (match := re.fullmatch(r"CAN-(\d{3})", str(claim.get("claim_id", ""))))),
        default=0,
    )
    if maximum >= 999:
        raise ValueError("canon claim ID space exhausted")
    return f"CAN-{maximum + 1:03d}"


def merge_registered_canon(canon: dict[str, Any], incoming: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Merge a registered canon document into the current one."""
    errors: list[str] = []
    existing_ids = {claim["claim_id"] for claim in canon.get("claims", [])}
    incoming_ids = [claim.get("claim_id") for claim in incoming.get("claims", [])]
    if len(incoming_ids) != len(set(incoming_ids)):
        errors.append("registered canon has duplicate claim ids")
    for claim_id in incoming_ids:
        if claim_id in existing_ids:
            errors.append(f"claim {claim_id} is already registered; supersede it first")
    if errors:
        return canon, errors
    merged = {
        "schema_version": "1.0",
        "project_id": canon.get("project_id"),
        "canon_version": int(canon.get("canon_version", 0)) + 1,
        "claims": [*copy.deepcopy(canon.get("claims", [])), *copy.deepcopy(incoming.get("claims", []))],
        "candidates": copy.deepcopy(canon.get("candidates", [])),
    }
    return merged, []


# ------------------------------------------------------------------ gates

def _contract_text(episode: dict[str, Any]) -> str:
    contract = episode.get("contract")
    if not isinstance(contract, dict):
        return ""
    parts: list[str] = []
    for key in _STRUCTURE_FIELDS:
        value = contract.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            parts.extend(
                str(item) for bucket in value.values()
                for item in (bucket if isinstance(bucket, list) else [bucket])
            )
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    parts.extend(str(part) for part in item.values() if isinstance(part, (str, int)))
                elif isinstance(item, str):
                    parts.append(item)
    return "\n".join(parts)


def claim_gate_errors(canon: dict[str, Any], episode: dict[str, Any]) -> list[str]:
    """Hard claim gates over the audience-visible surface of one episode."""
    errors: list[str] = []
    ep = episode.get("ep")
    label = f"第 {ep} 集"
    visible = surface_of_episode(episode)
    contract_text = _contract_text(episode)
    for claim in canon.get("claims", []):
        if not isinstance(claim, dict) or claim.get("status") != "active":
            continue
        claim_id = claim.get("claim_id", "?")
        claim_type = claim.get("claim_type")
        content = str(claim.get("content", ""))
        visibility = claim.get("visibility") if isinstance(claim.get("visibility"), dict) else {}
        reader_known_from = visibility.get("reader_known_from")
        constraints = claim.get("constraints") if isinstance(claim.get("constraints"), dict) else {}

        if claim_type == "secret_truth" and (reader_known_from is None or reader_known_from > ep):
            if evidence_echoes(visible, content):
                errors.append(
                    f"{label}：canon {claim_id}（秘密真相）在读者揭示集 {reader_known_from or '未定'} 前泄露到可见正文"
                )
        if claim_type == "prohibition" and evidence_echoes(visible, content):
            errors.append(f"{label}：正文触碰了 canon 禁令 {claim_id}（{content}）")
        if claim_type in {"objective_rule", "institution_rule"}:
            authority = claim.get("authority") if isinstance(claim.get("authority"), dict) else {}
            requires_cost = [str(item) for item in constraints.get("requires_cost", [])]
            if authority.get("priority") == "hard" and requires_cost and evidence_echoes(visible, content):
                if not any(evidence_echoes(visible, cost) for cost in requires_cost):
                    errors.append(
                        f"{label}：正文动用了硬规则 {claim_id}（{content}）却没有支付声明代价"
                        f"（{'、'.join(requires_cost)}）"
                    )
        forbidden_uses = [str(item).strip() for item in constraints.get("forbidden_uses", []) if str(item).strip()]
        for forbidden_use in forbidden_uses:
            if evidence_echoes(visible, forbidden_use):
                errors.append(
                    f"{label}：正文触碰了 canon {claim_id} 的 forbidden_use（{forbidden_use}）"
                )
        if constraints.get("non_generalizable") is True and evidence_echoes(visible, content):
            if _GENERALIZATION_SIGNALS.search(contract_text):
                errors.append(f"{label}：canon {claim_id} 是不可泛化设定，正文/合同出现扩散信号")
    return errors


def claim_reveal_warnings(canon: dict[str, Any], script: dict[str, Any]) -> list[str]:
    """Warning when a claim scheduled for reader reveal this episode has no visible landing.

    Warning only: reveal adequacy is ultimately judged by the conformance
    audit; this deterministic signal catches silently dropped reveals before
    import reports them downstream.
    """
    warnings: list[str] = []
    for episode in ordered_episodes(script):
        ep = episode.get("ep")
        visible = surface_of_episode(episode)
        for claim in canon.get("claims", []):
            if not isinstance(claim, dict) or claim.get("status") != "active":
                continue
            reader_known_from = claim.get("visibility", {}).get("reader_known_from")
            if reader_known_from != ep:
                continue
            content = str(claim.get("content", ""))
            if not evidence_echoes(visible, content):
                warnings.append(
                    f"第 {ep} 集：canon {claim.get('claim_id')}（{content}）计划在本集向读者揭示，"
                    f"但正文没有可见落点；补上揭示场面，或在 canon 中调整 reader_known_from"
                )
    return warnings


# -------------------------------------------------------------- evolution

def derive_canon_updates(canon: dict[str, Any], script: dict[str, Any]) -> dict[str, Any]:
    """Settle claims and record unclaimed facts from an episode batch."""
    next_canon = copy.deepcopy(canon)
    claims = next_canon.get("claims", [])
    candidates = next_canon.get("candidates", [])
    existing_facts = {(item.get("fact"), item.get("source_episode")) for item in candidates if isinstance(item, dict)}
    known_claim_texts = [str(claim.get("content", "")) for claim in claims if isinstance(claim, dict)]

    for episode in ordered_episodes(script):
        ep = episode.get("ep")
        contract = episode.get("contract")
        if not isinstance(contract, dict):
            continue
        local_result = contract.get("localDramaticResult") if isinstance(contract.get("localDramaticResult"), dict) else {}
        state_text = "；".join([
            *[str(item) for item in contract.get("handoffState", {}).get("knowledge", []) if isinstance(item, str)],
            str(local_result.get("stateChange", "")),
            str(contract.get("endState", "")),
        ])
        permissions = contract.get("informationPermissions", [])
        for claim in claims:
            if not isinstance(claim, dict) or claim.get("status") != "active":
                continue
            content = str(claim.get("content", ""))
            visible = surface_of_episode(episode)
            if claim.get("claim_type") in {"secret_truth", "temporary_state"}:
                reader_known_from = claim.get("visibility", {}).get("reader_known_from")
                reveal_allowed = claim.get("claim_type") == "temporary_state" or (
                    isinstance(reader_known_from, int) and reader_known_from <= ep
                )
                if reveal_allowed and evidence_echoes(visible, content):
                    claim["status"] = "resolved"
                    claim["status_updated_at_episode"] = ep
            if isinstance(permissions, list):
                for permission in permissions:
                    if not isinstance(permission, dict):
                        continue
                    subject = str(permission.get("subject", "")).strip()
                    audience = str(permission.get("audience", "")).strip()
                    known_text = "；".join(
                        str(item) for item in permission.get("known", []) if isinstance(item, str)
                    )
                    if (
                        subject
                        and audience not in {"", "观众"}
                        and evidence_echoes(known_text, content)
                    ):
                        known_by = claim.setdefault("visibility", {}).setdefault("character_known_by", [])
                        if audience not in known_by:
                            known_by.append(audience)
        for fact in [str(item) for item in contract.get("handoffState", {}).get("knowledge", []) if isinstance(item, str)]:
            if not any(evidence_echoes(fact, content) for content in known_claim_texts):
                entry = (fact, ep)
                if entry not in existing_facts and fact not in {item[0] for item in existing_facts}:
                    candidates.append({"fact": fact, "source_episode": ep})
                    existing_facts.add(entry)
    next_canon["canon_version"] = int(next_canon.get("canon_version", 0)) + 1
    return next_canon


def refresh_canon(canon: dict[str, Any]) -> dict[str, Any]:
    """Promote recorded unclaimed facts into canon claims."""
    next_canon = copy.deepcopy(canon)
    claims = next_canon.get("claims", [])
    for candidate in next_canon.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        fact = str(candidate.get("fact", "")).strip()
        if not fact:
            continue
        claims.append({
            "claim_id": next_claim_id(claims),
            "domain": "world",
            "claim_type": "temporary_state",
            "content": fact,
            "scope": {"applies_to": [], "excludes": []},
            "authority": {"source": f"第 {candidate.get('source_episode')} 集正文事实", "priority": "soft"},
            "visibility": {"reader_known_from": candidate.get("source_episode"), "character_known_by": [], "hidden_from": []},
            "relations": {"conflicts_with": [], "resolves_by": None, "depends_on": []},
            "constraints": {"non_generalizable": False, "requires_cost": [], "forbidden_uses": []},
            "status": "active",
            "status_updated_at_episode": None,
            "evidence": [f"第 {candidate.get('source_episode')} 集交接事实"],
        })
    next_canon["candidates"] = []
    next_canon["canon_version"] = int(next_canon.get("canon_version", 0)) + 1
    return next_canon
