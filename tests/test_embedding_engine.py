import os
import unittest
from unittest import mock

import httpx
from openai import APIConnectionError, AuthenticationError

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import embedding_engine as ee  # noqa: E402


def _authentication_error() -> AuthenticationError:
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    response = httpx.Response(401, request=request)
    return AuthenticationError("bad key", response=response, body=None)


def _connection_error() -> APIConnectionError:
    request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    return APIConnectionError(request=request)


class CreateEmbeddingLoggingTests(unittest.TestCase):
    def test_authentication_error_logged_at_error(self):
        with mock.patch.object(
            ee.client.embeddings,
            "create",
            side_effect=_authentication_error(),
        ), self.assertLogs("embedding_engine", level="ERROR") as logs:
            result = ee.create_embedding("hello world")

        self.assertIsNone(result)
        combined = " ".join(record.getMessage() for record in logs.records)
        self.assertIn("OPENAI_API_KEY", combined)

    def test_transient_api_error_logged_at_warning(self):
        with mock.patch.object(
            ee.client.embeddings,
            "create",
            side_effect=_connection_error(),
        ), self.assertLogs("embedding_engine", level="WARNING") as logs:
            result = ee.create_embedding("hello world")

        self.assertIsNone(result)
        self.assertTrue(
            any("Transient" in record.getMessage() for record in logs.records)
        )
        self.assertFalse(any(record.levelno >= 40 for record in logs.records))

    def test_unexpected_exception_logged_at_error(self):
        with mock.patch.object(
            ee.client.embeddings,
            "create",
            side_effect=RuntimeError("boom"),
        ), self.assertLogs("embedding_engine", level="ERROR") as logs:
            result = ee.create_embedding("hello world")

        self.assertIsNone(result)
        self.assertTrue(
            any(
                "Unexpected error in create_embedding" in record.getMessage()
                for record in logs.records
            )
        )


if __name__ == "__main__":
    unittest.main()
