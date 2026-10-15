"""HTML 报告渲染：自包含单文件仪表盘 + 终端窗口包装。

设计取向：深色金融仪表盘（麦当劳红/黄点缀），无外部依赖，
生成的 HTML 可直接双击打开，也可由无头浏览器截图。
"""
from __future__ import annotations

import html

# 麦当劳品牌色 + 深色金融风
_RED = "#DA291C"
_YELLOW = "#FFC72C"
_BG = "#0e1013"
_CARD = "#171a20"
_CARD2 = "#1d2129"
_TEXT = "#e8eaed"
_MUTED = "#9aa3b2"
_GREEN = "#3fb950"
_LINE = "#2a2f3a"


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _fmt(v, nd=1) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        s = f"{v:,.{nd}f}"
        return s.rstrip("0").rstrip(".") if "." in s else s
    return f"{v:,}"


def render_html(account, valuation, rows, lot_analysis, warnings, now_str,
                title="麦麦积分罗盘 · mcd-points-compass") -> str:
    """把报告数据渲染成自包含 HTML 仪表盘。"""
    value = valuation.get("value")
    rate = valuation.get("rate")
    best = rate

    # ---- 资产总览卡片 ----
    stats = [
        ("可用积分", _fmt(account.available), _YELLOW, account.currency),
        ("资产估值", f"¥{value:.2f}" if value is not None else "—", _GREEN,
         f"按最优汇率 {rate:.4f} 元/分" if rate else "暂无可参照汇率"),
        ("累计积分", _fmt(account.accumulative), _TEXT, ""),
        ("已过期（沉没）", _fmt(account.expired), _RED if account.expired > 0 else _MUTED,
         "上月清理，无法找回" if account.expired > 0 else ""),
    ]
    stat_cards = "".join(
        f'<div class="stat"><div class="stat-label">{_esc(label)}</div>'
        f'<div class="stat-value" style="color:{color}">{_esc(val)}</div>'
        f'<div class="stat-sub">{_esc(sub)}</div></div>'
        for label, val, color, sub in stats)

    # ---- 过期预警 ----
    if warnings:
        warn_html = "".join(f'<div class="warn-item">⚠ {_esc(w)}</div>' for w in warnings)
        warn_block = f'<div class="card"><h2>🚨 积分过期预警</h2>{warn_html}</div>'
    else:
        warn_block = ('<div class="card"><h2>✅ 积分过期预警</h2>'
                      '<div class="ok-item">暂无即将过期的积分</div></div>')

    # ---- 兑换性价比榜 ----
    max_rate = max((r["rate"] or 0) for r in rows) if rows else 0
    trs = []
    for i, r in enumerate(rows, 1):
        rt = r["rate"]
        bar_w = 100 * rt / max_rate if (rt and max_rate) else 0
        bar = (f'<div class="bar"><div class="bar-fill" style="width:{bar_w:.0f}%"></div></div>'
               if rt else "")
        badge = ""
        if i == 1 and rt:
            badge = '<span class="badge-best">最优汇率</span>'
        if r.get("cheaper_alt"):
            badge += (f'<span class="badge-cheap">同款更低:{_fmt(r["cheaper_alt"], 0)}分</span>')
        name = _esc(r["name"]) + (" " + badge if badge else "")
        trs.append(
            "<tr>"
            f'<td class="num">{i}</td>'
            f'<td class="name">{name}</td>'
            f'<td class="num">{_fmt(r["points"], 0)}</td>'
            f'<td class="num">¥{_fmt(r["face_value"])}</td>'
            f'<td class="num rate">{f"{rt:.4f}" if rt else "待确认"}<div class="bar-box">{bar}</div></td>'
            f'<td class="num">{r["days_left"] if r["days_left"] is not None else "-"} 天</td>'
            "</tr>")
    redeem_table = (
        '<table><thead><tr>'
        "<th>#</th><th>商品</th><th>积分</th><th>面值</th><th>元/分（越高越划算）</th><th>剩余</th>"
        "</tr></thead><tbody>" + "".join(trs) + "</tbody></table>"
        if rows else "<p>当前没有可兑换的确定面值商品。</p>")

    # ---- 抽奖决策 ----
    lot = lot_analysis
    prizes = "".join(
        f'<span class="chip">{_esc(p["name"])}'
        + (f'<em>¥{_fmt(p["value"])}</em>' if p["value"] is not None else "")
        + "</span>"
        for p in lot.get("prizes", []))
    details = "".join(f"<li>{_esc(d)}</li>" for d in lot.get("verdict_detail", []))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:{_BG}; color:{_TEXT};
  font-family:"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif;
  padding:36px 28px 48px; }}
.wrap {{ max-width:980px; margin:0 auto; }}
header {{ display:flex; align-items:baseline; gap:14px; margin-bottom:6px; }}
header .logo {{ font-size:30px; font-weight:800; letter-spacing:1px; }}
header .logo b {{ color:{_YELLOW}; }}
header .tag {{ color:{_MUTED}; font-size:13px; }}
.time {{ color:{_MUTED}; font-size:12px; margin-bottom:22px; }}
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:14px; }}
.stat {{ background:{_CARD}; border:1px solid {_LINE}; border-radius:12px; padding:16px 18px; }}
.stat-label {{ color:{_MUTED}; font-size:12px; margin-bottom:8px; }}
.stat-value {{ font-size:26px; font-weight:800; font-variant-numeric:tabular-nums; }}
.stat-sub {{ color:{_MUTED}; font-size:11px; margin-top:6px; min-height:14px; }}
.card {{ background:{_CARD}; border:1px solid {_LINE}; border-radius:12px;
  padding:18px 20px; margin-bottom:14px; }}
.card h2 {{ font-size:15px; margin-bottom:12px; color:{_TEXT}; }}
.warn-item {{ background:rgba(218,41,28,.12); border:1px solid rgba(218,41,28,.4);
  color:#ffb3ad; border-radius:8px; padding:10px 14px; margin-bottom:8px; font-size:13px; }}
.ok-item {{ color:{_GREEN}; font-size:13px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ text-align:left; color:{_MUTED}; font-weight:500; font-size:12px;
  padding:8px 10px; border-bottom:1px solid {_LINE}; }}
td {{ padding:9px 10px; border-bottom:1px solid {_LINE}; vertical-align:middle; }}
tr:last-child td {{ border-bottom:none; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
td.name {{ max-width:300px; }}
.rate {{ min-width:150px; }}
.bar-box {{ margin-top:4px; }}
.bar {{ background:{_CARD2}; border-radius:4px; height:5px; width:100%; }}
.bar-fill {{ background:linear-gradient(90deg,{_RED},{_YELLOW}); border-radius:4px; height:5px; }}
.badge-best {{ background:{_YELLOW}; color:#000; font-size:10px; font-weight:700;
  border-radius:4px; padding:2px 6px; margin-left:6px; vertical-align:middle; }}
.badge-cheap {{ background:rgba(63,185,80,.15); color:{_GREEN}; border:1px solid rgba(63,185,80,.4);
  font-size:10px; border-radius:4px; padding:2px 6px; margin-left:6px; vertical-align:middle; }}
.verdict {{ background:{_CARD2}; border-left:3px solid {_YELLOW};
  padding:12px 16px; border-radius:0 8px 8px 0; font-size:14px; margin-bottom:12px; }}
.verdict ul {{ margin:8px 0 0 18px; color:{_MUTED}; font-size:12px; }}
.verdict li {{ margin-bottom:4px; }}
.chips {{ display:flex; flex-wrap:wrap; gap:8px; }}
.chip {{ background:{_CARD2}; border:1px solid {_LINE}; border-radius:20px;
  padding:5px 12px; font-size:12px; color:{_MUTED}; }}
.chip em {{ color:{_TEXT}; font-style:normal; font-weight:700; margin-left:5px; }}
footer {{ color:{_MUTED}; font-size:11px; text-align:center; margin-top:20px; }}
@media (max-width:760px) {{ .stats {{ grid-template-columns:repeat(2,1fr); }} }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="logo">麦麦积分<b>罗盘</b></div>
  <div class="tag">把麦当劳积分当一笔资产来管理</div>
</header>
<div class="time">数据时间：{_esc(now_str or "—")} · 麦当劳 MCP Server</div>
<div class="stats">{stat_cards}</div>
{warn_block}
<div class="card">
  <h2>💱 兑换性价比榜（元/分，越高越划算）</h2>
  {redeem_table}
</div>
<div class="card">
  <h2>🎰 积分抽奖决策</h2>
  <div class="verdict">{_esc(lot.get("verdict", ""))}<ul>{details}</ul></div>
  <div class="chips">{prizes}</div>
</div>
<footer>本报告由 mcd-points-compass 生成；积分/奖品数据以麦当劳官方实时结果为准。</footer>
</div>
</body>
</html>"""


def wrap_terminal(text: str, title="mcd-points-compass — report") -> str:
    """把终端文本包进 macOS 风格窗口，便于生成美观的 README 截图。"""
    lines = _esc(text).split("\n")
    body = "\n".join(f'<div class="tl">{line or "&nbsp;"}</div>' for line in lines)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#2b2f36; padding:28px;
  font-family:"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif; }}
.window {{ background:#0d0f12; border-radius:10px; overflow:hidden;
  box-shadow:0 18px 50px rgba(0,0,0,.55); max-width:920px; margin:0 auto; }}
.titlebar {{ background:#1c1f26; padding:10px 14px; display:flex; align-items:center; gap:8px; }}
.dot {{ width:12px; height:12px; border-radius:50%; }}
.r {{ background:#ff5f57; }} .y {{ background:#febc2e; }} .g {{ background:#28c840; }}
.title {{ color:#8b93a1; font-size:12px; margin-left:10px;
  font-family:monospace; }}
.term {{ padding:16px 20px 20px; font-family:"Noto Sans Mono CJK SC",monospace;
  font-size:13px; line-height:1.55; color:#d6dae2; white-space:pre; }}
.tl {{ min-height:1.55em; }}
</style>
</head>
<body>
<div class="window">
  <div class="titlebar">
    <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
    <span class="title">{_esc(title)}</span>
  </div>
  <div class="term">{body}</div>
</div>
</body>
</html>"""
