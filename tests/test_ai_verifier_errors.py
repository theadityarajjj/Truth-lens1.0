from app.services.ai_verifier import classify_api_error


def test_quota_exhaustion():
    error = "429 RESOURCE_EXHAUSTED: daily limit exceeded"
    assert classify_api_error(error) == "quota_exhausted"


def test_rate_limit():
    error = "429 Too Many Requests"
    assert classify_api_error(error) == "rate_limited"


def test_service_unavailable():
    error = "503 Service Unavailable"
    assert classify_api_error(error) == "service_unavailable"


def test_timeout():
    error = "504 Gateway Timeout"
    assert classify_api_error(error) == "timeout"


def test_unknown_error():
    error = "Invalid API response"
    assert classify_api_error(error) == "unknown"


def test_missing_timeout():
    error = "Request timed out"
    assert classify_api_error(error) == "timeout"