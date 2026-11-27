"""Where does a request's time go? One log line and one header per request.

Why this exists: a household save felt very slow on the live site, and "how slow, and is it the
database?" cannot be answered by guessing. Each request now reports

    total   the whole request, from the first byte in to the last byte out
    db      time spent inside database statements that went through SQLAlchemy
    queries how many such statements ran
    connects how many NEW database connections were opened for it

The log line (stdout, so Render shows it) and the `Server-Timing` header (the browser's Network tab
shows it under "Timing") carry the same numbers. Nothing identifying is logged: the route pattern
("/households/{household_id}"), never the real URL; no ids, no tokens, no bodies.

What it cannot see: SQLAlchemy does not report the small round trips psycopg makes by itself (the
"BEGIN", COMMIT and ROLLBACK, and the pool's pre-ping), which cost a full network round trip each.
That is why `db` can be well below `total` on a far-away database; /health/db measures one round
trip directly, so `total` can be read as roughly (round trips) x (that number).
"""

import logging
import sys
import time
from contextvars import ContextVar
from dataclasses import dataclass

from sqlalchemy import Engine, event
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("yojana.timing")
SLOW_SECONDS = 2.0  # over this, the line is a WARNING so it stands out in the logs


@dataclass
class RequestStats:
    queries: int = 0
    db_seconds: float = 0.0
    connects: int = 0


# One RequestStats per request. A context variable (not a global) so concurrent requests, and the
# worker threads FastAPI runs synchronous endpoints in, never mix their numbers up.
_current: ContextVar[RequestStats | None] = ContextVar("request_stats", default=None)


def _use_stdout() -> None:
    """Render shows what the app prints. Python's logging prints nothing below WARNING by default,
    so give this one logger a stdout handler (once) and let it speak at INFO."""
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def install_query_timing(engine: Engine) -> None:
    """Count and time every statement and every new connection of this engine."""

    @event.listens_for(engine, "before_cursor_execute")
    def _start(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        conn.info.setdefault("timing_starts", []).append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def _stop(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        started = conn.info["timing_starts"].pop()
        stats = _current.get()
        if stats is not None:
            stats.queries += 1
            stats.db_seconds += time.perf_counter() - started

    @event.listens_for(engine, "connect")
    def _connected(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        stats = _current.get()
        if stats is not None:
            stats.connects += 1


class TimingMiddleware:
    """Plain ASGI middleware (not BaseHTTPMiddleware, which runs the app in another task and would
    hide the context variable from it)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        _use_stdout()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        stats = RequestStats()
        token = _current.set(stats)
        started = time.perf_counter()
        status = 500

        async def send_with_timing(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                total = time.perf_counter() - started
                header = (
                    f"app;dur={total * 1000:.0f}, db;dur={stats.db_seconds * 1000:.0f};"
                    f'desc="{stats.queries} queries, {stats.connects} new connections"'
                )
                message.setdefault("headers", []).append((b"server-timing", header.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_timing)
        finally:
            total = time.perf_counter() - started
            _current.reset(token)
            route = scope.get("route")
            path = getattr(route, "path", None) or "(no route)"  # the pattern, never the real URL
            line = (
                f"timing {scope['method']} {path} {status} total={total * 1000:.0f}ms "
                f"db={stats.db_seconds * 1000:.0f}ms queries={stats.queries} "
                f"connects={stats.connects}"
            )
            logger.log(logging.WARNING if total > SLOW_SECONDS else logging.INFO, line)
