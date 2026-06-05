import random


SHORT_ACKNOWLEDGEMENTS = [

    "I see.",
    "Interesting.",
    "Right.",
    "Understood.",
    "Fair enough.",
    "Noted.",
    "Hm.",
    "Makes sense."
]


OBSERVATIONAL_INSERTS = [

    "That detail seems important.",
    "You hesitated there mentally.",
    "There's probably more behind that.",
    "That didn't sound accidental.",
    "You sound more certain than before."
]


def apply_rhythm(response, intent, intensity):

    modified = response

    # =====================================================
    # OCCASIONAL SHORT OPENINGS
    # =====================================================

    if random.random() < 0.22:

        opening = random.choice(
            SHORT_ACKNOWLEDGEMENTS
        )

        modified = f"{opening} {modified}"

    # =====================================================
    # OCCASIONAL OBSERVATIONAL ENDINGS
    # =====================================================

    if intensity > 0.45 and random.random() < 0.28:

        observation = random.choice(
            OBSERVATIONAL_INSERTS
        )

        modified += f"\n\n{observation}"

    # =====================================================
    # RHYTHM BREAKS
    # =====================================================

    if len(modified) > 220 and random.random() < 0.35:

        modified = modified.replace(". ", ".\n\n", 1)

    return modified