# workbuddy.md — WorkBuddy 对话上下文（开发记录）

> 本文件用于麦当劳程序员创意开发大赛 WorkBuddy 联动奖励核验，记录本项目使用腾讯 WorkBuddy 进行开发的对话上下文。
>
> **注意：以下为开发过程关键节点的人工整理稿。正式提交前，请使用 WorkBuddy 官方的对话导出功能重新导出完整上下文并替换本文件。**

## 项目信息

- 项目名称：麦麦积分罗盘 · mcd-points-compass
- 开发工具：腾讯 WorkBuddy（全程）
- 开发周期：2026-10-15（单日完成选题、开发、测试）

## 开发过程关键节点

### 1. 赛事调研与诊断（2026-10-15 晚间）

- 读取赛事仓库 `M-China/mcd-developer-innovation-challenge` 的 README、活动规则、参赛声明与排行榜
- 读取 `M-China/mcd-mcp-server` 获取 MCP 接入方式与工具清单
- 分析当日榜单（100 个项目）：优惠券策略/卡路里搭配/预算套餐/MBTI/活动雷达等方向已严重同质化；积分相关项目（points vault/actuary/steward）均排在 15-18⭐ 低位——需求被验证但无人做好
- 结论：选择"积分资产管理"作为差异化方向

### 2. MCP 配置与连通性诊断

- 用户已完成 MCP 配置但客户端显示未连接
- 诊断发现根因：`~/.workbuddy/mcp.json` 中 `Authorization` 头缺少 `Bearer ` 前缀（官方格式为 `Bearer <token>`），服务端会返回 401
- 修复后通过实际调用验证：`initialize` 握手成功，`tools/list` 返回 35 个工具（比官方文档多 `query-survey-coupon`、`query-promotions` 两个）

### 3. 形态决策

- 用户提出关键问题：赛事是 WorkBuddy 发起的 Skill，是否意味着发布的技能必须依赖大家的模型配合
- 结论：官方对 Skill 的定义极宽（应用程序/智能体/插件/自动化流程/工作流等），不限定模型；排名只看 GitHub Star，纯提示词型 Skill 传播力弱
- 决策：采用混合形态——零依赖 Python CLI 作为可独立运行的核心（clone 即用，无需任何模型）+ 模型无关的 `SKILL.md` 供任意 MCP 客户端 Agent 调用

### 4. 开发与实测

- 基于实时工具 schema 开发（未凭文档猜测）：发现服务端将工具结果包在 markdown 信封中（`## Original Response` + JSON），客户端实现了解包逻辑
- 真实数据验证中发现两个产品级洞察并落入功能：
  1. 商城接口会返回 `status=2` 但 `downTime` 已过的脏数据 → 按服务器时间二次过滤
  2. 同一商品存在多个积分档位（如"10.9元指定小食任选"100 分与 200 分两个链接）→ 自动标注"同款更低"
- 抽奖模块坚持诚实原则：官方不公开中奖概率，不编造期望值，改用"机会成本 = 单次积分 × 最优兑换汇率"与奖池确定面值对照

### 5. 安全设计

- 全程只读：不调用任何消耗积分/产生订单的工具
- 隐私脱敏：终端不展示 `accountId`，JSON 输出自动打码
- Token 安全：配置文件仅环境变量占位符，`mcp-config.json`/`.env` 已列入 `.gitignore`

## 使用的 WorkBuddy 能力

- 对话式开发：需求分析、代码生成、调试、文档撰写全程在 WorkBuddy 中完成
- 本地文件读写与命令执行：项目搭建、实时 API 联调、测试运行
- MCP 连接器：麦当劳 MCP（mcd-mcp）的配置、诊断与调用
