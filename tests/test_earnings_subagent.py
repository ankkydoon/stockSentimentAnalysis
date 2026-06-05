from agents.earnings_subagent import extract_earnings_figures

def test_extract_eps_from_text():
    text = "Apple reported EPS of $1.52, beating estimates of $1.43"
    result = extract_earnings_figures(text)
    assert result["reported_eps"] == 1.52
    assert result["estimated_eps"] == 1.43

def test_extract_revenue_from_text():
    text = "Revenue came in at $94.8 billion vs $93.2 billion expected"
    result = extract_earnings_figures(text)
    assert result["reported_revenue"] is not None

def test_beat_miss_detected():
    text = "EPS of $2.10, estimates of $1.95"
    result = extract_earnings_figures(text)
    assert result["beat_miss"] == "beat"

def test_no_figures_returns_none_values():
    result = extract_earnings_figures("Company held annual meeting today")
    assert result["reported_eps"] is None
    assert result["beat_miss"] is None
