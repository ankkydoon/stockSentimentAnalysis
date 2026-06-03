from agents.sentiment_analysis import compute_ewma, aggregate_sentiment


def test_ewma_first_value():
    result = compute_ewma(previous=0.0, new_value=0.8, alpha=0.3)
    assert abs(result - (0.3 * 0.8 + 0.7 * 0.0)) < 1e-6


def test_ewma_blends_with_history():
    result = compute_ewma(previous=0.5, new_value=0.0, alpha=0.3)
    assert abs(result - (0.3 * 0.0 + 0.7 * 0.5)) < 1e-6


def test_aggregate_sentiment_net_positive():
    scores = [
        {"label": "positive", "score": 0.9},
        {"label": "positive", "score": 0.8},
        {"label": "negative", "score": 0.3},
    ]
    assert aggregate_sentiment(scores) > 0


def test_aggregate_sentiment_empty_returns_zero():
    assert aggregate_sentiment([]) == 0.0
