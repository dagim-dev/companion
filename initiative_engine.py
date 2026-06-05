import random


OBSERVATIONS = [
    "You seem more focused today.",
    "Your tone is calmer than earlier.",
    "You sound mentally exhausted, Sir.",
    "You're thinking several steps ahead again.",
    "That seems unusually important to you."
]



def maybe_add_initiative(intent, intensity):

    if intent == "casual_talk":
        return None

    if intensity < 0.5:
        return None

    if random.random() > 0.18:
        return None

    return random.choice(OBSERVATIONS)