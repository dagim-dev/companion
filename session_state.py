from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from curiosity_engine import CuriosityEngine
from internal_state import InternalState
from meta_cognition import MetaCognition
from personality_state import PersonalityState
from self_perception import SelfPerception

if TYPE_CHECKING:
    from companion_prefs import CompanionPreferences


@dataclass
class JarvisState:
    user_id: str
    conversation: list[dict[str, str]] = field(default_factory=list)
    internal_state: InternalState = field(default_factory=InternalState)
    meta_cognition: MetaCognition = field(default_factory=MetaCognition)
    personality_state: PersonalityState = field(default_factory=PersonalityState)
    self_perception: SelfPerception = field(default_factory=SelfPerception)
    curiosity_engine: CuriosityEngine = field(default_factory=CuriosityEngine)
    analyzer: SentimentIntensityAnalyzer = field(
        default_factory=SentimentIntensityAnalyzer
    )
    companion_prefs: Any = None  # CompanionPreferences | None
    turn_count: int = 0
    # Turn index when the current persistence cycle started (resets after each persist).
    persistence_cycle_start_turn: int = 0


def create_state(user_id: str) -> JarvisState:
    return JarvisState(user_id=user_id)
