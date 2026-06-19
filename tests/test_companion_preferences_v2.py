import json
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import config  # noqa: E402
from companion_prefs import (  # noqa: E402
    TEMPLATE_VERSION,
    complete_onboarding,
    get_companion_preferences,
    list_role_catalog,
    onboarding_answers_to_baseline,
    save_runtime_personality,
)
from memory import get_connection, init_db  # noqa: E402
from memory_scope import user_scope  # noqa: E402


class CompanionPreferencesV2Tests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.config_patch = mock.patch.object(config, "DATABASE_PATH", self.db_path)
        self.config_patch.start()
        init_db()

    def tearDown(self):
        self.config_patch.stop()
        self.tempdir.cleanup()

    def test_onboarding_answers_generate_versioned_baseline_without_roles(self):
        baseline = onboarding_answers_to_baseline(
            communication_style="direct",
            energy_level="upbeat",
            challenge_level="high",
            emotional_support="low",
            detail_level="concise",
            examples_preference="often",
            accountability_style="firm",
        )

        sliders = baseline.sliders.to_dict()
        self.assertGreaterEqual(sliders["directness"], 0.8)
        self.assertGreaterEqual(sliders["accountability"], 0.8)
        self.assertLessEqual(sliders["emotional_support"], 0.45)
        self.assertLessEqual(sliders["verbosity"], 0.4)
        self.assertEqual(
            baseline.directives,
            {"examples_frequency": "often"},
        )

    def test_complete_onboarding_persists_v2_baseline_and_general_jarvis_identity(self):
        with user_scope("user-123"):
            prefs = complete_onboarding(
                role_id="fitness_coach",
                communication="direct",
                energy="upbeat",
                address_as="Dagi",
                challenge_level="high",
                emotional_support="low",
                detail_level="concise",
                examples_preference="often",
                accountability_style="firm",
                user_id="user-123",
            )

            loaded = get_companion_preferences("user-123")

        self.assertEqual(TEMPLATE_VERSION, "2")
        self.assertEqual(prefs.role_id, "general_jarvis")
        self.assertEqual(loaded.role_id, "general_jarvis")
        self.assertEqual(loaded.challenge_level, "high")
        self.assertEqual(loaded.detail_level, "concise")
        self.assertEqual(loaded.baseline_directives["examples_frequency"], "often")

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT prefs_json FROM companion_preferences WHERE user_id = ?",
                ("user-123",),
            ).fetchone()
        finally:
            conn.close()

        stored = json.loads(row["prefs_json"])
        self.assertEqual(stored["schema_version"], 2)
        self.assertIn("baseline", stored)
        self.assertIn("baseline_sliders", stored)
        self.assertNotIn("role_id", stored["baseline"])

    def test_runtime_json_persists_runtime_state_without_personality_slider_drift(self):
        with user_scope("user-123"):
            complete_onboarding(
                role_id="general_jarvis",
                communication="balanced",
                energy="calm",
                address_as="Dagi",
                user_id="user-123",
            )
            save_runtime_personality(
                {
                    "relationship_depth": 0.4,
                    "last_emotional_context": "stress",
                    "active_modifier_summary": [{"key": "distress_support"}],
                },
                user_id="user-123",
            )
            loaded = get_companion_preferences("user-123")

        self.assertEqual(loaded.runtime_json["schema_version"], 2)
        runtime_state = loaded.runtime_json["runtime_state"]
        self.assertEqual(runtime_state["relationship_depth"], 0.4)
        self.assertNotIn("warmth", runtime_state)
        self.assertNotIn("humor", runtime_state)
        self.assertNotIn("formality", runtime_state)

    def test_role_catalog_exposes_only_general_jarvis_compatibility_item(self):
        roles = list_role_catalog()

        self.assertEqual([role["id"] for role in roles], ["general_jarvis"])


if __name__ == "__main__":
    unittest.main()
