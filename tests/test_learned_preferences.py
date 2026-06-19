import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import config  # noqa: E402
from learned_preferences import (  # noqa: E402
    aggregate_preference_insights,
    clear_learned_preferences,
    disable_learned_preference,
    get_active_learned_preferences,
)
from memory import create_conversation_message, get_connection, init_db  # noqa: E402
from memory_insights import save_insights  # noqa: E402
from memory_intelligence import ExtractedInsight  # noqa: E402
from memory_scope import user_scope  # noqa: E402
from memory_recall import retrieve_style_preference_memories  # noqa: E402
from companion_prefs import clear_learned_style  # noqa: E402


class LearnedPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.config_patch = mock.patch.object(config, "DATABASE_PATH", self.db_path)
        self.config_patch.start()
        init_db()

    def tearDown(self):
        self.config_patch.stop()
        self.tempdir.cleanup()

    def test_init_db_creates_learned_preference_tables(self):
        conn = get_connection()
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        finally:
            conn.close()

        self.assertIn("learned_preferences", tables)
        self.assertIn("learned_preference_evidence", tables)
        self.assertIn("learned_preference_conflicts", tables)

    def test_aggregates_explicit_concise_preference_with_evidence(self):
        with user_scope("user-123"):
            message_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="I like shorter answers.",
            )
            save_insights(
                message_id,
                [
                    ExtractedInsight(
                        label="User prefers shorter answers",
                        type="preference",
                        confidence=0.94,
                        evidence="I like shorter answers.",
                        source="latest_user_message",
                        stability="long_term",
                        preference_key="response.length",
                        preference_value={"target": "concise"},
                        scope="global",
                        evidence_polarity="positive",
                    )
                ],
            )

            aggregate_preference_insights(message_id=message_id)
            prefs = get_active_learned_preferences()

        self.assertEqual(len(prefs), 1)
        self.assertEqual(prefs[0]["preference_key"], "response.length")
        self.assertEqual(prefs[0]["value"]["target"], "concise")
        self.assertGreaterEqual(prefs[0]["confidence"], 0.9)
        self.assertEqual(prefs[0]["source_count"], 1)

    def test_conflicting_explicit_preference_marks_existing_conflicted(self):
        with user_scope("user-123"):
            concise_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="I like shorter answers.",
            )
            detailed_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="Actually, give me detailed answers.",
            )
            save_insights(
                concise_id,
                [
                    ExtractedInsight(
                        label="User prefers shorter answers",
                        type="preference",
                        confidence=0.92,
                        evidence="I like shorter answers.",
                        source="latest_user_message",
                        stability="long_term",
                        preference_key="response.length",
                        preference_value={"target": "concise"},
                        scope="global",
                    )
                ],
            )
            aggregate_preference_insights(message_id=concise_id)
            save_insights(
                detailed_id,
                [
                    ExtractedInsight(
                        label="User prefers detailed answers",
                        type="preference",
                        confidence=0.95,
                        evidence="Actually, give me detailed answers.",
                        source="latest_user_message",
                        stability="long_term",
                        preference_key="response.length",
                        preference_value={"target": "detailed"},
                        scope="global",
                    )
                ],
            )
            aggregate_preference_insights(message_id=detailed_id)

            conn = get_connection()
            try:
                active = [
                    dict(row)
                    for row in conn.execute(
                        """
                        SELECT preference_key, status
                        FROM learned_preferences
                        WHERE user_id = ?
                        ORDER BY id
                        """,
                        ("user-123",),
                    ).fetchall()
                ]
                conflicts = conn.execute(
                    """
                    SELECT status, resolution_strategy
                    FROM learned_preference_conflicts
                    WHERE user_id = ?
                    """,
                    ("user-123",),
                ).fetchall()
            finally:
                conn.close()

        self.assertEqual(active[0]["status"], "conflicted")
        self.assertEqual(active[1]["status"], "active")
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["resolution_strategy"], "latest_explicit_wins")

    def test_disable_and_clear_learned_preferences_stop_recall(self):
        with user_scope("user-123"):
            message_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="I like shorter answers.",
            )
            save_insights(
                message_id,
                [
                    ExtractedInsight(
                        label="User prefers shorter answers",
                        type="preference",
                        confidence=0.94,
                        evidence="I like shorter answers.",
                        source="latest_user_message",
                        stability="long_term",
                        preference_key="response.length",
                        preference_value={"target": "concise"},
                        scope="global",
                    )
                ],
            )
            aggregate_preference_insights(message_id=message_id)
            pref_id = get_active_learned_preferences()[0]["id"]

            disable_learned_preference(pref_id)
            self.assertEqual(get_active_learned_preferences(), [])

            clear_learned_preferences()
            conn = get_connection()
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM learned_preferences WHERE user_id = ?",
                    ("user-123",),
                ).fetchone()[0]
            finally:
                conn.close()

        self.assertEqual(count, 0)

    def test_style_recall_reads_active_learned_preferences(self):
        with user_scope("user-123"):
            message_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="I like shorter answers.",
            )
            save_insights(
                message_id,
                [
                    ExtractedInsight(
                        label="User prefers shorter answers",
                        type="preference",
                        confidence=0.94,
                        evidence="I like shorter answers.",
                        source="latest_user_message",
                        stability="long_term",
                        preference_key="response.length",
                        preference_value={"target": "concise"},
                        scope="global",
                    )
                ],
            )
            aggregate_preference_insights(message_id=message_id)
            recalled = retrieve_style_preference_memories("Can you explain this?")

        self.assertEqual(recalled[0]["category"], "learned_preference")
        self.assertEqual(recalled[0]["key"], "response.length")
        self.assertIn("concise", recalled[0]["value"])

    def test_clear_learned_style_clears_canonical_preferences(self):
        with user_scope("user-123"):
            message_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="I like shorter answers.",
            )
            save_insights(
                message_id,
                [
                    ExtractedInsight(
                        label="User prefers shorter answers",
                        type="preference",
                        confidence=0.94,
                        evidence="I like shorter answers.",
                        source="latest_user_message",
                        stability="long_term",
                        preference_key="response.length",
                        preference_value={"target": "concise"},
                        scope="global",
                    )
                ],
            )
            aggregate_preference_insights(message_id=message_id)
            self.assertEqual(len(get_active_learned_preferences()), 1)

            clear_learned_style(user_id="user-123")
            self.assertEqual(get_active_learned_preferences(), [])

    def test_disabled_preference_can_be_relearned_without_unique_conflict(self):
        with user_scope("user-123"):
            message_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="For coding, I like shorter answers.",
            )
            save_insights(
                message_id,
                [
                    ExtractedInsight(
                        label="User prefers shorter coding answers",
                        type="preference",
                        confidence=0.94,
                        evidence="For coding, I like shorter answers.",
                        source="latest_user_message",
                        stability="long_term",
                        preference_key="response.length",
                        preference_value={"target": "concise"},
                        scope="domain",
                        context={"domain": "coding"},
                    )
                ],
            )
            aggregate_preference_insights(message_id=message_id)
            first_pref_id = get_active_learned_preferences()[0]["id"]
            disable_learned_preference(first_pref_id)

            second_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="For coding, I still like shorter answers.",
            )
            save_insights(
                second_id,
                [
                    ExtractedInsight(
                        label="User prefers shorter coding answers",
                        type="preference",
                        confidence=0.96,
                        evidence="For coding, I still like shorter answers.",
                        source="latest_user_message",
                        stability="long_term",
                        preference_key="response.length",
                        preference_value={"target": "concise"},
                        scope="domain",
                        context={"domain": "coding"},
                    )
                ],
            )
            aggregate_preference_insights(message_id=second_id)
            active = get_active_learned_preferences()

        self.assertEqual(len(active), 1)
        self.assertNotEqual(active[0]["id"], first_pref_id)

    def test_relearned_contextual_preference_can_be_disabled_again(self):
        with user_scope("user-123"):
            message_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="For coding, I like shorter answers.",
            )
            for content, confidence in (
                ("For coding, I like shorter answers.", 0.94),
                ("For coding, I still like shorter answers.", 0.96),
            ):
                current_id = message_id if "still" not in content else create_conversation_message(
                    user_id="user-123",
                    role="user",
                    content=content,
                )
                save_insights(
                    current_id,
                    [
                        ExtractedInsight(
                            label="User prefers shorter coding answers",
                            type="preference",
                            confidence=confidence,
                            evidence=content,
                            source="latest_user_message",
                            stability="long_term",
                            preference_key="response.length",
                            preference_value={"target": "concise"},
                            scope="domain",
                            context={"domain": "coding"},
                        )
                    ],
                )
                aggregate_preference_insights(message_id=current_id)
                active = get_active_learned_preferences()
                disable_learned_preference(active[0]["id"])

            self.assertEqual(get_active_learned_preferences(), [])

    def test_negative_examples_preference_becomes_few_examples(self):
        with user_scope("user-123"):
            message_id = create_conversation_message(
                user_id="user-123",
                role="user",
                content="Don't include examples unless I ask.",
            )
            save_insights(
                message_id,
                [
                    ExtractedInsight(
                        label="User does not want examples by default",
                        type="preference",
                        confidence=0.93,
                        evidence="Don't include examples unless I ask.",
                        source="latest_user_message",
                        stability="long_term",
                        preference_key="response.examples",
                        preference_value={"target": "examples"},
                        evidence_polarity="negative",
                    )
                ],
            )
            aggregate_preference_insights(message_id=message_id)
            active = get_active_learned_preferences()

        self.assertEqual(active[0]["value"], {"target": "few"})


if __name__ == "__main__":
    unittest.main()
