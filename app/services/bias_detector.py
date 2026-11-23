import re


BIAS_TERMS = {
    "emotional_language": [
        "disgusting", "outrageous", "terrible", "wonderful",
        "evil", "shocking", "horrific", "brilliant"
    ],

    "loaded_language": [
        "radical", "corrupt", "traitor", "propaganda",
        "extremist", "cowardly", "reckless"
    ],

    "absolute_language": [
        "always", "never", "everyone", "nobody",
        "completely", "undeniably", "impossible"
    ],

    "generalization": [
        "all people", "every single person",
        "none of them", "people like them"
    ]
}


EXPLANATIONS = {
    "emotional_language": (
        "Emotionally charged wording may influence the reader's "
        "reaction rather than presenting information neutrally."
    ),

    "loaded_language": (
        "These terms can carry strong negative or positive "
        "connotations depending on their context."
    ),

    "absolute_language": (
        "Absolute wording may oversimplify a situation or "
        "present a claim without acknowledging exceptions."
    ),

    "generalization": (
        "Broad statements may generalize about groups without "
        "providing sufficient supporting evidence."
    )
}


def get_context(text, start, end, window=60):

    context_start = max(0, start - window)
    context_end = min(len(text), end + window)

    return text[context_start:context_end].strip()


def detect_bias(text):

    if not isinstance(text, str) or not text.strip():

        return {
            "potential_bias_detected": False,
            "findings": [],
            "limitations": "No valid text was provided."
        }

    findings = []

    for category, terms in BIAS_TERMS.items():

        detected = []
        details = []

        for term in terms:

            pattern = r"\b" + re.escape(term) + r"\b"

            matches = list(
                re.finditer(pattern, text, re.IGNORECASE)
            )

            if matches:

                detected.append(term)

                for match in matches:

                    details.append({
                        "term": term,
                        "context": get_context(
                            text,
                            match.start(),
                            match.end()
                        )
                    })

        if detected:

            findings.append({
                "category": category,
                "indicators": detected,
                "occurrences": len(details),
                "examples": details,
                "explanation": EXPLANATIONS[category]
            })

    return {
        "potential_bias_detected": bool(findings),
        "findings": findings,
        "limitations": (
            "These are potential linguistic indicators, not proof "
            "of intentional bias. Context, attribution, sarcasm "
            "and the overall argument must be considered."
        )
    }