import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from reflection_content import (  # noqa: E402
    MAX_REFLECTION_CONTENT_CHARS,
    MAX_REFLECTION_CONTENT_FRAGMENTS,
    REFLECTION_CONTENT_DELIMITER,
    build_bounded_reflection_content,
    count_reflection_fragments,
    normalize_reflection_content,
)


class ReflectionContentHelperTests(unittest.TestCase):
    def test_empty_existing_content_behaves_like_fresh_reflection(self):
        self.assertEqual(
            build_bounded_reflection_content(None, "first mention"),
            "first mention",
        )
        self.assertEqual(
            build_bounded_reflection_content("", "first mention"),
            "first mention",
        )

    def test_append_keeps_only_newest_five_fragments(self):
        existing = REFLECTION_CONTENT_DELIMITER.join(
            [f"fragment-{index}" for index in range(1, 6)]
        )
        result = build_bounded_reflection_content(existing, "fragment-6")

        fragments = result.split(REFLECTION_CONTENT_DELIMITER)
        self.assertEqual(len(fragments), MAX_REFLECTION_CONTENT_FRAGMENTS)
        self.assertEqual(fragments[-1], "fragment-6")
        self.assertEqual(fragments[0], "fragment-2")

    def test_final_string_never_exceeds_character_cap(self):
        long_fragment = "x" * 800
        existing = REFLECTION_CONTENT_DELIMITER.join(
            [long_fragment for _ in range(MAX_REFLECTION_CONTENT_FRAGMENTS)]
        )
        result = build_bounded_reflection_content(existing, "newest")

        self.assertLessEqual(len(result), MAX_REFLECTION_CONTENT_CHARS)
        self.assertTrue(result.endswith("newest"))

    def test_trimming_removes_oldest_content_first(self):
        existing = REFLECTION_CONTENT_DELIMITER.join(
            ["oldest", "middle", "recent-1", "recent-2", "recent-3"]
        )
        result = build_bounded_reflection_content(existing, "newest")

        self.assertNotIn("oldest", result)
        self.assertIn("middle", result)
        self.assertIn("recent-3", result)
        self.assertIn("newest", result)

    def test_single_oversized_fragment_is_trimmed_from_oldest_side(self):
        oversized = "a" * 2000 + "KEEP-NEWEST"
        result = build_bounded_reflection_content(None, oversized)

        self.assertLessEqual(len(result), MAX_REFLECTION_CONTENT_CHARS)
        self.assertTrue(result.endswith("KEEP-NEWEST"))

    def test_normalize_existing_content_without_append(self):
        existing = REFLECTION_CONTENT_DELIMITER.join(
            [f"fragment-{index}" for index in range(1, 8)]
        )
        result = normalize_reflection_content(existing)

        self.assertLessEqual(
            count_reflection_fragments(result),
            MAX_REFLECTION_CONTENT_FRAGMENTS,
        )
        self.assertLessEqual(len(result), MAX_REFLECTION_CONTENT_CHARS)
        self.assertTrue(result.endswith("fragment-7"))


if __name__ == "__main__":
    unittest.main()
