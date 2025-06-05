import uuid
from typing import Any, Dict, List, Optional


class InMemoryEventStore:
    """Simple in-memory event store for demonstration purposes."""
    
    def __init__(self):
        self._streams: Dict[str, Dict[str, Any]] = {}
    
    def create_stream(self, name: str, initial_data: Dict[str, Any]) -> str:
        """Create a new stream and return its ID."""
        stream_id = str(uuid.uuid4())
        self._streams[stream_id] = {
            "name": name,
            "data": initial_data,
            "created_at": "now",  # In a real implementation, use proper timestamps
        }
        return stream_id
    
    def get_stream_data(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get stream data by ID."""
        stream = self._streams.get(stream_id)
        return stream["data"] if stream else None
    
    def update_stream_data(self, stream_id: str, data: Dict[str, Any]) -> bool:
        """Update stream data."""
        if stream_id in self._streams:
            self._streams[stream_id]["data"].update(data)
            return True
        return False
    
    def list_streams(self) -> List[str]:
        """List all stream IDs."""
        return list(self._streams.keys())
    
    def delete_stream(self, stream_id: str) -> bool:
        """Delete a stream."""
        if stream_id in self._streams:
            del self._streams[stream_id]
            return True
        return False
