"""Bound POST bodies before model parsing, without buffering unbounded input."""

from starlette.responses import JSONResponse
from starlette.requests import Request


class LocalBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        request = Request(scope)
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return await JSONResponse({"detail": "Cross-origin writes disabled"}, 403)(
                scope, receive, send
            )
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > 4096:
                return await JSONResponse({"detail": "Request too large"}, 413)(
                    scope, receive, send
                )
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        consumed = False

        async def bounded_receive():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {
                    "type": "http.request",
                    "body": b"".join(chunks),
                    "more_body": False,
                }
            return await receive()

        await self.app(scope, bounded_receive, send)
