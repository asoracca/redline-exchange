"""Start the installed local research application; no credentials needed offline."""

import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1..65535")
    uvicorn.run(
        "research_copilot.api:create_app",
        factory=True,
        host="127.0.0.1",
        port=args.port,
        workers=1,
        limit_concurrency=32,
    )
