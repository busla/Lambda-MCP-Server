from typing import Any, Dict, List

from fastmcp import FastMCP
from pydantic import BaseModel

from .event_store import InMemoryEventStore

mcp = FastMCP("MCP StreamableHttp Server")

event_store = InMemoryEventStore()


class NotificationRequest(BaseModel):
    interval: float
    count: int
    caller: str


@mcp.tool()
def start_notification_stream(
    interval: float, count: int, caller: str
) -> Dict[str, Any]:
    """Start a notification stream with specified interval and count."""
    request = NotificationRequest(interval=interval, count=count, caller=caller)
    
    stream_id = event_store.create_stream(
        f"notifications-{caller}",
        {
            "interval": request.interval,
            "count": request.count,
            "caller": request.caller,
            "current_count": 0,
        }
    )
    
    return {
        "stream_id": stream_id,
        "message": f"Started notification stream for {caller}",
        "interval": interval,
        "count": count,
    }


@mcp.tool()
def get_stream_status(stream_id: str) -> Dict[str, Any]:
    """Get the status of a notification stream."""
    stream_data = event_store.get_stream_data(stream_id)
    if not stream_data:
        return {"error": "Stream not found"}
    
    return {
        "stream_id": stream_id,
        "data": stream_data,
        "status": "active" if stream_data.get("current_count", 0) < stream_data.get("count", 0) else "completed"
    }


@mcp.tool()
def list_streams() -> List[str]:
    """List all active notification streams."""
    return event_store.list_streams()


def create_app():
    """Create and return the FastMCP application."""
    return mcp.http_app()
