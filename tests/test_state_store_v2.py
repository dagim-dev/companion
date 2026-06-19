import unittest
from types import SimpleNamespace
from unittest import mock

import state_store
from personality_state import PersonalityState


class StateStoreV2Tests(unittest.TestCase):
    def test_hydrate_state_loads_v2_runtime_state_relationship_depth(self):
        state = SimpleNamespace(
            user_id="user-123",
            personality_state=PersonalityState(),
            conversation=[],
            companion_prefs=None,
        )
        prefs = SimpleNamespace(
            runtime_json={
                "schema_version": 2,
                "runtime_state": {"relationship_depth": 0.77},
            }
        )

        with mock.patch.object(state_store, "get_companion_preferences", return_value=prefs), \
                mock.patch.object(state_store, "get_recent_conversations", return_value=[]):
            state_store._hydrate_state(state)

        self.assertEqual(state.personality_state.relationship_depth, 0.77)


if __name__ == "__main__":
    unittest.main()
