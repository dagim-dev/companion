const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

const TOKEN_KEY = "companion_access_token";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export type SSEEvent =
  | { type: "token"; content: string }
  | {
      type: "done";
      content: string;
      intent?: string;
      emotion?: string;
    };

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
};

export type UserMe = {
  user_id: string;
  email: string;
  onboarding_completed: boolean;
};

export type OnboardingRole = {
  id: string;
  title: string;
  description: string;
};

export type Preferences = {
  role_id: string;
  communication: "direct" | "balanced" | "gentle";
  energy: "calm" | "upbeat";
  sliders: Record<string, number>;
  custom_notes: string;
  onboarding_completed: boolean;
  template_version: string;
};

export type VoiceHealth = {
  enabled: boolean;
  stt_configured: boolean;
  tts_configured: boolean;
  available: boolean;
};

export type HealthResponse = {
  status: string;
  db: string;
  voice?: VoiceHealth;
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`);
  }
  return response.json() as Promise<HealthResponse>;
}

export type UserProfile = {
  address_as: string | null;
  name: string | null;
};

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return (
    localStorage.getItem(TOKEN_KEY) ||
    process.env.NEXT_PUBLIC_DEV_TOKEN ||
    null
  );
}

export function setAccessToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

function formatApiError(
  err: { detail?: string | { msg: string }[] | { message?: string } },
  fallback: string,
): string {
  const { detail } = err;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const msg = (detail as { message?: string }).message;
    if (msg) return msg;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg).join("; ");
  }
  return fallback;
}

function wrapFetchError(error: unknown, context: string): Error {
  if (error instanceof TypeError) {
    return new Error(
      `Cannot reach the API at ${API_URL} (${context}). Is uvicorn running on port 8000?`,
    );
  }
  if (error instanceof Error) return error;
  return new Error(`${context} failed`);
}

export async function register(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const response = await fetch(`${API_URL}/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail ||
        `Registration failed (${response.status})`,
    );
  }

  const data = (await response.json()) as TokenResponse;
  setAccessToken(data.access_token);
  return data;
}

export async function fetchMe(): Promise<UserMe> {
  const response = await fetch(`${API_URL}/v1/auth/me`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(formatApiError(err, `Auth check failed (${response.status})`));
  }
  return response.json() as Promise<UserMe>;
}

export async function fetchOnboardingRoles(): Promise<OnboardingRole[]> {
  const response = await fetch(`${API_URL}/v1/onboarding/roles`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(formatApiError(err, "Failed to load roles"));
  }
  return response.json() as Promise<OnboardingRole[]>;
}

export async function fetchProfile(): Promise<UserProfile> {
  const response = await fetch(`${API_URL}/v1/profile`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(formatApiError(err, "Failed to load profile"));
  }
  return response.json() as Promise<UserProfile>;
}

export async function updateAddressAs(address_as: string): Promise<UserProfile> {
  const response = await fetch(`${API_URL}/v1/profile`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ address_as }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(formatApiError(err, "Failed to update profile"));
  }
  return response.json() as Promise<UserProfile>;
}

export async function completeOnboarding(body: {
  role_id: string;
  communication: "direct" | "balanced" | "gentle";
  energy: "calm" | "upbeat";
  address_as: string;
  display_name?: string;
  custom_notes?: string;
}): Promise<Preferences> {
  const response = await fetch(`${API_URL}/v1/onboarding/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(formatApiError(err, "Onboarding failed"));
  }
  return response.json() as Promise<Preferences>;
}

export async function fetchPreferences(): Promise<Preferences> {
  const response = await fetch(`${API_URL}/v1/preferences`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(formatApiError(err, "Failed to load preferences"));
  }
  return response.json() as Promise<Preferences>;
}

export async function updatePreferences(body: {
  role_id?: string;
  communication?: "direct" | "balanced" | "gentle";
  energy?: "calm" | "upbeat";
  custom_notes?: string;
}): Promise<Preferences> {
  const response = await fetch(`${API_URL}/v1/preferences`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(formatApiError(err, "Failed to update preferences"));
  }
  return response.json() as Promise<Preferences>;
}

export async function resetLearnedStyle(): Promise<void> {
  const response = await fetch(`${API_URL}/v1/preferences/reset-learned`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(formatApiError(err, "Reset failed"));
  }
}

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const response = await fetch(`${API_URL}/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail ||
        `Login failed (${response.status})`,
    );
  }

  const data = (await response.json()) as TokenResponse;
  setAccessToken(data.access_token);
  return data;
}

export async function streamChat(
  message: string,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getAccessToken();
  if (!token) {
    throw new Error("Not authenticated. Please sign in.");
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}/v1/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify({ message }),
      signal,
    });
  } catch (error) {
    throw wrapFetchError(error, "Chat stream");
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      formatApiError(err as { detail?: string }, `Chat failed (${response.status})`),
    );
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const payload = JSON.parse(line.slice(6)) as SSEEvent;
          onEvent(payload);
        } catch {
          /* ignore malformed chunks */
        }
      }
    }
  } catch (error) {
    throw wrapFetchError(error, "Chat stream read");
  }
}

export async function transcribeAudio(blob: Blob): Promise<string> {
  const token = getAccessToken();
  if (!token) {
    throw new Error("Not authenticated. Please sign in.");
  }

  const form = new FormData();
  form.append("file", blob, "recording.webm");

  const response = await fetch(`${API_URL}/v1/transcribe`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      formatApiError(
        err as { detail?: string | { msg: string }[] },
        `Transcription failed (${response.status})`,
      ),
    );
  }

  const data = (await response.json()) as { text: string };
  return data.text;
}

export async function synthesizeSpeech(text: string): Promise<Blob> {
  const token = getAccessToken();
  if (!token) {
    throw new Error("Not authenticated. Please sign in.");
  }

  const response = await fetch(`${API_URL}/v1/tts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      formatApiError(
        err as { detail?: string | { msg: string }[] },
        `TTS failed (${response.status})`,
      ),
    );
  }

  return response.blob();
}

export { API_URL };
