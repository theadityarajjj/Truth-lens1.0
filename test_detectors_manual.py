from app.services.bias_detector import detect_bias
from app.services.fallacy_detector import detect_fallacies


text = """
Everyone knows this politician is corrupt.
Either you support this decision or you hate the country.
You are an idiot if you disagree.
If we allow this, society will eventually collapse.
"""


print("========== BIAS ANALYSIS ==========")

bias = detect_bias(text)

print("Potential bias:", bias["potential_bias_detected"])

for finding in bias["findings"]:
    print("\nCategory:", finding["category"])
    print("Indicators:", finding["indicators"])
    print("Explanation:", finding["explanation"])


print("\n========== FALLACY ANALYSIS ==========")

fallacies = detect_fallacies(text)

print("Potential fallacies:", fallacies["potential_fallacies_detected"])

for finding in fallacies["findings"]:
    print("\nFallacy:", finding["fallacy"])
    print("Examples:", finding["examples"])
    print("Explanation:", finding["explanation"])