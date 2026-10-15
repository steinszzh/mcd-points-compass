"""mcd-points-compass —— 麦当劳积分资产罗盘。

把麦当劳积分当一笔资产来管理：余额与过期风险、商城兑换性价比、
积分抽奖决策。零第三方依赖，直连麦当劳中国 MCP Server。
"""

from .analyze import analyze_lottery, rank_redemptions, account_valuation
from .mcp import DEFAULT_URL, McpClient, McpError
from .models import LotteryActivity, MallItem, PointsAccount, Prize

__version__ = "0.1.0"
__all__ = [
    "McpClient", "McpError", "DEFAULT_URL",
    "PointsAccount", "MallItem", "LotteryActivity", "Prize",
    "rank_redemptions", "analyze_lottery", "account_valuation",
]
