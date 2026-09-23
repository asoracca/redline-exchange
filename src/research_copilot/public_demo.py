"""Opt-in, anonymous showcase policy; no private questions or provider calls."""

import threading
import time
from collections import deque
from fastapi import HTTPException
from .models import Limits, StartRequest
from .planner import EXAMPLES, normalize


class PublicDemo:
    def __init__(self):
        self.lock = threading.Lock()
        self.requests = deque()

    def prepare(self, request):
        if request.mode != "offline":
            raise HTTPException(403, "Live AI is disabled on the public demo")
        examples = {normalize(q): q for q in EXAMPLES}
        if normalize(request.question) not in examples:
            raise HTTPException(
                400,
                "Public demo accepts the example questions only; use the local app for private research",
            )
        with self.lock:
            now = time.monotonic()
            while self.requests and self.requests[0] <= now - 60:
                self.requests.popleft()
            if len(self.requests) >= 6:
                raise HTTPException(429, "Public demo is busy; try again in one minute")
            self.requests.append(now)
        return StartRequest(
            question=examples[normalize(request.question)],
            workflow=request.workflow,
            limits=Limits(
                max_work=min(request.limits.max_work, 9000),
                max_tools=40,
                max_seconds=30,
                max_model_calls=1,
                max_output_tokens=256,
            ),
        )
