"""ORM 模型定义：用户、面试会话、聊天消息、面试报告、行业调研报告、项目报告。

说明：
- 数据表由启动时 create_all 自动创建，见 database.py
- 模型变更走增量加列，不删库重建
- chat_messages.reference 为 AI 回复的"参考要点"，面试结束后回看时展示
- 各 JSON 字段（dimensions/match_analysis/suggestions/content）存 JSON 字符串，
  读写时在业务层用 json 序列化/反序列化
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    """注册用户（单用户本地使用，但也支持多账号）。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="用户名"
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="0",
        comment="管理员标记：可查看/删除所有账号数据",
    )
    member_until: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="会员到期时间（NULL=非会员；判断以 server 时间为准）"
    )
    free_quota_used: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0",
        comment="免费面试已用场次（会员不计）",
    )
    export_quota_used: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0",
        comment="免费报告导出已用次数",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class InterviewSession(Base):
    """一次模拟面试会话。"""

    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_title: Mapped[str] = mapped_column(String(255), nullable=False, comment="目标岗位")
    interviewer_role: Mapped[str] = mapped_column(
        String(32), default="technical", nullable=False, comment="面试官角色：technical/HR/stress"
    )
    difficulty: Mapped[str] = mapped_column(
        String(16), default="medium", server_default="medium", nullable=False,
        comment="面试难度：easy/medium/hard",
    )
    education: Mapped[str] = mapped_column(
        String(16), default="any", server_default="any", nullable=False,
        comment="学历门槛：any/college/bachelor/master",
    )
    resume_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="简历文本（供 Agent 使用）"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="in_progress", nullable=False, comment="in_progress/completed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ChatMessage(Base):
    """会话中的一条消息（user / assistant / system）。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, comment="user/assistant/system")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    reference: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AI 回复的参考要点（面试后展示）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class InterviewReport(Base):
    """面试结束后的评分报告。"""

    __tablename__ = "interview_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="总体评语")
    overall_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="总分 0-100")
    dimensions: Mapped[str | None] = mapped_column(Text, nullable=True, comment="五维评分 JSON")
    match_analysis: Mapped[str | None] = mapped_column(Text, nullable=True, comment="岗位匹配度分析 JSON")
    suggestions: Mapped[str | None] = mapped_column(Text, nullable=True, comment="改进建议 JSON")
    expression_analysis: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="表情时间轴 + 点评 JSON（视觉模块）"
    )
    qna: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="逐题复盘 JSON：AI 生成的参考答案（question/answer/model_answer）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class IndustryReport(Base):
    """行业调研报告：对陌生行业做结构化拆解。"""

    __tablename__ = "industry_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    industry_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="调研行业名称")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="调研报告 JSON")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class ProjectReport(Base):
    """求职渠道清单 / 讲项目话术脚本。"""

    __tablename__ = "project_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="channels（渠道清单）/ script（讲项目话术）"
    )
    project_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="话术对应的项目名称（type=script 时填写）"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="内容 JSON")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class MembershipCode(Base):
    """会员兑换码（后台生成，激活后绑定用户）。

    说明：used_by 有意不建库级外键（MySQL 对本组合 SET NULL FK 建表偶发 3780 不兼容），
    孤儿引用由业务层清理（见 admin.delete_user）。
    """

    __tablename__ = "membership_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    grant_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False, comment="激活赠送天数")
    used_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True,
        comment="已使用的用户 id（NULL=未使用）",
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class MemberOrder(Base):
    """会员订单（模拟支付：渠道固定 mock，状态机 pending/paid/refunded）。"""

    __tablename__ = "member_orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, index=True, nullable=False,
        comment="下单用户 id（无库级外键，删除用户时由业务层级联清理）",
    )
    plan: Mapped[str] = mapped_column(String(16), nullable=False, comment="month/year")
    plan_name: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, comment="金额（分）")
    grant_days: Mapped[int] = mapped_column(Integer, nullable=False, comment="开通天数")
    status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False, comment="pending/paid/refunded"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class QuestionBank(Base):
    """题库：沉淀面试题，面试组卡时优先复用（AI 生成 + 人工维护双轨）。"""

    __tablename__ = "question_bank"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stage: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="opening/basic/deep/stress/closing"
    )
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="technical/HR/stress"
    )
    difficulty: Mapped[str] = mapped_column(
        String(16), default="medium", nullable=False, comment="easy/medium/hard"
    )
    education: Mapped[str] = mapped_column(
        String(16), default="any", nullable=False, comment="any/college/bachelor/master"
    )
    job_tag: Mapped[str] = mapped_column(
        String(255), default="", nullable=False, comment="岗位关键词（空=通用）"
    )
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="题目")
    reference: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="参考答案要点"
    )
    source: Mapped[str] = mapped_column(
        String(16), default="manual", nullable=False, comment="ai_generated/manual"
    )
    status: Mapped[str] = mapped_column(
        String(16), default="draft", nullable=False, comment="draft/approved/disabled"
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False, comment="题目文本哈希（去重）"
    )
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class UserAIConfig(Base):
    """用户自定义大模型配置（本地部署 / 云端 API），每个用户至多一条。

    说明：user_id 有意不建库级外键（与 membership_codes / member_orders 同约定，
    规避 MySQL 对部分 FK DDL 的 3780 兼容问题），删除用户时由 admin.delete_user
    业务层清理。
    """

    __tablename__ = "user_ai_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False, comment="所属用户 id"
    )
    provider_type: Mapped[str] = mapped_column(
        String(16), default="cloud", nullable=False,
        comment="部署方式：local（本地部署）/ cloud（云端 API）",
    )
    provider: Mapped[str] = mapped_column(
        String(32), default="custom", nullable=False,
        comment="服务商标识（ollama/openai/deepseek/dashscope/… 或 custom）",
    )
    base_url: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="OpenAI 兼容接口地址"
    )
    api_key: Mapped[str] = mapped_column(
        String(512), default="", nullable=False, comment="API Key（本地部署可留空）"
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False, comment="模型名称")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
