"""Container entry point: public restrictions must be explicitly enabled."""

import os
import uvicorn

if __name__ == "__main__":
    if os.getenv("REDLINE_PUBLIC_DEMO") != "1":
        raise SystemExit("Public launcher requires REDLINE_PUBLIC_DEMO=1")
    uvicorn.run(
        "research_copilot.api:create_app",
        factory=True,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        workers=1,
        limit_concurrency=32,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
