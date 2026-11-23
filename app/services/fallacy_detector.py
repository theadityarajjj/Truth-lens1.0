import re


FALLACY_PATTERNS = {

    "ad_hominem": [
        r"\byou are (an )?(idiot|stupid|ignorant)\b",
        r"\bthey are (all )?(idiots|stupid|fools)\b",
        r"\bignore .{2,60} because .{2,60} is (an? )?(idiot|fool)\b"
    ],

    "false_dilemma": [
        r"\beither .{3,80} or .{3,80}\b",
        r"\bthere are only two choices\b",
        r"\bno other option\b",
        r"\byou are either with us or against us\b"
    ],

    "appeal_to_authority": [
        r"\ban expert said\b",
        r"\ba famous person said\b",
        r"\bbecause .{2,50} said so\b",
        r"\bit must be true because .{2,50} said so\b"
    ],

    "bandwagon": [
        r"\beveryone believes\b",
        r"\beverybody is doing it\b",
        r"\bmost people believe\b",
        r"\beveryone agrees\b"
    ],

    "slippery_slope": [
        r"\bif we allow this, .{3,100} will happen\b",
        r"\bthis will eventually lead to\b",
        r"\bif this continues, .{3,100} will happen\b"
    ],

    "hasty_generalization": [
        r"\bone person .{3,80} therefore everyone\b",
        r"\bone example proves\b",
        r"\bthis proves that all .{2,60}\b",
        r"\bbecause one .{2,60} all .{2,60}\b"
    ],

    "straw_man": [
        r"\bso you are saying that .{3,100}\b",
        r"\byour argument is basically that .{3,100}\b"
    ],

    "circular_reasoning": [
        r"\bit is true because it is true\b",
        r"\bthis is correct because it is the correct thing\b"
    ],

    "appeal_to_emotion": [
        r"\bif you have a heart, you will\b",
        r"\bonly a monster would disagree\b",
        r"\byou should agree if you care about\b"
    ]
}


FALLACY_EXPLANATIONS = {

    "ad_hominem":
        "The wording may attack a person instead of addressing "
        "the person's argument.",

    "false_dilemma":
        "The wording may present limited choices while overlooking "
        "other possible alternatives.",

    "appeal_to_authority":
        "The argument may rely on someone's authority rather than "
        "providing supporting evidence.",

    "bandwagon":
        "The argument may use popularity as evidence that a claim "
        "is true or correct.",

    "slippery_slope":
        "The argument may assume that one action will inevitably "
        "trigger a chain of consequences without sufficient support.",

    "hasty_generalization":
        "The argument may draw a broad conclusion from too few examples.",

    "straw_man":
        "The wording may misrepresent an opposing argument instead "
        "of addressing its actual position.",

    "circular_reasoning":
        "The argument may use its conclusion as support for itself.",

    "appeal_to_emotion":
        "The argument may rely on emotional pressure instead of "
        "relevant supporting reasons."
}


def detect_fallacies(text):

    if not isinstance(text, str) or not text.strip():

        return {
            "potential_fallacies_detected": False,
            "findings": [],
            "limitations": "No valid text was provided."
        }

    findings = []

    for fallacy, patterns in FALLACY_PATTERNS.items():

        matches = []
        seen = set()

        for pattern in patterns:

            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE
            ):

                example = match.group(0).strip()

                normalized = example.lower()

                if normalized in seen:
                    continue

                seen.add(normalized)

                matches.append({
                    "matched_text": example,
                    "start": match.start(),
                    "end": match.end()
                })

        if matches:

            findings.append({

                "fallacy": fallacy,

                "examples": [
                    item["matched_text"]
                    for item in matches
                ],

                "occurrences": len(matches),

                "explanation": FALLACY_EXPLANATIONS[fallacy],

                "details": matches
            })

    return {

        "potential_fallacies_detected": bool(findings),

        "findings": findings,

        "limitations": (
            "These results identify possible linguistic indicators, "
            "not confirmed logical fallacies. Full argument context "
            "and reasoning must be examined before making a conclusion."
        )
    }