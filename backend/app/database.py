"""数据库连接：SQLAlchemy engine + SessionLocal + Base。

数据表由启动时 Base.metadata.create_all() 自动创建，不手写 DDL。
模型变更采用增量加列，不删库重建。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config


class Base(DeclarativeBase):
    """ORM 模型基类。"""


# pool_pre_ping：每次取连接前先探活，避免 MySQL 服务重启后连接失效
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI 依赖：提供一个数据库会话，请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """启动时建表（不删除已存在的表）。"""
    from . import models  # noqa: F401  确保模型注册到 Base.metadata

    Base.metadata.create_all(bind=engine)
    _migrate_users_is_admin()
    _migrate_session_fields()
    _migrate_member_fields()
    _seed_admin()


def _migrate_member_fields() -> None:
    """增量迁移：users 表补会员字段（到期时间/免费面试已用/免费导出已用）。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    columns = {c["name"] for c in insp.get_columns("users")}
    plan = []
    if "member_until" not in columns:
        plan.append("member_until DATETIME NULL")
    if "free_quota_used" not in columns:
        plan.append("free_quota_used INT NOT NULL DEFAULT 0")
    if "export_quota_used" not in columns:
        plan.append("export_quota_used INT NOT NULL DEFAULT 0")
    if not plan:
        return
    with engine.begin() as conn:
        for ddl in plan:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {ddl}"))


def _migrate_session_fields() -> None:
    """增量迁移：interview_sessions 表补 difficulty/education 列（难度与学历门槛）。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "interview_sessions" not in insp.get_table_names():
        return
    columns = {c["name"] for c in insp.get_columns("interview_sessions")}
    plan = []
    if "difficulty" not in columns:
        plan.append(("difficulty", "VARCHAR(16)", "medium"))
    if "education" not in columns:
        plan.append(("education", "VARCHAR(16)", "any"))
    if not plan:
        return
    with engine.begin() as conn:
        for name, ctype, default in plan:
            conn.execute(
                text(
                    f"ALTER TABLE interview_sessions ADD COLUMN {name} {ctype} "
                    f"NOT NULL DEFAULT '{default}'"
                )
            )


def _migrate_users_is_admin() -> None:
    """增量迁移：users 表缺少 is_admin 列时补上（create_all 不会给旧表加列）。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    columns = {c["name"] for c in insp.get_columns("users")}
    if "is_admin" in columns:
        return
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE users ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0")
        )


def _seed_admin() -> None:
    """启动时确保管理员账号存在（用户名/密码可用环境变量覆盖，不落 .env）。"""
    import logging
    import os

    from sqlalchemy import select

    from .auth import hash_password
    from .models import User

    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "123456")

    with SessionLocal() as db:
        exists = db.scalar(select(User).where(User.username == admin_user))
        if exists:
            # 已存在则确保有管理员标记（兼容早于本功能注册的账号）
            if not exists.is_admin:
                exists.is_admin = True
                db.commit()
            return
        db.add(User(username=admin_user, password_hash=hash_password(admin_pass), is_admin=True))
        db.commit()
        logging.getLogger(__name__).info("已创建管理员账号：%s", admin_user)
