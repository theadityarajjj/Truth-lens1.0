import math

from flask import (
    Blueprint,
    jsonify,
    request,
    current_app,
    render_template
)

from app.services.claim_extractor import extract_claims

from app.services.evidence_retriever import (
    get_article_content,
    get_webpage_content
)

from app.services.evidence_ranker import rank_evidence

from app.services.evidence_processor import (
    extract_relevant_evidence
)

from app.services.ai_verifier import verify_claim
from app.services.bias_detector import detect_bias
from app.services.fallacy_detector import detect_fallacies

from app.services.history import (
    save_analysis,
    get_all_analyses,
    get_analysis_by_id
)

from app.services.multi_source_retriever import search_all_sources
from app.services.stance_detector import analyze_evidence_stances


bp = Blueprint("main", __name__)


# --------------------------------------------------
# REQUEST VALIDATION
# --------------------------------------------------

def get_request_data():

    data = request.get_json(silent=True)

    return data if isinstance(data, dict) else {}


def validate_text(text):

    if not isinstance(text, str):
        return "Please provide valid text."

    if not text.strip():
        return "Please provide text."

    max_chars = current_app.config.get(
        "MAX_INPUT_CHARS",
        5000
    )

    if len(text) > max_chars:
        return "Text exceeds the maximum allowed length."

    return None


# --------------------------------------------------
# SCORE HANDLING
# --------------------------------------------------

def safe_score(value):

    try:

        score = float(value)

        if not math.isfinite(score):
            return 0.0

        return max(0.0, min(score, 1.0))

    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------
# EVIDENCE CLEANING
# --------------------------------------------------

def clean_evidence(evidence_items, limit=10):

    if not isinstance(evidence_items, list):
        return []

    unique_evidence = []
    seen = set()

    for item in evidence_items:

        if not isinstance(item, dict):
            continue

        sentence = item.get("sentence", "")

        if not isinstance(sentence, str):
            continue

        sentence = sentence.strip()

        if not sentence:
            continue

        normalized_sentence = " ".join(
            sentence.lower().split()
        )

        source_url = item.get("source_url", "")

        if not isinstance(source_url, str):
            source_url = ""

        duplicate_key = (
            normalized_sentence,
            source_url.strip().lower()
        )

        if duplicate_key in seen:
            continue

        seen.add(duplicate_key)

        cleaned_item = item.copy()

        cleaned_item["relevance_score"] = safe_score(
            item.get("relevance_score", 0)
        )

        cleaned_item["credibility_score"] = safe_score(
            item.get(
                "credibility_score",
                item.get("source_quality_score", 0.4)
            )
        )

        unique_evidence.append(cleaned_item)

    unique_evidence.sort(
        key=lambda item: item["relevance_score"],
        reverse=True
    )

    return unique_evidence[:limit]


# --------------------------------------------------
# FULL SOURCE CONTENT RETRIEVAL
# --------------------------------------------------

def retrieve_source_content(article):

    if not isinstance(article, dict):
        return ""

    source_api = article.get(
        "source_api",
        "unknown"
    )

    title = article.get("title", "")
    url = article.get("url", "")
    snippet = article.get("snippet", "")

    article_text = ""

    try:

        # Wikipedia retrieval.
        if source_api == "wikipedia":

            if isinstance(title, str) and title.strip():

                article_text = get_article_content(
                    title.strip()
                )

        # Full webpage retrieval for other sources.
        elif isinstance(url, str) and url.strip():

            article_text = get_webpage_content(
                url.strip()
            )

    except Exception as error:

        print(
            f"Full content retrieval failed ({title}):",
            error
        )

    # Fall back to the search snippet if full content
    # cannot be retrieved.
    if not isinstance(article_text, str) or not article_text.strip():

        if isinstance(snippet, str) and snippet.strip():

            print(
                f"Using search snippet fallback: {title}"
            )

            return snippet.strip()

        return ""

    return article_text.strip()


# --------------------------------------------------
# SOURCE METADATA ATTACHMENT
# --------------------------------------------------

def build_evidence_record(item, article):

    if not isinstance(item, dict):
        return None

    if not isinstance(article, dict):
        return None

    sentence = item.get("sentence", "")

    if not isinstance(sentence, str) or not sentence.strip():
        return None

    source_api = article.get(
        "source_api",
        "unknown"
    )

    publisher_name = article.get(
        "publisher_name",
        article.get("fact_check_publisher", "Unknown")
    )

    source_category = article.get(
        "source_category",
        article.get("source_type", "unknown")
    )

    credibility_score = safe_score(
        article.get(
            "credibility_score",
            article.get("source_quality_score", 0.4)
        )
    )

    evidence_quality = safe_score(
        item.get("evidence_quality", 0.5)
    )

    record = {

        "sentence": sentence.strip(),

        "relevance_score": safe_score(
            item.get("relevance_score", 0)
        ),

        "keyword_coverage": safe_score(
            item.get("keyword_coverage", 0)
        ),

        "evidence_type": item.get(
            "evidence_type",
            "unknown"
        ),

        "evidence_quality": evidence_quality,

        "quality_reason": item.get(
            "quality_reason",
            ""
        ),

        # Source identification.
        "source_title": article.get(
            "title",
            "Unknown source"
        ),

        "source_url": article.get("url", ""),

        "title": article.get(
            "title",
            "Unknown source"
        ),

        "url": article.get("url", ""),

        # Publisher information.
        "publisher": publisher_name,

        "publisher_name": publisher_name,

        "publisher_domain": article.get(
            "publisher_domain",
            "unknown"
        ),

        # Credibility and classification.
        "source_type": source_category,

        "source_category": source_category,

        "source_quality_score": credibility_score,

        "credibility_score": credibility_score,

        "article_transparency_score": safe_score(
            article.get("article_transparency_score", 0)
        ),

        "assessment_confidence": article.get(
            "assessment_confidence",
            "LOW"
        ),

        # Independence information.
        "independence_group": article.get(
            "independence_group",
            "unknown"
        ),

        "publisher_group_size": article.get(
            "publisher_group_size",
            0
        ),

        "source_diversity": article.get(
            "source_diversity",
            "UNKNOWN"
        ),

        "source_api": source_api

    }

    # Preserve fact-check information.
    if article.get("fact_check_rating"):

        record["fact_check_rating"] = (
            article["fact_check_rating"]
        )

    if article.get("fact_check_date"):

        record["fact_check_date"] = (
            article["fact_check_date"]
        )

    return record


# --------------------------------------------------
# GENERAL ROUTES
# --------------------------------------------------

@bp.route("/")
def index():

    return render_template("index.html")


@bp.route("/health")
def health():

    return jsonify({

        "status": "ok",

        "app": "Truth Lens 1.0",

        "gemini_key_set": bool(
            current_app.config.get("GEMINI_API_KEY")
        ),

        "groq_key_set": bool(
            current_app.config.get("GROQ_API_KEY")
        )

    })


# --------------------------------------------------
# CLAIM EXTRACTION
# --------------------------------------------------

@bp.route("/extract", methods=["POST"])
def extract():

    data = get_request_data()

    text = data.get("text")

    error = validate_text(text)

    if error:
        return jsonify({"error": error}), 400

    try:

        claims = extract_claims(text.strip())

        if not isinstance(claims, list):
            raise ValueError(
                "Invalid claim extraction response."
            )

        return jsonify({

            "success": True,

            "claims": claims,

            "total_claims": len(claims)

        })

    except Exception as error:

        print("Claim extraction error:", error)

        return jsonify({

            "error": (
                "Unable to extract claims "
                "from the provided text."
            )

        }), 500


# --------------------------------------------------
# EVIDENCE SEARCH
# --------------------------------------------------

@bp.route("/search", methods=["POST"])
def search():

    data = get_request_data()

    claim = data.get("claim")

    error = validate_text(claim)

    if error:
        return jsonify({"error": error}), 400

    claim = claim.strip()

    try:

        results = search_all_sources(claim)

        if not isinstance(results, list):
            results = []

        ranked_results = rank_evidence(
            claim,
            results
        )

        return jsonify({

            "success": True,

            "claim": claim,

            "results": ranked_results,

            "total_results": len(ranked_results)

        })

    except Exception as error:

        print("Evidence search error:", error)

        return jsonify({

            "error": "Unable to retrieve evidence."

        }), 500


# --------------------------------------------------
# MAIN ANALYSIS
# --------------------------------------------------

@bp.route("/analyze", methods=["POST"])
def analyze():

    data = get_request_data()

    text = data.get("text")

    error = validate_text(text)

    if error:
        return jsonify({"error": error}), 400

    text = text.strip()

    # ----------------------------------------------
    # STEP 1: CLAIM EXTRACTION
    # ----------------------------------------------

    try:

        claims = extract_claims(text)

        if not isinstance(claims, list):
            raise ValueError(
                "Invalid claim extraction response."
            )

    except Exception as error:

        print("Claim extraction error:", error)

        return jsonify({

            "error": (
                "Unable to extract claims "
                "from the provided text."
            )

        }), 500

    max_claims = current_app.config.get(
        "MAX_CLAIMS_PER_ANALYSIS",
        20
    )

    if len(claims) > max_claims:

        return jsonify({

            "error": (
                f"Too many claims detected. "
                f"Maximum allowed: {max_claims}."
            )

        }), 400

    # ----------------------------------------------
    # STEP 2: BIAS AND FALLACY DETECTION
    # ----------------------------------------------

    try:

        bias_analysis = detect_bias(text)

        fallacy_analysis = detect_fallacies(text)

    except Exception as error:

        print("Language analysis error:", error)

        bias_analysis = {

            "potential_bias_detected": False,

            "findings": [],

            "limitations": (
                "Bias analysis was unavailable."
            )

        }

        fallacy_analysis = {

            "potential_fallacies_detected": False,

            "findings": [],

            "limitations": (
                "Fallacy analysis was unavailable."
            )

        }

    # ----------------------------------------------
    # STEP 3: CLAIM VERIFICATION
    # ----------------------------------------------

    claim_results = []

    for claim in claims:

        if not isinstance(claim, str) or not claim.strip():
            continue

        claim = claim.strip()

        evidence_items = []

        # ------------------------------------------
        # STEP 3A: SOURCE RETRIEVAL
        # ------------------------------------------

        try:

            search_results = search_all_sources(claim)

            if not isinstance(search_results, list):
                search_results = []

            ranked_results = rank_evidence(
                claim,
                search_results
            )

            if not isinstance(ranked_results, list):
                ranked_results = []

            # Process up to five ranked sources.
            for article in ranked_results[:5]:

                if not isinstance(article, dict):
                    continue

                title = article.get(
                    "title",
                    "Unknown source"
                )

                try:

                    # Retrieve full article/webpage content.
                    article_text = retrieve_source_content(
                        article
                    )

                    if not article_text:
                        continue

                    # Extract relevant evidence.
                    relevant_sentences = extract_relevant_evidence(
                        claim,
                        article_text,
                        top_n=5
                    )

                    if not isinstance(relevant_sentences, list):
                        continue

                    # Attach complete source metadata.
                    for item in relevant_sentences:

                        evidence = build_evidence_record(
                            item,
                            article
                        )

                        if evidence:
                            evidence_items.append(evidence)

                except Exception as error:

                    print(
                        f"Source processing error ({title}):",
                        error
                    )

                    continue

        except Exception as error:

            print("Evidence retrieval error:", error)

        # ------------------------------------------
        # STEP 3B: EVIDENCE STANCE ANALYSIS
        # ------------------------------------------

        try:

            evidence_items = analyze_evidence_stances(
                claim,
                evidence_items
            )

            if not isinstance(evidence_items, list):
                evidence_items = []

        except Exception as error:

            print("Stance analysis error:", error)

        # ------------------------------------------
        # STEP 3C: EVIDENCE CLEANING
        # ------------------------------------------

        evidence_items = clean_evidence(
            evidence_items,
            limit=10
        )

        # ------------------------------------------
        # STEP 3D: AI VERIFICATION
        # ------------------------------------------

        try:

            verification = verify_claim(
                claim,
                evidence_items
            )

            if not isinstance(verification, dict):

                raise ValueError(
                    "Invalid verification response."
                )

        except Exception as error:

            print("Verification pipeline error:", error)

            verification = {

                "verdict": "VERIFICATION UNAVAILABLE",

                "explanation": (
                    "The verification service could not "
                    "complete the analysis."
                ),

                "evidence_assessment": [],

                "limitations": (
                    "An unexpected verification error occurred."
                ),

                "error": True

            }

        # ------------------------------------------
        # STEP 3E: CLAIM RESULT
        # ------------------------------------------

        claim_results.append({

            "claim": claim,

            "verdict": verification.get(
                "verdict",
                "VERIFICATION UNAVAILABLE"
            ),

            "explanation": verification.get(
                "explanation",
                ""
            ),

            "evidence": evidence_items,

            "evidence_assessment": verification.get(
                "evidence_assessment",
                []
            ),

            "limitations": verification.get(
                "limitations",
                ""
            ),

            "verification_error": verification.get(
                "error",
                False
            ),

            "provider": verification.get(
                "provider",
                "unknown"
            )

        })

    # ----------------------------------------------
    # STEP 4: FINAL ANALYSIS
    # ----------------------------------------------

    analysis_results = {

        "success": True,

        "input_text": text,

        "total_claims": len(claim_results),

        "claims": claim_results,

        "bias_analysis": bias_analysis,

        "fallacy_analysis": fallacy_analysis,

        "history_saved": False

    }

    # ----------------------------------------------
    # STEP 5: SAVE HISTORY
    # ----------------------------------------------

    try:

        analysis_id = save_analysis(
            text,
            claims,
            analysis_results
        )

        analysis_results["analysis_id"] = analysis_id

        analysis_results["history_saved"] = True

    except Exception as error:

        print("History saving error:", error)

        analysis_results["history_saved"] = False

    return jsonify(analysis_results)


# --------------------------------------------------
# HISTORY
# --------------------------------------------------

@bp.route("/history", methods=["GET"])
def history():

    try:

        analyses = get_all_analyses()

        return jsonify({

            "success": True,

            "total": len(analyses),

            "history": analyses

        })

    except Exception as error:

        print("History retrieval error:", error)

        return jsonify({

            "error": "Unable to retrieve analysis history."

        }), 500


@bp.route("/history/<int:analysis_id>", methods=["GET"])
def history_detail(analysis_id):

    try:

        analysis = get_analysis_by_id(analysis_id)

        if analysis is None:

            return jsonify({

                "error": "Analysis not found."

            }), 404

        return jsonify({

            "success": True,

            "analysis": analysis

        })

    except Exception as error:

        print("Analysis retrieval error:", error)

        return jsonify({

            "error": "Unable to retrieve this analysis."

        }), 500