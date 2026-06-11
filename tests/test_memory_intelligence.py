import unittest

from memory_intelligence import detect_issues, extract_user_insights


class DetectIssuesEmotionTests(unittest.TestCase):
    def _run_detect(self, emotion, text="hello"):
        insights = {"traits": set(), "interests": set(), "issues": set()}
        detect_issues(text, insights, {"current": emotion, "intensity": 0.8})
        return insights["issues"]

    def test_stress_emotion_adds_stress_issue(self):
        self.assertIn("stress", self._run_detect("stress"))

    def test_sad_emotion_adds_low_mood_issue(self):
        self.assertIn("low mood", self._run_detect("sad"))

    def test_anxiety_emotion_adds_anxiety_issue(self):
        self.assertIn("anxiety", self._run_detect("anxiety"))

    def test_neutral_emotion_adds_no_emotion_issues(self):
        issues = self._run_detect("neutral")
        self.assertEqual(issues, set())

    def test_pressure_text_without_stress_keyword_uses_emotion(self):
        """Implicit stress signals rely on emotion, not keyword patterns."""
        issues = self._run_detect("stress", "there is so much pressure at work")
        self.assertIn("stress", issues)
        self.assertNotIn("burnout", issues)

    def test_keyword_detection_still_works(self):
        issues = self._run_detect("neutral", "i feel anxious and worried")
        self.assertIn("anxiety", issues)


class ExtractUserInsightsTests(unittest.TestCase):
    def test_passes_emotional_state_shape_from_caller(self):
        conversation = [{"role": "user", "content": "too much going on"}]
        emotional_state = {"current": "stress", "intensity": 0.7}

        insights = extract_user_insights(conversation, emotional_state)

        self.assertIn("stress", insights["issues"])


if __name__ == "__main__":
    unittest.main()
