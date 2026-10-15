"""分析逻辑：兑换性价比、资产估值、抽奖决策。

核心思想（也是本项目的差异化所在）：
把积分当一笔资产来管理。
- 资产的"汇率"由商城兑换决定：商品名中的确定现金面值 ÷ 所需积分
- 抽奖的概率官方不公开，因此不编造期望值，
  而是用"机会成本 = 单次积分 × 最优兑换汇率"与奖池面对照，给出诚实决策
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from .models import LotteryActivity, MallItem, PointsAccount

# "18.8元2份麦辣鸡翅" -> 18.8 ；"5.9元香芋派" -> 5.9
_YUAN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*元")
# "下单立减3元券" -> 3.0
_LIJIAN_RE = re.compile(r"立减\s*(\d+(?:\.\d+)?)\s*元")
_DISCOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*折")

_DT_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def parse_dt(text: str) -> Optional[datetime]:
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def parse_face_value(item: MallItem) -> tuple[Optional[float], bool]:
    """解析商品确定现金面值。

    先认商品名（spuName，属于确定面值），
    商品名没有时再看卖点文案（selling，属于估算，不计入汇率）。
    """
    m = _YUAN_RE.search(item.name)
    if m:
        return float(m.group(1)), False
    m = _YUAN_RE.search(item.selling)
    if m:
        return float(m.group(1)), True
    return None, False


def rank_redemptions(items: list, now: Optional[datetime] = None,
                     top: int = 10) -> list:
    """按"元/分"折算率给可兑换商品排序。

    过滤规则（只保留现在真能换的）：
    - status == 2（上架）
    - downTime 未到（接口会返回已下架的历史商品，且 status 仍可能是 2）
    - 积分要求 > 0

    返回 dict 列表，按折算率降序；无法确定面值的排在最后。
    """
    now = now or datetime.now()
    rows = []
    for it in items:
        face, estimated = parse_face_value(it)
        it.face_value, it.face_estimated = face, estimated
        if it.status != 2:
            continue
        down = parse_dt(it.down_time)
        if down and down < now:
            continue
        if it.points <= 0:
            continue
        rate = (face / it.points) if (face and not estimated) else None
        days_left = (down - now).days if down else None
        rows.append({
            "name": it.name,
            "category": it.category,
            "points": it.points,
            "face_value": face,
            "face_estimated": estimated,
            "rate": rate,                      # 元/分，估算面值不计入
            "days_left": days_left,
            "down_time": it.down_time,
            "selling": it.selling,
        })

    # 同款低价提示：同名同面值的商品，若存在更便宜的兑换档位则标注
    cheapest = {}
    for r in rows:
        if r["face_value"] is None:
            continue
        key = (r["name"], r["face_value"])
        cheapest[key] = min(cheapest.get(key, r["points"]), r["points"])
    for r in rows:
        r["cheaper_alt"] = None
        if r["face_value"] is not None:
            key = (r["name"], r["face_value"])
            if cheapest[key] < r["points"]:
                r["cheaper_alt"] = cheapest[key]

    rows.sort(key=lambda r: (r["rate"] is None, -(r["rate"] or 0.0)))
    return rows[:top]


def best_redemption_rate(rows: list) -> Optional[float]:
    """当前可兑换商品中的最优折算率（元/分）。"""
    rates = [r["rate"] for r in rows if r["rate"]]
    return max(rates) if rates else None


def account_valuation(account: PointsAccount, best_rate: Optional[float]) -> dict:
    """把积分余额折算成"确定性能换到的钱"。"""
    if best_rate is None:
        return {"value": None, "rate": None}
    return {"value": round(account.available * best_rate, 2), "rate": best_rate}


def _prize_value(prize) -> tuple[Optional[float], str]:
    """解析奖品面值。立减券精确；折扣券取决于订单金额，只给区间提示。"""
    m = _LIJIAN_RE.search(prize.name)
    if m:
        return float(m.group(1)), "确定面值"
    m = _DISCOUNT_RE.search(prize.name)
    if m:
        zhe = float(m.group(1)) / 10.0
        return None, f"{m.group(1)}折券，实际价值取决于订单金额"
    return None, "面值以券面规则为准"


def analyze_lottery(lot: LotteryActivity, best_rate: Optional[float],
                    account: Optional[PointsAccount] = None) -> dict:
    """抽奖决策分析。

    官方不公开各奖品中奖概率，因此本函数刻意不计算"期望值"，
    而是给出三样诚实的东西：
    1. 每次抽奖的机会成本（按最优兑换汇率折算成钱）
    2. 奖池中可精确解析的面值区间
    3. 明确的行动建议
    """
    result: dict = {
        "activity": lot,
        "cost_per_draw_points": lot.draw_point,
        "opportunity_cost_yuan": None,
        "best_rate": best_rate,
        "prizes": [],
        "free_draw": False,
        "verdict": "",
        "verdict_detail": [],
    }

    # 奖品面值解析
    exact_values = []
    for p in lot.prizes:
        value, note = _prize_value(p)
        if value is not None:
            exact_values.append(value)
        result["prizes"].append({
            "name": p.name, "type": p.type_text,
            "value": value, "note": note,
        })

    # 是否免费抽
    result["free_draw"] = (
        lot.next_consumption_type in ("CHANCES", "NONE")
        or (lot.available_times or 0) > 0 and lot.draw_point <= 0
    )

    # 机会成本
    if best_rate and lot.draw_point > 0:
        result["opportunity_cost_yuan"] = round(lot.draw_point * best_rate, 2)

    # 结论
    if lot.status_text and "进行中" not in lot.status_text:
        result["verdict"] = f"活动状态：{lot.status_text}，暂不参与。"
        return result
    if not lot.resource_eligible:
        result["verdict"] = f"资源不足：{lot.ineligible_reason or '积分/次数不满足'}"
        return result
    if result["free_draw"]:
        result["verdict"] = "本次抽奖不消耗积分（消耗免费次数），必抽。"
        return result

    opp = result["opportunity_cost_yuan"]
    if opp is not None:
        result["verdict"] = (
            f"每次抽奖消耗 {lot.draw_point:g} {account.currency if account else '积分'}"
            f" ≈ ¥{opp:.2f} 机会成本"
            f"（按当前最优兑换汇率 {best_rate:.4f} 元/分折算）。"
        )
        if exact_values:
            lo, hi = min(exact_values), max(exact_values)
            result["verdict_detail"].append(
                f"奖池中确定面值奖品：¥{lo:g} ~ ¥{hi:g}；单抽成本 ¥{opp:.2f}。"
            )
        result["verdict_detail"].append(
            "各奖品中奖概率官方未公开，此处不编造期望值。"
            "决策规则：只有当你主观认为单抽价值高于机会成本时才抽；"
            "否则把积分留到商城兑换成确定价值更稳妥。"
        )
    else:
        result["verdict"] = "暂无可用兑换汇率参照，无法计算机会成本。"
    return result


def expiry_warnings(account: PointsAccount) -> list:
    """积分过期风险清单。"""
    warnings = []
    if account.expired > 0:
        warnings.append(
            f"已有 {account.expired:g} {account.currency}过期失效（上月清理），无法找回。"
        )
    if account.expire_this_month > 0:
        warnings.append(
            f"本月将有 {account.expire_this_month:g} {account.currency}过期，请尽快使用。"
        )
    if account.expire_next_month > 0:
        warnings.append(
            f"下月将有 {account.expire_next_month:g} {account.currency}过期，提前规划兑换。"
        )
    if account.frozen > 0:
        warnings.append(f"{account.frozen:g} {account.currency}处于冻结状态。")
    return warnings
