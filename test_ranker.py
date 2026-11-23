from app.services.evidence_retriever import search_evidence
from app.services.evidence_ranker import rank_evidence

claim = "The Earth revolves around the Sun"

results = search_evidence(claim)

ranked_results = rank_evidence(claim, results)

for result in ranked_results:
    print("\nTitle:", result["title"])
    print("Relevance:", result["relevance_score"])
    print("URL:", result["url"])
    print("Evidence:", result["snippet"])