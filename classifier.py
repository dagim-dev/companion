from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def classify_intent(message):
    intent_scores = _score_intents(message)

    # --- PICK BEST INTENT ---
    best_intent = max(intent_scores, key=intent_scores.get)
    confidence = intent_scores[best_intent]

    # --- UNCERTAINTY CHECK ---
    if confidence < 0.5:
        return "casual_talk"

    return best_intent


def _score_intents(message):
    msg = message.lower()
    sentiment = analyzer.polarity_scores(msg)

    intent_scores = {
        "help_request": 0.0,
        "anxiety_stress": 0.0,
        "reflection": 0.0,
        "casual_talk": 0.0,
        "technical_problem": 0.0
    }

    # --- RULE 1: help request ---
    help_keywords = ["what should i do", "help me", "what now", "advice"]
    for k in help_keywords:
        if k in msg:
            intent_scores["help_request"] += 0.6

    # --- RULE 2: anxiety / stress ---
    stress_keywords = ["anxious", "stress", "nervous", "overwhelmed", "scared"]
    for k in stress_keywords:
        if k in msg:
            intent_scores["anxiety_stress"] += 0.6

    technical_keywords = [
        "code",
        "python",
        "bug",
        "error",
        "programming",
        "algorithm",
        "project"
    ]

    for k in technical_keywords:
        if k in msg:
            intent_scores["technical_problem"] += 0.5

    if sentiment["compound"] < -0.5:
        intent_scores["anxiety_stress"] += 0.4

    # --- RULE 3: reflection ---
    reflection_keywords = ["i think", "i feel", "i've been", "today was", "lately"]
    for k in reflection_keywords:
        if k in msg:
            intent_scores["reflection"] += 0.5

    # --- DEFAULT casual boost ---
    intent_scores["casual_talk"] += 0.2  # small baseline

    return intent_scores


def intent_confidence(message, intent=None):
    intent_scores = _score_intents(message)
    selected_intent = intent or max(intent_scores, key=intent_scores.get)
    if selected_intent == "casual_talk" and max(intent_scores.values()) < 0.5:
        return intent_scores["casual_talk"]
    return intent_scores.get(selected_intent, 0.0)

def detect_emotion(message, sentiment):

    msg = message.lower()

    compound = sentiment["compound"]

    # =====================================================
    # ADVANCED KEYWORD SIGNALS
    # =====================================================

    emotion_map = {

        "stress": [
            "overwhelmed",
            "too much",
            "pressure",
            "burned out",
            "exhausted"
        ],

        "anxiety": [
            "anxious",
            "nervous",
            "worried",
            "panic",
            "scared"
        ],

        "sad": [
            "empty",
            "lonely",
            "sad",
            "down",
            "hopeless"
        ],

        "anger": [
            "angry",
            "frustrated",
            "mad",
            "annoyed"
        ]
    }

    for emotion, keywords in emotion_map.items():

        matches = sum(1 for k in keywords if k in msg)

        if matches >= 1:

            confidence = min(0.95, 0.55 + (matches * 0.1))

            return emotion, confidence

    # =====================================================
    # SENTIMENT FALLBACK
    # =====================================================

    if compound <= -0.6:
        return "negative", abs(compound)

    elif compound >= 0.6:
        return "positive", compound

    return "neutral", 0.3