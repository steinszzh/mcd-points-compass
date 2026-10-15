"""麦当劳 MCP Server 的最小 Streamable-HTTP 客户端（仅标准库）。

- 协议：JSON-RPC 2.0 over Streamable HTTP
- 响应：同时兼容 application/json 与 text/event-stream(SSE)
- 解包：麦当劳服务端会把工具结果包在一层 markdown 里
  （字段说明 + "## Original Response" + 真实 JSON），这里统一剥离
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-03-26"

_ORIGINAL_RE = re.compile(r"##\s*Original Response\s*\n+(\{.*\})\s*$", re.S)


class McpError(RuntimeError):
    """MCP 通信或响应解析失败。"""


class McpClient:
    """极简 MCP 客户端。用法::

        client = McpClient(token)
        client.list_tools()
        client.call("query-my-account")
    """

    def __init__(self, token: str, url: str = DEFAULT_URL,
                 timeout: float = 30.0, retries: int = 3) -> None:
        if not token:
            raise McpError(
                "缺少 MCP Token。请通过 --token 参数或环境变量 MCD_MCP_TOKEN 提供；"
                "Token 可在 open.mcd.cn/mcp 用手机号登录后申请。"
            )
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.retries = max(0, retries)
        self._id = 0
        self._initialized = False

    # ------------------------------------------------------------------ 底层
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    def _post(self, payload: dict, expect_reply: bool = True) -> dict:
        body = json.dumps(payload).encode("utf-8")
        last_err: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(
                    self.url, data=body, headers=self._headers(), method="POST"
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                if not expect_reply:
                    return {}
                return self._parse(raw)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:300]
                if e.code == 401:
                    raise McpError(
                        "MCP Token 无效或已过期（HTTP 401）。请检查 Token，"
                        "或前往 open.mcd.cn/mcp 重新申请。"
                    ) from e
                if e.code == 429:
                    raise McpError(
                        "触发 MCP 限流（HTTP 429，上限 600 次/分钟）。请稍后重试。"
                    ) from e
                raise McpError(f"MCP 请求失败（HTTP {e.code}）：{detail}") from e
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = e
                if attempt >= self.retries:
                    break
                time.sleep(1.5 * (attempt + 1))
        raise McpError(f"无法连接 MCP 服务器 {self.url}：{last_err}")

    @staticmethod
    def _parse(raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("{"):
            return json.loads(raw)
        # SSE：最后一条 data: 行携带 JSON-RPC 消息
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        raise McpError("无法解析 MCP 响应（既不是 JSON 也不是 SSE 格式）")

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        msg = self._post(
            {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        )
        if "error" in msg:
            err = msg["error"]
            raise McpError(f"MCP 错误 {err.get('code')}: {err.get('message')}")
        return msg.get("result", {})

    # ---------------------------------------------------------------- 协议握手
    def ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "mcd-points-compass", "version": "0.1.0"},
        })
        # notifications/initialized 无需响应，失败可忽略
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"},
                       expect_reply=False)
        except McpError:
            pass
        self._initialized = True

    # ------------------------------------------------------------------ 工具
    def list_tools(self) -> list:
        self.ensure_initialized()
        return self._rpc("tools/list").get("tools", [])

    def call(self, name: str, arguments: dict | None = None) -> Any:
        """调用工具并返回剥离包装后的业务数据。"""
        self.ensure_initialized()
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        content = result.get("content") or []
        blob = "\n".join(
            c.get("text", "") for c in content if c.get("type") == "text"
        )
        if result.get("isError"):
            raise McpError(f"工具 {name} 返回错误：{blob[:300]}")
        m = _ORIGINAL_RE.search(blob)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        stripped = blob.strip()
        if stripped.startswith("{"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        raise McpError(f"工具 {name} 返回了无法解析的内容：{blob[:200]}")
