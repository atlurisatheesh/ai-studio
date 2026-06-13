"""Lightweight in-process per-IP rate limiting.

A fixed-window counter keyed by client IP. Good enough to blunt abuse and
runaway scripts on a single-process deployment. For multi-worker or
multi-host setups, put a real limiter (nginx, a gateway, or Redis) in front.
"""
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.config import RATE_LIMIT_PER_MINUTE


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int = RATE_LIMIT_PER_MINUTE):
        super().__init__(app)
        self.limit = limit_per_minute
        self._hits: dict[str, list] = defaultdict(list)  # ip -> [window_start, count]

    async def dispatch(self, request: Request, call_next):
        if self.limit <= 0:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[ip]
        if not window or now - window[0] >= 60:
            self._hits[ip] = [now, 1]
        else:
            window[1] += 1
            if window[1] > self.limit:
                retry = int(60 - (now - window[0]))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Slow down and try again shortly."},
                    headers={"Retry-After": str(max(retry, 1))},
                )

        # Opportunistic cleanup so the dict doesn't grow unbounded.
        if len(self._hits) > 10000:
            for k in [k for k, v in self._hits.items() if now - v[0] >= 120]:
                self._hits.pop(k, None)

        return await call_next(request)
