import re

from sklearn.feature_extraction.text import (
    TfidfVectorizer,
    ENGLISH_STOP_WORDS
)

from sklearn.metrics.pairwise import cosine_similarity


# ==========================================
# CONFIGURATION
# ==========================================

MIN_WORDS = 6
MAX_SENTENCE_LENGTH = 600

MIN_KEYWORD_COVERAGE = 0.25
MIN_RELEVANCE_SCORE = 0.12

DUPLICATE_SIMILARITY_THRESHOLD = 0.88


# ==========================================
# TEXT NORMALIZATION
# ==========================================

def normalize_text(text):

    if not isinstance(text, str):
        return ""

    text = text.lower()

    text = re.sub(
        r"https?://\S+",
        "",
        text
    )

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ==========================================
# SENTENCE SPLITTING
# ==========================================

def split_into_sentences(text):

    if not isinstance(text, str) or not text.strip():
        return []

    text = re.sub(
        r"={2,}.*?={2,}",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    sentences = re.split(
        r'(?<=[.!?])\s+(?=[A-Z0-9"\'])',
        text
    )

    cleaned = []
    seen = set()

    for sentence in sentences:

        sentence = re.sub(
            r"\s+",
            " ",
            sentence
        ).strip()

        word_count = len(sentence.split())

        if word_count < MIN_WORDS:
            continue

        if len(sentence) > MAX_SENTENCE_LENGTH:
            continue

        normalized = normalize_text(sentence)

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)

        cleaned.append(sentence)

    return cleaned


# ==========================================
# CLAIM KEYWORDS
# ==========================================

def get_claim_keywords(claim):

    return {
        word
        for word in normalize_text(claim).split()
        if word not in ENGLISH_STOP_WORDS
        and len(word) > 2
    }


# ==========================================
# DUPLICATE DETECTION
# ==========================================

def remove_near_duplicates(evidence):

    if not evidence:
        return []

    if len(evidence) == 1:
        return evidence

    sentences = [
        item["sentence"]
        for item in evidence
    ]

    normalized = [
        normalize_text(sentence)
        for sentence in sentences
    ]

    similarities = None

    try:

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2)
        )

        matrix = vectorizer.fit_transform(
            normalized
        )

        similarities = cosine_similarity(matrix)

    except ValueError:
        return evidence

    selected = []

    for index, item in enumerate(evidence):

        duplicate = False

        for selected_index in selected:

            similarity = similarities[
                index,
                selected_index
            ]

            if similarity >= DUPLICATE_SIMILARITY_THRESHOLD:

                duplicate = True
                break

        if not duplicate:
            selected.append(index)

    return [
        evidence[index]
        for index in selected
    ]


# ==========================================
# EVIDENCE TYPE CLASSIFICATION
# ==========================================

DIRECT_INDICATORS = {
    "is", "are", "was", "were",
    "shows", "demonstrates",
    "confirms", "measures",
    "observed", "evidence",
    "indicates", "reveals",
    "orbits", "revolves"
}

CONTEXTUAL_INDICATORS = {
    "history", "historical",
    "proposed", "believed",
    "theory", "theoretical",
    "developed", "discovered",
    "according", "idea",
    "concept", "explained"
}


def classify_evidence(sentence):

    words = set(
        normalize_text(sentence).split()
    )

    direct_matches = words.intersection(
        DIRECT_INDICATORS
    )

    contextual_matches = words.intersection(
        CONTEXTUAL_INDICATORS
    )

    # These labels are linguistic heuristics,
    # not proof of evidential strength.

    if direct_matches and not contextual_matches:

        return {
            "evidence_type": "DIRECT",
            "evidence_quality": 0.8,
            "quality_reason": (
                "The statement directly describes "
                "the claim or a relevant observation."
            )
        }

    if contextual_matches:

        return {
            "evidence_type": "CONTEXTUAL",
            "evidence_quality": 0.5,
            "quality_reason": (
                "The statement provides historical, "
                "theoretical or explanatory context."
            )
        }

    return {
        "evidence_type": "WEAK",
        "evidence_quality": 0.3,
        "quality_reason": (
            "The statement has limited direct "
            "evidential content."
        )
    }


# ==========================================
# RELEVANCE EXTRACTION
# ==========================================

def extract_relevant_evidence(
    claim,
    article_text,
    top_n=5
):

    if not isinstance(claim, str) or not claim.strip():
        return []

    if not isinstance(article_text, str) or not article_text.strip():
        return []

    sentences = split_into_sentences(article_text)

    if not sentences:
        return []

    claim_keywords = get_claim_keywords(claim)

    if not claim_keywords:
        return []

    candidates = []

    # --------------------------------------
    # Keyword filtering
    # --------------------------------------

    for sentence in sentences:

        sentence_words = set(
            normalize_text(sentence).split()
        )

        overlap = claim_keywords.intersection(
            sentence_words
        )

        coverage = (
            len(overlap) / len(claim_keywords)
        )

        if coverage < MIN_KEYWORD_COVERAGE:
            continue

        candidates.append({
            "sentence": sentence,
            "keyword_coverage": coverage
        })

    if not candidates:
        return []

    # --------------------------------------
    # TF-IDF relevance
    # --------------------------------------

    candidate_sentences = [
        item["sentence"]
        for item in candidates
    ]

    similarities = [0.0] * len(candidates)

    try:

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )

        matrix = vectorizer.fit_transform(
            [normalize_text(claim)]
            + [
                normalize_text(sentence)
                for sentence in candidate_sentences
            ]
        )

        similarities = cosine_similarity(
            matrix[0:1],
            matrix[1:]
        )[0]

    except ValueError:
        pass

    # --------------------------------------
    # Build evidence results
    # --------------------------------------

    ranked = []

    for candidate, similarity in zip(
        candidates,
        similarities
    ):

        relevance = (
            0.75 * float(similarity)
            + 0.25 * candidate["keyword_coverage"]
        )

        if relevance < MIN_RELEVANCE_SCORE:
            continue

        evidence_classification = classify_evidence(
            candidate["sentence"]
        )

        ranked.append({

            "sentence": candidate["sentence"],

            "relevance_score": round(
                relevance,
                4
            ),

            "keyword_coverage": round(
                candidate["keyword_coverage"],
                4
            ),

            "evidence_type": (
                evidence_classification["evidence_type"]
            ),

            "evidence_quality": (
                evidence_classification["evidence_quality"]
            ),

            "quality_reason": (
                evidence_classification["quality_reason"]
            )

        })

    # --------------------------------------
    # Sort by relevance
    # --------------------------------------

    ranked.sort(
        key=lambda item: item["relevance_score"],
        reverse=True
    )

    # --------------------------------------
    # Remove near-duplicates
    # --------------------------------------

    ranked = remove_near_duplicates(ranked)

    # --------------------------------------
    # Return requested number
    # --------------------------------------

    try:

        limit = max(
            1,
            min(int(top_n), 20)
        )

    except (ValueError, TypeError):

        limit = 5

    return ranked[:limit]