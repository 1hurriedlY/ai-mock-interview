"""Agent 流水线编排：面试状态机（题卡 → 逐阶段逐题推进 → 收尾）。

设计：
- 一次面试 = 一份题卡（Redis session:{id}:card）+ 一个推进游标
- 游标用 (stage_idx, question_idx) 定位当前题；阶段顺序与题内索引推进
- 每题两轮制：先读题 → 候选人作答 → 面试官决策
  - action=probe/followup → 停留在本题再追问一轮（最多追加 2 次追问）
  - action=next → 推进到下一题
  - action=finish → 提前收尾（返回 None 表示应结束面试）
- 阶段/题卡缓存读写走 redis_client，全部 try/except 降级 MySQL 语义（内存兜底）
"""
import json
import logging
from typing import Any, Optional

from ... import config
from ...redis_client import redis_client
from ..agents.interviewer_agent import InterviewerAgent, STAGE_NAMES

logger = logging.getLogger(__name__)

# 每道题最多允许的追问次数（probe/followup 达到后强制 next/finish）
MAX_PROBES_PER_QUESTION = 2


class PipelineError(RuntimeError):
    """流水线状态异常（题卡缺失、游标越界等）。"""


class InterviewPipeline:
    """单场面试的状态机。所有状态都挂在 session_id 上。"""

    def __init__(self, session_id: int, *, role: str = "technical",
                 resume_summary: str = "", resume_analysis: dict | None = None):
        self.session_id = session_id
        self.role = role
        self.resume_summary = resume_summary or _summarize(resume_analysis)
        self.interviewer = InterviewerAgent()

    # ---------- 状态读写 ----------
    def _load_card(self) -> dict:
        card = redis_client.get_question_card(self.session_id)
        if not card:
            raise PipelineError(f"会话 {self.session_id} 缺少题卡，请重新开始面试")
        return card

    def _save_card(self, card: dict) -> None:
        redis_client.set_question_card(self.session_id, card)

    def _load_state(self) -> dict:
        card = self._load_card()
        state = card.setdefault("_state", {})
        if "stage_idx" not in state:
            state.update({"stage_idx": 0, "question_idx": 0, "probes": 0})
            self._save_card(card)
        return state

    def _save_state(self, state: dict) -> None:
        card = self._load_card()
        card["_state"] = state
        self._save_card(card)

    # ---------- 题目定位 ----------
    def current(self) -> Optional[dict]:
        """返回当前题信息 {stage, stage_label, question, reference}；面试结束返回 None。"""
        card = self._load_card()
        stages = card.get("stages", {})
        state = card.get("_state") or {"stage_idx": 0, "question_idx": 0}
        stage_key = config.STAGES[state["stage_idx"]]
        questions = stages.get(stage_key) or []
        if state["question_idx"] >= len(questions):
            return None
        item = questions[state["question_idx"]]
        return {
            "stage": stage_key,
            "stage_label": STAGE_NAMES.get(stage_key, stage_key),
            "question": item.get("question", ""),
            "reference": item.get("reference", ""),
        }

    def next_question(self) -> Optional[dict]:
        """返回下一题信息（用于面试官决策时告知下一题）；无则 None。"""
        card = self._load_card()
        stages = card.get("stages", {})
        state = card.get("_state") or {"stage_idx": 0, "question_idx": 0}
        # 同一阶段内下一题
        stage_key = config.STAGES[state["stage_idx"]]
        questions = stages.get(stage_key) or []
        if state["question_idx"] + 1 < len(questions):
            item = questions[state["question_idx"] + 1]
            return {
                "stage": stage_key,
                "question": item.get("question", ""),
                "reference": item.get("reference", ""),
            }
        # 下一阶段第一题
        if state["stage_idx"] + 1 < len(config.STAGES):
            nxt = config.STAGES[state["stage_idx"] + 1]
            items = stages.get(nxt) or []
            if items:
                return {
                    "stage": nxt,
                    "question": items[0].get("question", ""),
                    "reference": items[0].get("reference", ""),
                }
        return None

    # ---------- 面试推进 ----------
    def advance(self, *, conversation: list[dict], candidate_answer: str) -> Optional[dict]:
        """处理候选人一条回答，返回面试官回复；返回 None 表示应结束面试。"""
        state = self._load_state()
        cur = self.current()
        if cur is None:
            return None

        nxt = self.next_question()
        decision = self.interviewer.decide(
            role=self.role,
            stage_label=cur["stage_label"],
            current_question=cur["question"],
            current_reference=cur["reference"],
            next_question=nxt["question"] if nxt else None,
            conversation=conversation,
            candidate_answer=candidate_answer,
            resume_summary=self.resume_summary,
        )

        action = decision["action"]
        if action == "finish":
            # 提前收尾（或最后一题），直接结束
            return decision

        if action in ("probe", "followup"):
            state["probes"] += 1
            if state["probes"] >= MAX_PROBES_PER_QUESTION:
                # 追问次数达到上限，强制推进
                self._advance_cursor(state)
            else:
                self._save_state(state)
            return decision

        # action == next：推进到下一题
        self._advance_cursor(state)
        return decision

    def _advance_cursor(self, state: dict) -> None:
        """游标前进到下一题；跨阶段推进；已到最后一道题则标记 finished。"""
        card = self._load_card()
        stages = card.get("stages", {})
        stage_key = config.STAGES[state["stage_idx"]]
        questions = stages.get(stage_key) or []

        if state["question_idx"] + 1 < len(questions):
            state["question_idx"] += 1
        elif state["stage_idx"] + 1 < len(config.STAGES):
            state["stage_idx"] += 1
            state["question_idx"] = 0
        else:
            state["finished"] = True
        state["probes"] = 0
        card["_state"] = state
        self._save_card(card)

    def is_finished(self) -> bool:
        """是否已到题卡末尾（自然结束）。"""
        return bool((self._load_card().get("_state") or {}).get("finished"))


def _summarize(resume_analysis: dict | None) -> str:
    """从简历分析结果拼一句话画像。"""
    if not resume_analysis:
        return ""
    skills = ", ".join(resume_analysis.get("skills") or [])
    projects = "；".join(
        f"{p.get('name')}({p.get('description')})" for p in (resume_analysis.get("projects") or [])
    )
    return f"技能：{skills}；项目：{projects}"
