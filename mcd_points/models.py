"""数据模型：积分账户、商城商品、抽奖活动。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class PointsAccount:
    """积分账户快照（query-my-account）。"""

    available: float = 0.0
    accumulative: float = 0.0
    used: float = 0.0
    expired: float = 0.0
    frozen: float = 0.0
    expire_this_month: float = 0.0
    expire_next_month: float = 0.0
    expire_last_month: float = 0.0
    currency: str = "积分"
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "PointsAccount":
        return cls(
            available=_num(data.get("availablePoint")),
            accumulative=_num(data.get("accumulativePoint")),
            used=_num(data.get("usedPoint")),
            expired=_num(data.get("expiredPoint")),
            frozen=_num(data.get("frozenPoint")),
            expire_this_month=_num(data.get("currentMouthExpirePoint")),
            expire_next_month=_num(data.get("nextMouthExpirePoint")),
            expire_last_month=_num(data.get("lastMouthExpirePoint")),
            currency=str(data.get("currency") or "积分"),
            raw=data,
        )


@dataclass
class MallItem:
    """积分商城可兑换商品（mall-points-products）。"""

    spu_id: Any = None
    name: str = ""
    selling: str = ""
    category: str = ""
    points: float = 0.0
    api_price: float = 0.0          # 接口 price 字段（积分+现金混合购买时才有值）
    face_value: Optional[float] = None   # 从商品名解析出的确定现金面值（元）
    face_estimated: bool = False    # 面值是否来自卖点文案的估算
    status: int = 0
    up_time: str = ""
    down_time: str = ""
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_api(cls, d: dict) -> "MallItem":
        return cls(
            spu_id=d.get("spuId"),
            name=str(d.get("spuName") or ""),
            selling=str(d.get("selling") or ""),
            category=str(d.get("catName") or ""),
            points=_num(d.get("point")),
            api_price=_num(d.get("price")),
            status=int(d.get("status") or 0),
            up_time=str(d.get("upTime") or ""),
            down_time=str(d.get("downTime") or ""),
            raw=d,
        )


@dataclass
class Prize:
    """抽奖奖池中的单个奖品。"""

    name: str = ""
    type_text: str = ""
    value: Optional[float] = None   # 确定面值（元），无法精确解析时为 None
    value_note: str = ""

    @classmethod
    def from_api(cls, d: dict) -> "Prize":
        return cls(
            name=str(d.get("name") or ""),
            type_text=str(d.get("typeText") or ""),
        )


@dataclass
class LotteryActivity:
    """积分抽奖活动（query-lottery-info）。"""

    code: str = ""
    name: str = ""
    status_text: str = ""
    begin_time: str = ""
    end_time: str = ""
    draw_point: float = 0.0
    draw_type_text: str = ""
    available_times: Optional[int] = None
    available_point: Optional[float] = None
    resource_eligible: bool = False
    ineligible_reason: str = ""
    next_consumption_type: str = ""
    next_consumption_text: str = ""
    prizes: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "LotteryActivity":
        decision = data.get("drawDecision") or {}
        nxt = decision.get("nextConsumption") or {}
        times = data.get("availableTimes")
        point = data.get("availablePoint")
        return cls(
            code=str(data.get("activityCode") or ""),
            name=str(data.get("activityName") or ""),
            status_text=str(data.get("activityStatusText") or ""),
            begin_time=str(data.get("beginTime") or ""),
            end_time=str(data.get("endTime") or ""),
            draw_point=_num(data.get("drawPoint")),
            draw_type_text=str(data.get("drawTypeText") or ""),
            available_times=int(times) if times is not None else None,
            available_point=_num(point) if point is not None else None,
            resource_eligible=bool(decision.get("resourceEligible")),
            ineligible_reason=str(decision.get("reason") or ""),
            next_consumption_type=str(nxt.get("type") or ""),
            next_consumption_text=str(nxt.get("text") or ""),
            prizes=[Prize.from_api(p) for p in (data.get("prizes") or [])],
            raw=data,
        )
