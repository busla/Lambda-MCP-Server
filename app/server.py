import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Any, Dict, List

import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from .event_store import InMemoryEventStore

logger = logging.getLogger(__name__)

def create_app():
    """Create and return the MCP StreamableHttp ASGI application."""
    
    app = Server("mcp-streamable-http-demo")

    @app.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        ctx = app.request_context
        interval = arguments.get("interval", 1.0)
        count = arguments.get("count", 5)
        caller = arguments.get("caller", "unknown")

        for i in range(count):
            notification_msg = (
                f"[{i+1}/{count}] Event from '{caller}' - "
                f"Use Last-Event-ID to resume if disconnected"
            )
            await ctx.session.send_log_message(
                level="info",
                data=notification_msg,
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )
            logger.debug(f"Sent notification {i+1}/{count} for caller: {caller}")
            if i < count - 1:  # Don't wait after the last notification
                await anyio.sleep(interval)

        await ctx.session.send_resource_updated(uri=AnyUrl("http:///test_resource"))
        return [
            types.TextContent(
                type="text",
                text=(
                    f"Sent {count} notifications with {interval}s interval"
                    f" for caller: {caller}"
                ),
            )
        ]

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="start-notification-stream",
                description=(
                    "Sends a stream of notifications with configurable count"
                    " and interval"
                ),
                inputSchema={
                    "type": "object",
                    "required": ["interval", "count", "caller"],
                    "properties": {
                        "interval": {
                            "type": "number",
                            "description": "Interval between notifications in seconds",
                        },
                        "count": {
                            "type": "number",
                            "description": "Number of notifications to send",
                        },
                        "caller": {
                            "type": "string",
                            "description": (
                                "Identifier of the caller to include in notifications"
                            ),
                        },
                    },
                },
            )
        ]

    async def handle_streamable_http(
        scope: Scope, receive: Receive, send: Send
    ) -> None:
        session_manager = StreamableHTTPSessionManager(
            app=app,
            event_store=None,  # No event store in stateless mode
            json_response=True,  # Use StreamableHttp protocol, not SSE
            stateless=True,  # Create new transport for each request
        )
        
        async with session_manager.run():
            await session_manager.handle_request(scope, receive, send)

    starlette_app = Starlette(
        debug=True,
        routes=[
            Mount("/mcp", app=handle_streamable_http),
        ],
    )

    return starlette_app
