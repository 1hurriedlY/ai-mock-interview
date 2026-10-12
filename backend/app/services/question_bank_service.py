# -*- coding: utf-8 -*-
"""题库服务：面试组卡时优先从题库选题，AI 现场生成的好题回填沉淀。

双轨策略：
- 组卡：按 岗位/角色/难度/学历 从题库取 approved 题；每阶段数量达标才走题库，
  否则整体回退 QuestionAgent 现场生成（pipeline 无感知）。
- 回填：AI 现场生成的题卡按文本哈希去重后以 draft 状态入库，待管理员审核。
- 冷却：选题按 used_count / last_used_at 升序，避免同一用户连续两场见原题。
"""
import hashlib
import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import QuestionBank

logger = logging.getLogger(__name__)

# 每阶段需要的题量（与 QuestionAgent 题卡规格对齐的最低要求）
STAGE_NEED = {"opening": 1, "basic": 2, "deep": 2, "stress": 1, "closing": 1}
STAGES = list(STAGE_NEED.keys())


def content_hash(text: str) -> str:
    """题目文本哈希（去重用）：去空白后 sha256。"""
    normalized = "".join(str(text or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_card_from_bank(
    db: Session,
    *,
    job_title: str,
    role: str,
    difficulty: str,
    education: str,
    resume_skills: list[str] | None = None,
) -> dict | None:
    """尝试从题库组一张完整题卡；任一阶段数量不足则返回 None（回退 AI 生成）。

    匹配规则：role / difficulty 精确，education 为 any 或等于本场；
    job_tag 为空视为通用题，否则与岗位关键词或简历技能命中（LIKE）。
    选中题按 used_count / last_used_at 升序（冷却降权）。
    """
    stages: dict[str, list[dict]] = {}
    chosen_ids: list[int] = []
    kw = (job_title or "").strip()

    for stage in STAGES:
        need = STAGE_NEED[stage]
        stmt = (
            select(QuestionBank)
            .where(
                QuestionBank.stage == stage,
                QuestionBank.role == role,
                QuestionBank.difficulty == difficulty,
                QuestionBank.status == "approved",
                QuestionBank.education.in_(["any", education or "any"]),
            )
            .order_by(
                QuestionBank.used_count.asc(),
                func.coalesce(QuestionBank.last_used_at, QuestionBank.created_at).asc(),
            )
        )
        rows = db.scalars(stmt).all()
        if kw:
            hits = [q for q in rows if not q.job_tag or kw in q.job_tag or q.job_tag in kw]
        else:
            hits = [q for q in rows if not q.job_tag]
        if len(hits) < need and resume_skills:
            for q in rows:
                if q in hits:
                    continue
                if any(sk and sk in q.question for sk in resume_skills if sk):
                    hits.append(q)
        hits = hits[:need]
        if len(hits) < need:
            return None
        stages[stage] = [
            {"question": q.question, "reference": q.reference or ""} for q in hits
        ]
        chosen_ids.extend(q.id for q in hits)

    # 选中题计数 +1（冷却降权依据）
    now = datetime.now()
    for qid in chosen_ids:
        q = db.get(QuestionBank, qid)
        if q:
            q.used_count = (q.used_count or 0) + 1
            q.last_used_at = now
    db.commit()

    return {"stages": stages}


def backfill_from_card(
    db: Session,
    card: dict,
    *,
    role: str,
    difficulty: str,
    education: str = "any",
    job_title: str = "",
) -> int:
    """把 AI 现场生成的题卡按哈希去重后以 draft 入库，返回新增条数。"""
    stages = (card or {}).get("stages") or {}
    added = 0
    now = datetime.now()
    for stage in STAGES:
        val = stages.get(stage)
        items = val if isinstance(val, list) else ([val] if isinstance(val, dict) else [])
        for item in items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("question") or "").strip()
            if not text:
                continue
            h = content_hash(text)
            exists = db.scalar(
                select(func.count(QuestionBank.id)).where(QuestionBank.content_hash == h)
            )
            if exists:
                continue
            db.add(
                QuestionBank(
                    stage=stage,
                    role=role,
                    difficulty=difficulty,
                    education=education,
                    job_tag=(job_title or "")[:255],
                    question=text,
                    reference=str(item.get("reference") or ""),
                    source="ai_generated",
                    status="draft",
                    content_hash=h,
                    created_at=now,
                )
            )
            added += 1
    if added:
        db.commit()
    return added
