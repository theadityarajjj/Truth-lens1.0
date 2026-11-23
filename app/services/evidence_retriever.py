import requests
import re
import time
import ipaddress
import socket

from html import unescape
from functools import lru_cache
from urllib.parse import urlsplit
from html.parser import HTMLParser


# ==========================================
# CONFIGURATION
# ==========================================

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent": (
        "TruthLens/1.0 "
        "(educational fact-checking project)"
    )
}

REQUEST_TIMEOUT = 15
MAX_RETRIES = 2
MAX_CONTENT_BYTES = 2_000_000

STOP_WORDS = {
    "the", "is", "are", "was", "were", "a", "an",
    "of", "to", "in", "on", "for", "and", "or",
    "does", "do", "did", "has", "have", "had",
    "that", "this", "it", "its", "with", "by",
    "from", "be", "been", "being", "can", "could",
    "would", "should", "will", "about"
}


# ==========================================
# SESSION
# ==========================================

session = requests.Session()
session.headers.update(HEADERS)


# ==========================================
# HTML EXTRACTION
# ==========================================

class ArticleParser(HTMLParser):

    SKIP_TAGS = {
        "script", "style", "noscript",
        "svg", "nav", "footer", "header",
        "aside", "form", "button"
    }

    def __init__(self):

        super().__init__()

        self.skip_depth = 0
        self.article_depth = 0

        self.article_parts = []
        self.body_parts = []
        self.title_parts = []

        self.in_title = False

    def handle_starttag(self, tag, attrs):

        if tag == "title":
            self.in_title = True

        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return

        if self.skip_depth:
            return

        if tag in ("article", "main"):
            self.article_depth += 1

    def handle_endtag(self, tag):

        if tag == "title":
            self.in_title = False

        if tag in self.SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return

        if self.skip_depth:
            return

        if tag in ("article", "main"):
            self.article_depth = max(
                0,
                self.article_depth - 1
            )

    def handle_data(self, data):

        text = data.strip()

        if not text:
            return

        if self.in_title:
            self.title_parts.append(text)

        if self.skip_depth:
            return

        self.body_parts.append(text)

        if self.article_depth:
            self.article_parts.append(text)

    def get_text(self):

        parts = (
            self.article_parts
            if self.article_parts
            else self.body_parts
        )

        return re.sub(
            r"\s+",
            " ",
            " ".join(parts)
        ).strip()


# ==========================================
# TEXT CLEANING
# ==========================================

def clean_html(text):

    if not isinstance(text, str):
        return ""

    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_text(text):

    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ==========================================
# SEARCH QUERY GENERATION
# ==========================================

def build_search_queries(claim):

    if not isinstance(claim, str):
        return []

    claim = claim.strip()

    if not claim:
        return []

    queries = [claim]

    words = [
        word
        for word in normalize_text(claim).split()
        if word not in STOP_WORDS and len(word) > 2
    ]

    keyword_query = " ".join(words)

    if keyword_query and keyword_query.lower() != claim.lower():
        queries.append(keyword_query)

    return list(dict.fromkeys(queries))


# ==========================================
# REQUEST HANDLING
# ==========================================

def make_request(params):

    for attempt in range(MAX_RETRIES + 1):

        try:

            response = session.get(
                WIKIPEDIA_API,
                params=params,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 429:

                if attempt < MAX_RETRIES:

                    retry_after = response.headers.get(
                        "Retry-After", "2"
                    )

                    try:
                        wait_time = min(
                            float(retry_after), 5
                        )
                    except ValueError:
                        wait_time = 2

                    time.sleep(wait_time)
                    continue

                return None

            if response.status_code in [500, 502, 503, 504]:

                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue

            response.raise_for_status()

            return response.json()

        except requests.RequestException as error:

            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue

            print("Wikipedia request failed:", error)

    return None


# ==========================================
# SINGLE WIKIPEDIA SEARCH
# ==========================================

def _search_wikipedia(query, max_results):

    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": max_results
    }

    data = make_request(params)

    if not data:
        return []

    results = []

    for item in data.get("query", {}).get("search", []):

        title = item.get("title", "")

        if not title:
            continue

        results.append({
            "title": title,
            "url": (
                "https://en.wikipedia.org/wiki/"
                + requests.utils.quote(
                    title.replace(" ", "_"),
                    safe="/"
                )
            ),
            "snippet": clean_html(
                item.get("snippet", "")
            ),
            "source_api": "wikipedia"
        })

    return results


# ==========================================
# CACHED WIKIPEDIA SEARCH
# ==========================================

@lru_cache(maxsize=200)
def _cached_search(claim, max_results):

    all_results = []
    seen_titles = set()

    queries = build_search_queries(claim)

    for query in queries:

        results = _search_wikipedia(
            query,
            max_results
        )

        for item in results:

            normalized_title = normalize_text(
                item["title"]
            )

            if normalized_title in seen_titles:
                continue

            seen_titles.add(normalized_title)
            all_results.append(item)

    return tuple(
        (
            item["title"],
            item["url"],
            item["snippet"],
            item["source_api"]
        )
        for item in all_results[:max_results]
    )


def search_evidence(claim, max_results=8):

    if not isinstance(claim, str) or not claim.strip():
        return []

    try:
        max_results = max(
            1,
            min(int(max_results), 20)
        )
    except (ValueError, TypeError):
        max_results = 8

    cached_results = _cached_search(
        claim.strip(),
        max_results
    )

    return [
        {
            "title": title,
            "url": url,
            "snippet": snippet,
            "source_api": source_api
        }
        for title, url, snippet, source_api in cached_results
    ]


# ==========================================
# WIKIPEDIA FULL ARTICLE
# ==========================================

@lru_cache(maxsize=100)
def _cached_article_content(title):

    params = {
        "action": "query",
        "prop": "extracts",
        "titles": title,
        "explaintext": 1,
        "format": "json"
    }

    data = make_request(params)

    if not data:
        return ""

    pages = data.get(
        "query", {}
    ).get("pages", {})

    for page in pages.values():

        return page.get("extract", "")

    return ""


def get_article_content(title):

    if not isinstance(title, str) or not title.strip():
        return ""

    return _cached_article_content(title.strip())


# ==========================================
# URL VALIDATION
# ==========================================

def is_safe_public_url(url):

    if not isinstance(url, str):
        return False

    try:

        parsed = urlsplit(url.strip())

        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname

        if not hostname:
            return False

        if parsed.username or parsed.password:
            return False

        if parsed.port and parsed.port not in (80, 443):
            return False

        hostname = hostname.lower()

        if hostname == "localhost":
            return False

        if hostname.endswith(".local"):
            return False

        try:

            address = ipaddress.ip_address(hostname)

            if not address.is_global:
                return False

        except ValueError:
            pass

        # Reject domains that resolve to private,
        # loopback or otherwise non-public IP addresses.
        try:

            addresses = socket.getaddrinfo(
                hostname,
                None,
                type=socket.SOCK_STREAM
            )

            if not addresses:
                return False

            for address_info in addresses:

                ip = ipaddress.ip_address(
                    address_info[4][0]
                )

                if not ip.is_global:
                    return False

        except (socket.gaierror, ValueError):
            return False

        return True

    except Exception:
        return False


# ==========================================
# WEBPAGE CONTENT RETRIEVAL
# ==========================================

@lru_cache(maxsize=100)
def _cached_webpage_content(url):

    if not is_safe_public_url(url):
        return ""

    try:

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            stream=True,
            allow_redirects=True
        )

        response.raise_for_status()

        # Validate the final redirect destination too.
        if not is_safe_public_url(response.url):
            response.close()
            return ""

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if "text/html" not in content_type:
            response.close()
            return ""

        content = bytearray()

        try:

            for chunk in response.iter_content(
                chunk_size=8192
            ):

                if not chunk:
                    continue

                content.extend(chunk)

                if len(content) > MAX_CONTENT_BYTES:
                    print("Webpage exceeded content size limit.")
                    return ""

        finally:
            response.close()

        encoding = response.encoding or "utf-8"

        html = bytes(content).decode(
            encoding,
            errors="replace"
        )

        parser = ArticleParser()
        parser.feed(html)

        extracted_text = parser.get_text()

        return extracted_text[:100000]

    except requests.RequestException as error:

        print(f"Webpage retrieval error: {error}")
        return ""

    except Exception as error:

        print(f"Webpage processing error: {error}")
        return ""


def get_webpage_content(url):

    if not isinstance(url, str) or not url.strip():
        return ""

    return _cached_webpage_content(url.strip())


# ==========================================
# CACHE MANAGEMENT
# ==========================================

def clear_retrieval_cache():

    _cached_search.cache_clear()
    _cached_article_content.cache_clear()
    _cached_webpage_content.cache_clear()

    print("Evidence retrieval cache cleared.")