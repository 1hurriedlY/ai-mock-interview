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
