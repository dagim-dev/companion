#!/usr/bin/env python3
"""List ElevenLabs voices available to your API key. Run from project root."""
import sys

sys.path.insert(0, ".")

import httpx
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

if not ELEVENLABS_API_KEY:
    print("Set ELEVENLABS_API_KEY in .env first.")
    sys.exit(1)

r = httpx.get(
    "https://api.elevenlabs.io/v1/voices",
    headers={"xi-api-key": ELEVENLABS_API_KEY},
    timeout=30,
)
if r.status_code != 200:
    print("Failed to list voices:", r.status_code, r.text[:400])
    sys.exit(1)

voices = r.json().get("voices", [])
print(f"Found {len(voices)} voices. Copy one voice_id into ELEVENLABS_VOICE_ID in .env\n")
for v in voices:
    vid = v.get("voice_id", "")
    mark = "  <-- currently in .env" if vid == ELEVENLABS_VOICE_ID else ""
    if vid == ELEVENLABS_VOICE_ID and vid not in [x.get("voice_id") for x in voices]:
        mark = "  <-- NOT FOUND (invalid)"
    print(f"{vid}  {v.get('name', '')}{mark}")

configured = ELEVENLABS_VOICE_ID
if configured and not any(v.get("voice_id") == configured for v in voices):
    print(f"\nWARNING: ELEVENLABS_VOICE_ID={configured!r} is NOT in this list → TTS will 404.")
