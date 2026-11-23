from unittest.mock import patch

from app.services.ai_verifier import verify_claim


evidence = [
    {
        "sentence": "The Sun's diameter is approximately 109 times Earth's."
    }
]

mock_groq_response = {
    "verdict": "SUPPORTED",
    "explanation": "The supplied evidence supports the claim.",
    "evidence_assessment": [
        {
            "evidence": evidence[0]["sentence"],
            "stance": "SUPPORTS"
        }
    ],
    "limitations": "Based on the supplied evidence.",
    "error": False,
    "provider": "Groq"
}


with patch(
    "app.services.ai_verifier.verify_with_gemini",
    side_effect=Exception("429 RESOURCE_EXHAUSTED daily quota exceeded")
):

    with patch(
        "app.services.ai_verifier.verify_with_groq",
        return_value=mock_groq_response
    ) as groq_mock:

        result = verify_claim(
            "The Sun is bigger than Earth.",
            evidence
        )

        print("\nFALLBACK TEST RESULT")
        print("Verdict:", result["verdict"])
        print("Provider:", result["provider"])
        print("Groq called:", groq_mock.called)

        assert result["provider"] == "Groq"
        assert result["verdict"] == "SUPPORTED"
        assert groq_mock.called

        print("\nSUCCESS: Gemini → Groq fallback works!")