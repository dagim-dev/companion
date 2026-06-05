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
    sliders: dict[str, float]
    custom_notes: str
    onboarding_completed: bool
    template_version: str


class ProfileResponse(BaseModel):
    address_as: str | None = None
    name: str | None = None


class ProfileUpdateRequest(BaseModel):
    address_as: str = Field(min_length=1, max_length=32)


class OnboardingCompleteRequest(BaseModel):
    role_id: str
    communication: Literal["direct", "balanced", "gentle"] = "balanced"
    energy: Literal["calm", "upbeat"] = "calm"
    address_as: str = Field(min_length=1, max_length=32)
    display_name: str | None = Field(default=None, max_length=64)
    custom_notes: str | None = Field(default=None, max_length=300)


class PreferencesUpdateRequest(BaseModel):
    role_id: str | None = None
    communication: Literal["direct", "balanced", "gentle"] | None = None
    energy: Literal["calm", "upbeat"] | None = None
    custom_notes: str | None = Field(default=None, max_length=300)
