#!/usr/bin/env python3
"""Deterministic screenplay quality gates for the governed short-drama pipeline.

These checks complement the short-drama kernel engine's ten gates: the engine verifies
the script is complete and reconciled with upstream, this module verifies the
episode drama contract and craft-level signals that are cheap to check
without a model. Structural contract failures are errors; craft signals are
warnings (per the suite's gate policy: an over-eager gate is worse than no
gate).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------- surfaces

def surface_of_episode(episode: dict[str, Any]) -> str:
    parts: list[str] = []
    for scene in episode.get("scenes", []):
        if not isinstance(scene, dict):
            continue
        for beat in scene.get("flow", []):
            if not isinstance(beat, dict):
                continue
            if isinstance(beat.get("action"), str) and beat["action"].strip():
                parts.append(beat["action"].strip())
            if isinstance(beat.get("line"), str) and beat["line"].strip():
                parts.append(f"{beat.get('speaker', '')}: {beat['line']}".strip())
            if isinstance(beat.get("delivery"), str) and beat["delivery"].strip():
                parts.append(beat["delivery"].strip())
    return "\n".join(parts)


def ordered_episodes(script: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (item for item in script.get("episodes", []) if isinstance(item, dict)),
        key=lambda item: item.get("ep") if isinstance(item.get("ep"), int) else 0,
    )


_CHARACTER_ID = re.compile(r"^(?:CHAR|C)-?\d+$", re.IGNORECASE)


def hook_evidence_is_concrete(value: str, character_names: set[str] | None = None) -> bool:
    """Reject evidence labels that cannot identify an observable carrier."""
    text = re.sub(r"[\s，。！？、；：,.!?;:]", "", (value or "").strip())
    if len(text) < 2 or _CHARACTER_ID.fullmatch(text):
        return False
    if character_names and text in character_names:
        return False
    return True


def _episode_character_names(episode: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for scene in episode.get("scenes", []):
        if not isinstance(scene, dict):
            continue
        names.update(str(item).strip() for item in scene.get("characters", []) if str(item).strip())
        for beat in scene.get("flow", []):
            if isinstance(beat, dict) and isinstance(beat.get("speaker"), str):
                names.add(beat["speaker"].strip())
    return names

# An emotional hook must be a concrete audience question about a relationship,
# danger, identity, sacrifice, or choice. Three tiers, from most to least
# strict, so valid fate-uncertainty questions are not rejected:
# 1. question form (interrogative marker or explicit interrogative lead);
# 2. theme vocabulary;
# 3. fate-uncertainty fallback for questions phrased without theme words.
_QUESTION_FORM = re.compile(
    r"[?？吗呢么]|观众(?:追问|想知道|会问)|到底.{1,6}|能否.{1,6}|是否.{1,6}|会不会.{1,6}"
    r"|为什么.{1,6}|为何.{1,6}|谁.{1,6}(?:会|能|要|还)|什么.{1,6}(?:会|能|要|还)"
    r"|\b(?:who|what|why|will|would|can|could|should|whether)\b",
    re.IGNORECASE,
)
_THEME_WORDS = re.compile(
    r"关系|相信|信任|背叛|盟友|敌人|爱|恨|救|危险|生死|活|死|出口|身份|秘密|真相|牺牲|代价"
    r"|选择|决定|交给|离开|留下|说出|隐瞒|公开|是谁|什么人|来路|底细|看穿|察觉|揭穿|暴露"
    r"|除掉|处置|对付|知道太多|骗|欺骗|做假|伪造|威胁|报复|陷害"
    r"|relationship|trust|betray|ally|enemy|love|hate|save|danger|survive|die|escape"
    r"|identity|secret|truth|sacrifice|cost|choose|choice|decide|leave|stay|reveal|hide",
    re.IGNORECASE,
)
_FATE_UNCERTAINTY = re.compile(
    r"还能|能不能|能否|会不会|该不该|要不要|究竟|到底|凭什么|怎么办|怎么活|怎么死|如何"
    r"|怎样|拿什么|怎么才|自保|保命|性命|罪名|灭顶|杀身|下场|还是|冒险|来得及|撑得住|撑不住",
)


def has_concrete_audience_question(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    if not _QUESTION_FORM.search(text):
        return False
    if _THEME_WORDS.search(text):
        return True
    return bool(_FATE_UNCERTAINTY.search(text))


# ------------------------------------------------------- delivery strategy

# delivery must name an executable strategy, not an emotion or a volume.
# Full-match only: a delivery like "声音很轻，却没商量" carries a strategy and
# passes; a bare "低声" gives the actor nothing to do.
_EMOTION_ONLY_DELIVERY = re.compile(
    r"^(?:愤怒|生气|激动|平静|冷静|冷漠|温柔|严肃|委屈|尴尬|得意|轻蔑|嘲讽|哽咽|颤抖"
    r"|震惊|疑惑|害怕|恐惧|紧张|高兴|开心|伤心|难过|崩溃|不耐烦|无奈|苦笑|冷笑|淡淡"
    r"|冷冷|缓缓|低声|轻声|大声|急促|失神|犹豫|坚定|坚决|迟疑"
    r")(?:地)?[，。！？、\s]*$",
)


def check_delivery_strategy(episode: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    label = f"第 {episode.get('ep')} 集"
    for scene_index, scene in enumerate(episode.get("scenes", []), start=1):
        if not isinstance(scene, dict):
            continue
        for beat_index, beat in enumerate(scene.get("flow", []), start=1):
            if not isinstance(beat, dict):
                continue
            delivery = beat.get("delivery")
            if isinstance(delivery, str) and delivery.strip() and _EMOTION_ONLY_DELIVERY.match(delivery.strip()):
                issues.append({
                    "severity": "warning", "gate": "delivery-strategy",
                    "detail": f"{label} 场 {scene_index} 拍 {beat_index}：delivery「{delivery.strip()}」只有情绪没有策略，换成试探、逼问、划界等可执行动作",
                })
    return issues


# ------------------------------------------------- cross-episode repetition

_BEHAVIOR_TOKENS = [
    "进入", "离开", "走出", "回到", "打开", "关上", "拿出", "放下", "递上", "接过",
    "检查", "查看", "翻看", "威胁", "警告", "逼近", "后退", "抓住", "按住", "跪下",
    "起身", "转身", "抬头", "低头", "沉默", "摇头", "点头", "攥紧", "拍", "敲",
    "扔", "撕", "捡", "扶", "坐下", "站起", "对视", "拦住", "推", "拽", "指",
    "吼", "压低", "挡住", "躲开", "冲到", "转身就走", "翻出",
]


def _han_ngrams(text: str, size: int = 6) -> set[str]:
    cleaned = re.sub(r"[\s\n\r]", "", text)
    return {
        cleaned[index:index + size]
        for index in range(len(cleaned) - size + 1)
        if re.fullmatch(r"[\u4e00-\u9fff]{%d}" % size, cleaned[index:index + size])
    }


def _behavior_signature(surface: str) -> set[str]:
    return {token for token in _BEHAVIOR_TOKENS if token in surface}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def check_cross_episode_repeat(
    episode: dict[str, Any], previous_surfaces: list[str],
) -> list[dict[str, Any]]:
    if not previous_surfaces:
        return []
    issues: list[dict[str, Any]] = []
    label = f"第 {episode.get('ep')} 集"
    surface = surface_of_episode(episode)
    current_ngrams = _han_ngrams(surface)
    for previous in previous_surfaces:
        previous_ngrams = _han_ngrams(previous)
        shared = {phrase for phrase in current_ngrams if phrase in previous_ngrams}
        if len(shared) >= 3:
            sample = "、".join(sorted(shared)[:5])
            issues.append({
                "severity": "warning", "gate": "cross-episode-repeat",
                "detail": f"{label} 有 {len(shared)} 个镜头表面短语与近期剧集重复（{sample}…），检查是否在用上一集的旧镜头写法凑时长",
            })
            break
    signature = _behavior_signature(surface)
    for previous in previous_surfaces:
        overlap = _jaccard(signature, _behavior_signature(previous))
        if len(signature) >= 3 and overlap >= 0.6:
            sample = "、".join(sorted(signature)[:5])
            issues.append({
                "severity": "warning", "gate": "behavior-repeat",
                "detail": f"{label} 动作节拍与近期剧集有 {round(overlap * 100)}% 的行为词重合（{sample}…），同一套动作在重复",
            })
            break
    return issues


# --------------------------------------------------------------- AI tells

_SURPRISE_MARKERS = ["仿佛", "忽然", "竟然", "猛地", "猛然", "不禁", "宛如", "骤然", "蓦地"]
_HEDGE_WORDS = ["似乎", "可能", "或许", "大概", "某种程度上", "一定程度上", "在某种意义上"]
_TRANSITION_WORDS = ["然而", "不过", "与此同时", "另一方面", "尽管如此", "话虽如此", "但值得注意的是"]
_META_PATTERNS = [
    re.compile(r"接下来[，,]?(?:就是|将会|即将)"),
    re.compile(r"(?:后面|之后)[，,]?(?:会|将|还会)"),
    re.compile(r"(?:故事|剧情)(?:发展)?到了"),
    re.compile(r"读者[，,]?(?:可能|应该|也许)"),
    re.compile(r"我们[，,]?(?:可以|不妨|来看)"),
]
_REPORT_TERMS = [
    "核心动机", "信息边界", "信息落差", "核心风险", "利益最大化", "当前处境",
    "行为约束", "性格过滤", "情绪外化", "锚定效应", "沉没成本", "认知共鸣",
]
_SERMON_WORDS = ["显然", "毋庸置疑", "不言而喻", "众所周知", "不难看出"]
_COLLECTIVE_SHOCK = [
    re.compile(r"(?:全场|众人|所有人|在场的人)[，,]?(?:都|全|齐齐|纷纷)?(?:震惊|惊呆|倒吸凉气|目瞪口呆|哗然|惊呼)"),
    re.compile(r"(?:全场|一片)[，,]?(?:寂静|哗然|沸腾|震动)"),
]


def _count_all(text: str, words: list[str]) -> dict[str, int]:
    return {word: text.count(word) for word in words if text.count(word) > 0}


def check_ai_tells(episode: dict[str, Any]) -> list[dict[str, Any]]:
    surface = surface_of_episode(episode)
    if not surface:
        return []
    issues: list[dict[str, Any]] = []
    label = f"第 {episode.get('ep')} 集"

    marker_counts = _count_all(surface, _SURPRISE_MARKERS)
    marker_total = sum(marker_counts.values())
    marker_limit = max(2, len(surface) // 2000)
    if marker_total > marker_limit:
        detail = "、".join(f"「{word}」×{count}" for word, count in marker_counts.items())
        issues.append({
            "severity": "warning", "gate": "surprise-marker-density",
            "detail": f"{label} 转折/惊讶标记词共 {marker_total} 次（上限 {marker_limit} 次）：{detail}。用具体动作或感官变化传递突然性",
        })

    hedge_total = sum(text_count for text_count in _count_all(surface, _HEDGE_WORDS).values())
    hedge_density = hedge_total / max(1, len(surface) / 1000)
    if hedge_density > 3:
        issues.append({
            "severity": "warning", "gate": "hedge-density",
            "detail": f"{label} 套话词密度 {round(hedge_density, 1)} 次/千字（阈值 3），语气过于模糊。删掉「似乎/可能」直接描述状态",
        })

    transition_counts = _count_all(surface, _TRANSITION_WORDS)
    repeated = {word: count for word, count in transition_counts.items() if count >= 3}
    if repeated:
        detail = "、".join(f"「{word}」×{count}" for word, count in repeated.items())
        issues.append({
            "severity": "warning", "gate": "formulaic-transition",
            "detail": f"{label} 同一转折词重复：{detail}。用动作切入、时间跳跃或视角切换替代转折词",
        })

    for pattern in _META_PATTERNS:
        match = pattern.search(surface)
        if match:
            issues.append({
                "severity": "warning", "gate": "meta-narration",
                "detail": f"{label} 出现编剧旁白式表述：「{match.group(0)}…」。删除元叙事，让剧情自己展开",
            })
            break

    found_terms = [term for term in _REPORT_TERMS if term in surface]
    if found_terms:
        issues.append({
            "severity": "warning", "gate": "report-term",
            "detail": f"{label} 正文出现分析报告术语：{'、'.join(f'「{term}」' for term in found_terms)}。这些词属于工作语言，不属于画面",
        })

    found_sermons = [word for word in _SERMON_WORDS if word in surface]
    if found_sermons:
        issues.append({
            "severity": "warning", "gate": "sermon-word",
            "detail": f"{label} 出现说教词：{'、'.join(f'「{word}」' for word in found_sermons)}。让观众从情节中自己判断",
        })

    for pattern in _COLLECTIVE_SHOCK:
        match = pattern.search(surface)
        if match:
            issues.append({
                "severity": "warning", "gate": "collective-shock",
                "detail": f"{label} 出现集体反应套话：「{match.group(0)}」。改写成 1-2 个具体角色的身体反应",
            })
            break

    if re.search(r"不是[^，。！？\n]{0,30}[，,]?\s*而是", surface):
        issues.append({
            "severity": "warning", "gate": "forbidden-pattern",
            "detail": f"{label} 出现「不是……而是……」句式，改用直述句",
        })

    return issues


# ---------------------------------------------------------- payoff rotation

def check_payoff_rotation(
    episode: dict[str, Any], previous_types: list[set[str]],
) -> list[dict[str, Any]]:
    types = {str(item) for item in episode.get("beatsClaimed", []) if isinstance(item, str) and item}
    if not types or not previous_types:
        return []
    if types & previous_types[-1]:
        return [{
            "severity": "warning", "gate": "payoff-rotation",
            "detail": f"第 {episode.get('ep')} 集的爽点类型与上一集重复（{'、'.join(sorted(types & previous_types[-1]))}）。爽点类型应在最近几集轮换",
        }]
    return []


# ------------------------------------------------------------ contract gate

def _handoff_from_previous(previous: dict[str, Any] | None) -> dict[str, Any] | None:
    """Accept a handoff state or common cross-batch helper wrappers."""
    if not isinstance(previous, dict):
        return None
    wrapped = previous.get("handoff_state")
    if isinstance(wrapped, dict):
        return wrapped
    contract = previous.get("contract")
    if isinstance(contract, dict) and isinstance(contract.get("handoffState"), dict):
        return contract["handoffState"]
    episodes = ordered_episodes(previous)
    if episodes:
        final_contract = episodes[-1].get("contract")
        if isinstance(final_contract, dict) and isinstance(final_contract.get("handoffState"), dict):
            return final_contract["handoffState"]
    return previous


def validate_handoff_chain(
    script: dict[str, Any], previous: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    episodes = ordered_episodes(script)
    expected = _handoff_from_previous(previous)
    buckets = ("knowledge", "power", "relationship", "physical", "activeAction")
    for episode in episodes:
        contract = episode.get("contract") if isinstance(episode.get("contract"), dict) else {}
        incoming = contract.get("incomingState") if isinstance(contract.get("incomingState"), dict) else {}
        if expected is not None:
            for bucket in buckets:
                required = {str(item) for item in expected.get(bucket, []) if isinstance(item, str)}
                present = {str(item) for item in incoming.get(bucket, []) if isinstance(item, str)}
                missing = sorted(required - present)
                if missing:
                    errors.append(f"第 {episode.get('ep')} 集 incomingState.{bucket} 未承接：{'、'.join(missing)}")
        expected = contract.get("handoffState") if isinstance(contract.get("handoffState"), dict) else None
    return errors


def validate_episode_contracts(script: dict[str, Any]) -> list[str]:
    """Structural gate for per-episode contracts. Returns hard errors."""
    errors: list[str] = []
    sys.path.insert(0, str(SCRIPTS_DIR))
    from schema_validator import validate_file  # pylint: disable=import-outside-toplevel
    schema_path = ROOT / "schemas" / "episode-contract.schema.json"
    for episode in ordered_episodes(script):
        label = f"第 {episode.get('ep')} 集"
        contract = episode.get("contract")
        if not isinstance(contract, dict):
            errors.append(f"{label} 缺少 contract")
            continue
        errors.extend(f"{label}：{item}" for item in validate_file(contract, schema_path, "episode-contract"))
        emotional_hook = contract.get("emotionalHook", "")
        if not has_concrete_audience_question(emotional_hook):
            errors.append(
                f"{label}：emotionalHook 必须是关于关系、危险、身份、牺牲或选择的具体观众疑问，"
                f"情绪标签或「下集揭晓」式空话无效"
            )
        character_names = _episode_character_names(episode)
        for action in contract.get("hookActions", []):
            if not isinstance(action, dict):
                continue
            if action.get("action") in {"advance", "resolve"}:
                evidence = action.get("evidence") if isinstance(action.get("evidence"), list) else []
                if not 1 <= len(evidence) <= 3:
                    errors.append(
                        f"{label}：hook 动作 {action.get('hookId')}（{action.get('action')}）"
                        f"必须声明 1-3 个画面可见的证据载体"
                    )
                invalid = [
                    str(item) for item in evidence
                    if not isinstance(item, str) or not hook_evidence_is_concrete(item, character_names)
                ]
                if invalid:
                    errors.append(
                        f"{label}：hook 动作 {action.get('hookId')} 的 evidence 不能用单字、角色名或角色 ID 充当证据载体："
                        f"{'、'.join(invalid)}"
                    )
        for permission in contract.get("informationPermissions", []):
            if not isinstance(permission, dict):
                continue
            seen: dict[str, str] = {}
            for bucket in ("known", "suspected", "mistaken", "unknown"):
                for item in permission.get(bucket, []):
                    if not isinstance(item, str):
                        continue
                    fact = item.strip()
                    if fact in seen and seen[fact] != bucket:
                        errors.append(
                            f"{label}：informationPermissions subject「{permission.get('subject')}」中"
                            f"同一事实「{fact}」不能同时属于 {seen[fact]} 与 {bucket}"
                        )
                    else:
                        seen[fact] = bucket
    return errors


# ----------------------------------------------------------------- driver

def run_script_quality(
    script: dict[str, Any], previous_scripts: list[dict[str, Any]] | None = None,
    canon: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    previous_scripts = previous_scripts or []
    issues: list[dict[str, Any]] = []
    episodes = ordered_episodes(script)
    if not episodes:
        return [{"severity": "error", "gate": "episodes", "detail": "script 没有 episodes"}]
    for message in validate_episode_contracts(script):
        issues.append({"severity": "error", "gate": "episode-contract", "detail": message})
    if isinstance(canon, dict):
        # Lazy import: canon imports this module, so it must stay runtime-only.
        from canon import claim_reveal_warnings  # pylint: disable=import-outside-toplevel
        for message in claim_reveal_warnings(canon, script):
            issues.append({"severity": "warning", "gate": "canon-reveal-missing", "detail": message})
    previous_surfaces: list[str] = []
    previous_types: list[set[str]] = []
    for script_ in previous_scripts:
        for item in ordered_episodes(script_):
            previous_surfaces.append(surface_of_episode(item))
            previous_types.append({
                str(value) for value in item.get("beatsClaimed", []) if isinstance(value, str) and value
            })
    recent_surfaces = previous_surfaces[-6:]
    for episode in episodes:
        issues.extend(check_delivery_strategy(episode))
        issues.extend(check_cross_episode_repeat(episode, recent_surfaces))
        issues.extend(check_ai_tells(episode))
        issues.extend(check_payoff_rotation(episode, previous_types))
        previous_types.append({
            str(value) for value in episode.get("beatsClaimed", []) if isinstance(value, str) and value
        })
    return issues


def render_quality_report(issues: list[dict[str, Any]]) -> str:
    errors = [item for item in issues if item.get("severity") == "error"]
    warnings = [item for item in issues if item.get("severity") != "error"]
    lines: list[str] = []
    for item in errors:
        lines.append(f"✗ [{item['gate']}] {item['detail']}")
    for item in warnings:
        lines.append(f"! [{item['gate']}] {item['detail']}")
    lines.append(f"error: {len(errors)}, warning: {len(warnings)}")
    return "\n".join(lines)
