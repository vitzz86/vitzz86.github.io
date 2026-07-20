"""Production ASGI entry point for remote MCP clients."""

from __future__ import annotations

import hmac
import os
from typing import Any

from starlette.responses import JSONResponse

from .server import mcp


class OptionalBearerTokenMiddleware:
    """Protect `/mcp` when a static token is configured; keep `/health` public."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.token = os.getenv("COCKPIT_MCP_BEARER_TOKEN", "").strip()

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if self.token and scope.get("type") == "http" and str(scope.get("path") or "").startswith("/mcp"):
            headers = {key.lower(): value for key, value in scope.get("headers") or []}
            authorization = headers.get(b"authorization", b"").decode("latin-1")
            expected = "Bearer %s" % self.token
            if not hmac.compare_digest(authorization, expected):
                response = JSONResponse(
                    {"error": "unauthorized", "message": "A valid bearer token is required."},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


app = OptionalBearerTokenMiddleware(mcp.streamable_http_app())
