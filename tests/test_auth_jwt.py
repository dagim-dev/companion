import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt

import config
from auth_jwt import (
    LOCAL_DEV_JWT_SECRET,
    create_access_token,
    decode_token,
    get_jwt_secret,
)

TEST_SECRET = "test-secret-for-unit-tests"


class AuthJwtTests(unittest.TestCase):
    def setUp(self):
        self.secret_patch = mock.patch.object(config, "JWT_SECRET", TEST_SECRET)
        self.env_patch = mock.patch.object(config, "ENV", "development")
        self.secret_patch.start()
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.secret_patch.stop()

    def test_token_round_trip(self):
        user_id = "user-abc-123"
        token = create_access_token(user_id)
        self.assertEqual(decode_token(token), user_id)

    def test_expired_token(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "user-abc-123",
                "iat": now - timedelta(hours=2),
                "exp": now - timedelta(hours=1),
            },
            TEST_SECRET,
            algorithm=config.JWT_ALGORITHM,
        )
        with self.assertRaises(ValueError):
            decode_token(token)

    def test_invalid_signature(self):
        token = jwt.encode(
            {"sub": "user-abc-123", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret",
            algorithm=config.JWT_ALGORITHM,
        )
        with self.assertRaises(ValueError):
            decode_token(token)

    def test_missing_sub_claim(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {"exp": now + timedelta(hours=1)},
            TEST_SECRET,
            algorithm=config.JWT_ALGORITHM,
        )
        with self.assertRaises(ValueError):
            decode_token(token)

    def test_token_includes_iat(self):
        token = create_access_token("user-abc-123")
        payload = jwt.decode(
            token,
            TEST_SECRET,
            algorithms=[config.JWT_ALGORITHM],
        )
        self.assertIn("iat", payload)


class GetJwtSecretTests(unittest.TestCase):
    def test_get_jwt_secret_dev_fallback(self):
        with mock.patch.object(config, "JWT_SECRET", None), mock.patch.object(
            config, "ENV", "development"
        ):
            self.assertEqual(get_jwt_secret(), LOCAL_DEV_JWT_SECRET)

    def test_get_jwt_secret_raises_when_unconfigured(self):
        with mock.patch.object(config, "JWT_SECRET", None), mock.patch.object(
            config, "ENV", "production"
        ):
            with self.assertRaises(RuntimeError):
                get_jwt_secret()


if __name__ == "__main__":
    unittest.main()
