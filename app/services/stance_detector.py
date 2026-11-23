def detect_stance(claim, evidence):
    """
    Conservative stance classification.

    This module identifies relevance, not truth.
    It deliberately avoids predicting support or contradiction.
    """

    if not claim or not evidence:
        return "uncertain"

    return "potentially_relevant"


def analyze_evidence_stances(claim, evidence_items):

    analyzed = []

    for item in evidence_items:

        result = item.copy()

        text = (
            result.get("sentence")
            or result.get("snippet")
            or result.get("content")
            or ""
        )

        if not text.strip():
            stance = "uncertain"

        else:
            stance = detect_stance(claim, text)

        result["stance"] = stance
        result["stance_method"] = "conservative_classification"

        analyzed.append(result)

    return analyzed