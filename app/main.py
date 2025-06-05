import logging
from typing import Any, Dict

from mangum import Mangum

from app.server import create_app

logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = create_app()

handler = Mangum(app, lifespan="on")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function."""
    return handler(event, context)


def main() -> None:
    """Entry point for local development."""
    import uvicorn
    
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=3000)


if __name__ == "__main__":
    main()
