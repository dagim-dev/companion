const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

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

export async function streamChat(
  message: string,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail || `Chat failed (${response.status})`,
    );
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

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
}

export async function transcribeAudio(blob: Blob): Promise<string> {
  const form = new FormData();
  form.append("file", blob, "recording.webm");

  const response = await fetch(`${API_URL}/transcribe`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail ||
        `Transcription failed (${response.status})`,
    );
  }

  const data = (await response.json()) as { text: string };
  return data.text;
}

export async function synthesizeSpeech(text: string): Promise<Blob> {
  const response = await fetch(`${API_URL}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail || `TTS failed (${response.status})`,
    );
  }

  return response.blob();
}

export { API_URL };
