import os
import unittest
from unittest import mock

import httpx

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-elevenlabs-key")

import voice_service as vs  # noqa: E402
from voice_capabilities import VoiceUnavailableError  # noqa: E402


class VoiceServiceLoggingTests(unittest.TestCase):
    def test_transcribe_failure_logged(self):
        audio = b"x" * vs.MIN_AUDIO_BYTES
        mock_client = mock.MagicMock()
        mock_client.audio.transcriptions.create.side_effect = RuntimeError("whisper down")

        with mock.patch.object(vs, "require_stt"), mock.patch.object(
            vs, "_openai", return_value=mock_client
        ), self.assertLogs("voice_service", level="ERROR"):
            with self.assertRaises(VoiceUnavailableError) as ctx:
                vs.transcribe_audio(audio)

        self.assertEqual(ctx.exception.reason, "transcribe_failed")

    def test_tts_http_error_logged(self):
        request = httpx.Request(
            "POST",
            f"https://api.elevenlabs.io/v1/text-to-speech/test-voice-id",
        )
        response = httpx.Response(401, request=request)
        http_error = httpx.HTTPStatusError(
            "unauthorized",
            request=request,
            response=response,
        )

        mock_http_client = mock.MagicMock()
        mock_http_client.post.return_value = response
        mock_http_client.__enter__ = mock.Mock(return_value=mock_http_client)
        mock_http_client.__exit__ = mock.Mock(return_value=False)

        with mock.patch.object(vs, "require_tts"), mock.patch.object(
            vs, "_validate_voice_id"
        ), mock.patch("voice_service.httpx.Client", return_value=mock_http_client), mock.patch.object(
            vs, "ELEVENLABS_VOICE_ID", "test-voice-id"
        ), self.assertLogs("voice_service", level="ERROR"):
            with self.assertRaises(VoiceUnavailableError) as ctx:
                vs.synthesize_speech("Hello")

        self.assertEqual(ctx.exception.reason, "tts_auth_failed")
        mock_http_client.post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
