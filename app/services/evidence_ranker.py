import re

from sklearn.feature_extraction.text import (
    TfidfVectorizer,
    ENGLISH_STOP_WORDS
)
from sklearn.metrics.pairwise import cosine_similarity


def normalize_text(text):

    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_evidence_text(result):

    if isinstance(result, str):
        return result

    if not isinstance(result, dict):
        return ""

    # Prioritize the actual extracted evidence sentence.
    fields = [
        result.get("sentence", ""),
        result.get("snippet", ""),
        result.get("content", ""),
        result.get("text", ""),
        result.get("title", "")
    ]

    return " ".join(
        value for value in fields
        if isinstance(value, str) and value.strip()
    ).strip()


def get_claim_keywords(claim):

    return {
        word
        for word in normalize_text(claim).split()
        if word not in ENGLISH_STOP_WORDS
        and len(word) > 2
    }


def rank_evidence(claim, results):

    if not isinstance(claim, str) or not claim.strip():
        return []

    if not isinstance(results, list) or not results:
        return []

    claim_keywords = get_claim_keywords(claim)

    if not claim_keywords:
        return results

    valid_results = []
    evidence_texts = []

    for result in results:

        if not isinstance(result, dict):
            continue

        evidence_text = normalize_text(
            get_evidence_text(result)
        )

        if not evidence_text:
            continue

        valid_results.append(result)
        evidence_texts.append(evidence_text)

    if not valid_results:
        return []

    similarities = [0.0] * len(valid_results)

    try:

        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )

        matrix = vectorizer.fit_transform(
            [normalize_text(claim)] + evidence_texts
        )

        similarities = cosine_similarity(
            matrix[0:1],
            matrix[1:]
        )[0]

    except ValueError:
        pass

    ranked_results = []

    for result, evidence_text, similarity in zip(
        valid_results,
        evidence_texts,
        similarities
    ):

        evidence_words = set(evidence_text.split())

        overlap = claim_keywords.intersection(evidence_words)

        coverage = len(overlap) / len(claim_keywords)

        # Relevance measures textual similarity, NOT truth.
        combined_score = (
            0.75 * float(similarity)
            + 0.25 * coverage
        )

        ranked_result = result.copy()

        ranked_result["relevance_score"] = round(
            combined_score,
            4
        )

        ranked_result["keyword_coverage"] = round(
            coverage,
            4
        )

        ranked_result["ranking_method"] = (
            "TF-IDF + keyword coverage"
        )

        ranked_results.append(ranked_result)

    ranked_results.sort(
        key=lambda item: item["relevance_score"],
        reverse=True
    )

    return ranked_results