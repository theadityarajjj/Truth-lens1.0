from app.services.multi_source_retriever import search_all_sources

from app.services.evidence_retriever import (
    get_article_content,
    get_webpage_content
)

from app.services.evidence_processor import extract_relevant_evidence
from app.services.evidence_ranker import rank_evidence
from app.services.ai_verifier import verify_claim


# ==========================================
# CONFIGURATION
# ==========================================

CLAIM = "The Earth revolves around the Sun"

MAX_RESULTS = 5
MAX_SOURCES_TO_PROCESS = 15
MAX_EVIDENCE_FOR_AI = 10

# ==========================================
# DISPLAY HELPERS
# ==========================================

def print_separator():
    print("\n" + "=" * 55)


# ==========================================
# STEP 1: RETRIEVE SOURCES
# ==========================================

def retrieve_sources(claim):

    print_separator()
    print("STEP 1: EVIDENCE RETRIEVAL")
    print_separator()

    print("Searching for evidence...")

    sources = search_all_sources(
        claim,
        max_results=MAX_RESULTS
    )

    if not isinstance(sources, list) or not sources:

        print("No sources retrieved.")
        return []

    print(f"\nRetrieved {len(sources)} sources.")

    for index, source in enumerate(sources, start=1):

        print(f"\nSOURCE {index}")
        print("Title:", source.get("title", "Unknown"))
        print("URL:", source.get("url", "Unavailable"))
        print("API:", source.get("source_api", "Unknown"))
        print(
            "Category:",
            source.get("source_category", "Unknown")
        )

    return sources


# ==========================================
# STEP 2: RETRIEVE FULL ARTICLE CONTENT
# ==========================================

def retrieve_full_content(source):

    title = source.get("title", "Unknown source")
    url = source.get("url", "")
    source_api = source.get("source_api", "")

    print(f"\nRetrieving: {title}")

    text = ""

    try:

        if source_api == "wikipedia":

            text = get_article_content(title)

        else:

            text = get_webpage_content(url)

    except Exception as error:

        print("Full article retrieval failed:", error)

    # Fall back to search snippet if full content fails

    if not text:

        print("Full article unavailable. Using search snippet.")

        text = (
            source.get("snippet", "")
            or source.get("content", "")
        )

    if not isinstance(text, str):
        return ""

    return text.strip()


# ==========================================
# STEP 3: EXTRACT RELEVANT EVIDENCE
# ==========================================

def process_sources(claim, sources):

    print_separator()
    print("STEP 2: FULL ARTICLE PROCESSING")
    print_separator()

    all_evidence = []

    # Prioritize more authoritative source categories.
    priority = {
        "government": 0,
        "academic": 1,
        "scientific": 2,
        "international": 3,
        "reference": 4,
        "news": 5,
        "other": 6,
        "unknown": 7
    }

    sources = sorted(
        sources,
        key=lambda item: priority.get(
            item.get("source_category", "unknown"),
            7
        )
    )

    sources = sources[:MAX_SOURCES_TO_PROCESS]

    for index, source in enumerate(sources, start=1):

        print(f"\nProcessing source {index}/{len(sources)}")

        title = source.get("title", "Unknown source")
        url = source.get("url", "")
        source_api = source.get("source_api", "")

        text = retrieve_full_content(source)

        if not text:

            print("No usable content. Skipping source.")
            continue

        print(f"Retrieved {len(text)} characters.")

        try:

            extracted = extract_relevant_evidence(
                claim,
                text[:100000],
                top_n=3
            )

        except Exception as error:

            print("Evidence extraction failed:", error)
            continue

        if not extracted:

            print("No relevant evidence found.")
            continue

        for evidence in extracted:

            if not isinstance(evidence, dict):
                continue

            sentence = evidence.get("sentence", "")

            if not isinstance(sentence, str) or not sentence.strip():
                continue

            evidence["title"] = title
            evidence["url"] = url
            evidence["source_api"] = source_api

            evidence["source_category"] = source.get(
                "source_category",
                "unknown"
            )

            evidence["credibility_score"] = source.get(
                "credibility_score",
                source.get("source_quality_score", 0.4)
            )

            all_evidence.append(evidence)

            print("\nExtracted evidence:")
            print(sentence)

    print_separator()

    print(
        "Total extracted evidence statements:",
        len(all_evidence)
    )

    return all_evidence


# ==========================================
# STEP 4: RANK EVIDENCE
# ==========================================

def rank_all_evidence(claim, evidence):

    print_separator()
    print("STEP 3: EVIDENCE RANKING")
    print_separator()

    if not evidence:

        print("No evidence available for ranking.")
        return []

    ranked = rank_evidence(
        claim,
        evidence
    )

    if not isinstance(ranked, list) or not ranked:

        print("Evidence ranking returned no results.")
        return []

    print(f"Ranked {len(ranked)} evidence statements.")

    for index, item in enumerate(ranked, start=1):

        print(f"\nEVIDENCE {index}")

        print("Sentence:", item.get("sentence", ""))
        print("Source:", item.get("title", "Unknown"))
        print("URL:", item.get("url", ""))

        print(
            "Relevance:",
            round(
                item.get("relevance_score", 0),
                4
            )
        )

        print(
            "Source credibility:",
            item.get("credibility_score", "Unknown")
        )

    return ranked


# ==========================================
# STEP 5: AI VERIFICATION
# ==========================================

def verify_with_ai(claim, ranked_evidence):

    print_separator()
    print("STEP 4: AI VERIFICATION")
    print_separator()

    if not ranked_evidence:

        print("Cannot verify: no usable evidence.")

        return {
            "verdict": "INSUFFICIENT EVIDENCE",
            "explanation": "No usable evidence was retrieved.",
            "error": False,
            "provider": "None"
        }

    evidence_for_ai = ranked_evidence[:MAX_EVIDENCE_FOR_AI]

    print("Sending evidence to AI verification...")
    print("Primary: Groq | Backup: Gemini")
    print("Evidence statements:", len(evidence_for_ai))

    try:

        result = verify_claim(
            claim,
            evidence_for_ai
        )

        return result

    except Exception as error:

        print("AI verification failed:", error)

        return {
            "verdict": "VERIFICATION UNAVAILABLE",
            "explanation": str(error),
            "error": True,
            "provider": "None"
        }


# ==========================================
# STEP 6: DISPLAY RESULTS
# ==========================================

def display_results(result):

    print_separator()
    print("TRUTH LENS RESULTS")
    print_separator()

    if not isinstance(result, dict):

        print("Invalid verification response.")
        return

    print("\nVERDICT:")
    print(result.get("verdict", "Unavailable"))

    print("\nEXPLANATION:")
    print(result.get("explanation", "No explanation available."))

    print("\nEVIDENCE ASSESSMENT:")

    assessments = result.get(
        "evidence_assessment",
        []
    )

    if isinstance(assessments, list):

        for item in assessments:

            if isinstance(item, dict):

                print("\nEvidence:", item.get("evidence", ""))
                print("Stance:", item.get("stance", "Unknown"))

    print("\nLIMITATIONS:")
    print(result.get("limitations", "Not provided."))

    print("\nPROVIDER:")
    print(result.get("provider", "Unknown"))

    print("\nERROR:")
    print(result.get("error", False))

    print_separator()


# ==========================================
# MAIN ANALYSIS
# ==========================================

def run_analysis(claim):

    if not isinstance(claim, str) or not claim.strip():

        print("Invalid claim.")
        return

    claim = claim.strip()

    print_separator()
    print("TRUTH LENS 1.0")
    print_separator()

    print("\nCLAIM:")
    print(claim)

    # 1. Retrieve sources

    sources = retrieve_sources(claim)

    if not sources:
        print("\nAnalysis stopped: no sources found.")
        return

    # 2. Retrieve full articles and extract evidence

    evidence = process_sources(
        claim,
        sources
    )

    if not evidence:
        print("\nAnalysis stopped: no usable evidence found.")
        return

    # 3. Rank evidence

    ranked_evidence = rank_all_evidence(
        claim,
        evidence
    )

    if not ranked_evidence:
        print("\nAnalysis stopped: evidence ranking failed.")
        return

    # 4. AI verification

    result = verify_with_ai(
        claim,
        ranked_evidence
    )

    # 5. Display results

    display_results(result)


# ==========================================
# EXECUTION
# ==========================================

if __name__ == "__main__":

    run_analysis(CLAIM)