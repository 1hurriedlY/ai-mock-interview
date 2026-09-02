"""应用配置：从 .env 读取数据库、Redis、JWT、DashScope 等配置。

.env 位于项目根目录（backend 上一级），本文件负责加载它。
所有敏感信息（数据库密码、API Key、JWT 密钥）都不写死在代码里。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录 = backend 的上一级
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# .env 位于项目根目录
load_dotenv(BASE_DIR / ".env")

# ---------- 数据库（MySQL） ----------
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_DB = os.getenv("MYSQL_DB", "interview")
# utf8mb4 保证中文不乱码
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4",
)

# ---------- Redis ----------
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

# ---------- JWT 认证 ----------
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# token 有效期，默认 24 小时
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
# 开发环境缺省 secret 仅 20 字节，PyJWT 会告警但不影响功能，正式使用请在 .env 配置

# ---------- DashScope（通义千问，OpenAI 兼容模式） ----------
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")

# ---------- 运行期目录 ----------
# 上传的简历文件目录
UPLOAD_DIR = BASE_DIR / "backend" / "uploads"
# 导出的报告文件目录
EXPORT_DIR = BASE_DIR / "backend" / "exports"
# 面试题卡阶段定义（供前端展示当前阶段）
STAGES = [
    "opening",       # 开场自我介绍
    "basic",         # 基础题
    "deep",          # 深度题
    "stress",        # 压力/场景题
    "closing",       # 收尾反问
]
