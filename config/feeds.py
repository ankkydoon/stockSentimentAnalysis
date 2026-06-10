RSS_FEEDS = [
    # CNBC — open RSS, article bodies accessible
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",   # Top News
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",    # Finance
    # MarketWatch — RSS works; article bodies fall back to RSS summary
    "https://www.marketwatch.com/rss/topstories",
    # SEC EDGAR 8-K filings — plain XML (User-Agent set in EDGAR_USER_AGENT env var)
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=40&output=atom",
]
