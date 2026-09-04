"""会员路由：状态 / 兑换码 / 模拟支付订单。

- GET  /api/member/status               当前用户会员与免费额度状态
- POST /api/member/codes/redeem         兑换码激活会员 {code}
- POST /api/member/orders               创建模拟支付订单 {plan: month/year}
- POST /api/member/orders/{id}/mock-pay 模拟渠道确认支付（幂等）

说明：本期为「模拟支付」，渠道确认由前端一键触发；接真实支付时，
把 mock-pay 换成渠道回调入口即可（订单状态机与幂等已按真实标准实现）。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..services.membership_service import (
    confirm_mock_pay,
    create_order,
    membership_status,
    redeem_code,
)

router = APIRouter()


class RedeemRequest(BaseModel):
    code: str = Field(min_length=6, max_length=40)


class OrderRequest(BaseModel):
    plan: str = Field(default="month", max_length=16)


@router.get("/status")
def get_status(
    current: User = Depends(get_current_user),
):
    return membership_status(current)


@router.post("/codes/redeem")
def redeem(
    body: RedeemRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return redeem_code(db, current, body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/orders")
def new_order(
    body: OrderRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        order = create_order(db, current, body.plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "order_id": order.id,
        "plan": order.plan,
        "plan_name": order.plan_name,
        "amount_cents": order.amount_cents,
        "grant_days": order.grant_days,
        "status": order.status,
        "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.post("/orders/{order_id}/mock-pay")
def mock_pay(
    order_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        order = confirm_mock_pay(db, current, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    st = membership_status(current)
    return {
        "order_id": order.id,
        "status": order.status,
        "grant_days": order.grant_days,
        "member_until": st["member_until"],
        "paid": True,
    }
