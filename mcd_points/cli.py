"""命令行入口：report / redeem / lottery / expiry / tools"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .analyze import (account_valuation, analyze_lottery, best_redemption_rate,
                      expiry_warnings, parse_dt, rank_redemptions)
from .mcp import DEFAULT_URL, McpClient, McpError
from .models import LotteryActivity, MallItem, PointsAccount
from .render import render_report


def _token_from_config(path: str) -> str:
    """从 MCP 配置文件（含 mcpServers 结构）中读取 Token。"""
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    server = (cfg.get("mcpServers") or {}).get("mcd-mcp") or {}
    auth = (server.get("headers") or {}).get("Authorization", "")
    return auth.removeprefix("Bearer ").strip()


def resolve_token(args) -> str:
    if args.token:
        return args.token.strip()
    if os.environ.get("MCD_MCP_TOKEN"):
        return os.environ["MCD_MCP_TOKEN"].strip()
    if args.config:
        return _token_from_config(args.config)
    raise McpError(
        "未找到 MCP Token。请任选其一：\n"
        "  1) 环境变量  export MCD_MCP_TOKEN=<你的Token>\n"
        "  2) 命令行参数  --token <你的Token>\n"
        "  3) 配置文件    --config mcp-config.json\n"
        "Token 可在 open.mcd.cn/mcp 用手机号登录后申请。"
    )


def build_client(args) -> McpClient:
    return McpClient(resolve_token(args), url=args.url)


def _load_account(client) -> PointsAccount:
    data = client.call("query-my-account")
    return PointsAccount.from_api(data.get("data") or {})


def _load_mall(client, cat: str | None) -> list:
    args = {"catRuleIds": cat} if cat else {}
    data = client.call("mall-points-products", args)
    return [MallItem.from_api(d) for d in (data.get("data") or [])]


def _load_lottery(client) -> LotteryActivity:
    data = client.call("query-lottery-info")
    return LotteryActivity.from_api(data.get("data") or {})


def _load_now(client) -> str:
    try:
        data = client.call("now-time-info")
        return (data.get("data") or {}).get("formatted", "")
    except McpError:
        return ""


def _sanitize(obj):
    """JSON 输出前脱敏：会员账号等敏感字段一律打码。"""
    if isinstance(obj, dict):
        return {k: ("***" if k in ("accountId", "traceId", "phone", "mobile")
                    else _sanitize(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def _emit_json(payload: dict) -> None:
    def default(o):
        return getattr(o, "raw", str(o))
    print(json.dumps(_sanitize(payload), ensure_ascii=False, indent=2, default=default))


def cmd_report(client, args) -> int:
    account = _load_account(client)
    now_str = _load_now(client)
    now = parse_dt(now_str) if now_str else None
    items = _load_mall(client, args.cat)
    rows = rank_redemptions(items, now=now, top=args.top)
    rate = best_redemption_rate(rows)
    valuation = account_valuation(account, rate)
    lottery = _load_lottery(client)
    lot_analysis = analyze_lottery(lottery, rate, account)
    warnings = expiry_warnings(account)

    if args.json:
        _emit_json({
            "server_time": now_str,
            "account": account.raw,
            "valuation": valuation,
            "redemptions": rows,
            "lottery": {
                "activity": lottery.raw,
                "analysis": {k: v for k, v in lot_analysis.items() if k != "activity"},
            },
            "warnings": warnings,
        })
    else:
        print(render_report(account, valuation, rows, lot_analysis, warnings, now_str))
    return 0


def cmd_redeem(client, args) -> int:
    now_str = _load_now(client)
    now = parse_dt(now_str) if now_str else None
    items = _load_mall(client, args.cat)
    rows = rank_redemptions(items, now=now, top=args.top)
    if args.json:
        _emit_json({"server_time": now_str, "redemptions": rows})
        return 0
    from .render import section, table
    print(section(f"兑换性价比榜（数据时间 {now_str}）"))
    if not rows:
        print("（当前没有可用的确定面值兑换商品）")
        return 0
    trows = []
    for i, r in enumerate(rows, 1):
        rate = f"{r['rate']:.4f}" if r["rate"] else "待确认"
        face = f"{r['face_value']:g}" if r["face_value"] else "-"
        if r["face_estimated"]:
            face += "(估)"
        trows.append([i, r["name"][:28], f"{r['points']:g}", face, rate,
                      r["category"], r["down_time"]])
    print(table(["#", "商品", "积分", "面值(元)", "元/分", "类目", "截止"],
                trows, aligns=["right", "left", "right", "right", "right", "left", "left"]))
    return 0


def cmd_lottery(client, args) -> int:
    account = _load_account(client)
    now_str = _load_now(client)
    now = parse_dt(now_str) if now_str else None
    items = _load_mall(client, None)
    rate = best_redemption_rate(rank_redemptions(items, now=now, top=50))
    lottery = _load_lottery(client)
    analysis = analyze_lottery(lottery, rate, account)
    if args.json:
        _emit_json({
            "server_time": now_str,
            "best_rate": rate,
            "lottery": {k: v for k, v in analysis.items() if k != "activity"},
            "activity_raw": lottery.raw,
        })
        return 0
    lot = lottery
    print(f"活动：{lot.name}（{lot.status_text}）")
    print(f"规则：{lot.draw_type_text}，单次 {lot.draw_point:g} 积分")
    print(f"时间：{lot.begin_time} ~ {lot.end_time}")
    print(f"结论：{analysis['verdict']}")
    for d in analysis["verdict_detail"]:
        print(f"  · {d}")
    if analysis["prizes"]:
        print("奖池：")
        from .render import table
        prows = [[p["name"][:24], p["type"],
                  f"¥{p['value']:g}" if p["value"] is not None else "-", p["note"]]
                 for p in analysis["prizes"]]
        print(table(["奖品", "类型", "面值", "说明"], prows))
    return 0


def cmd_expiry(client, args) -> int:
    account = _load_account(client)
    warnings = expiry_warnings(account)
    if args.json:
        _emit_json({"account": account.raw, "warnings": warnings})
        return 0
    from .render import table
    print(table(["项目", "数值"], [
        ["可用积分", f"{account.available:g}"],
        ["已过期", f"{account.expired:g}"],
        ["本月将过期", f"{account.expire_this_month:g}"],
        ["下月将过期", f"{account.expire_next_month:g}"],
        ["冻结中", f"{account.frozen:g}"],
    ], aligns=["left", "right"]))
    print()
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")
    else:
        print("  ✓ 暂无即将过期的积分")
    return 0


def cmd_html(client, args) -> int:
    """生成自包含 HTML 仪表盘报告。"""
    from .htmlreport import render_html
    account = _load_account(client)
    now_str = _load_now(client)
    now = parse_dt(now_str) if now_str else None
    items = _load_mall(client, args.cat)
    rows = rank_redemptions(items, now=now, top=args.top)
    rate = best_redemption_rate(rows)
    valuation = account_valuation(account, rate)
    lottery = _load_lottery(client)
    lot_analysis = analyze_lottery(lottery, rate, account)
    warnings = expiry_warnings(account)
    doc = render_html(account, valuation, rows, lot_analysis, warnings, now_str)
    if args.out == "-":
        print(doc)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(doc)
        print(f"HTML 报告已生成：{args.out}", file=sys.stderr)
    return 0


def cmd_tools(client, args) -> int:
    tools = client.list_tools()
    if args.json:
        _emit_json({"tools": [t.get("name") for t in tools]})
        return 0
    from .render import table
    print(table(["#", "工具名", "说明"], [
        [i, t.get("name", ""), (t.get("description", "") or "").split("\n")[0][:40]]
        for i, t in enumerate(tools, 1)
    ], aligns=["right", "left", "left"]))
    print(f"\n共 {len(tools)} 个工具（MCP Server: {client.url}）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mcd-points-compass",
        description="麦麦积分罗盘：积分过期预警 · 商城兑换性价比 · 抽奖决策分析",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--token", help="麦当劳 MCP Token（也可用环境变量 MCD_MCP_TOKEN）")
    p.add_argument("--config", help="包含 mcd-mcp 配置的 JSON 文件路径（自动读取 Token）")
    p.add_argument("--url", default=DEFAULT_URL, help=f"MCP Server 地址（默认 {DEFAULT_URL}）")
    p.add_argument("--json", action="store_true", help="以 JSON 输出，便于脚本处理")
    p.add_argument("--top", type=int, default=10, help="排行榜展示条数（默认 10）")
    p.add_argument("--cat", help="商城类目筛选，如 1>4,2（逗号分隔多选）")

    # 子命令同样接受这些参数（放在子命令后），SUPPRESS 保证不覆盖主解析器已解析的值
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--token", default=argparse.SUPPRESS,
                        help=argparse.SUPPRESS)
    common.add_argument("--config", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    common.add_argument("--url", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help=argparse.SUPPRESS)
    common.add_argument("--top", type=int, default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    common.add_argument("--cat", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    sub = p.add_subparsers(dest="command")
    sub.add_parser("report", parents=[common], help="完整资产报告（默认）")
    sub.add_parser("redeem", parents=[common], help="兑换性价比榜")
    sub.add_parser("lottery", parents=[common], help="抽奖决策分析")
    sub.add_parser("expiry", parents=[common], help="积分过期预警")
    sub.add_parser("tools", parents=[common], help="列出 MCP Server 全部工具")
    p_html = sub.add_parser("html", parents=[common],
                            help="生成自包含 HTML 仪表盘报告")
    p_html.add_argument("--out", default="mcd-report.html",
                        help="输出文件路径（默认 mcd-report.html，- 表示打印到 stdout）")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.command = args.command or "report"
    handlers = {
        "report": cmd_report, "redeem": cmd_redeem, "lottery": cmd_lottery,
        "expiry": cmd_expiry, "tools": cmd_tools, "html": cmd_html,
    }
    try:
        client = build_client(args)
        return handlers[args.command](client, args)
    except McpError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
