from urllib.parse import urlparse


SCIENTIFIC_DOMAINS = [
    "nature.com",
    "science.org",
    "sciencedirect.com",
    "springer.com",
    "pubmed.ncbi.nlm.nih.gov",
    "arxiv.org",
    "jstor.org"
]

NEWS_DOMAINS = [
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "nytimes.com",
    "theguardian.com"
]


def matches_domain(domain, trusted_domain):
    return (
        domain == trusted_domain
        or domain.endswith("." + trusted_domain)
    )


def classify_source(url):

    if not isinstance(url, str) or not url.strip():
        return {
            "source_type": "unknown",
            "source_category": "unknown",
            "publisher": "Unknown"
        }

    try:
        domain = urlparse(url.strip()).hostname or ""
        domain = domain.lower()

        if domain.startswith("www."):
            domain = domain[4:]

    except Exception:
        domain = ""

    if not domain:
        source_type = "unknown"

    elif (
        domain.endswith(".gov")
        or ".gov." in domain
    ):
        source_type = "government"

    elif (
        domain.endswith(".edu")
        or ".edu." in domain
    ):
        source_type = "academic"

    elif domain.endswith(".int"):
        source_type = "international_organization"

    elif any(
        matches_domain(domain, trusted)
        for trusted in SCIENTIFIC_DOMAINS
    ):
        source_type = "scientific"

    elif any(
        matches_domain(domain, trusted)
        for trusted in NEWS_DOMAINS
    ):
        source_type = "news"

    elif matches_domain(domain, "wikipedia.org"):
        source_type = "reference"

    else:
        source_type = "other"

    return {
        "source_type": source_type,
        "source_category": source_type,
        "publisher": domain or "Unknown"
    }