---
name: mcd-points-compass
description: 麦当劳积分资产罗盘。查询积分余额与过期风险、按元/分折算率排序商城兑换性价比、分析积分抽奖机会成本。当用户询问"我的积分"、"积分能换什么"、"抽奖值不值"、"积分快过期了"时使用。需要麦当劳 MCP（mcd-mcp）已连接。
---

# 麦麦积分罗盘 · mcd-points-compass

把麦当劳积分当一笔资产来管理。本技能基于麦当劳中国 MCP（mcd-mcp）的 4 个只读工具完成全部分析。

## 可用工具（MCP）

| 工具 | 用途 |
|---|---|
| `query-my-account` | 积分账户：可用/累计/已用/已过期/冻结/本月与下月将过期 |
| `mall-points-products` | 积分商城可兑换商品列表（名称/积分/上下架时间/状态） |
| `query-lottery-info` | 积分抽奖活动：状态/单次消耗/奖池/资源决策 |
| `now-time-info` | 服务器当前时间（判断截止日期用） |

## 工作流

1. **取数**：依次调用 `now-time-info`、`query-my-account`、`mall-points-products`（可带 `catRuleIds` 筛选类目）、`query-lottery-info`。
2. **资产总览**：汇总积分结构；若 `expiredPoint > 0` 或本月/下月将过期 > 0，优先给出过期预警。
3. **资产估值**：计算最优确定面值汇率 = max(商品名中的"X元"面值 ÷ 所需积分)，可用积分 × 该汇率 = 确定性能换到的钱。只统计 `status=2` 且 `downTime` 未到的商品（接口会返回已下架的商品，必须按服务器时间过滤）。
4. **兑换性价比榜**：按元/分降序排列；同名同面值商品标注更低积分档位（如"10.9元小食"有 100 分和 200 分两个链接）。
5. **抽奖决策**：机会成本 = 单次积分 × 最优汇率；与奖池中可精确解析的确定面值（"下单立减X元券"）对照。若 `drawDecision.nextConsumption.type` 为 `CHANCES`/`NONE`（免费次数），直接建议"必抽"。

## 决策规则（必须遵守）

- **诚实原则**：中奖概率官方不公开，禁止编造或暗示期望值。只呈现：机会成本、奖池确定面值区间、明确的行动规则。
- **同款比价**：同一商品存在多个积分档位时，必须指出最低档。
- **时间意识**：所有"能否兑换"判断以 `now-time-info` 返回的服务器时间为准，不用本地时间猜。

## 红线

- 本技能**只读**：不得调用 `draw-lottery`、`mall-create-order`、`auto-bind-coupons` 等任何消耗积分或产生订单的工具。
- 若用户明确要求执行消耗性操作：先展示 `drawDecision.nextConsumption` 的消耗明细，获得用户明确确认后，才可代为实现（且需说明操作不可逆）。
- 不得输出 `accountId`、`traceId` 等敏感字段。

## 可选：命令行模式

若环境已安装本项目（`pip install .` 或 `python -m mcd_points`），可优先调用 CLI 获得确定性计算结果，再向用户解读：

```bash
python -m mcd_points report            # 完整资产报告
python -m mcd_points redeem --top 10   # 兑换性价比榜
python -m mcd_points lottery           # 抽奖决策
python -m mcd_points report --json     # 结构化输出（自动脱敏）
```

## 输出模板（回复用户时）

1. 一句话结论：积分资产约合 ¥X，本月/已过期风险如何
2. 兑换性价比榜 Top 3-5（商品/积分/面值/元/分）
3. 抽奖结论：单次机会成本 ¥Y，值与不值的一句话判断
4. 行动建议：先处理什么、按什么顺序花
