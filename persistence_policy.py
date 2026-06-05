"""
Runtime personality persistence policy.

Behavior today: free-tier interval (5 turns) everywhere.
Future: subscription tier can lower interval for paying users.

Constraints (current phase): logging + structure only — interval stays 5.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Standard cycle length (free tier). Paid tiers will use lower values later.
FREE_PERSIST_INTERVAL_TURNS = 5
DEFAULT_PERSIST_INTERVAL_TURNS = FREE_PERSIST_INTERVAL_TURNS


def get_persist_interval_turns(user_id: str) -> int:
    """
    Turns between runtime_json writes for this user.

    TODO(subscription): load tier from users / billing; e.g. paid -> 2, free -> 5.
    """
    _ = user_id
    return DEFAULT_PERSIST_INTERVAL_TURNS


@dataclass
class PersistenceCycleClock:
    """
    Per-user turn clock for one persistence cycle.

    cycle_start_turn: turn_count when the current N-turn window started.
    Resets when persistence fires (cycle completes).
    """

    interval_turns: int
    cycle_start_turn: int = 0

    def turns_until_persist(self, current_turn: int) -> int:
        if self.interval_turns <= 0:
            return 0
        elapsed = max(0, current_turn - self.cycle_start_turn)
        remainder = elapsed % self.interval_turns
        if remainder == 0 and elapsed > 0:
            return 0
        if remainder == 0:
            return self.interval_turns
        return self.interval_turns - remainder

    def should_persist(self, current_turn: int) -> bool:
        if self.interval_turns <= 0:
            return False
        elapsed = max(0, current_turn - self.cycle_start_turn)
        return elapsed > 0 and elapsed % self.interval_turns == 0

    def complete_cycle(self, current_turn: int) -> None:
        """Reset clock when persistence runs."""
        self.cycle_start_turn = current_turn


def log_persistence_status(
    user_id: str,
    current_turn: int,
    clock: PersistenceCycleClock,
) -> None:
    remaining = clock.turns_until_persist(current_turn)
    if remaining == 0:
        logger.info(
            "user=%s turn=%s runtime persist this turn (interval=%s cycle_start=%s)",
            user_id,
            current_turn,
            clock.interval_turns,
            clock.cycle_start_turn,
        )
    else:
        logger.info(
            "user=%s turn=%s runtime persist in %s turns (interval=%s cycle_start=%s)",
            user_id,
            current_turn,
            remaining,
            clock.interval_turns,
            clock.cycle_start_turn,
        )


def cycle_timestamp() -> str:
    """ISO timestamp when a persistence cycle completes (for future tier analytics)."""
    return datetime.now(timezone.utc).isoformat()
