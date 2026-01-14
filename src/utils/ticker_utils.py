"""
Ticker Extraction Utility
========================

Shared ticker extraction logic for all agents.
Extracts stock ticker symbols from natural language queries.
"""

import re
from typing import Optional

# Known tickers we support (expanded list)
KNOWN_TICKERS = {
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA",
    "AMD", "INTC", "NFLX", "DIS", "BA", "JPM", "GS", "V", "MA",
    "WMT", "TGT", "COST", "HD", "NKE", "SBUX", "MCD", "KO", "PEP",
    "JNJ", "PFE", "UNH", "CVS", "ABBV", "MRK", "LLY", "BMY",
    "XOM", "CVX", "COP", "SLB", "OXY",
    "SPY", "QQQ", "DIA", "IWM", "VTI",
    "IBM", "ORCL", "CRM", "SAP", "CSCO", "ADBE", "NOW", "SNOW",
    "UBER", "LYFT", "ABNB", "DASH", "RBLX", "COIN", "SQ", "PYPL",
    "F", "GM", "TM", "HMC", "RIVN", "LCID",
    "T", "VZ", "TMUS", "CMCSA",
    "BRK.A", "BRK.B", "BRKB",
    "C", "BAC", "WFC", "USB", "PNC", "SCHW",
}

# Company name to ticker mapping
COMPANY_TO_TICKER = {
    "APPLE": "AAPL",
    "APPLE'S": "AAPL",
    "MICROSOFT": "MSFT",
    "MICROSOFT'S": "MSFT",
    "GOOGLE": "GOOGL",
    "GOOGLE'S": "GOOGL",
    "ALPHABET": "GOOGL",
    "AMAZON": "AMZN",
    "AMAZON'S": "AMZN",
    "TESLA": "TSLA",
    "TESLA'S": "TSLA",
    "NVIDIA": "NVDA",
    "NVIDIA'S": "NVDA",
    "META": "META",
    "FACEBOOK": "META",
    "NETFLIX": "NFLX",
    "DISNEY": "DIS",
    "BOEING": "BA",
    "WALMART": "WMT",
    "TARGET": "TGT",
    "COSTCO": "COST",
    "NIKE": "NKE",
    "STARBUCKS": "SBUX",
    "MCDONALD'S": "MCD",
    "MCDONALDS": "MCD",
    "COCA-COLA": "KO",
    "PEPSI": "PEP",
    "PEPSICO": "PEP",
    "INTEL": "INTC",
    "ORACLE": "ORCL",
    "SALESFORCE": "CRM",
    "CISCO": "CSCO",
    "ADOBE": "ADBE",
    "UBER": "UBER",
    "LYFT": "LYFT",
    "AIRBNB": "ABNB",
    "DOORDASH": "DASH",
    "ROBLOX": "RBLX",
    "COINBASE": "COIN",
    "PAYPAL": "PYPL",
    "FORD": "F",
    "CHEVRON": "CVX",
    "EXXON": "XOM",
    "JPMORGAN": "JPM",
    "JP MORGAN": "JPM",
    "GOLDMAN": "GS",
    "GOLDMAN SACHS": "GS",
    "BANK OF AMERICA": "BAC",
    "WELLS FARGO": "WFC",
}

# Common non-ticker words to exclude
EXCLUDED_WORDS = {
    "A", "I", "THE", "OF", "AND", "FOR", "IS", "IT", "MY", "TO", "IN", "AT",
    "ON", "BE", "AS", "OR", "AN", "BY", "IF", "UP", "SO", "NO", "DO", "GO",
    "HAS", "CAN", "GET", "HOW", "NEW", "NOW", "OLD", "OUR", "OUT", "OWN",
    "SAY", "SEE", "WHAT", "WHEN", "WHO", "WHY", "WAY", "WELL", "WANT", "ME",
    "GIVE", "TAKE", "MAKE", "GOOD", "TIME", "JUST", "KNOW", "COME", "THINK",
    "LOOK", "USE", "FIND", "TELL", "ASK", "WORK", "SEEM", "FEEL", "TRY", "ALSO",
    "STOCK", "PRICE", "QUOTE", "SHARE", "VALUE", "CURRENT", "TODAY", "BUY", "SELL",
    "INDUSTRY", "SECTOR", "MARKET", "ANALYSTS", "SAYING", "ABOUT", "SHOW", "TRENDS",
    "LONG", "TERM", "SHORT", "POTENTIAL", "INVESTMENT", "INVEST", "INVESTING",
    "BASED", "RECENT", "NEWS", "SENTIMENT", "ANALYSIS", "ANALYZE", "TECHNICAL",
    "INDICATORS", "PATTERNS", "BULLISH", "BEARISH", "RISK", "RISKY", "METRICS",
    "VAR", "BETA", "VOLATILITY", "COMPARED", "ARE", "SAYING", "HAPPENING",
    "COMPREHENSIVE", "PORTFOLIO", "REVIEW", "PERFORMANCE", "SUGGEST", "REBALANCING",
    "RSI", "MACD", "BOLLINGER", "BANDS", "CALCULATE", "SEMICONDUCTOR", "CHIP",
    "OPINIONS", "OPINION", "ANALYST", "PLEASE", "THANK", "THANKS", "WOULD", "COULD",
    "VIEWS", "VIEW", "OUTLOOK", "SUMMARIZE", "SUMMARY", "DESCRIBE", "EXPLAIN",
    "GIVE", "PROVIDE", "INFO", "INFORMATION", "DATA", "DETAILS", "TREND",
    "ASSESS", "PROFILE", "CALCULATE", "LATEST", "KEY", "FINANCIALS", "FILINGS",
    "SEC", "COMPLETE", "INCLUDING", "FUNDAMENTALS",
}


def extract_ticker(query: str) -> Optional[str]:
    """
    Extract stock ticker symbol from a natural language query.
    
    Uses multiple strategies:
    1. Company name matching (e.g., "Apple" -> "AAPL")
    2. Pattern matching (e.g., "$AAPL", "AAPL stock")
    3. Known ticker lookup
    4. Fallback to uppercase words that look like tickers
    
    Args:
        query: Natural language query string
        
    Returns:
        Ticker symbol (uppercase) or None if not found
        
    Examples:
        >>> extract_ticker("What is the price of AAPL?")
        'AAPL'
        >>> extract_ticker("Tell me about Tesla stock")
        'TSLA'
        >>> extract_ticker("$NVDA analysis")
        'NVDA'
    """
    query_upper = query.upper()
    
    # Normalize apostrophes (curly to straight)
    query_normalized = query_upper.replace("'", "'").replace("'", "'")
    
    # First, check for company names (longest match first to avoid partial matches)
    for company in sorted(COMPANY_TO_TICKER.keys(), key=len, reverse=True):
        if company in query_normalized:
            return COMPANY_TO_TICKER[company]
    
    # Look for common ticker patterns
    patterns = [
        r'\b([A-Z]{1,5})\b(?:\s+stock|\s+shares?)',  # "AAPL stock"
        r'(?:ticker|symbol)\s+([A-Z]{1,5})\b',       # "ticker AAPL"
        r'\$([A-Z]{1,5})\b',                          # "$AAPL"
        r'(?:price\s+of|analyze|about)\s+([A-Z]{1,5})\b',  # "price of AAPL"
        r'(?:risk|volatility|beta)\s+(?:of|for)\s+([A-Z]{1,5})\b',  # "risk of AMZN"
        r'([A-Z]{1,5})(?:\'s|\s+price|\s+news|\s+risk)',  # "AAPL's" or "AAPL price"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query_upper)
        if match:
            ticker = match.group(1)
            if ticker in KNOWN_TICKERS:
                return ticker
    
    # Check for standalone words that match known tickers (strip punctuation first)
    words = query_upper.split()
    for word in words:
        # Strip common punctuation from word boundaries
        clean_word = word.strip("?.,!;:'\"()[]")
        if clean_word in KNOWN_TICKERS:
            return clean_word
    
    # Last resort: look for any word that looks like a ticker
    # Must be uppercase, 1-5 chars, alphabetic, and not an excluded word
    for word in words:
        clean_word = word.strip("?.,!;:'\"()[]")
        if (1 <= len(clean_word) <= 5 and 
            clean_word.isalpha() and 
            clean_word.isupper() and 
            clean_word not in EXCLUDED_WORDS):
            return clean_word
    
    return None
