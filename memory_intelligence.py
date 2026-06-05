# -------------------------
# MAIN ENTRY POINT
# -------------------------
def extract_user_insights(conversation, emotional_profile):
    insights = {
        "traits": set(),
        "interests": set(),
        "issues": set()
    }

    for msg in conversation:
        text = normalize_text(msg.get("content", ""))

        if not text:
            continue

        detect_traits(text, insights)
        detect_interests(text, insights)
        detect_issues(text, insights, emotional_profile)

    return {
        "traits": list(insights["traits"]),
        "interests": list(insights["interests"]),
        "issues": list(insights["issues"])
    }


# -------------------------
# TEXT PREPROCESSING
# -------------------------
def normalize_text(text):
    return text.lower().strip()


# -------------------------
# TRAITS DETECTION
# -------------------------
def detect_traits(text, insights):
    trait_patterns = {
        "habit-driven": ["i always", "i usually", "i tend to"],
        "overthinker": ["i overthink", "i think too much"],
        "procrastinator": ["i procrastinate", "i delay things"],
        "self-aware": ["i know i", "i realize i"],
    }

    for trait, patterns in trait_patterns.items():
        if any(p in text for p in patterns):
            insights["traits"].add(trait)


# -------------------------
# INTEREST DETECTION
# -------------------------
def detect_interests(text, insights):
    interest_keywords = {
    # -------------------------
    # FITNESS & PERFORMANCE
    # -------------------------
    "calisthenics": [
        "calisthenics", "pull up", "push up", "dip", "muscle up",
        "bodyweight", "handstand", "rings", "planche", "front lever"
    ],

    "body_optimization": [
        "recovery", "protein", "sleep", "mobility", "flexibility",
        "performance", "gains", "progress", "routine", "discipline"
    ],

    # -------------------------
    # SCIENCE & SPACE
    # -------------------------
    "space": [
        "space", "nasa", "galaxy", "universe", "black hole",
        "planet", "cosmos", "orbit", "solar system",
        "rocket", "astronaut", "mars", "moon"
    ],

    "science_discovery": [
        "discovery", "breakthrough", "new study", "research",
        "scientists found", "new finding"
    ],

    # -------------------------
    # MONEY & OPPORTUNITY
    # -------------------------
    "making_money": [
        "make money", "income", "side hustle", "passive income",
        "profit", "revenue", "monetize", "cash flow",
        "investing", "returns"
    ],

    "trend_analysis": [
        "trend", "trending", "viral", "market",
        "opportunity", "demand", "emerging"
    ],

    # -------------------------
    # MIND & SPIRIT
    # -------------------------
    "mindfulness": [
        "meditate", "inner peace", "mindfulness", "present moment",
        "breathe", "awareness", "calm", "clear my head",
        "relax", "unwind", "focused", "grounded", "higher conscious"
    ]
}

    for interest, keywords in interest_keywords.items():
        match_count = sum(1 for word in keywords if word in text)

        if match_count >= 1:  # you can tune this later
            insights["interests"].add(interest)


# -------------------------
# ISSUE DETECTION
# -------------------------
def detect_issues(text, insights, emotional_profile):
    emotion = emotional_profile.get("current_emotion")

    # emotion-based detection
    if emotion == "stress":
        insights["issues"].add("stress")

    if emotion == "sad":
        insights["issues"].add("low mood")

    # keyword-based detection
    issue_patterns = {
        "burnout": ["burnout", "exhausted", "drained"],
        "focus problems": ["can't focus", "distracted", "no focus"],
        "motivation issues": ["no motivation", "can't start", "lazy"],
        "anxiety": ["anxious", "worried", "nervous"],
    }

    for issue, patterns in issue_patterns.items():
        if any(p in text for p in patterns):
            insights["issues"].add(issue)