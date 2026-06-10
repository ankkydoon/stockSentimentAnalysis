RSS_FEEDS = [
    # Yahoo Finance — open RSS, no scraping needed, full headlines
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    # SEC EDGAR 8-K filings — plain XML, requires EDGAR_USER_AGENT header
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=40&output=atom",
    # Add more bot-friendly feeds here as needed
]
