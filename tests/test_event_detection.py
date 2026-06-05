from agents.event_detection import parse_event_json, should_run_llm

def test_parse_valid_event_json():
    raw = '{"category": "earnings_report", "severity": 0.8, "summary": "Beat estimates"}'
    result = parse_event_json(raw)
    assert result["category"] == "earnings_report"
    assert result["severity"] == 0.8

def test_parse_malformed_json_returns_none():
    raw = '{"category": "earnings_report", "severity": bad}'
    result = parse_event_json(raw)
    assert result is None

def test_should_run_llm_skips_neutral_no_keywords():
    result = should_run_llm(sentiment_score=0.05, article_text="The weather is nice today")
    assert result is False

def test_should_run_llm_triggers_on_keyword():
    result = should_run_llm(sentiment_score=0.05, article_text="Company announced merger with rival")
    assert result is True
