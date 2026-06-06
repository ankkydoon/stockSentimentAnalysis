from agents.signal_generation import compute_signal_score, score_to_direction, compute_confidence

def test_bullish_signal():
    score = compute_signal_score(sentiment_ewma=0.7, event_severity_weight=0.5, price_zscore=0.3)
    assert score > 0.25
    assert score_to_direction(score) == "bullish"

def test_bearish_signal():
    score = compute_signal_score(sentiment_ewma=-0.8, event_severity_weight=-0.5, price_zscore=-0.2)
    assert score < -0.25
    assert score_to_direction(score) == "bearish"

def test_neutral_signal():
    score = compute_signal_score(sentiment_ewma=0.1, event_severity_weight=0.0, price_zscore=0.0)
    assert score_to_direction(score) == "neutral"

def test_confidence_bounded():
    c = compute_confidence(score=0.4, components=[0.5, 0.3, 0.1])
    assert 0.0 <= c <= 1.0

def test_score_formula_weights():
    # 0.50*sentiment + 0.35*event + 0.15*price
    score = compute_signal_score(sentiment_ewma=1.0, event_severity_weight=0.0, price_zscore=0.0)
    assert abs(score - 0.50) < 1e-6
