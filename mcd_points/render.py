"""终端渲染：表格 + 分区报告（仅标准库，CJK 宽度感知）。"""
from __future__ import annotations

import unicodedata
from typing import Optional


def _dw(s: str) -> int:
    """字符串显示宽度（CJK 全角字符按 2 列计）。"""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def _pad(s: str, width: int, align: str = "left") -> str:
    gap = max(0, width - _dw(s))
    return (" " * gap + s) if align == "right" else (s + " " * gap)


def _fmt_num(v: Optional[float], digits: int = 1) -> str:
    if v is None:
        return "-"
    if v == int(v):
        return f"{v:,.0f}"
    return f"{v:,.{digits}f}"


def table(headers: list, rows: list, aligns: Optional[list] = None) -> str:
    """渲染一张轻量表格（中文对齐安全）。rows 元素为 str 列表。"""
    if not rows:
        return "（无数据）"
    cols = len(headers)
    widths = [_dw(str(h)) for h in headers]
    for r in rows:
        for i in range(cols):
            widths[i] = max(widths[i], _dw(str(r[i])))
    aligns = aligns or ["left"] * cols

    def line(cells):
        return "  ".join(_pad(str(c), widths[i], aligns[i]) for i, c in enumerate(cells))

    sep = "  ".join("-" * w for w in widths)
    return "\n".join([line(headers), sep] + [line(r) for r in rows])


def section(title: str) -> str:
    pad = max(0, 58 - _dw(title))
    return f"┌─ {title} " + "─" * pad


def _header() -> str:
    return (
        "═══════════════════════════════════════════════\n"
        "   麦麦积分罗盘 · mcd-points-compass\n"
        "   把麦当劳积分当一笔资产来管理\n"
        "═══════════════════════════════════════════════"
    )


def render_report(account, valuation, rows, lottery, warnings, server_time: str) -> str:
    """积分资产罗盘 · 完整报告。"""
    out = [_header(), f"数据时间：{server_time}（麦当劳 MCP Server）"]

    # 1. 资产总览
    out.append(section("积分资产总览"))
    out.append(table(
        ["项目", "数值"],
        [
            ["可用积分", _fmt_num(account.available)],
            ["累计积分", _fmt_num(account.accumulative)],
            ["已使用", _fmt_num(account.used)],
            ["已过期（沉没）", _fmt_num(account.expired)],
            ["冻结中", _fmt_num(account.frozen)],
            ["本月将过期", _fmt_num(account.expire_this_month)],
            ["下月将过期", _fmt_num(account.expire_next_month)],
        ],
        aligns=["left", "right"],
    ))

    # 2. 资产估值
    out.append(section("资产估值"))
    if valuation["value"] is not None:
        out.append(
            f"可用 {_fmt_num(account.available)} {account.currency}"
            f" ≈ ¥{valuation['value']:.2f}"
            f"（按当前可兑换最优确定面值汇率 {valuation['rate']:.4f} 元/分折算）"
        )
        out.append("含义：这些积分现在就能换成约等值的麦当劳餐品券；怎么花，决定了实际价值。")
    else:
        out.append("暂无可用的确定面值兑换参照，无法估值。")

    # 3. 过期预警
    out.append(section("积分过期预警"))
    if warnings:
        for w in warnings:
            out.append(f"  ! {w}")
    else:
        out.append("  OK 暂无即将过期的积分")

    # 4. 兑换性价比榜
    out.append(section("兑换性价比榜（元/分，越高越划算）"))
    if rows:
        trows = []
        for i, r in enumerate(rows, 1):
            rate = f"{r['rate']:.4f}" if r["rate"] else "待确认"
            face = _fmt_num(r["face_value"], 2) if r["face_value"] else "-"
            if r["face_estimated"]:
                face += "(估)"
            days = f"{r['days_left']}天" if r["days_left"] is not None else "-"
            name = r["name"][:22]
            if r.get("cheaper_alt"):
                name += f" (同款更低:{r['cheaper_alt']:g}分)"
            trows.append([i, name, _fmt_num(r["points"]), face, rate, days])
        out.append(table(
            ["#", "商品", "积分", "面值(元)", "元/分", "剩余"],
            trows,
            aligns=["right", "left", "right", "right", "right", "right"],
        ))
        out.append("注：仅统计当前上架且未到兑换截止时间的商品；面值取自商品名中的确定金额。")
    else:
        out.append("  当前没有可用的确定面值兑换商品。")

    # 5. 抽奖决策
    out.append(section("积分抽奖决策"))
    lot = lottery["activity"]
    if lot.name:
        out.append(f"活动：{lot.name}（{lot.status_text}）")
        out.append(f"规则：{lot.draw_type_text}，单次 {_fmt_num(lot.draw_point)} 积分"
                   f"（{lot.begin_time} ~ {lot.end_time}）")
        out.append(f"结论：{lottery['verdict']}")
        for d in lottery["verdict_detail"]:
            out.append(f"  · {d}")
        if lottery["prizes"]:
            out.append("奖池：")
            prows = []
            for p in lottery["prizes"][:12]:
                v = f"¥{p['value']:g}" if p["value"] is not None else "-"
                prows.append([p["name"][:20], p["type"], v, p["note"]])
            out.append(table(["奖品", "类型", "面值", "说明"], prows))
    else:
        out.append("  当前没有进行中的积分抽奖活动。")

    # 6. 行动建议
    out.append(section("行动建议"))
    tips = []
    if account.expire_this_month > 0:
        tips.append(f"优先处理本月过期的 {_fmt_num(account.expire_this_month)} 积分。")
    if valuation["value"] is not None:
        tips.append(f"积分资产约合 ¥{valuation['value']:.2f}，按性价比榜从上往下花最保值。")
    if lottery["opportunity_cost_yuan"] is not None and not lottery["free_draw"]:
        tips.append(
            f"抽奖单次机会成本约 ¥{lottery['opportunity_cost_yuan']:.2f}，"
            "概率不公开，谨慎参与。"
        )
    if not tips:
        tips.append("积分状态健康，按需兑换即可。")
    for t in tips:
        out.append(f"  -> {t}")

    out.append("")
    out.append("本报告由 mcd-points-compass 生成；积分/奖品数据以麦当劳官方实时结果为准。")
    return "\n".join(out)
