"""面试路由：开始面试、流式对话（SSE）、结束面试、角色列表。

流程：
- POST /start     建会话 + 面试题生成 Agent 出题卡 → 返回 session_id + 开场白
- POST /{id}/chat SSE 流式：面试官 Agent 决策 + 回复（打字机），落库，返回决策与参考要点
- POST /{id}/end  结束 → 生成评分报告（任务 9 接入评分 Agent），预留表情序列参数
- GET  /roles     面试官角色列表

SSE 事件设计（前端按 data: 逐行解析）：
  event: message    data: {"delta": "…"}                 流式增量
  event: done       data: {"reply": "…", "action": "…",
                           "reference": "…", "stage": "…", "finished": false}
"""
import json
import logging
import threading
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..auth import get_current_user
from ..database import SessionLocal, get_db
from ..models import ChatMessage, InterviewReport, InterviewSession, User
from ..redis_client import redis_client
from ..services.agents.pipeline import InterviewPipeline, PipelineError
from ..services.agents.question_agent import (
    DIFF_NAMES,
    EDU_NAMES,
    QuestionAgent,
    ROLE_NAMES,
)
from ..services.report_service import generate_and_store_report
from ..services.membership_service import consume_free, ensure_allowed

logger = logging.getLogger(__name__)

router = APIRouter()

# 可选角色集合（对外只暴露这三个）
VALID_ROLES = {"technical", "HR", "stress"}
VALID_DIFFICULTY = {"easy", "medium", "hard"}
VALID_EDUCATION = {"any", "college", "bachelor", "master"}

# 报告生成中的会话（单进程内防重；进程重启后由幂等逻辑兜底）
_REPORT_LOCKS: dict[int, bool] = {}


# ---------- 请求 / 响应模型 ----------
class StartRequest(BaseModel):
    job_title: str = Field(min_length=1, max_length=255, description="目标岗位，如：Python 后端")
    role: str = Field(default="technical", description="面试官角色：technical/HR/stress")
    resume_id: str = Field(default="", description="简历分析缓存 id（来自 /api/resume/upload）")
    difficulty: str = Field(default="medium", description="面试难度：easy/medium/hard")
    education: str = Field(default="any", description="学历门槛：any/college/bachelor/master")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000, description="候选人本轮回答")


class EndRequest(BaseModel):
    expression_seq: list[dict] = Field(
        default_factory=list,
        description="表情时间轴：[{time, expression, confidence}, ...]（视觉模块，可空）",
    )


class RoleItem(BaseModel):
    key: str
    name: str
    description: str


class StartResponse(BaseModel):
    session_id: int
    role: str
    job_title: str
    opening: str
    stage: str


# ---------- 内部辅助 ----------
def _get_session_or_404(db: Session, session_id: int) -> InterviewSession:
    """按 id 查询会话，不存在返回 404。"""
    s = db.get(InterviewSession, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return s


def _require_session(db: Session, session_id: int, user: User) -> InterviewSession:
    """校验会话归属当前用户。"""
    s = _get_session_or_404(db, session_id)
    if s.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    if s.status == "completed":
        raise HTTPException(status_code=400, detail="该会话已结束")
    return s


def _opening_message(
    session_id: int,
    role: str,
    job_title: str,
    difficulty: str = "medium",
    education: str = "any",
) -> str:
    """构造开场白文本（不调大模型，保证 start 稳定快速）。"""
    role_name = ROLE_NAMES.get(role, role)
    level = (
        f"本场将按「{DIFF_NAMES.get(difficulty, difficulty)}难度 / "
        f"学历{EDU_NAMES.get(education, education)}」的定位出题。"
    )
    return (
        f"你好，我是本次模拟面试的{role_name}面试官，岗位是{job_title}。{level}"
        "我们先做个自我介绍吧：请用 1 分钟时间介绍一下你自己，"
        "包括你的技术栈、主要项目和擅长的方向。"
    )


def _spawn_report_builder(
    session_id: int,
    session: InterviewSession,
    conversation: list[dict] | None = None,
    expression_seq: list[dict] | None = None,
    *,
    db: Session | None = None,
) -> None:
    """按需拉起后台报告生成（带进程内防重）。"""
    if _REPORT_LOCKS.get(session_id):
        return
    meta = redis_client.get_session_meta(session_id) or {}
    resume_text = session.resume_text or ""
    resume_summary = meta.get("resume_summary") or ""
    if conversation is None and db is not None:
        conversation = _load_context_from_db(db, session_id)
    _REPORT_LOCKS[session_id] = True
    threading.Thread(
        target=_build_report_async,
        args=(
            session_id,
            session.interviewer_role,
            session.job_title,
            resume_text,
            resume_summary,
            conversation or [],
            expression_seq or meta.get("expression_seq") or [],
        ),
        daemon=True,
    ).start()


def _build_report_async(
    session_id: int,
    role: str,
    job_title: str,
    resume_text: str,
    resume_summary: str,
    conversation: list[dict],
    expression_seq: list[dict],
) -> None:
    """后台生成评分报告并落库（独立数据库会话，不占用请求连接）。"""
    db = SessionLocal()
    try:
        generate_and_store_report(
            db,
            session_id=session_id,
            role=role,
            job_title=job_title,
            resume_text=resume_text,
            resume_summary=resume_summary,
            conversation=conversation,
            expression_seq=expression_seq,
        )
        logger.info("后台评分报告已生成 session_id=%s", session_id)
    except Exception:  # noqa: BLE001
        logger.exception("后台评分报告生成异常 session_id=%s", session_id)
    finally:
        try:
            db.close()
        finally:
            _REPORT_LOCKS.pop(session_id, None)


# ---------- 路由 ----------
@router.get("/roles", response_model=list[RoleItem])
def list_roles():
    """可选的面试官角色列表。"""
    return [
        {"key": "technical", "name": ROLE_NAMES["technical"], "description": "考察技术深度、方案取舍、项目细节"},
        {"key": "HR", "name": ROLE_NAMES["HR"], "description": "考察沟通表达、稳定性、职业规划、团队协作"},
        {"key": "stress", "name": ROLE_NAMES["stress"], "description": "压力施压、挑战漏洞、考察抗压应变"},
    ]


@router.post("/start", response_model=StartResponse)
def start_interview(
    body: StartRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """开始一场面试：建会话 → 出题卡 → 返回开场白。

    resume_id 来自简历上传接口；无简历时按岗位通用出题。
    """
    role = body.role
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"不支持的面试官角色：{role}")
    difficulty = body.difficulty
    if difficulty not in VALID_DIFFICULTY:
        raise HTTPException(status_code=400, detail=f"不支持的面试难度：{difficulty}")
    education = body.education
    if education not in VALID_EDUCATION:
        raise HTTPException(status_code=400, detail=f"不支持的学历门槛：{education}")

    # 会员/免费额度拦截（非会员免费 3 场）
    try:
        ensure_allowed(current, "interview")
    except PermissionError as exc:
        raise HTTPException(status_code=402, detail=str(exc))

    # 取简历分析结果（缓存中找；不存在则无简历模式）
    resume_analysis = None
    resume_text = ""
    if body.resume_id:
        resume_analysis = redis_client.get_resume_analysis(body.resume_id)
        if not resume_analysis:
            raise HTTPException(
                status_code=400,
                detail="简历分析结果不存在或已过期，请重新上传简历",
            )
        resume_text = resume_analysis.get("_text") or ""

    # 建会话
    session = InterviewSession(
        user_id=current.id,
        job_title=body.job_title,
        interviewer_role=role,
        difficulty=difficulty,
        education=education,
        resume_text=resume_text or None,
        status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 同步生成面试题卡：失败则回滚会话（原行为，保证进入面试即有完整题卡）
    try:
        card = QuestionAgent().generate_card(
            job_title=body.job_title,
            role=role,
            resume_analysis=resume_analysis,
            difficulty=difficulty,
            education=education,
        )
    except Exception as exc:
        # 题卡失败则将会话回滚删除，避免留下脏数据
        db.delete(session)
        db.commit()
        logger.exception("题卡生成失败")
        raise HTTPException(status_code=502, detail=f"题卡生成失败：{exc}")
    redis_client.set_question_card(session.id, card)

    # 会话元信息（供面试官/评分使用）
    meta = {
        "job_title": body.job_title,
        "role": role,
        "resume_id": body.resume_id,
        "difficulty": difficulty,
        "education": education,
    }
    if resume_analysis:
        meta["resume_summary"] = (
            resume_analysis.get("summary")
            or _summarize_from_analysis(resume_analysis)
        )
    redis_client.set_session_meta(session.id, meta)

    # 开场白（本地模板，不等待大模型）
    opening = _opening_message(session.id, role, body.job_title, difficulty, education)

    # 落库开场白（assistant）便于历史回看；非会员在此扣减一次免费额度
    db.add(ChatMessage(session_id=session.id, role="assistant", content=opening, reference=""))
    consume_free(current, "interview")
    db.commit()

    return StartResponse(
        session_id=session.id,
        role=role,
        job_title=body.job_title,
        opening=opening,
        stage=config.STAGES[0],
    )


@router.post("/{session_id}/chat")
def chat(
    session_id: int,
    body: ChatRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SSE 流式：面试官针对候选人回答决策并回复。

    流程：
    1. 加载题卡 + 会话上下文
    2. 面试官 Agent 决策（next/probe/followup/finish）→ 返回 action + 完整 reply
    3. 落库 user 消息与 assistant 消息（含 reference）
    4. 流式逐字推送 reply，最后推送 done 事件（含 action/stage/finished）

    注：本期用非流式调用先拿到完整决策与 JSON，再按字符流式推送给前端，
    兼顾打字机体验与决策可靠性（流式 JSON 解析不稳定）。
    用同步 def 让阻塞的大模型调用在线程池执行，不卡事件循环。
    """
    session = _require_session(db, session_id, current)
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")

    try:
        pipeline = InterviewPipeline(session_id, role=session.interviewer_role)
    except PipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 会话上下文（最近若干条，Redis 优先，回退 MySQL）
    conversation = redis_client.get_session_context(session_id)
    if conversation is None:
        conversation = _load_context_from_db(db, session_id)

    try:
        decision = pipeline.advance(
            conversation=conversation,
            candidate_answer=message,
        )
    except PipelineError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("面试官决策失败")
        raise HTTPException(status_code=502, detail=f"面试官决策失败：{exc}")

    if decision is None:
        # 没有题卡/游标已越界 → 视为面试结束
        raise HTTPException(status_code=400, detail="面试已结束，请结束面试获取报告")

    action = decision["action"]
    reply = decision["reply"] or "（面试官未发言）"
    reference = decision.get("reference") or ""

    # 落库：候选人消息 + 面试官消息
    db.add(ChatMessage(session_id=session_id, role="user", content=message))
    db.add(ChatMessage(
        session_id=session_id,
        role="assistant",
        content=reply,
        reference=reference,
    ))
    db.commit()

    # 更新 Redis 上下文
    ctx = conversation + [{"role": "user", "content": message}]
    if reply:
        ctx = ctx + [{"role": "assistant", "content": reply}]
    redis_client.set_session_context(session_id, ctx)

    # 当前阶段与是否结束
    cur = pipeline.current()
    stage = cur["stage"] if cur else "closing"
    finished = action == "finish" or pipeline.is_finished()

    done_payload = json.dumps(
        {
            "reply": reply,
            "action": action,
            "reference": reference,
            "stage": stage,
            "finished": finished,
        },
        ensure_ascii=False,
    )

    async def gen() -> AsyncGenerator[str, None]:
        # 打字机：整段已生成，这里按"小批字符 + 极短节流"推送，前端能看到逐字浮现
        chunk = 3           # 每批字符数（越大越快）
        interval = 0.02     # 每批间隔（秒）：打字机明显但不拖沓（长文约 3-4 秒推完）
        import asyncio

        for i in range(0, len(reply), chunk):
            piece = reply[i : i + chunk]
            # 首片带 event 头，其余只发 data（前端按 data: 行解析，event 仅语义标记）
            head = "event: message\n" if i == 0 else ""
            yield f"{head}data: {json.dumps({'delta': piece}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(interval)
        yield f"event: done\ndata: {done_payload}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{session_id}/end")
def end_interview(
    session_id: int,
    body: EndRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """结束面试：评分报告 + 标记 completed + 清理 Redis。

    expression_seq 为前端摄像头采集的表情时间轴（v3 视觉模块），
    交给评分 Agent 生成表情点评。
    """
    session = _get_session_or_404(db, session_id)
    if session.user_id != current.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")

    # 幂等判断
    existing_report = db.scalar(
        select(InterviewReport).where(InterviewReport.session_id == session_id)
    )
    already = session.status == "completed"

    # 已有报告 → 幂等返回
    if already and existing_report:
        redis_client.delete_session(session_id)
        return {
            "session_id": session_id,
            "status": session.status,
            "already_completed": True,
            "message_count": _message_count(db, session_id),
            "expression_count": len(body.expression_seq),
            "report_id": existing_report.id,
            "report": _report_payload(existing_report),
        }

    # 已 completed 但报告还没写完（后台生成中）→ 幂等返回"生成中"，不重复触发
    if already and not existing_report:
        if not _REPORT_LOCKS.get(session_id):
            # 极端情况：进程重启后锁丢失，重新拉起生成
            _spawn_report_builder(session_id, session, db=db)
        return {
            "session_id": session_id,
            "status": session.status,
            "already_completed": True,
            "message_count": _message_count(db, session_id),
            "expression_count": len(body.expression_seq),
            "report_id": None,
            "report": None,
            "generating": True,
        }

    # 首次结束：加载完整对话（Redis 优先，回退 MySQL）
    conversation = redis_client.get_session_context(session_id)
    if conversation is None:
        conversation = _load_context_from_db(db, session_id)

    # 组装简历画像
    resume_summary = ""
    resume_text = session.resume_text or ""
    meta = redis_client.get_session_meta(session_id) or {}
    resume_summary = meta.get("resume_summary") or ""

    # 表情序列（body 优先，其次会话 meta——二次 end 且本次未带表情时用已存的）
    expression_seq = body.expression_seq or meta.get("expression_seq") or []

    # 先标记完成并提交（让报告页/历史立即可进，避免重复触发）
    session.status = "completed"
    session.ended_at = datetime.now()
    db.commit()

    # 报告改后台生成：接口立刻返回，页面进入"生成中"并轮询
    _spawn_report_builder(
        session_id,
        session,
        conversation=conversation,
        expression_seq=expression_seq,
    )

    return {
        "session_id": session_id,
        "status": session.status,
        "already_completed": False,
        "message_count": _message_count(db, session_id),
        "expression_count": len(expression_seq),
        "report_id": None,
        "report": None,
        "generating": True,
    }


# ---------- 内部工具 ----------
def _message_count(db: Session, session_id: int) -> int:
    """统计会话消息条数。"""
    from sqlalchemy import func

    return db.scalar(
        select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
    ) or 0


def _report_payload(report: InterviewReport) -> dict:
    """把报告 ORM 转成 JSON 响应（history 详情同款结构）。"""

    def _load(raw, default):
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    return {
        "id": report.id,
        "summary": report.summary or "",
        "overall_score": report.overall_score,
        "dimensions": _load(report.dimensions, {}),
        "match_analysis": _load(report.match_analysis, {}),
        "suggestions": _load(report.suggestions, []),
        "expression_analysis": _load(report.expression_analysis, {}),
        "created_at": report.created_at.strftime("%Y-%m-%d %H:%M:%S")
        if report.created_at
        else "",
    }


def _load_context_from_db(db: Session, session_id: int) -> list[dict]:
    """从 MySQL 加载最近若干条会话消息（Redis 无缓存时）。"""
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(20)
    ).all()
    messages = [
        {"role": "assistant" if m.role == "assistant" else "user", "content": m.content}
        for m in reversed(rows)
        if m.role in ("user", "assistant")
    ]
    return messages


def _summarize_from_analysis(analysis: dict) -> str:
    """从简历分析字段拼一句话画像（与 pipeline._summarize 语义一致）。"""
    skills = ", ".join(analysis.get("skills") or [])
    projects = "；".join(
        f"{p.get('name')}({p.get('description')})" if isinstance(p, dict) else str(p)
        for p in (analysis.get("projects") or [])
    )
    return f"技能：{skills}；项目：{projects}"
