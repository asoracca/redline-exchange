"""Start the already-installed, offline local demo with one command."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "exchange.api:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        workers=1,
        limit_concurrency=32,
    )
