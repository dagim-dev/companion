import unittest
from datetime import datetime, timedelta
from unittest import mock

import memory_followups as mf
from memory_followups import (
    FollowupCandidate,
    FollowupType,
    build_template_followup,
    decide_followup,
    rank_followup_candidates,
    select_followup_type,
    topic_similarity,
)


def _row(summary, emotion="neutral", importance=0.5, resolved=1, age_hours=1, ep_id=1):
    created = (datetime.now() - timedelta(hours=age_hours)).isoformat()
    return {
        "id": ep_id,
        "summary": summary,
        "emotion": emotion,
        "importance": importance,
        "created_at": created,
        "resolved": resolved,
    }


class TopicSimilarityTests(unittest.TestCase):
    def test_overlapping_topics_score_above_zero(self):
        sim = topic_similarity("job interview next week", "how was the interview")
        self.assertGreater(sim, 0.0)

    def test_unrelated_topics_score_zero(self):
        sim = topic_similarity("python project deadline", "weekend hiking trip")
        self.assertEqual(sim, 0.0)


class RankingTests(unittest.TestCase):
    def test_unresolved_outranks_resolved_trivial(self):
        rows = [
            _row("had coffee with a friend", emotion="joy", importance=0.5,
                 resolved=1, ep_id=1),
            _row("the job interview", emotion="stress", importance=0.5,
                 resolved=0, ep_id=2),
        ]
        ranked = rank_followup_candidates(rows, current_topic="", now=datetime.now())
        self.assertEqual(ranked[0].episode_id, 2)

    def test_trivial_low_importance_is_dropped(self):
        rows = [_row("minor small talk", importance=0.05)]
        ranked = rank_followup_candidates(rows, current_topic="")
        self.assertEqual(ranked, [])

    def test_topic_similarity_boosts_score(self):
        rows = [
            _row("the exam results", emotion="anxiety", importance=0.5,
                 resolved=1, ep_id=1),
            _row("a weekend trip", emotion="joy", importance=0.5,
                 resolved=1, ep_id=2),
        ]
        ranked = rank_followup_candidates(
            rows, current_topic="how did the exam go", now=datetime.now()
        )
        self.assertEqual(ranked[0].episode_id, 1)

    def test_recent_outranks_old_when_otherwise_equal(self):
        rows = [
            _row("topic one", emotion="joy", importance=0.5, resolved=1,
                 age_hours=2, ep_id=1),
            _row("topic two", emotion="joy", importance=0.5, resolved=1,
                 age_hours=1000, ep_id=2),
        ]
        ranked = rank_followup_candidates(rows, current_topic="", now=datetime.now())
        self.assertEqual(ranked[0].episode_id, 1)


class FollowupTypeTests(unittest.TestCase):
    def _cand(self, emotion="neutral", resolved=True):
        return FollowupCandidate(
            summary="something", emotion=emotion, importance=0.5,
            resolved=resolved, created_at=None,
        )

    def test_unresolved_picks_resolution(self):
        self.assertEqual(
            select_followup_type(self._cand(emotion="stress", resolved=False)),
            FollowupType.RESOLUTION,
        )

    def test_unresolved_goal_emotion_picks_goal(self):
        self.assertEqual(
            select_followup_type(self._cand(emotion="motivation", resolved=False)),
            FollowupType.GOAL,
        )

    def test_resolved_negative_picks_emotional(self):
        self.assertEqual(
            select_followup_type(self._cand(emotion="sad", resolved=True)),
            FollowupType.EMOTIONAL,
        )

    def test_resolved_neutral_picks_reflection(self):
        self.assertEqual(
            select_followup_type(self._cand(emotion="neutral", resolved=True)),
            FollowupType.REFLECTION,
        )


class TemplateWordingTests(unittest.TestCase):
    def _cand(self, **kw):
        base = dict(summary="The job interview", emotion="stress",
                    importance=0.5, resolved=False, created_at=None)
        base.update(kw)
        return FollowupCandidate(**base)

    def test_reserved_opener_for_low_depth(self):
        text = build_template_followup(self._cand(), 0.4, FollowupType.RESOLUTION)
        self.assertTrue(
            any(text.startswith(o) for o in mf.RESERVED_OPENERS), text
        )

    def test_personal_opener_for_high_depth(self):
        text = build_template_followup(self._cand(), 0.9, FollowupType.RESOLUTION)
        self.assertTrue(
            any(text.startswith(o) for o in mf.PERSONAL_OPENERS), text
        )

    def test_emotional_followup_uses_emotion_question(self):
        cand = self._cand(emotion="excitement", resolved=True)
        text = build_template_followup(cand, 0.6, FollowupType.EMOTIONAL)
        self.assertIn(mf.EMOTION_QUESTION_STYLES["excitement"], text)


class GenerateFollowupTextTests(unittest.TestCase):
    def test_falls_back_to_template_when_llm_disabled(self):
        with mock.patch.object(mf, "USE_LLM_WORDING", False):
            text = mf.generate_followup_text(
                "the exam", "anxiety", 0.6, FollowupType.RESOLUTION
            )
        self.assertIn("exam", text.lower())

    def test_falls_back_to_template_on_llm_error(self):
        with mock.patch.object(mf, "USE_LLM_WORDING", True), \
                mock.patch.object(mf, "_llm_followup_text", side_effect=RuntimeError):
            text = mf.generate_followup_text(
                "the exam", "anxiety", 0.6, FollowupType.RESOLUTION
            )
        self.assertIn("exam", text.lower())


class DecidePipelineTests(unittest.TestCase):
    def setUp(self):
        self._patchers = [
            mock.patch.object(mf, "USE_LLM_WORDING", False),
            mock.patch.object(mf, "get_last_followup_at", return_value=None),
            mock.patch.object(mf, "set_last_followup_at"),
            mock.patch.object(
                mf, "retrieve_followup_candidates",
                return_value=[_row("the job interview", emotion="stress",
                                    resolved=0, importance=0.6)],
            ),
        ]
        for p in self._patchers:
            p.start()
        self.set_last = mf.set_last_followup_at

    def tearDown(self):
        for p in self._patchers:
            p.stop()

    def test_relationship_gate_blocks_low_depth(self):
        result = decide_followup({}, {}, 0.2, current_topic="", user_id="u1")
        self.assertIsNone(result)

    def test_cooldown_gate_blocks_recent_followup(self):
        with mock.patch.object(
            mf, "get_last_followup_at",
            return_value=datetime.now() - timedelta(hours=1),
        ):
            result = decide_followup({}, {}, 0.8, current_topic="", user_id="u1")
        self.assertIsNone(result)

    def test_probability_gate_blocks_when_roll_high(self):
        with mock.patch.object(mf.random, "random", return_value=0.99):
            result = decide_followup({}, {}, 0.8, current_topic="", user_id="u1")
        self.assertIsNone(result)

    def test_emits_followup_and_records_cooldown_when_roll_low(self):
        now = datetime.now()
        with mock.patch.object(mf.random, "random", return_value=0.0):
            result = decide_followup(
                {}, {}, 0.8, current_topic="how was the interview",
                user_id="u1", now=now,
            )
        self.assertIsNotNone(result)
        self.assertIn("interview", result.lower())
        self.set_last.assert_called_once_with("u1", now)

    def test_no_candidates_returns_none(self):
        with mock.patch.object(mf, "retrieve_followup_candidates", return_value=[]):
            result = decide_followup({}, {}, 0.8, current_topic="", user_id="u1")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
