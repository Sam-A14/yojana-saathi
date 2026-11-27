import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import auth, documents, eligibility, households, schemes
from app.api.deps import DbSession
from app.config import Settings, get_settings
from app.timing import TimingMiddleware

settings = get_settings()
logger = logging.getLogger("yojana")

app = FastAPI(title="Yojana Saathi API", version=settings.app_version)


def add_cors(application: FastAPI, config: Settings) -> None:
    """Only our own frontend may call the API from a browser: production, plus (when configured)
    this project's Vercel previews, so a pull request's preview site can reach the API.

    The session token travels in the Authorization header, which is listed by name because a "*"
    wildcard does not cover it in browsers.
    """
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[config.frontend_url],
        allow_origin_regex=config.frontend_preview_regex,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


add_cors(app, settings)
app.add_middleware(TimingMiddleware)  # added last, so it wraps everything, CORS included

app.include_router(auth.router)
app.include_router(households.router)
app.include_router(eligibility.router)
app.include_router(schemes.router)
app.include_router(documents.router)


@app.exception_handler(Exception)
async def hide_internal_errors(request: Request, error: Exception) -> JSONResponse:
    """Anything unexpected becomes a plain 500. The details go to our log, never to the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side."})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}


@app.get("/health/db")
def health_db(db: DbSession) -> dict[str, object]:
    """How long one database round trip takes from this server, measured now.

    For finding out why requests are slow, not for the uptime ping: unlike /health this wakes the
    database (and keeps it awake, which on a free plan costs compute hours). `first_ms` includes
    getting a connection (a new one if the database had closed the old); `round_trip_ms` is the
    median of three more plain "SELECT 1" round trips. A request that needs N statements costs
    about N x round_trip_ms before any query work is done.
    """
    started = time.perf_counter()
    db.execute(text("SELECT 1"))
    first = time.perf_counter() - started
    trips = []
    for _ in range(3):
        started = time.perf_counter()
        db.execute(text("SELECT 1"))
        trips.append(time.perf_counter() - started)
    trips.sort()
    return {
        "status": "ok",
        "first_ms": round(first * 1000),
        "round_trip_ms": round(trips[1] * 1000),
    }
