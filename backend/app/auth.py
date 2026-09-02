"""认证工具：密码哈希、JWT 签发与校验、当前用户依赖。

密码哈希用 hashlib.pbkdf2_hmac（标准库，无需额外依赖）。
JWT 用 PyJWT（需安装：pip install PyJWT）。
"""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import User

# 密码哈希参数
_PBKDF2_ITERATIONS = 200_000
_SALT_BYTES = 16

_bearer = HTTPBearer(auto_error=False)


# ---------- 密码哈希 ----------
def hash_password(password: str) -> str:
    """用 PBKDF2-HMAC-SHA256 生成密码哈希，格式：iterations$salt$hash。"""
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"{_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验密码是否与存储的哈希匹配（常数时间比较）。"""
    try:
        iterations_s, salt_hex, hash_hex = stored.split("$")
        iterations = int(iterations_s)
    except (ValueError, AttributeError):
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iterations
    )
    return hmac.compare_digest(digest.hex(), hash_hex)


# ---------- JWT 签发与校验 ----------
def create_access_token(user_id: int) -> str:
    """签发 JWT access token，包含用户 id 与过期时间。"""
    expire = datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    """校验 JWT，返回用户 id；无效/过期返回 None。"""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return int(payload.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


# ---------- FastAPI 依赖 ----------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization: Bearer <token> 解析当前用户，失败返回 401。"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证 token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    """管理员专用依赖：当前用户必须 is_admin，否则 403。"""
    if not current.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current
