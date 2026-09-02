"""认证路由：注册、登录、当前用户信息。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import User

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64, description="用户名")
    password: str = Field(min_length=6, max_length=128, description="密码")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    is_admin: bool = False


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool = False
    created_at: str

    class Config:
        from_attributes = True


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户，成功后直接返回 access token。"""
    exists = db.scalar(select(User).where(User.username == body.username))
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, username=user.username, is_admin=user.is_admin)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """登录：校验用户名密码，返回 access token。"""
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, username=user.username, is_admin=user.is_admin)


@router.get("/me", response_model=UserResponse)
def me(current: User = Depends(get_current_user)):
    """返回当前登录用户信息（用于验证 JWT 认证）。"""
    return {
        "id": current.id,
        "username": current.username,
        "is_admin": current.is_admin,
        "created_at": current.created_at.strftime("%Y-%m-%d %H:%M:%S") if current.created_at else "",
    }
