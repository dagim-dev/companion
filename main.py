# main.py
from memory import init_db, set_profile
from message_processor import process_message
from session_state import create_state


def main():
    init_db()

    set_profile("name", "Dagi")
    set_profile("communication_style", "direct")

    state = create_state()

    print("AI Companion started. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() == "exit":
            break

        result = process_message(state, user_input, echo_to_terminal=True)

        if result.get("intent") != "uncertain" or not result.get("skipped"):
            print(f"[DEBUG] Intent: {result.get('intent', 'unknown')}")

        print(f"[RESPONSE TIME] {result['response_time_s']}s")
        print(f"AI: {result['response']}\n")


if __name__ == "__main__":
    main()
