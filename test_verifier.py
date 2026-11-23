from app.services.evidence_retriever import (
    search_evidence,
    get_article_content
)

from app.services.evidence_processor import (
    extract_relevant_evidence
)

from app.services.ai_verifier import verify_claim


claim = "The Earth revolves around the Sun"

print("Searching for evidence...")

results = search_evidence(claim)

if not results:
    print("No search results found.")
    exit()

print("Retrieving article...")

article = get_article_content(results[0]["title"])

if not article:
    print("Could not retrieve article content.")
    exit()

print("Processing evidence...")

evidence = extract_relevant_evidence(
    claim,
    article,
    top_n=5
)

if not evidence:
    print("No relevant evidence extracted.")
    exit()

print("Sending evidence to AI verification...")
print("Primary: Groq | Backup: Gemini")

result = verify_claim(claim, evidence)

print("\n========== TRUTH LENS RESULTS ==========")

for key, value in result.items():
    print(f"\n{key.upper()}:")
    print(value)