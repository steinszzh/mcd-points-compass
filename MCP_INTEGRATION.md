# MCP 集成说明

## MCP Server

| 项 | 值 |
|---|---|
| 名称 | 麦当劳中国 MCP Server（mcd-mcp） |
| 地址 | `https://mcp.mcd.cn` |
| 协议 | Streamable HTTP（JSON-RPC 2.0） |
| 认证 | 请求头 `Authorization: Bearer <MCP Token>` |
| 限流 | 600 次/分钟（超限返回 429） |
| Token 申请 | open.mcd.cn/mcp，手机号登录后控制台激活 |

## 使用的 Tool

| Tool | 用途 | 本项目中的角色 |
|---|---|---|
| `query-my-account` | 查询积分账户：可用/累计/已用/已过期/冻结/本月与下月将过期积分 | 资产总览 + 过期预警的数据源 |
| `mall-points-products` | 查询积分商城可兑换商品（名称、所需积分、上下架时间、状态） | 兑换性价比榜的数据源 |
| `query-lottery-info` | 查询积分抽奖活动：状态、单次消耗、奖池列表、资源决策 | 抽奖决策分析的数据源 |
| `now-time-info` | 获取服务器当前时间 | 判断商品兑换截止日、奖池活动窗口 |

> 说明：项目**刻意不使用** `draw-lottery`、`mall-create-order`、`auto-bind-coupons` 等消耗/写操作工具。本项目定位为只读分析顾问，"花积分"的决策与动作永远留给用户本人。

## 调用流程

```
1. initialize（MCP 协议握手，protocolVersion 2025-03-26）
2. notifications/initialized
3. tools/call query-my-account      → 积分余额与过期结构
4. tools/call now-time-info         → 服务器当前时间
5. tools/call mall-points-products  → 全部可兑换商品
   └─ 本地分析：过滤 status!=2 与 downTime 已到的商品
                → 从商品名解析确定现金面值（如 "18.8元板烧鸡腿堡两件套" → 18.8）
                → 计算 元/分 折算率并排序，标注同款更低积分档位
6. tools/call query-lottery-info    → 抽奖活动与奖池
   └─ 本地分析：机会成本 = 单次积分 × 最优折算率；与奖池确定面值对照
7. 渲染终端报告 / 输出 JSON
```

## 实现要点

麦当劳 MCP Server 有两个值得注意的行为，本项目的客户端（`mcd_points/mcp.py`，约 150 行、仅标准库）分别做了处理：

1. **markdown 包装**：`tools/call` 返回的 `content[0].text` 不是纯 JSON，而是"字段说明 + `## Original Response` + 真实 JSON"的 markdown 文档。客户端用正则剥离包装后解析，同时兼容纯 JSON 与 SSE（`text/event-stream`）两种响应格式。
2. **脏数据**：`mall-points-products` 会返回 `status=2`（上架）但 `downTime` 已过的历史商品。分析层以服务器时间为准二次过滤，保证榜单里每一个商品现在都真能兑换。

## 业务价值

- **对用户**：积分从"看不见的资产"变成"看得见的资产负债表"——知道有多少、值多少、什么时候过期、怎么花最保值。
- **对麦当劳生态**：提升积分（麦享会）的存在感与消耗效率，把沉睡积分引导向商城兑换而非无人问津地过期。
- **对开发者**：提供一个零依赖、可直接读懂的麦当劳 MCP 集成范例（含上述两个服务端行为的兼容处理）。
