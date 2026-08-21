import config
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import logging

from logging_config import configure_logging
from memory import get_legacy_personal_memory_status, init_db
from memory_extraction_worker import start_worker, stop_worker
from api.routers import (
    auth,
    chat,
    dev_memory,
    health,
    onboarding,
    preferences,
    profile,
    voice,
)
from auth_jwt import get_jwt_secret

get_jwt_secret()

app = FastAPI(title="NOVA API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    configure_logging()
    init_db()
    start_worker()
    logger = logging.getLogger("api.main")
    legacy_status = get_legacy_personal_memory_status()
    if legacy_status["status"] != "clean":
        logger.warning(
            "legacy_personal_memory_status=%s tables=%s rows=%s",
            legacy_status["status"],
            ",".join(legacy_status["legacy_tables"]),
            legacy_status["record_count"],
        )
    logger.info(
        "NOVA API ready — persistence logs appear on POST /v1/chat (not on /health or /v1/profile)"
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    await stop_worker()


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger = logging.getLogger("api.main")
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    logger.exception("unhandled_request_exception path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Apologies. An internal fault occurred. "
                "Please try again shortly."
            ),
        },
    )


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(preferences.router)
app.include_router(profile.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(dev_memory.router)
