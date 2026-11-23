from app.services.bias_detector import detect_bias
from app.services.fallacy_detector import detect_fallacies


def test_bias_detection():

    result = detect_bias(
        "This disgusting and outrageous policy is terrible."
    )

    assert result["potential_bias_detected"] is True


def test_bias_no_detection():

    result = detect_bias(
        "The committee published its annual report."
    )

    assert result["potential_bias_detected"] is False


def test_bias_invalid_input():

    result = detect_bias(None)

    assert result["potential_bias_detected"] is False


def test_fallacy_detection():

    result = detect_fallacies(
        "Everyone believes this, so it must be true."
    )

    assert result["potential_fallacies_detected"] is True


def test_false_dilemma():

    result = detect_fallacies(
        "Either you support us or you oppose us."
    )

    assert result["potential_fallacies_detected"] is True


def test_fallacy_no_detection():

    result = detect_fallacies(
        "The report was published yesterday."
    )

    assert result["potential_fallacies_detected"] is False


def test_fallacy_invalid_input():

    result = detect_fallacies(None)

    assert result["potential_fallacies_detected"] is False