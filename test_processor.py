from app.services.evidence_retriever import (
    search_evidence,
    get_article_content
)

from app.services.evidence_processor import extract_relevant_evidence

claim = "The Earth revolves around the Sun"

results = search_evidence(claim)

if results:
    title = results[0]["title"]

    article = get_article_content(title)

    evidence = extract_relevant_evidence(claim, article)

    print("\nCLAIM:", claim)
    print("\nSELECTED EVIDENCE:")

    for item in evidence:
        print("\nScore:", item["relevance_score"])
        print("Sentence:", item["sentence"])
else:
    print("No search results found.")