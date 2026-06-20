import unittest

from api.routers.onboarding import _prefs_to_response as onboarding_response
from api.routers.preferences import _prefs_to_response as preferences_response
from api.schemas import (
    OnboardingCompleteRequest,
    PersonalityResetRequest,
    PreferencesUpdateRequest,
)
from companion_prefs import CompanionPreferences, SliderPrefs


class PreferencesApiV2ContractTests(unittest.TestCase):
    def test_onboarding_request_accepts_v2_style_answers_without_role(self):
        body = OnboardingCompleteRequest(
            communication="direct",
            energy="upbeat",
            challenge_level="high",
            emotional_support="low",
            detail_level="concise",
            examples_preference="often",
            accountability_style="firm",
            address_as="Dagi",
        )

        self.assertEqual(body.role_id, "general_nova")
        self.assertEqual(body.challenge_level, "high")
        self.assertEqual(body.examples_preference, "often")

    def test_preferences_update_accepts_v2_fields_and_sliders(self):
        body = PreferencesUpdateRequest(
            challenge_level="low",
            emotional_support="high",
            detail_level="detailed",
            examples_preference="few",
            accountability_style="light",
            sliders={"verbosity": 0.8},
        )

        self.assertEqual(body.challenge_level, "low")
        self.assertEqual(body.sliders["verbosity"], 0.8)

    def test_reset_request_defaults_to_learned_scope(self):
        body = PersonalityResetRequest()

        self.assertEqual(body.scope, "learned")

    def test_preferences_response_includes_v2_baseline_fields(self):
        prefs = CompanionPreferences(
            user_id="user-123",
            role_id="general_nova",
            communication="direct",
            energy="upbeat",
            challenge_level="high",
            emotional_support="low",
            detail_level="concise",
            examples_preference="often",
            accountability_style="firm",
            sliders=SliderPrefs(),
            baseline_directives={"examples_frequency": "often"},
            onboarding_completed=True,
        )

        response = onboarding_response(prefs)
        also_response = preferences_response(prefs)

        self.assertEqual(response.role_id, "general_nova")
        self.assertEqual(response.challenge_level, "high")
        self.assertEqual(response.baseline_directives["examples_frequency"], "often")
        self.assertEqual(also_response.detail_level, "concise")


if __name__ == "__main__":
    unittest.main()
