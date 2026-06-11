"""Memory follow-up engine.

Responsibility: decide *whether* a proactive memory follow-up should happen,
*which* memory it should be about, and *which* follow-up category to use.

The final wording is delegated to a small text layer (`generate_followup_text`)
that prefers an LLM phrasing but always has a deterministic template fallback.
Policy (gating, ranking, category) is code-based; only the surface wording is
optionally model-generated. This keeps behaviour controllable and cheap: the
LLM is the last step and only runs on the small fraction of turns that pass
every gate.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from episodic_memory import (
    get_last_followup_at,
    retrieve_followup_candidates,
    set_last_followup_at,
)


# =====================================================
# CONFIGURATION (no magic numbers below this block)
# =====================================================

# Gate 1: relationship depth required before any follow-up.
MIN_RELATIONSHIP_DEPTH = 0.35

# Gate 2: minimum spacing between two proactive follow-ups for one user.
MIN_FOLLOWUP_INTERVAL_HOURS = 24

# Gate 4: probability that an otherwise-eligible turn produces a follow-up.
# Tuned so Jarvis brings memories up in roughly 5-10% of eligible conversations.
FOLLOWUP_PROBABILITY = 0.08
# When the best candidate is only weakly related to the current topic we still
# allow the occasional spontaneous check-in, but far more rarely.
LOW_RELEVANCE_PROBABILITY = 0.02

# Gate 3: a candidate counts as "related to the current topic" at/above this
# lexical-overlap similarity.
RELEVANCE_SIMILARITY_THRESHOLD = 0.12

# How many recent episodes to consider when ranking.
CANDIDATE_LIMIT = 12

# Toggle for the optional LLM wording layer. When False (or on any model
# error) the deterministic template path is used.
USE_LLM_WORDING = True

# --- Ranking weights -------------------------------------------------------

# Emotional significance per emotion (drives emotional_strength_weight).
EMOTION_WEIGHTS = {
    "stress": 1.0,
    "anxiety": 1.0,
    "fear": 0.95,
    "sad": 0.9,
    "anger": 0.85,
    "frustration": 0.8,
    "uncertainty": 0.75,
    "motivation": 0.7,
    "pride": 0.65,
    "excitement": 0.65,
    "curiosity": 0.55,
    "joy": 0.5,
    "positive": 0.4,
    "neutral": 0.2,
}
DEFAULT_EMOTION_WEIGHT = 0.3

# Recency buckets (hours -> weight). Newer events score higher; very old
# events are deprioritised.
RECENCY_WEIGHTS = (
    (24, 1.0),       # last day
    (72, 0.8),       # last 3 days
    (168, 0.6),      # last week
    (336, 0.4),      # last 2 weeks
    (720, 0.2),      # last month
)
STALE_RECENCY_WEIGHT = 0.05  # older than the last bucket

# Coefficients combining the scoring factors.
RECENCY_COEFF = 1.0
EMOTION_COEFF = 1.3
UNRESOLVED_COEFF = 2.2          # unresolved events should often outrank others
TOPIC_SIMILARITY_COEFF = 1.6
IMPORTANCE_COEFF = 1.2

# Memories below this importance are treated as trivial and skipped entirely.
MIN_IMPORTANCE = 0.15


# =====================================================
# TYPES
# =====================================================


class FollowupType(Enum):
    PROGRESS = "progress"
    REFLECTION = "reflection"
    EMOTIONAL = "emotional"
    GOAL = "goal"
    RESOLUTION = "resolution"


@dataclass
class FollowupCandidate:
    summary: str
    emotion: str
    importance: float
    resolved: bool
    created_at: Optional[datetime]
    episode_id: Optional[int] = None
    score: float = 0.0
    similarity: float = 0.0
    factors: dict = field(default_factory=dict)


# Emotions we treat as negative/heavy for category + tone selection.
NEGATIVE_EMOTIONS = {"stress", "anxiety", "sad", "anger", "frustration", "fear"}
# Emotions oriented toward forward action / aspiration.
GOAL_EMOTIONS = {"motivation", "curiosity"}


# =====================================================
# RELATIONSHIP-DEPTH TONE TIERS
# =====================================================
# Openers warm up as the relationship deepens.

RESERVED_OPENERS = (
    "You mentioned",
    "You brought up",
    "Earlier you talked about",
)
FAMILIAR_OPENERS = (
    "I remember you talking about",
    "I recall you mentioning",
    "You'd been thinking about",
)
PERSONAL_OPENERS = (
    "Last time we spoke, you seemed caught up in",
    "I've been thinking about what you said about",
    "You seemed really invested in",
)


def _opener_pool(relationship_depth: float) -> tuple:
    if relationship_depth >= 0.75:
        return PERSONAL_OPENERS
    if relationship_depth >= 0.50:
        return FAMILIAR_OPENERS
    return RESERVED_OPENERS


# =====================================================
# EMOTION -> QUESTION STYLE
# =====================================================
# Each emotion maps to a phrasing that fits how a close friend would check in.

EMOTION_QUESTION_STYLES = {
    "stress": "How have you been feeling about that lately?",
    "anxiety": "Has that been weighing on you any less?",
    "sad": "How are you holding up with that these days?",
    "fear": "Are you feeling any steadier about that now?",
    "anger": "Did things ever settle down with that?",
    "frustration": "Did that ever get any less frustrating?",
    "uncertainty": "Have things gotten any clearer with that?",
    "motivation": "Have you made any progress on that?",
    "pride": "Are you still feeling good about how that went?",
    "excitement": "Did it end up being as exciting as you expected?",
    "curiosity": "Did you ever find out more about that?",
    "joy": "Is that still going well for you?",
    "positive": "How's that been going since?",
    "neutral": "How did that end up going?",
}
DEFAULT_QUESTION = "How did that end up going?"

# Category-specific phrasing used when it fits better than the emotion phrasing.
TYPE_QUESTIONS = {
    FollowupType.PROGRESS: "How did that turn out?",
    FollowupType.REFLECTION: "What do you think about it now?",
    FollowupType.GOAL: "Have you taken any steps toward it?",
    FollowupType.RESOLUTION: "Did everything end up working out?",
}


# =====================================================
# RANKING
# =====================================================

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for",
    "with", "about", "that", "this", "it", "is", "was", "were", "be", "been",
    "i", "you", "we", "they", "he", "she", "my", "your", "our", "me",
    "have", "has", "had", "do", "did", "doing", "at", "as", "so", "if",
    "then", "than", "really", "just", "very", "feel", "feeling", "felt",
}


def _content_words(text: str) -> set:
    if not text:
        return set()
    return {
        w for w in _WORD_RE.findall(text.lower())
        if w not in _STOPWORDS and len(w) > 2
    }


def topic_similarity(summary: str, current_topic: str) -> float:
    """Lightweight lexical overlap (Jaccard over content words). No model
    calls, so this stays cheap enough to run on every turn."""
    a = _content_words(summary)
    b = _content_words(current_topic)
    if not a or not b:
        return 0.0
    intersection = a & b
    union = a | b
    return len(intersection) / len(union)


def _parse_timestamp(value) -> Optional[datetime]:
    if not value:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _recency_weight(created_at: Optional[datetime], now: datetime) -> float:
    if created_at is None:
        return STALE_RECENCY_WEIGHT
    age_hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
    for max_hours, weight in RECENCY_WEIGHTS:
        if age_hours <= max_hours:
            return weight
    return STALE_RECENCY_WEIGHT


def _score_candidate(
    candidate: FollowupCandidate,
    current_topic: str,
    now: datetime,
) -> None:
    recency = _recency_weight(candidate.created_at, now)
    emotion_weight = EMOTION_WEIGHTS.get(
        candidate.emotion, DEFAULT_EMOTION_WEIGHT
    )
    unresolved_weight = 1.0 if not candidate.resolved else 0.0
    similarity = topic_similarity(candidate.summary, current_topic)
    importance = candidate.importance if candidate.importance is not None else 0.5

    score = (
        RECENCY_COEFF * recency
        + EMOTION_COEFF * emotion_weight
        + UNRESOLVED_COEFF * unresolved_weight
        + TOPIC_SIMILARITY_COEFF * similarity
        + IMPORTANCE_COEFF * importance
    )

    candidate.similarity = similarity
    candidate.score = score
    candidate.factors = {
        "recency": recency,
        "emotion": emotion_weight,
        "unresolved": unresolved_weight,
        "similarity": similarity,
        "importance": importance,
    }


def _to_candidate(row: dict) -> FollowupCandidate:
    return FollowupCandidate(
        summary=row.get("summary") or "",
        emotion=(row.get("emotion") or "neutral"),
        importance=row.get("importance") if row.get("importance") is not None else 0.5,
        resolved=bool(row.get("resolved")),
        created_at=_parse_timestamp(row.get("created_at")),
        episode_id=row.get("id"),
    )


def rank_followup_candidates(
    candidates: list[dict],
    current_topic: str,
    now: Optional[datetime] = None,
) -> list[FollowupCandidate]:
    """Score and sort candidate memories. Trivial memories are dropped.

    score = recency_weight + emotional_strength_weight + unresolved_topic_weight
            + current_topic_similarity + user_importance_weight
    """
    now = now or datetime.now()
    ranked: list[FollowupCandidate] = []
    for row in candidates:
        candidate = _to_candidate(row)
        if not candidate.summary:
            continue
        if (candidate.importance or 0.0) < MIN_IMPORTANCE:
            continue
        _score_candidate(candidate, current_topic, now)
        ranked.append(candidate)

    ranked.sort(key=lambda c: c.score, reverse=True)
    return ranked


# =====================================================
# CATEGORY SELECTION
# =====================================================


def select_followup_type(candidate: FollowupCandidate) -> FollowupType:
    """Pick a follow-up category from memory metadata."""
    if not candidate.resolved:
        # Open situations: ask how they resolved or progressed.
        if candidate.emotion in GOAL_EMOTIONS:
            return FollowupType.GOAL
        return FollowupType.RESOLUTION
    if candidate.emotion in GOAL_EMOTIONS:
        return FollowupType.GOAL
    if candidate.emotion in NEGATIVE_EMOTIONS:
        return FollowupType.EMOTIONAL
    return FollowupType.REFLECTION


# =====================================================
# WORDING (template fallback + optional LLM)
# =====================================================


def _clean_summary(summary: str) -> str:
    text = summary.strip().rstrip(".")
    # Lead with lowercase so it reads naturally after an opener.
    if text and text[0].isupper() and not text.isupper():
        text = text[0].lower() + text[1:]
    return text


def _question_for(candidate: FollowupCandidate, followup_type: FollowupType) -> str:
    if followup_type == FollowupType.EMOTIONAL:
        return EMOTION_QUESTION_STYLES.get(candidate.emotion, DEFAULT_QUESTION)
    if followup_type in TYPE_QUESTIONS:
        # Prefer an emotion-specific phrasing when we have a strong one.
        if candidate.emotion in EMOTION_QUESTION_STYLES and (
            followup_type in (FollowupType.RESOLUTION, FollowupType.GOAL)
        ):
            return EMOTION_QUESTION_STYLES[candidate.emotion]
        return TYPE_QUESTIONS[followup_type]
    return EMOTION_QUESTION_STYLES.get(candidate.emotion, DEFAULT_QUESTION)


def build_template_followup(
    candidate: FollowupCandidate,
    relationship_depth: float,
    followup_type: FollowupType,
) -> str:
    """Deterministic, no-I/O wording. Used as the LLM fallback."""
    opener = random.choice(_opener_pool(relationship_depth))
    summary = _clean_summary(candidate.summary)
    question = _question_for(candidate, followup_type)
    return f"{opener} {summary}. {question}"


def generate_followup_text(
    memory_summary: str,
    emotion: str,
    relationship_depth: float,
    followup_type: FollowupType,
) -> str:
    """Produce a single natural follow-up question.

    Prefers an LLM phrasing (1-2 sentences, conversational, never therapeutic,
    never referencing internal system concepts) and always falls back to the
    deterministic template if the LLM is disabled or unavailable.
    """
    candidate = FollowupCandidate(
        summary=memory_summary,
        emotion=emotion or "neutral",
        importance=0.5,
        resolved=followup_type
        not in (FollowupType.RESOLUTION, FollowupType.GOAL),
        created_at=None,
    )

    if not USE_LLM_WORDING:
        return build_template_followup(candidate, relationship_depth, followup_type)

    try:
        return _llm_followup_text(
            memory_summary, emotion, relationship_depth, followup_type
        )
    except Exception:
        return build_template_followup(candidate, relationship_depth, followup_type)


def _warmth_hint(relationship_depth: float) -> str:
    if relationship_depth >= 0.75:
        return "warm, personal, like a close friend who remembers details"
    if relationship_depth >= 0.50:
        return "familiar and friendly, but not overly intimate"
    return "gentle and a little reserved"


def _llm_followup_text(
    memory_summary: str,
    emotion: str,
    relationship_depth: float,
    followup_type: FollowupType,
) -> str:
    # Imported lazily so the module (and tests) don't require the LLM client.
    from openai import OpenAI
    from config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)

    system = (
        "You write a single short, natural follow-up question that a close "
        "friend would casually bring up about something the person mentioned "
        "before. Constraints: 1-2 sentences maximum, conversational, never "
        "therapeutic or clinical, never sound like a counselor, never mention "
        "memory systems, scores, or any internal concepts. Output only the "
        "question text."
    )
    user = (
        f"They previously brought up: {memory_summary}\n"
        f"Their emotion at the time: {emotion}\n"
        f"Follow-up angle: {followup_type.value}\n"
        f"Tone: {_warmth_hint(relationship_depth)}\n"
        "Write the follow-up now."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=60,
    )

    text = (response.choices[0].message.content or "").strip().strip('"')
    if not text:
        raise ValueError("empty LLM follow-up")
    return text


# =====================================================
# DECISION PIPELINE (main entry point)
# =====================================================


def decide_followup(
    emotional_profile,
    patterns,
    relationship_depth: float,
    current_topic: str,
    user_id: Optional[str] = None,
    *,
    now: Optional[datetime] = None,
) -> Optional[str]:
    """Run the layered gate pipeline. Returns follow-up text or None.

    Gates, cheapest first: relationship -> cooldown -> candidate retrieval ->
    ranking -> topic relevance -> probability. The LLM wording step runs last,
    only once a follow-up is committed.
    """
    now = now or datetime.now()

    # Gate 1: relationship depth.
    if relationship_depth < MIN_RELATIONSHIP_DEPTH:
        return None

    # Gate 2: cooldown.
    last = get_last_followup_at(user_id)
    if last is not None:
        if now - last < timedelta(hours=MIN_FOLLOWUP_INTERVAL_HOURS):
            return None

    # Retrieve + rank.
    rows = retrieve_followup_candidates(limit=CANDIDATE_LIMIT)
    if not rows:
        return None

    ranked = rank_followup_candidates(rows, current_topic, now=now)
    if not ranked:
        return None

    best = ranked[0]

    # Gate 3 + 4: relevance-aware probability.
    relevant = best.similarity >= RELEVANCE_SIMILARITY_THRESHOLD or not best.resolved
    probability = FOLLOWUP_PROBABILITY if relevant else LOW_RELEVANCE_PROBABILITY
    if random.random() > probability:
        return None

    followup_type = select_followup_type(best)
    text = generate_followup_text(
        best.summary,
        best.emotion,
        relationship_depth,
        followup_type,
    )

    # Record the cooldown only once we actually emit a follow-up.
    set_last_followup_at(user_id, now)
    return text


# Backwards-compatible alias for the previous public name.
def generate_followup(emotional_profile, patterns, relationship_depth, current_topic="", user_id=None):
    return decide_followup(
        emotional_profile,
        patterns,
        relationship_depth,
        current_topic,
        user_id,
    )
