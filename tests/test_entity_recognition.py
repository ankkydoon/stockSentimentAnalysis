from agents.entity_recognition import extract_ticker_patterns, has_financial_cue, FINANCIAL_CUES


def test_extract_dollar_ticker():
    tickers = extract_ticker_patterns("Shares of $AAPL rose 3% today")
    assert "AAPL" in tickers


def test_extract_exchange_ticker():
    tickers = extract_ticker_patterns("Microsoft (NASDAQ: MSFT) reported earnings")
    assert "MSFT" in tickers


def test_has_financial_cue_true():
    assert has_financial_cue("Apple shares rose on strong earnings") is True


def test_has_financial_cue_false():
    assert has_financial_cue("The weather is nice today in London") is False
