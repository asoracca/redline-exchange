"""Start the installed local research application; no credentials needed offline."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "research_copilot.api:create_app",
        factory=True,
        host="127.0.0.1",
        port=8001,
        workers=1,
        limit_concurrency=32,
    )
