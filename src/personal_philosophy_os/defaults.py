"""Public, synthetic defaults used to initialize a Vault."""

from __future__ import annotations

from datetime import date
from typing import Any

DEFAULT_ROOTS: list[dict[str, Any]] = [
    {
        "id": "root-00",
        "question_zh": "待归区：现在还不知道它属于哪里",
        "question_en": "Unclassified: where does this belong?",
        "unclassified": True,
        "enabled": True,
    },
    {
        "id": "root-01",
        "question_zh": "我是谁，我愿意成为什么样的人？",
        "question_en": "Who am I, and who am I willing to become?",
        "unclassified": False,
        "enabled": True,
    },
    {
        "id": "root-02",
        "question_zh": "我如何与他人相处，同时不失去自己？",
        "question_en": "How do I relate to others without losing myself?",
        "unclassified": False,
        "enabled": True,
    },
    {
        "id": "root-03",
        "question_zh": "我如何面对痛苦、不确定和失去？",
        "question_en": "How do I face pain, uncertainty, and loss?",
        "unclassified": False,
        "enabled": True,
    },
    {
        "id": "root-04",
        "question_zh": "我如何选择，并承担选择的代价？",
        "question_en": "How do I choose and carry the cost of my choice?",
        "unclassified": False,
        "enabled": True,
    },
    {
        "id": "root-05",
        "question_zh": "我如何成长、行动和修正自己？",
        "question_en": "How do I grow, act, and revise myself?",
        "unclassified": False,
        "enabled": True,
    },
]


def default_vault_config() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "engine_family": "root-question-os",
        "rollout_mode": "active",
        "locale": "zh-CN",
        "owner": {"id": "person:self", "display_name": "我"},
        "policies": {
            "unclassified_root": "root-00",
            "max_secondary_roots": 2,
            "human_confirmation_required": True,
            "default_read_only": True,
        },
    }


def demo_records() -> dict[str, list[dict[str, Any]]]:
    today = date(2026, 1, 15).isoformat()
    cards = [
        {
            "schema_version": 1,
            "id": "card-0001",
            "kind": "value",
            "subject_id": "person:self",
            "text": "做选择时，我愿意先写下自己能够承担的代价。",
            "status": "confirmed",
            "evidence_grade": "A",
            "created_at": today,
            "synthetic": True,
        },
        {
            "schema_version": 1,
            "id": "card-0002",
            "kind": "view",
            "subject_id": "person:self",
            "text": "帮助别人不等于替别人承担全部责任。",
            "status": "confirmed",
            "evidence_grade": "A",
            "created_at": today,
            "synthetic": True,
        },
        {
            "schema_version": 1,
            "id": "card-0003",
            "kind": "decision",
            "subject_id": "person:self",
            "text": "先做一个可验证的小版本，再决定是否扩大投入。",
            "status": "confirmed",
            "evidence_grade": "A",
            "created_at": today,
            "synthetic": True,
        },
        {
            "schema_version": 1,
            "id": "card-0004",
            "kind": "reflection",
            "subject_id": "person:self",
            "text": "结果不好不一定说明当时的判断错误，要回到当时的信息。",
            "status": "confirmed",
            "evidence_grade": "A",
            "created_at": today,
            "synthetic": True,
        },
        {
            "schema_version": 1,
            "id": "card-0005",
            "kind": "view",
            "subject_id": "person:self",
            "text": "有些事情我还不知道该放在哪里，暂时不分类也可以。",
            "status": "confirmed",
            "evidence_grade": "A",
            "created_at": today,
            "synthetic": True,
        },
    ]
    mappings = [
        _mapping("card-0001", "root-04", ["root-01"], "选择与承担", today),
        _mapping("card-0002", "root-02", [], "关系中的责任边界", today),
        _mapping("card-0003", "root-05", ["root-04"], "用行动验证选择", today),
        _mapping("card-0004", "root-05", ["root-04"], "根据当时信息修正判断", today),
        _mapping("card-0005", "root-00", [], "证据不足，保留不知道", today),
    ]
    principles = [
        {
            "schema_version": 1,
            "id": "principle-001",
            "version": 1,
            "status": "confirmed",
            "statement": "选择之前先看自己愿意承担什么代价。",
            "primary_root": "root-04",
            "secondary_roots": ["root-01"],
            "evidence_card_ids": ["card-0001"],
            "conditions": "存在多个可行选项且需要本人承担后果时",
            "extreme_cost": "把所有事情都算成代价会导致迟迟不行动",
            "opposing_principle_ids": [],
            "case_ids": [],
            "confirmed_by": "person:self",
            "created_at": today,
            "synthetic": True,
        },
        {
            "schema_version": 1,
            "id": "principle-002",
            "version": 1,
            "status": "confirmed",
            "statement": "帮助可以有边界，责任仍要回到责任人。",
            "primary_root": "root-02",
            "secondary_roots": [],
            "evidence_card_ids": ["card-0002"],
            "conditions": "对方有能力为自己的行动负责时",
            "extreme_cost": "机械强调边界可能忽略紧急援助",
            "opposing_principle_ids": [],
            "case_ids": ["case-001"],
            "confirmed_by": "person:self",
            "created_at": today,
            "synthetic": True,
        },
    ]
    cases = [
        {
            "schema_version": 1,
            "id": "case-001",
            "version": 1,
            "status": "confirmed",
            "subject_ids": ["person:self", "person:friend"],
            "primary_root": "root-02",
            "secondary_roots": [],
            "fact_summary": "一位虚构朋友请求长期代办本应由其完成的事项。",
            "responsibility": "本人决定是否提供有限帮助；朋友负责完成自己的事项。",
            "boundary": "可以说明方法，不持续替代执行。",
            "motivation": "关心与避免冲突同时存在。",
            "cost": "全部代办会形成依赖；完全拒绝会损失必要支持。",
            "action": "提供一次方法说明并约定边界。",
            "result": "synthetic-demo",
            "transfer_signal": "帮助逐渐变成长期替代时",
            "failure_condition": "对方处于无法自助的紧急状态时不适用",
            "principle_ids": ["principle-002"],
            "confirmed_by": "person:self",
            "created_at": today,
            "synthetic": True,
        }
    ]
    reflections = [
        {
            "schema_version": 1,
            "id": "reflection-001",
            "version": 1,
            "status": "confirmed",
            "facts_known_then": "小版本可在一周内得到反馈。",
            "judgment_then": "先验证再扩大投入。",
            "action": "完成一个最小演示。",
            "expected_result": "确认是否值得继续。",
            "actual_result": "反馈不足，暂不扩大。",
            "what_held": "用低成本获得了有效信息。",
            "what_distorted": "样本量太小，不能推断长期需求。",
            "revision_proposal": "后续验证应预先定义最小样本量。",
            "principle_ids": [],
            "confirmed_by": "person:self",
            "created_at": today,
            "synthetic": True,
        }
    ]
    external_sources = [
        {
            "schema_version": 1,
            "id": "source-001",
            "version": 1,
            "source": "fictional:field-notes",
            "source_text": "Separate what can be influenced from what cannot.",
            "agent_interpretation": "区分可以介入与无法控制的部分。",
            "owner_interpretation": "",
            "root_ids": ["root-02", "root-04"],
            "principle_ids": ["principle-002"],
            "relationship": "tool",
            "status": "candidate",
            "created_at": today,
            "synthetic": True,
        }
    ]
    return {
        "cards": cards,
        "mappings": mappings,
        "verdicts": [],
        "principles": principles,
        "cases": cases,
        "reflections": reflections,
        "external_sources": external_sources,
    }


def _mapping(
    card_id: str,
    primary_root: str,
    secondary_roots: list[str],
    reason: str,
    created_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "card_id": card_id,
        "primary_root": primary_root,
        "secondary_roots": secondary_roots,
        "candidate_roots": [],
        "status": "confirmed",
        "mapped_by": "person:self",
        "confirmed_by": "person:self",
        "reason": reason,
        "version": 1,
        "created_at": created_at,
        "synthetic": True,
    }
