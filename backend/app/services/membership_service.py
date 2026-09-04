"""会员机制服务（纯业务逻辑，不含 HTTP 层）。

职责：
- 权益常量与套餐定义
- 会员/免费额度判断与扣次
- 兑换码生成 / 激活
- 模拟支付订单：创建 / 渠道确认（幂等）
"""
import secrets
import string
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MemberOrder, MembershipCode, User

# 免费额度（非会员）
FREE_INTERVIEW_QUOTA = 3   # 免费可体验的面试场次
FREE_EXPORT_QUOTA = 2      # 免费可导出的报告次数

# 会员套餐（模拟支付；金额单位：分）
MEMBER_PLANS = {
    "month": {"name": "月度会员", "days": 30, "price_cents": 1990},
    "year": {"name": "年度会员", "days": 365, "price_cents": 19900},
}


# ---------- 判断 / 额度 ----------
def is_member(user: User) -> bool:
    """是否处于会员有效期（以本机时间为准）。"""
    return bool(user.member_until) and user.member_until > datetime.now()


def fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def free_left(user: User, kind: str) -> int:
    """某类免费额度剩余：kind=interview / export。"""
    total = FREE_INTERVIEW_QUOTA if kind == "interview" else FREE_EXPORT_QUOTA
    used = user.free_quota_used if kind == "interview" else user.export_quota_used
    return max(total - (used or 0), 0)


def ensure_allowed(user: User, kind: str) -> None:
    """非会员在额度用尽时抛 PermissionError（kind: interview/export）。"""
    if is_member(user):
        return
    if free_left(user, kind) <= 0:
        name = "面试" if kind == "interview" else "导出"
        raise PermissionError(f"免费{name}次数已用完，请开通会员")


def consume_free(user: User, kind: str) -> None:
    """扣减一次免费额度（会员不扣；调用方 commit）。"""
    if is_member(user):
        return
    if kind == "interview":
        user.free_quota_used = (user.free_quota_used or 0) + 1
    else:
        user.export_quota_used = (user.export_quota_used or 0) + 1


def membership_status(user: User) -> dict:
    """会员/额度状态，供 /member/status 与前端展示。"""
    return {
        "is_member": is_member(user),
        "member_until": fmt_dt(user.member_until),
        "free_interview": {
            "total": FREE_INTERVIEW_QUOTA,
            "used": user.free_quota_used or 0,
            "left": free_left(user, "interview"),
        },
        "free_export": {
            "total": FREE_EXPORT_QUOTA,
            "used": user.export_quota_used or 0,
            "left": free_left(user, "export"),
        },
        "plans": [
            {
                "key": k,
                "name": v["name"],
                "days": v["days"],
                "price_cents": v["price_cents"],
            }
            for k, v in MEMBER_PLANS.items()
        ],
    }


def grant_days(user: User, days: int) -> None:
    """在现有到期时间基础上顺延（过期或未开通则从当前时间起算）。"""
    base = user.member_until if (user.member_until and user.member_until > datetime.now()) else datetime.now()
    user.member_until = base + timedelta(days=int(days))


# ---------- 兑换码 ----------
def _gen_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    for ch in ("O", "0", "I", "1"):
        alphabet = alphabet.replace(ch, "")
    core = "".join(secrets.choice(alphabet) for _ in range(10))
    return f"MB-{core[:5]}-{core[5:]}"


def generate_codes(db: Session, count: int, days: int) -> list[str]:
    """批量生成兑换码（未使用状态），返回码列表。"""
    codes = []
    for _ in range(max(1, min(count, 200))):
        code = _gen_code()
        while db.scalar(select(MembershipCode).where(MembershipCode.code == code)):
            code = _gen_code()
        db.add(MembershipCode(code=code, grant_days=int(days)))
        codes.append(code)
    db.commit()
    return codes


def redeem_code(db: Session, user: User, raw: str) -> dict:
    """兑换码激活会员；返回开通天数与最新到期时间。"""
    code_str = (raw or "").strip().upper()
    row = db.scalar(select(MembershipCode).where(MembershipCode.code == code_str))
    if row is None:
        raise ValueError("兑换码不存在，请检查后重试")
    if row.used_by is not None:
        raise ValueError("该兑换码已被使用")
    row.used_by = user.id
    row.used_at = datetime.now()
    grant_days(user, row.grant_days)
    db.commit()
    return {"days": row.grant_days, "member_until": fmt_dt(user.member_until)}


# ---------- 模拟支付订单 ----------
def create_order(db: Session, user: User, plan_key: str) -> MemberOrder:
    """创建模拟支付订单（pending）。"""
    plan = MEMBER_PLANS.get(plan_key)
    if plan is None:
        raise ValueError("未知的会员套餐")
    order = MemberOrder(
        user_id=user.id,
        plan=plan_key,
        plan_name=plan["name"],
        amount_cents=plan["price_cents"],
        grant_days=plan["days"],
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def confirm_mock_pay(db: Session, user: User, order_id: int) -> MemberOrder:
    """模拟渠道确认：置 paid 并开通/顺延会员（幂等：已 paid 直接返回）。"""
    order = db.get(MemberOrder, order_id)
    if order is None or order.user_id != user.id:
        raise ValueError("订单不存在")
    if order.status == "paid":
        return order
    if order.status != "pending":
        raise ValueError("订单状态异常，无法支付")
    order.status = "paid"
    order.paid_at = datetime.now()
    grant_days(user, order.grant_days)
    db.commit()
    db.refresh(order)
    return order
