from app.services.history import (
    initialize_database,
    save_analysis,
    get_all_analyses,
    get_analysis_by_id
)

initialize_database()

sample_text = "The Earth revolves around the Sun."

sample_claims = [
    "The Earth revolves around the Sun."
]

sample_results = [
    {
        "verdict": "SUPPORTED",
        "explanation": "Sample test result."
    }
]

analysis_id = save_analysis(
    sample_text,
    sample_claims,
    sample_results
)

print("Saved analysis ID:", analysis_id)

print("\n========== HISTORY ==========")

history = get_all_analyses()

for item in history:
    print(item)

print("\n========== SPECIFIC ANALYSIS ==========")

analysis = get_analysis_by_id(analysis_id)

print(analysis)