import re

from urllib.parse import (
    urlsplit,
    urlunsplit,
    parse_qsl,
    urlencode
)

import requests
from ddgs import DDGS

from app.config import Config
from app.services.evidence_retriever import search_evidence
from app.services.source_credibility import assess_source


FACTCHECK_URL = (
    "https://factchecktools.googleapis.com/v1alpha1/claims:search"
)


# ==========================================
# HELPERS
# ==========================================

MULTIPART_SUFFIXES = {
    "co.uk",
    "org.uk",
    "ac.uk",
    "gov.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.in",
    "firm.in",
    "net.in",
    "org.in",
    "gen.in",
    "com.br",
    "com.cn",
    "com.sg",
    "co.nz"
}


def normalize_url(url):

    if not isinstance(url, str):
        return ""

    try:

        parsed = urlsplit(url.strip())

        hostname = (parsed.hostname or "").lower()

        if not hostname:
            return ""

        if hostname.startswith("www."):
            hostname = hostname[4:]

        path = parsed.path.rstrip("/")

        tracking_parameters = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid"
        }

        query = urlencode([
            (key, value)
            for key, value in parse_qsl(parsed.query)
            if key.lower() not in tracking_parameters
        ])

        return urlunsplit((
            parsed.scheme.lower(),
            hostname,
            path,
            query,
            ""
        ))

    except Exception:
        return url.strip().lower()


def get_publisher_domain(url):

    if not isinstance(url, str) or not url.strip():
        return "unknown"

    try:

        hostname = urlsplit(url).hostname

        if not hostname:
            return "unknown"

        hostname = hostname.lower().strip(".")

        if hostname.startswith("www."):
            hostname = hostname[4:]

        parts = hostname.split(".")

        if len(parts) <= 2:
            return hostname

        last_two = ".".join(parts[-2:])

        if last_two in MULTIPART_SUFFIXES and len(parts) >= 3:
            return ".".join(parts[-3:])

        return last_two

    except Exception:
        return "unknown"


def get_independence_group(item):

    source_api = item.get("source_api", "")

    if source_api == "wikipedia":
        return "wikipedia.org"

    domain = item.get("publisher_domain", "unknown")

    if domain == "unknown":
        return "unknown"

    return domain


def clean_text(text):

    if not isinstance(text, str):
        return ""

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_title(title):

    title = clean_text(title)

    if not title:
        return "Untitled source"

    if len(title) > 200:
        title = title[:197].rstrip() + "..."

    return title


# ==========================================
# WIKIPEDIA
# ==========================================

def retrieve_wikipedia(claim, max_results=8):

    try:

        results = search_evidence(
            claim,
            max_results=max_results
        )

        cleaned_results = []

        for item in results:

            if not isinstance(item, dict):
                continue

            result = item.copy()

            result["source_api"] = "wikipedia"

            cleaned_results.append(result)

        return cleaned_results

    except Exception as error:

        print(f"Wikipedia retrieval error: {error}")
        return []


# ==========================================
# GOOGLE FACT CHECK
# ==========================================

def retrieve_fact_checks(claim, max_results=5):

    api_key = Config.FACTCHECK_API_KEY

    if not api_key:
        print(
            "Google Fact Check skipped: "
            "API key not configured."
        )
        return []

    try:

        response = requests.get(
            FACTCHECK_URL,
            params={
                "query": claim,
                "key": api_key,
                "pageSize": max_results
            },
            timeout=12
        )

        response.raise_for_status()

        data = response.json()

        results = []

        for item in data.get("claims", []):

            claim_text = item.get("text", "")

            for review in item.get("claimReview", []):

                url = review.get("url", "")

                if not url:
                    continue

                publisher = review.get(
                    "publisher", {}
                ).get("name", "Unknown")

                rating = review.get(
                    "textualRating",
                    "Not specified"
                )

                results.append({

                    "title": clean_title(
                        review.get("title", "Fact Check")
                    ),

                    "url": url,

                    "snippet": (
                        f"Claim reviewed: {claim_text}. "
                        f"Rating: {rating}. "
                        f"Publisher: {publisher}."
                    ),

                    "fact_check_rating": rating,

                    "fact_check_date": review.get(
                        "reviewDate", ""
                    ),

                    "fact_check_publisher": publisher,

                    "source_api": "google_factcheck"

                })

                if len(results) >= max_results:
                    return results

        return results

    except Exception as error:

        print(f"Google Fact Check API error: {error}")
        return []


# ==========================================
# DUCKDUCKGO WEB SEARCH
# ==========================================

def build_search_queries(claim):

    return [
        claim,
        f"{claim} evidence",
        f"{claim} research",
        f"{claim} expert analysis"
    ]


def retrieve_web_results(claim, max_results=8):

    results = []
    seen_urls = set()

    search_queries = build_search_queries(claim)

    try:

        with DDGS() as ddgs:

            for query in search_queries:

                try:

                    search_results = ddgs.text(
                        query,
                        max_results=max_results
                    )

                    for item in search_results:

                        if not isinstance(item, dict):
                            continue

                        url = item.get("href", "").strip()

                        if not url:
                            continue

                        normalized_url = normalize_url(url)

                        if not normalized_url:
                            continue

                        if normalized_url in seen_urls:
                            continue

                        seen_urls.add(normalized_url)

                        results.append({

                            "title": clean_title(
                                item.get("title", "")
                            ),

                            "url": url,

                            "snippet": clean_text(
                                item.get("body", "")
                            ),

                            "source_api": "duckduckgo"

                        })

                except Exception as error:

                    print(
                        f"Search query failed "
                        f"('{query}'): {error}"
                    )

                    continue

                if len(results) >= max_results * 3:
                    break

    except Exception as error:

        print(
            f"DuckDuckGo initialization error: {error}"
        )

    return results


# ==========================================
# SOURCE ENRICHMENT
# ==========================================

def enrich_source(item):

    item = item.copy()

    url = item.get("url", "")

    # --------------------------------------
    # Publisher identification
    # --------------------------------------

    publisher_domain = get_publisher_domain(url)

    item["publisher_domain"] = publisher_domain

    if not item.get("fact_check_publisher"):

        item["publisher_name"] = publisher_domain

    else:

        item["publisher_name"] = (
            item["fact_check_publisher"]
        )

    # --------------------------------------
    # Source grouping
    # --------------------------------------

    if item.get("source_api") == "wikipedia":

        item["source_group"] = "wikipedia"

    elif publisher_domain != "unknown":

        item["source_group"] = publisher_domain

    else:

        item["source_group"] = "unknown"

    item["independence_group"] = (
        get_independence_group(item)
    )

    # --------------------------------------
    # Extract available metadata
    # --------------------------------------

    title = item.get("title")

    author = (
        item.get("author")
        or item.get("authors")
    )

    published_date = (
        item.get("published_date")
        or item.get("publication_date")
        or item.get("date")
        or item.get("fact_check_date")
    )

    # Convert metadata to safe strings.
    if not isinstance(title, str):
        title = None

    if isinstance(author, list):
        author = ", ".join(
            str(name) for name in author
        )

    if not isinstance(author, str):
        author = None

    if not isinstance(published_date, str):
        published_date = None

    # --------------------------------------
    # Credibility assessment
    # --------------------------------------

    try:

        source_info = assess_source(
            url,
            title=title,
            author=author,
            published_date=published_date
        )

        if isinstance(source_info, dict):

            item.update(source_info)

    except Exception as error:

        print(
            f"Source assessment error: {error}"
        )

    # --------------------------------------
    # Safe defaults
    # --------------------------------------

    item.setdefault("source_category", "unknown")
    item.setdefault("credibility_score", 0.4)
    item.setdefault("source_quality_score", 0.4)

    return item


# ==========================================
# DUPLICATE URL MERGING
# ==========================================

def merge_duplicate_sources(results):

    merged = {}
    ordered_urls = []

    for item in results:

        if not isinstance(item, dict):
            continue

        url = item.get("url", "")

        if not isinstance(url, str) or not url.strip():
            continue

        normalized_url = normalize_url(url)

        if not normalized_url:
            continue

        if normalized_url not in merged:

            merged[normalized_url] = item.copy()

            ordered_urls.append(normalized_url)

        else:

            existing = merged[normalized_url]

            for key, value in item.items():

                if value is None or value == "" or value == [] or value == {}:
                    continue

                current_value = existing.get(key)

                if (
                    key not in existing
                    or current_value is None
                    or current_value == ""
                    or current_value == []
                    or current_value == {}
                ):

                    existing[key] = value

            existing_apis = existing.get(
                "retrieval_apis",
                [existing.get("source_api", "unknown")]
            )

            new_api = item.get(
                "source_api",
                "unknown"
            )

            if new_api not in existing_apis:
                existing_apis.append(new_api)

            existing["retrieval_apis"] = existing_apis

    return [
        merged[url]
        for url in ordered_urls
    ]


# ==========================================
# SOURCE DIVERSITY ANALYSIS
# ==========================================

def analyze_source_diversity(results):

    groups = {}

    for item in results:

        group = item.get(
            "independence_group",
            "unknown"
        )

        if group == "unknown":
            continue

        if group not in groups:
            groups[group] = []

        groups[group].append(item)

    total_sources = len(results)

    independent_publishers = len(groups)

    for item in results:

        group = item.get(
            "independence_group",
            "unknown"
        )

        group_size = len(groups.get(group, []))

        item["publisher_source_count"] = group_size

        item["publisher_group_size"] = group_size

        item["source_diversity"] = (
            "MULTIPLE SOURCES FROM SAME PUBLISHER"
            if group_size > 1
            else "UNIQUE PUBLISHER IN THIS RESULT SET"
        )

    print(
        "Source diversity:",
        {
            "total_sources": total_sources,
            "publisher_groups": independent_publishers,
            "unique_publishers": len(groups)
        }
    )

    return results


# ==========================================
# COMBINED RETRIEVAL
# ==========================================

def search_all_sources(claim, max_results=8):

    if not isinstance(claim, str) or not claim.strip():
        return []

    claim = claim.strip()

    try:

        max_results = max(
            1,
            min(int(max_results), 20)
        )

    except (ValueError, TypeError):

        max_results = 8

    results = []

    print("Searching Wikipedia...")

    results.extend(
        retrieve_wikipedia(
            claim,
            max_results
        )
    )

    print("Searching Google Fact Check...")

    results.extend(
        retrieve_fact_checks(
            claim,
            max_results
        )
    )

    print("Searching DuckDuckGo...")

    results.extend(
        retrieve_web_results(
            claim,
            max_results
        )
    )

    # --------------------------------------
    # Merge duplicate URLs
    # --------------------------------------

    unique_results = merge_duplicate_sources(
        results
    )

    # --------------------------------------
    # Enrich source metadata
    # --------------------------------------

    enriched_results = []

    for item in unique_results:

        enriched_results.append(
            enrich_source(item)
        )

    # --------------------------------------
    # Analyze publisher diversity
    # --------------------------------------

    enriched_results = analyze_source_diversity(
        enriched_results
    )

    # --------------------------------------
    # Retrieval report
    # --------------------------------------

    print(
        f"Evidence retrieval completed: "
        f"{len(enriched_results)} unique sources found."
    )

    print(
        "Source breakdown:",
        {
            "wikipedia": sum(
                1 for item in enriched_results
                if item.get("source_api") == "wikipedia"
            ),

            "fact_check": sum(
                1 for item in enriched_results
                if item.get("source_api") == "google_factcheck"
            ),

            "web": sum(
                1 for item in enriched_results
                if item.get("source_api") == "duckduckgo"
            )
        }
    )

    return enriched_results