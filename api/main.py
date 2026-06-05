import traceback

import config
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import logging

from logging_config import configure_logging
from memory import init_db
from api.routers import auth, chat, health, onboarding, preferences, profile, voice

if config.ENV == "production" and not config.JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be set when ENV=production")

app = FastAPI(title="JARVIS API", version="2.0.0")

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
    logging.getLogger("api.main").info(
        "JARVIS API ready — persistence logs appear on POST /v1/chat (not on /health or /v1/profile)"
    )


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Apologies, Sir. An internal fault occurred. "
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
