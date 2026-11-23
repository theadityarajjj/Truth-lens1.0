from app.services.evidence_retriever import (
    search_evidence,
    get_article_content
)

claim = "The Earth revolves around the Sun"

results = search_evidence(claim)

if results:
    first_result = results[0]

    print("\nARTICLE:", first_result["title"])

    content = get_article_content(first_result["title"])

    print("\nARTICLE CONTENT:")
    print(content[:1500])

    print("\nCONTENT LENGTH:", len(content))
else:
    print("No search results found.")
    
from app.services.evidence_retriever import (
    get_article_content,
    _cached_article_content
)

print("\n========== CACHE TEST ==========")

_cached_article_content.cache_clear()

get_article_content("Heliocentrism")
print("First request:", _cached_article_content.cache_info())

get_article_content("Heliocentrism")
print("Second request:", _cached_article_content.cache_info())