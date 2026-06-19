from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    intent: str | None = None
    emotion: str | None = None
    response_time_s: float | None = None


class TTSRequest(BaseModel):
    text: str


class TranscribeResponse(BaseModel):
    text: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    onboarding_completed: bool


class RoleCatalogItem(BaseModel):
    id: str
    title: str
    description: str


class PreferencesResponse(BaseModel):
    role_id: str
    communication: str
    energy: str
    challenge_level: str = "medium"
    emotional_support: str = "medium"
    detail_level: str = "normal"
    examples_preference: str = "when_useful"
    accountability_style: str = "steady"
    sliders: dict[str, float]
    baseline_directives: dict[str, str] = {}
    custom_notes: str
    onboarding_completed: bool
    template_version: str


class ProfileResponse(BaseModel):
    address_as: str | None = None
    name: str | None = None


class ProfileUpdateRequest(BaseModel):
    address_as: str = Field(min_length=1, max_length=32)


class OnboardingCompleteRequest(BaseModel):
    role_id: str = "general_jarvis"
    communication: Literal["direct", "balanced", "gentle"] = "balanced"
    energy: Literal["calm", "upbeat"] = "calm"
    challenge_level: Literal["low", "medium", "high"] = "medium"
    emotional_support: Literal["low", "medium", "high"] = "medium"
    detail_level: Literal["concise", "normal", "detailed"] = "normal"
    examples_preference: Literal["few", "when_useful", "often"] = "when_useful"
    accountability_style: Literal["light", "steady", "firm"] = "steady"
    address_as: str = Field(min_length=1, max_length=32)
    display_name: str | None = Field(default=None, max_length=64)
    custom_notes: str | None = Field(default=None, max_length=300)


class PreferencesUpdateRequest(BaseModel):
    role_id: str | None = None
    communication: Literal["direct", "balanced", "gentle"] | None = None
    energy: Literal["calm", "upbeat"] | None = None
    challenge_level: Literal["low", "medium", "high"] | None = None
    emotional_support: Literal["low", "medium", "high"] | None = None
    detail_level: Literal["concise", "normal", "detailed"] | None = None
    examples_preference: Literal["few", "when_useful", "often"] | None = None
    accountability_style: Literal["light", "steady", "firm"] | None = None
    sliders: dict[str, float] | None = None
    custom_notes: str | None = Field(default=None, max_length=300)


class PersonalityResetRequest(BaseModel):
    scope: Literal["runtime", "learned", "baseline", "all_personality"] = "learned"
