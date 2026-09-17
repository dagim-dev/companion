from __future__ import annotations

REFLECTION_CONTENT_DELIMITER = " || "
MAX_REFLECTION_CONTENT_FRAGMENTS = 5
MAX_REFLECTION_CONTENT_CHARS = 1500


def count_reflection_fragments(content: str | None) -> int:
    if not content:
        return 0
    return len(split_reflection_fragments(content))


def split_reflection_fragments(content: str) -> list[str]:
    if not content:
        return []
    return [fragment for fragment in content.split(REFLECTION_CONTENT_DELIMITER) if fragment]


def join_reflection_fragments(fragments: list[str]) -> str:
    return REFLECTION_CONTENT_DELIMITER.join(fragments)


def _trim_single_fragment(fragment: str) -> str:
    if len(fragment) <= MAX_REFLECTION_CONTENT_CHARS:
        return fragment
    return fragment[-MAX_REFLECTION_CONTENT_CHARS:]


def _apply_fragment_cap(fragments: list[str]) -> list[str]:
    if len(fragments) <= MAX_REFLECTION_CONTENT_FRAGMENTS:
        return fragments
    return fragments[-MAX_REFLECTION_CONTENT_FRAGMENTS:]


def _apply_character_cap(fragments: list[str]) -> list[str]:
    bounded = list(fragments)

    while bounded:
        joined = join_reflection_fragments(bounded)
        if len(joined) <= MAX_REFLECTION_CONTENT_CHARS:
            return bounded

        if len(bounded) == 1:
            return [_trim_single_fragment(bounded[0])]

        bounded.pop(0)

    return []


def _normalize_fragments(fragments: list[str]) -> str:
    bounded = _apply_fragment_cap(fragments)
    bounded = _apply_character_cap(bounded)
    return join_reflection_fragments(bounded)


def build_bounded_reflection_content(
    existing_content: str | None,
    new_fragment: str | None = None,
) -> str:
    fragments = split_reflection_fragments(existing_content or "")

    if new_fragment:
        fragments.append(new_fragment)

    return _normalize_fragments(fragments)


def normalize_reflection_content(content: str | None) -> str:
    return _normalize_fragments(split_reflection_fragments(content or ""))
