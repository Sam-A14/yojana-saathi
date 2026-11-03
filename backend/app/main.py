import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import eligibility, households, schemes
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("yojana")

app = FastAPI(title="Yojana Saathi API", version=settings.app_version)

# Only our own frontend may call the API from a browser. The token travels in the Authorization
# header, which is listed by name because a "*" wildcard does not cover it in browsers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(households.router)
app.include_router(eligibility.router)
app.include_router(schemes.router)


@app.exception_handler(Exception)
async def hide_internal_errors(request: Request, error: Exception) -> JSONResponse:
    """Anything unexpected becomes a plain 500. The details go to our log, never to the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side."})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}
