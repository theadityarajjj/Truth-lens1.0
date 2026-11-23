from urllib.parse import urlsplit

from app.services.source_classifier import classify_source


# ==========================================
# DOMAIN INDICATORS
# ==========================================

DOMAIN_SCORES = {
    "government": 0.95,
    "academic": 0.90,
    "scientific": 0.90,
    "international_organization": 0.90,
    "news": 0.75,
    "reference": 0.65,
    "other": 0.50,
    "unknown": 0.40
}


# ==========================================
# ARTICLE TRANSPARENCY
# ==========================================

def assess_article_transparency(
    title=None,
    author=None,
    published_date=None,
    content=None
):

    indicators = {
        "title_available": bool(
            isinstance(title, str) and title.strip()
        ),

        "author_available": bool(
            isinstance(author, str) and author.strip()
        ),

        "publication_date_available": bool(
            isinstance(published_date, str)
            and published_date.strip()
        ),

        "content_available": bool(
            isinstance(content, str) and content.strip()
        )
    }

    available = sum(indicators.values())

    total = len(indicators)

    transparency_score = round(
        available / total,
        4
    )

    return {
        "article_transparency_score": transparency_score,
        "transparency_indicators": indicators,
        "available_metadata_fields": available,
        "total_metadata_fields": total
    }


# ==========================================
# URL VALIDATION
# ==========================================

def assess_url(url):

    if not isinstance(url, str) or not url.strip():

        return {
            "url_valid": False,
            "https_used": False,
            "url_assessment": "Missing or invalid URL."
        }

    try:

        parsed = urlsplit(url.strip())

        valid = (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )

        return {
            "url_valid": valid,

            "https_used": (
                valid and parsed.scheme == "https"
            ),

            "url_assessment": (
                "Valid HTTP/HTTPS URL."
                if valid
                else "URL format is invalid or unsupported."
            )
        }

    except Exception:

        return {
            "url_valid": False,
            "https_used": False,
            "url_assessment": "URL could not be evaluated."
        }


# ==========================================
# MAIN SOURCE ASSESSMENT
# ==========================================

def assess_source(
    url,
    title=None,
    author=None,
    published_date=None,
    content=None
):

    # --------------------------------------
    # Domain classification
    # --------------------------------------

    try:

        classification = classify_source(url)

        if not isinstance(classification, dict):
            classification = {}

    except Exception:

        classification = {
            "source_type": "unknown",
            "source_category": "unknown",
            "publisher_domain": "unknown"
        }

    source_type = classification.get(
        "source_type",
        "unknown"
    )

    domain_score = DOMAIN_SCORES.get(
        source_type,
        DOMAIN_SCORES["unknown"]
    )

    # --------------------------------------
    # Article transparency
    # --------------------------------------

    transparency = assess_article_transparency(
        title=title,
        author=author,
        published_date=published_date,
        content=content
    )

    # --------------------------------------
    # URL assessment
    # --------------------------------------

    url_info = assess_url(url)

    # --------------------------------------
    # Assessment confidence
    # --------------------------------------

    metadata_count = transparency[
        "available_metadata_fields"
    ]

    if metadata_count >= 3:

        assessment_confidence = "HIGH"

    elif metadata_count >= 1:

        assessment_confidence = "LIMITED"

    else:

        assessment_confidence = "LOW"

    # --------------------------------------
    # Overall assessment
    # --------------------------------------

    # This remains a domain indicator.
    # It is NOT a probability of truth.

    return {

        **classification,

        **transparency,

        **url_info,

        "domain_indicator_score": domain_score,

        # Compatibility with existing modules.
        "source_quality_score": domain_score,

        "credibility_score": domain_score,

        "assessment_confidence": assessment_confidence,

        "assessment_method": "domain_and_metadata_heuristic",

        "assessment_note": (
            "The domain indicator reflects a broad source "
            "category, not the accuracy of an individual "
            "article. Article transparency measures the "
            "availability of basic metadata. Neither score "
            "establishes factual accuracy or independence."
        )

    }