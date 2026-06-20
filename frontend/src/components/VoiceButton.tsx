"use client";

import { useCallback, useRef, useState } from "react";
import { synthesizeSpeech, transcribeAudio } from "@/lib/api";

type VoiceButtonProps = {
  disabled?: boolean;
  voiceAvailable?: boolean;
  onTranscript: (text: string) => void;
  onSpeak?: (text: string) => Promise<void>;
  lastAssistantText?: string;
};

export function VoiceButton({
  disabled,
  voiceAvailable = true,
  onTranscript,
  onSpeak,
  lastAssistantText,
}: VoiceButtonProps) {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    if (disabled || busy) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      mediaRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size === 0) return;

        setBusy(true);
        try {
          const text = await transcribeAudio(blob);
          if (text) onTranscript(text);
        } catch (err) {
          console.error(err);
          alert((err as Error).message);
        } finally {
          setBusy(false);
        }
      };

      recorder.start();
      setRecording(true);
    } catch {
      alert("Microphone access is required for voice input.");
    }
  }, [busy, disabled, onTranscript]);

  const stopRecording = useCallback(() => {
    mediaRef.current?.stop();
    setRecording(false);
  }, []);

  const playLastResponse = useCallback(async () => {
    if (!lastAssistantText?.trim() || busy) return;
    setBusy(true);
    try {
      if (onSpeak) {
        await onSpeak(lastAssistantText);
        return;
      }
      const audioBlob = await synthesizeSpeech(lastAssistantText);
      const url = URL.createObjectURL(audioBlob);
      const audio = new Audio(url);
      await audio.play();
      audio.onended = () => URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert((err as Error).message);
    } finally {
      setBusy(false);
    }
  }, [busy, lastAssistantText, onSpeak]);

  if (!voiceAvailable) {
    return null;
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        disabled={disabled || busy}
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onMouseLeave={() => recording && stopRecording()}
        onTouchStart={(e) => {
          e.preventDefault();
          startRecording();
        }}
        onTouchEnd={(e) => {
          e.preventDefault();
          stopRecording();
        }}
        className={`flex h-10 w-10 items-center justify-center rounded-full border transition ${
          recording
            ? "border-red-500 bg-red-500/20 text-red-400"
            : "border-nova-border bg-nova-panel text-nova-muted hover:border-nova-accent hover:text-nova-accent"
        } disabled:opacity-40`}
        title="Hold to speak"
        aria-label="Hold to speak"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="h-5 w-5"
        >
          <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 14 0h-2Zm-5 9a7 7 0 0 0 7-7h-2a5 5 0 0 1-10 0H5a7 7 0 0 0 7 7Z" />
        </svg>
      </button>
      <button
        type="button"
        disabled={disabled || busy || !lastAssistantText}
        onClick={playLastResponse}
        className="flex h-10 w-10 items-center justify-center rounded-full border border-nova-border bg-nova-panel text-nova-muted transition hover:border-nova-accent hover:text-nova-accent disabled:opacity-40"
        title="Play last response"
        aria-label="Play last response"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="h-5 w-5"
        >
          <path d="M8 5v14l11-7L8 5Z" />
        </svg>
      </button>
    </div>
  );
}
