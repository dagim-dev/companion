from dataclasses import dataclass, field
from typing import Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from curiosity_engine import CuriosityEngine
from internal_state import InternalState
from meta_cognition import MetaCognition
from personality_state import PersonalityState
from self_perception import SelfPerception
from thought_engine import ThoughtEngine


@dataclass
class JarvisState:
    conversation: list[dict[str, str]] = field(default_factory=list)
    internal_state: InternalState = field(default_factory=InternalState)
    meta_cognition: MetaCognition = field(default_factory=MetaCognition)
    personality_state: PersonalityState = field(default_factory=PersonalityState)
    thought_engine: ThoughtEngine = field(default_factory=ThoughtEngine)
    self_perception: SelfPerception = field(default_factory=SelfPerception)
    curiosity_engine: CuriosityEngine = field(default_factory=CuriosityEngine)
    analyzer: SentimentIntensityAnalyzer = field(
        default_factory=SentimentIntensityAnalyzer
    )


def create_state() -> JarvisState:
    return JarvisState()
