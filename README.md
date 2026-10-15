# 麦麦积分罗盘 · mcd-points-compass

> 把麦当劳积分当一笔资产来管理：**过期预警、兑换性价比、抽奖决策**，一个零依赖的 Python CLI + 跨模型 Agent Skill。

积分是麦当劳会员最容易被忽视的资产：不知不觉过期、不知道能换什么、抽奖值不值全靠感觉。这个项目基于**麦当劳中国 MCP**，把你的积分余额变成一张清清楚楚的资产清单。

## 功能特性

- **资产总览与估值** —— 可用/累计/已用/已过期/冻结积分一屏看清，并按当前商城汇率折算成"确定性能换到的钱"
- **积分过期预警** —— 已过期（沉没成本）、本月/下月将过期的积分主动告警
- **兑换性价比榜** —— 解析商品名中的确定现金面值，按「元/分」折算率排序；自动过滤已下架商品，自动标注"同款更低积分"档位
- **抽奖决策分析** —— 不编造期望值：用"机会成本 = 单次积分 × 最优兑换汇率"与奖池确定面值对照，给出诚实结论
- **JSON 输出** —— 所有命令支持 `--json`，`accountId` 等敏感字段自动脱敏
- **跨模型 Agent Skill** —— 附带模型无关的 `SKILL.md`，WorkBuddy / Cursor / Cherry Studio / Trae / VSCode 等任意 MCP 客户端都能用

## 示例输出

```
$ python -m mcd_points report
═══════════════════════════════════════════════
   麦麦积分罗盘 · mcd-points-compass
   把麦当劳积分当一笔资产来管理
═══════════════════════════════════════════════
数据时间：2026-10-15 20:16:25（麦当劳 MCP Server）

┌─ 积分资产总览 ──────────────────────────────
项目               数值
可用积分          386.0
累计积分        800.0
已过期（沉没）    294.0
本月将过期            0

┌─ 资产估值 ──────────────────────────────────
可用 386.0 麦享会积分 ≈ ¥53.27（按当前可兑换最优确定面值汇率 0.1380 元/分折算）

┌─ 积分过期预警 ──────────────────────────────
  ! 已有 294.0 麦享会积分过期失效（上月清理），无法找回。

┌─ 兑换性价比榜（元/分，越高越划算） ─────────
#  商品                                 积分  面值(元)   元/分  剩余
1  6.9元香芋派/菠萝派任选                 50      6.90  0.1380  76天
2  6.9元可乐麦炫酷                        50      6.90  0.1380  76天
3  10.9元指定小食任选                    100     10.90  0.1090  76天
4  10.9元指定小食任选 (同款更低:100分)   200     10.90  0.0545  76天

┌─ 积分抽奖决策 ──────────────────────────────
结论：每次抽奖消耗 24 麦享会积分 ≈ ¥3.31 机会成本（按当前最优兑换汇率折算）。
  · 各奖品中奖概率官方未公开，此处不编造期望值。
```

完整示例见 [`examples/sample-report.txt`](examples/sample-report.txt)。

## 安装

零第三方依赖，Python 3.9+ 即可：

```bash
git clone https://github.com/<your-name>/mcd-points-compass.git
cd mcd-points-compass
# 直接运行（无需安装）
python -m mcd_points --help
# 或安装为命令
pip install .
mcd-points-compass --help
```

## 使用

前置条件：一个麦当劳 MCP Token。前往 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) 用手机号登录，在控制台点击"激活"申请（参考 [mcd-mcp-server 指南](https://github.com/M-China/mcd-mcp-server)）。

Token 三种提供方式（任选其一）：

```bash
export MCD_MCP_TOKEN=<你的Token>          # 方式 1：环境变量（推荐）
python -m mcd_points report --token <Token>   # 方式 2：命令行参数
python -m mcd_points report --config mcp-config.json  # 方式 3：MCP 配置文件
```

命令一览：

| 命令 | 作用 |
|---|---|
| `report` | 完整资产报告（默认命令） |
| `redeem` | 兑换性价比榜（`--top 20` 控制条数，`--cat 1>4,2` 筛选类目） |
| `lottery` | 抽奖决策分析 |
| `expiry` | 积分过期预警 |
| `tools` | 列出 MCP Server 当前全部工具 |

所有命令均支持 `--json` 输出（参数放子命令前后均可），便于接入脚本或其他 Agent。

## 工作原理

```
                    ┌─────────────────────┐
                    │  mcd-points-compass │
                    └─────────┬───────────┘
                              │ JSON-RPC over Streamable HTTP
                    ┌─────────▼───────────┐
                    │  麦当劳 MCP Server   │
                    │   https://mcp.mcd.cn │
                    └─────────┬───────────┘
        ┌──────────────┬──────┴───────┬──────────────┐
        ▼              ▼              ▼              ▼
 query-my-account  mall-points-   query-lottery-  now-time-info
 积分余额/过期量     products        info          服务器时间
                   商城可兑商品      抽奖活动/奖池    （判断截止日期）
```

三个分析引擎：

1. **估值引擎**：最优确定面值汇率 = max(商品名面值 ÷ 所需积分)，仅统计当前上架且未到截止的商品
2. **性价比引擎**：同面值商品自动聚合，标注更低积分档位；过滤接口里"已下架但 status 仍为上架"的脏数据
3. **抽奖引擎**：官方不公开中奖概率 → 不计算期望值，改用机会成本模型对照奖池，结论永远诚实

## 作为 Agent Skill 使用（模型无关）

本项目同时是一个跨模型 Agent Skill。将 `SKILL.md` 放入任意支持 MCP 的 Agent 的技能目录（WorkBuddy、Cursor、Cherry Studio、Trae、VSCode 等），即可用自然语言获得同样的分析，例如：

> "帮我看看积分快过期了没，能换什么最划算，抽奖值不值得抽"

Skill 会按固定工作流调用 MCP 工具并遵守同一条红线：**任何消耗积分的操作必须先向用户展示并确认，不自动执行**。

## 安全与隐私设计

- **只读**：项目本身只调用 4 个查询类工具，不调用 `draw-lottery` / `mall-create-order` 等任何消耗性工具——花积分的事永远留给用户本人
- **脱敏**：终端报告不展示 `accountId`；`--json` 输出自动将 `accountId`/`traceId` 等字段替换为 `***`
- **Token 安全**：配置文件仅使用环境变量占位符（见 `mcp-config.example.json`）；`mcp-config.json`、`.env` 已在 `.gitignore` 中，真实 Token 不会进仓库

## 项目结构

```
mcd-points-compass/
├── mcd_points/               # 核心包（零依赖）
│   ├── mcp.py                #   最小 Streamable-HTTP MCP 客户端
│   ├── models.py             #   数据模型
│   ├── analyze.py            #   估值/性价比/抽奖分析引擎
│   ├── render.py             #   终端渲染（CJK 对齐）
│   └── cli.py                #   命令行入口
├── SKILL.md                  # 模型无关的 Agent Skill 定义
├── examples/sample-report.txt# 真实运行示例
├── README.md                 # 本文件
├── CONTEST_DECLARATION.md    # 参赛声明（官方模板，不可改动）
├── MCP_INTEGRATION.md        # MCP 集成说明
└── mcp-config.example.json   # 脱敏配置示例
```

## 目标用户

- **积分沉睡者**：账户里躺着几百上千积分、从没在意过什么时候过期的麦当劳会员
- **精算型消费者**：想知道"50 积分换 6.9 元香芋派"和"24 积分抽一次奖"哪个更值的 anyone
- **开发者**：需要一个零依赖、可直接读懂的麦当劳 MCP 调用范例

## 赛事信息

麦当劳程序员创意开发大赛参赛作品。仓库包含赛事要求的全部文件：`README.md`、`CONTEST_DECLARATION.md`、`MCP_INTEGRATION.md`、`mcp-config.example.json`、源代码及 `workbuddy.md`。

本项目与麦当劳无任何隶属关系，非官方产品；积分、奖品数据以麦当劳官方实时结果为准。
