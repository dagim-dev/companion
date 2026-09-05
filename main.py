# main.py
import os

from llm import LLMRequestError
from logging_config import configure_logging
from companion_prefs import complete_onboarding, is_onboarding_complete
from memory import init_db, set_profile
from memory_scope import user_scope
from message_processor import process_message
from state_store import get_nova_state

DEFAULT_CLI_USER_ID = os.getenv("CLI_USER_ID", "local-dev")


def main():
    configure_logging()
    init_db()

    with user_scope(DEFAULT_CLI_USER_ID):
        set_profile("name", "Dagi")
        set_profile("communication_style", "direct")

        if not is_onboarding_complete(DEFAULT_CLI_USER_ID):
            complete_onboarding(
                role_id="general_nova",
                communication="direct",
                energy="calm",
                address_as="Friend",
                display_name="Dagi",
                user_id=DEFAULT_CLI_USER_ID,
            )

        state = get_nova_state(DEFAULT_CLI_USER_ID)

        print("AI Companion started. Type 'exit' to quit.\n")

        while True:
            user_input = input("You: ")

            if user_input.lower() == "exit":
                break

            try:
                result = process_message(state, user_input, echo_to_terminal=True)
            except LLMRequestError:
                print(
                    "AI: NOVA could not finish that reply. "
                    "Your message was saved — please retry.\n"
                )
                continue

            if result.get("intent") != "uncertain" or not result.get("skipped"):
                print(f"[DEBUG] Intent: {result.get('intent', 'unknown')}")

            print(f"[RESPONSE TIME] {result['response_time_s']}s")
            print(f"AI: {result['response']}\n")


if __name__ == "__main__":
    main()
