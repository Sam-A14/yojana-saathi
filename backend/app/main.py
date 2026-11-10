import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, documents, eligibility, households, schemes
from app.config import Settings, get_settings

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
