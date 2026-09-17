from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Default ElevenLabs voice ID when unset; override via ELEVENLABS_VOICE_ID in .env
ELEVENLABS_VOICE_ID = os.getenv(
    "ELEVENLABS_VOICE_ID",
    "cgSgspJ2msm6clMCkdW9",
)

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]
DATABASE_PATH = os.getenv("DATABASE_PATH", "memory.db")
ENV = os.getenv("ENV", "development")

# Voice: set false in prod until keys + error handling are verified
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
)
