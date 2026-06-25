"""Project Cockpit — central configuration.

Target tickers, RSS strings, weather coordinates, model routing and
output-contract constants. Everything here is data, no logic.
"""
import os

# ---------------------------------------------------------------- timezone
WIB_UTC_OFFSET = 7  # Asia/Jakarta

# ---------------------------------------------------------------- telemetry
# (yahoo symbol, display label, asset class)
# PRD B3 monitored-asset registry (indices, assets, rates for marquee telemetry
# cards). yfinance symbol doubles as the Yahoo Finance source link.
TICKERS = [
    ("^JKSE",    "JCI / IHSG",          "index"),
    ("^IXIC",    "Nasdaq",              "index"),
    ("^GSPC",    "S&P 500",             "index"),
    ("^N225",    "Nikkei 225",          "index"),
    ("^DJI",     "Dow Jones",           "index"),
    ("BTC-USD",  "Bitcoin / USD",       "crypto"),
    ("GC=F",     "Gold Spot",           "commodity"),
    ("BZ=F",     "Brent Crude",         "commodity"),
    ("CL=F",     "Crude Oil (WTI)",     "commodity"),
    ("ITMG.JK",  "Coal proxy (ITMG)",   "commodity"),
    ("INCO.JK",  "Nickel proxy (INCO)", "commodity"),
    ("USDIDR=X", "USD/IDR",             "fx"),
    ("DX-Y.NYB", "US Dollar Index",     "fx"),
    ("^IRX",     "US 3M T-Bill",        "rates"),
    ("^TNX",     "US 10Y Yield",        "rates"),
    ("^VIX",     "CBOE VIX",            "rates"),
]
YF_QUOTE = "https://finance.yahoo.com/quote/"

# Non-Yahoo macro-rate benchmarks. These are fetched by tools.macro_rates and
# added to the same telemetry rail with source labels preserved.
MACRO_RATE_BENCHMARKS = [
    ("BI_RATE", "BI Rate", "policy"),
    ("ID10Y", "Indonesia 10Y SBN", "rates"),
]

# A JCI or Nasdaq move beyond this absolute % triggers the Market Anomaly Event.
ANOMALY_THRESHOLD_PCT = 1.2
ANOMALY_WATCHLIST = ("^JKSE", "^IXIC")

# ---------------------------------------------------------------- sector universe
# Project Cockpit v2 — Sector Flow Matrix. Extensible registry: add sectors or
# constituents here with no code changes (PRD C5). Curated subset of the full
# 201-ticker universe, weighted to Vito's climate / SEA venture thesis. Each
# constituent: (ticker, company, yfinance_symbol, exchange, country, mktcap,
# tier, *flags). tier ∈ mega|large|mid|small. flags: "spec" = speculative.
SECTOR_SIGNAL_PCT = {"alert": 1.5, "watch": 0.8}  # |aggregate %| thresholds
FUNDAMENTAL_REFRESH_HOURS = 24       # reuse real Yahoo metrics between daily refreshes
FUNDAMENTAL_WORKERS = 6              # bounded parallelism for yfinance quote-summary calls
GLOBAL_LEADERS_PRICE_ACTIVE = True   # price-only coverage; no fundamentals/news expansion yet
IDX_BROAD_PRICE_ACTIVE = True        # broad IDX quote-only heatmap coverage
SP500_PRICE_ACTIVE = True            # dynamic S&P 500 quote-only heatmap coverage
NASDAQ100_PRICE_ACTIVE = True        # dynamic Nasdaq 100 quote-only heatmap coverage
CRYPTO_TOP_PRICE_ACTIVE = True       # CoinGecko top market-cap crypto quote-only coverage
CRYPTO_TOP_PRICE_LIMIT = 100
PRICE_ONLY_CHART_LIMIT = 160         # core rows get charts; broad rows above this use quote-lite
US_INDEX_LIMITS = {"sp500": 520, "nasdaq100": 120}

# Country / region metadata used by the dashboard and by the next universe
# expansion. "OTHERS" is intentionally separate from US and Indonesia so sector
# cards can eventually show ID / US / Others without double-counting.
COUNTRY_META = {
    "ID": {"name": "Indonesia", "flag": "🇮🇩", "region": "ID"},
    "US": {"name": "United States", "flag": "🇺🇸", "region": "US"},
    "CR": {"name": "Crypto", "flag": "₿", "region": "CRYPTO"},
    "SG": {"name": "Singapore", "flag": "🇸🇬", "region": "OTHERS"},
    "JP": {"name": "Japan", "flag": "🇯🇵", "region": "OTHERS"},
    "KR": {"name": "South Korea", "flag": "🇰🇷", "region": "OTHERS"},
    "TW": {"name": "Taiwan", "flag": "🇹🇼", "region": "OTHERS"},
    "HK": {"name": "Hong Kong / China", "flag": "🇭🇰", "region": "OTHERS"},
    "NL": {"name": "Netherlands", "flag": "🇳🇱", "region": "OTHERS"},
    "DK": {"name": "Denmark", "flag": "🇩🇰", "region": "OTHERS"},
    "DE": {"name": "Germany", "flag": "🇩🇪", "region": "OTHERS"},
    "CH": {"name": "Switzerland", "flag": "🇨🇭", "region": "OTHERS"},
    "FR": {"name": "France", "flag": "🇫🇷", "region": "OTHERS"},
    "GB": {"name": "United Kingdom", "flag": "🇬🇧", "region": "OTHERS"},
    "ES": {"name": "Spain", "flag": "🇪🇸", "region": "OTHERS"},
    "AU": {"name": "Australia", "flag": "🇦🇺", "region": "OTHERS"},
    "IN": {"name": "India", "flag": "🇮🇳", "region": "OTHERS"},
}
REGION_LABELS = {
    "ID": "Indonesia",
    "US": "US",
    "CRYPTO": "Crypto",
    "OTHERS": "Others",
}

# Global Leaders V1 is a research/watch universe, not yet a cron-active scoring
# universe. It gives the UI and future screener/heatmap a clean source of truth
# for non-ID / non-US leaders before we scale into full S&P 500, Nasdaq 100,
# full IDX, and top-100 crypto coverage.
GLOBAL_LEADERS_V1 = [
    # Singapore
    {"sector": "financials", "ticker": "D05", "name": "DBS Group", "source_symbol": "D05.SI", "exchange": "SGX", "country": "SG", "tier": "mega"},
    {"sector": "financials", "ticker": "O39", "name": "OCBC Bank", "source_symbol": "O39.SI", "exchange": "SGX", "country": "SG", "tier": "large"},
    {"sector": "financials", "ticker": "U11", "name": "United Overseas Bank", "source_symbol": "U11.SI", "exchange": "SGX", "country": "SG", "tier": "large"},
    {"sector": "technology", "ticker": "Z74", "name": "Singtel", "source_symbol": "Z74.SI", "exchange": "SGX", "country": "SG", "tier": "large"},
    {"sector": "logistics", "ticker": "C6L", "name": "Singapore Airlines", "source_symbol": "C6L.SI", "exchange": "SGX", "country": "SG", "tier": "large"},
    {"sector": "logistics", "ticker": "BN4", "name": "Keppel", "source_symbol": "BN4.SI", "exchange": "SGX", "country": "SG", "tier": "large"},
    {"sector": "consumer", "ticker": "F34", "name": "Wilmar International", "source_symbol": "F34.SI", "exchange": "SGX", "country": "SG", "tier": "large"},
    {"sector": "financials", "ticker": "S68", "name": "Singapore Exchange", "source_symbol": "S68.SI", "exchange": "SGX", "country": "SG", "tier": "large"},
    {"sector": "property", "ticker": "C38U", "name": "CapitaLand Integrated Commercial Trust", "source_symbol": "C38U.SI", "exchange": "SGX", "country": "SG", "tier": "mid"},
    {"sector": "property", "ticker": "A17U", "name": "CapitaLand Ascendas REIT", "source_symbol": "A17U.SI", "exchange": "SGX", "country": "SG", "tier": "mid"},

    # Japan
    {"sector": "consumer", "ticker": "7203", "name": "Toyota Motor", "source_symbol": "7203.T", "exchange": "TSE", "country": "JP", "tier": "mega"},
    {"sector": "technology", "ticker": "6758", "name": "Sony Group", "source_symbol": "6758.T", "exchange": "TSE", "country": "JP", "tier": "mega"},
    {"sector": "technology", "ticker": "9984", "name": "SoftBank Group", "source_symbol": "9984.T", "exchange": "TSE", "country": "JP", "tier": "mega"},
    {"sector": "financials", "ticker": "8306", "name": "Mitsubishi UFJ Financial", "source_symbol": "8306.T", "exchange": "TSE", "country": "JP", "tier": "mega"},
    {"sector": "technology", "ticker": "6861", "name": "Keyence", "source_symbol": "6861.T", "exchange": "TSE", "country": "JP", "tier": "mega"},
    {"sector": "technology", "ticker": "8035", "name": "Tokyo Electron", "source_symbol": "8035.T", "exchange": "TSE", "country": "JP", "tier": "mega"},
    {"sector": "consumer", "ticker": "6098", "name": "Recruit Holdings", "source_symbol": "6098.T", "exchange": "TSE", "country": "JP", "tier": "large"},
    {"sector": "technology", "ticker": "9432", "name": "Nippon Telegraph and Telephone", "source_symbol": "9432.T", "exchange": "TSE", "country": "JP", "tier": "large"},
    {"sector": "energy", "ticker": "8058", "name": "Mitsubishi Corporation", "source_symbol": "8058.T", "exchange": "TSE", "country": "JP", "tier": "large"},
    {"sector": "entertainment", "ticker": "7974", "name": "Nintendo", "source_symbol": "7974.T", "exchange": "TSE", "country": "JP", "tier": "large"},
    {"sector": "healthcare", "ticker": "4568", "name": "Daiichi Sankyo", "source_symbol": "4568.T", "exchange": "TSE", "country": "JP", "tier": "large"},
    {"sector": "infrastructure", "ticker": "6501", "name": "Hitachi", "source_symbol": "6501.T", "exchange": "TSE", "country": "JP", "tier": "large"},

    # South Korea
    {"sector": "technology", "ticker": "005930", "name": "Samsung Electronics", "source_symbol": "005930.KS", "exchange": "KRX", "country": "KR", "tier": "mega"},
    {"sector": "technology", "ticker": "000660", "name": "SK Hynix", "source_symbol": "000660.KS", "exchange": "KRX", "country": "KR", "tier": "mega"},
    {"sector": "renewables", "ticker": "373220", "name": "LG Energy Solution", "source_symbol": "373220.KS", "exchange": "KRX", "country": "KR", "tier": "mega"},
    {"sector": "healthcare", "ticker": "207940", "name": "Samsung Biologics", "source_symbol": "207940.KS", "exchange": "KRX", "country": "KR", "tier": "large"},
    {"sector": "consumer", "ticker": "005380", "name": "Hyundai Motor", "source_symbol": "005380.KS", "exchange": "KRX", "country": "KR", "tier": "large"},
    {"sector": "consumer", "ticker": "000270", "name": "Kia", "source_symbol": "000270.KS", "exchange": "KRX", "country": "KR", "tier": "large"},
    {"sector": "healthcare", "ticker": "068270", "name": "Celltrion", "source_symbol": "068270.KS", "exchange": "KRX", "country": "KR", "tier": "large"},
    {"sector": "technology", "ticker": "035420", "name": "Naver", "source_symbol": "035420.KS", "exchange": "KRX", "country": "KR", "tier": "large"},
    {"sector": "technology", "ticker": "035720", "name": "Kakao", "source_symbol": "035720.KS", "exchange": "KRX", "country": "KR", "tier": "large"},
    {"sector": "renewables", "ticker": "051910", "name": "LG Chem", "source_symbol": "051910.KS", "exchange": "KRX", "country": "KR", "tier": "large"},
    {"sector": "energy", "ticker": "005490", "name": "POSCO Holdings", "source_symbol": "005490.KS", "exchange": "KRX", "country": "KR", "tier": "large"},

    # Taiwan
    {"sector": "technology", "ticker": "2330", "name": "Taiwan Semiconductor Manufacturing", "source_symbol": "2330.TW", "exchange": "TWSE", "country": "TW", "tier": "mega"},
    {"sector": "technology", "ticker": "2317", "name": "Hon Hai Precision", "source_symbol": "2317.TW", "exchange": "TWSE", "country": "TW", "tier": "mega"},
    {"sector": "technology", "ticker": "2454", "name": "MediaTek", "source_symbol": "2454.TW", "exchange": "TWSE", "country": "TW", "tier": "mega"},
    {"sector": "technology", "ticker": "2308", "name": "Delta Electronics", "source_symbol": "2308.TW", "exchange": "TWSE", "country": "TW", "tier": "large"},
    {"sector": "technology", "ticker": "2382", "name": "Quanta Computer", "source_symbol": "2382.TW", "exchange": "TWSE", "country": "TW", "tier": "large"},
    {"sector": "financials", "ticker": "2881", "name": "Fubon Financial", "source_symbol": "2881.TW", "exchange": "TWSE", "country": "TW", "tier": "large"},
    {"sector": "financials", "ticker": "2891", "name": "CTBC Financial", "source_symbol": "2891.TW", "exchange": "TWSE", "country": "TW", "tier": "large"},
    {"sector": "financials", "ticker": "2882", "name": "Cathay Financial", "source_symbol": "2882.TW", "exchange": "TWSE", "country": "TW", "tier": "large"},
    {"sector": "technology", "ticker": "2412", "name": "Chunghwa Telecom", "source_symbol": "2412.TW", "exchange": "TWSE", "country": "TW", "tier": "large"},
    {"sector": "technology", "ticker": "2303", "name": "United Microelectronics", "source_symbol": "2303.TW", "exchange": "TWSE", "country": "TW", "tier": "large"},
    {"sector": "technology", "ticker": "2357", "name": "ASUSTeK Computer", "source_symbol": "2357.TW", "exchange": "TWSE", "country": "TW", "tier": "large"},

    # Hong Kong / China
    {"sector": "technology", "ticker": "0700", "name": "Tencent Holdings", "source_symbol": "0700.HK", "exchange": "HKEX", "country": "HK", "tier": "mega"},
    {"sector": "technology", "ticker": "9988", "name": "Alibaba Group", "source_symbol": "9988.HK", "exchange": "HKEX", "country": "HK", "tier": "mega"},
    {"sector": "consumer", "ticker": "3690", "name": "Meituan", "source_symbol": "3690.HK", "exchange": "HKEX", "country": "HK", "tier": "mega"},
    {"sector": "consumer", "ticker": "9618", "name": "JD.com", "source_symbol": "9618.HK", "exchange": "HKEX", "country": "HK", "tier": "large"},
    {"sector": "financials", "ticker": "1299", "name": "AIA Group", "source_symbol": "1299.HK", "exchange": "HKEX", "country": "HK", "tier": "mega"},
    {"sector": "financials", "ticker": "0388", "name": "Hong Kong Exchanges and Clearing", "source_symbol": "0388.HK", "exchange": "HKEX", "country": "HK", "tier": "large"},
    {"sector": "financials", "ticker": "0005", "name": "HSBC Holdings", "source_symbol": "0005.HK", "exchange": "HKEX", "country": "HK", "tier": "mega"},
    {"sector": "financials", "ticker": "0939", "name": "China Construction Bank", "source_symbol": "0939.HK", "exchange": "HKEX", "country": "HK", "tier": "mega"},
    {"sector": "renewables", "ticker": "1211", "name": "BYD Company", "source_symbol": "1211.HK", "exchange": "HKEX", "country": "HK", "tier": "mega"},
    {"sector": "technology", "ticker": "1810", "name": "Xiaomi", "source_symbol": "1810.HK", "exchange": "HKEX", "country": "HK", "tier": "large"},
    {"sector": "energy", "ticker": "0883", "name": "CNOOC", "source_symbol": "0883.HK", "exchange": "HKEX", "country": "HK", "tier": "large"},

    # Europe
    {"sector": "technology", "ticker": "ASML", "name": "ASML Holding", "source_symbol": "ASML.AS", "exchange": "Euronext", "country": "NL", "tier": "mega"},
    {"sector": "healthcare", "ticker": "NOVO-B", "name": "Novo Nordisk", "source_symbol": "NOVO-B.CO", "exchange": "Nasdaq Copenhagen", "country": "DK", "tier": "mega"},
    {"sector": "technology", "ticker": "SAP", "name": "SAP", "source_symbol": "SAP.DE", "exchange": "XETRA", "country": "DE", "tier": "mega"},
    {"sector": "consumer", "ticker": "NESN", "name": "Nestle", "source_symbol": "NESN.SW", "exchange": "SIX", "country": "CH", "tier": "mega"},
    {"sector": "healthcare", "ticker": "ROG", "name": "Roche", "source_symbol": "ROG.SW", "exchange": "SIX", "country": "CH", "tier": "mega"},
    {"sector": "healthcare", "ticker": "NOVN", "name": "Novartis", "source_symbol": "NOVN.SW", "exchange": "SIX", "country": "CH", "tier": "mega"},
    {"sector": "consumer", "ticker": "MC", "name": "LVMH", "source_symbol": "MC.PA", "exchange": "Euronext Paris", "country": "FR", "tier": "mega"},
    {"sector": "consumer", "ticker": "RMS", "name": "Hermes International", "source_symbol": "RMS.PA", "exchange": "Euronext Paris", "country": "FR", "tier": "large"},
    {"sector": "consumer", "ticker": "OR", "name": "L'Oreal", "source_symbol": "OR.PA", "exchange": "Euronext Paris", "country": "FR", "tier": "mega"},
    {"sector": "energy", "ticker": "SHEL", "name": "Shell", "source_symbol": "SHEL.L", "exchange": "LSE", "country": "GB", "tier": "mega"},
    {"sector": "financials", "ticker": "HSBA", "name": "HSBC Holdings", "source_symbol": "HSBA.L", "exchange": "LSE", "country": "GB", "tier": "mega"},
    {"sector": "healthcare", "ticker": "AZN", "name": "AstraZeneca", "source_symbol": "AZN.L", "exchange": "LSE", "country": "GB", "tier": "mega"},
    {"sector": "consumer", "ticker": "ULVR", "name": "Unilever", "source_symbol": "ULVR.L", "exchange": "LSE", "country": "GB", "tier": "large"},
    {"sector": "energy", "ticker": "TTE", "name": "TotalEnergies", "source_symbol": "TTE.PA", "exchange": "Euronext Paris", "country": "FR", "tier": "mega"},
    {"sector": "infrastructure", "ticker": "AIR", "name": "Airbus", "source_symbol": "AIR.PA", "exchange": "Euronext Paris", "country": "FR", "tier": "large"},
    {"sector": "infrastructure", "ticker": "SIE", "name": "Siemens", "source_symbol": "SIE.DE", "exchange": "XETRA", "country": "DE", "tier": "mega"},
    {"sector": "financials", "ticker": "ALV", "name": "Allianz", "source_symbol": "ALV.DE", "exchange": "XETRA", "country": "DE", "tier": "large"},
    {"sector": "financials", "ticker": "SAN", "name": "Banco Santander", "source_symbol": "SAN.MC", "exchange": "BME", "country": "ES", "tier": "large"},

    # Australia
    {"sector": "energy", "ticker": "BHP", "name": "BHP Group", "source_symbol": "BHP.AX", "exchange": "ASX", "country": "AU", "tier": "mega"},
    {"sector": "financials", "ticker": "CBA", "name": "Commonwealth Bank of Australia", "source_symbol": "CBA.AX", "exchange": "ASX", "country": "AU", "tier": "mega"},
    {"sector": "healthcare", "ticker": "CSL", "name": "CSL", "source_symbol": "CSL.AX", "exchange": "ASX", "country": "AU", "tier": "mega"},
    {"sector": "financials", "ticker": "NAB", "name": "National Australia Bank", "source_symbol": "NAB.AX", "exchange": "ASX", "country": "AU", "tier": "large"},
    {"sector": "financials", "ticker": "WBC", "name": "Westpac Banking", "source_symbol": "WBC.AX", "exchange": "ASX", "country": "AU", "tier": "large"},
    {"sector": "financials", "ticker": "ANZ", "name": "ANZ Group", "source_symbol": "ANZ.AX", "exchange": "ASX", "country": "AU", "tier": "large"},
    {"sector": "financials", "ticker": "MQG", "name": "Macquarie Group", "source_symbol": "MQG.AX", "exchange": "ASX", "country": "AU", "tier": "large"},
    {"sector": "consumer", "ticker": "WES", "name": "Wesfarmers", "source_symbol": "WES.AX", "exchange": "ASX", "country": "AU", "tier": "large"},
    {"sector": "energy", "ticker": "FMG", "name": "Fortescue", "source_symbol": "FMG.AX", "exchange": "ASX", "country": "AU", "tier": "large"},
    {"sector": "consumer", "ticker": "WOW", "name": "Woolworths Group", "source_symbol": "WOW.AX", "exchange": "ASX", "country": "AU", "tier": "large"},

    # India
    {"sector": "energy", "ticker": "RELIANCE", "name": "Reliance Industries", "source_symbol": "RELIANCE.NS", "exchange": "NSE", "country": "IN", "tier": "mega"},
    {"sector": "technology", "ticker": "TCS", "name": "Tata Consultancy Services", "source_symbol": "TCS.NS", "exchange": "NSE", "country": "IN", "tier": "mega"},
    {"sector": "financials", "ticker": "HDFCBANK", "name": "HDFC Bank", "source_symbol": "HDFCBANK.NS", "exchange": "NSE", "country": "IN", "tier": "mega"},
    {"sector": "financials", "ticker": "ICICIBANK", "name": "ICICI Bank", "source_symbol": "ICICIBANK.NS", "exchange": "NSE", "country": "IN", "tier": "large"},
    {"sector": "technology", "ticker": "INFY", "name": "Infosys", "source_symbol": "INFY.NS", "exchange": "NSE", "country": "IN", "tier": "large"},
    {"sector": "technology", "ticker": "BHARTIARTL", "name": "Bharti Airtel", "source_symbol": "BHARTIARTL.NS", "exchange": "NSE", "country": "IN", "tier": "large"},
    {"sector": "financials", "ticker": "SBIN", "name": "State Bank of India", "source_symbol": "SBIN.NS", "exchange": "NSE", "country": "IN", "tier": "large"},
    {"sector": "consumer", "ticker": "HINDUNILVR", "name": "Hindustan Unilever", "source_symbol": "HINDUNILVR.NS", "exchange": "NSE", "country": "IN", "tier": "large"},
    {"sector": "consumer", "ticker": "ITC", "name": "ITC", "source_symbol": "ITC.NS", "exchange": "NSE", "country": "IN", "tier": "large"},
    {"sector": "infrastructure", "ticker": "LT", "name": "Larsen & Toubro", "source_symbol": "LT.NS", "exchange": "NSE", "country": "IN", "tier": "large"},
]

# Broad IDX V1 is quote-only. It expands the Indonesia heatmap and movers beyond
# the scored Sector Flow core without forcing every listed name through daily
# fundamentals, valuation, and DeepSeek reasoning.
IDX_BROAD_V1 = [
    {"sector": "technology", "ticker": "EDGE", "name": "Indointernet", "source_symbol": "EDGE.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "technology", "ticker": "DMMX", "name": "Digital Mediatama Maxima", "source_symbol": "DMMX.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "technology", "ticker": "NFCX", "name": "NFC Indonesia", "source_symbol": "NFCX.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "technology", "ticker": "KREN", "name": "Quantum Clovera Investama", "source_symbol": "KREN.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "technology", "ticker": "TFAS", "name": "Telefast Indonesia", "source_symbol": "TFAS.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "technology", "ticker": "CASH", "name": "Cashlez Worldwide Indonesia", "source_symbol": "CASH.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "financials", "ticker": "BBTN", "name": "Bank Tabungan Negara", "source_symbol": "BBTN.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "financials", "ticker": "PNBN", "name": "Bank Pan Indonesia", "source_symbol": "PNBN.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "financials", "ticker": "BNGA", "name": "Bank CIMB Niaga", "source_symbol": "BNGA.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "financials", "ticker": "BNLI", "name": "Bank Permata", "source_symbol": "BNLI.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "financials", "ticker": "NISP", "name": "Bank OCBC NISP", "source_symbol": "NISP.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "financials", "ticker": "BDMN", "name": "Bank Danamon Indonesia", "source_symbol": "BDMN.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "financials", "ticker": "BFIN", "name": "BFI Finance Indonesia", "source_symbol": "BFIN.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "financials", "ticker": "TUGU", "name": "Asuransi Tugu Pratama Indonesia", "source_symbol": "TUGU.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "energy", "ticker": "AKRA", "name": "AKR Corporindo", "source_symbol": "AKRA.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "energy", "ticker": "MEDC", "name": "Medco Energi Internasional", "source_symbol": "MEDC.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "energy", "ticker": "INDY", "name": "Indika Energy", "source_symbol": "INDY.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "energy", "ticker": "HRUM", "name": "Harum Energy", "source_symbol": "HRUM.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "energy", "ticker": "BUMI", "name": "Bumi Resources", "source_symbol": "BUMI.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "energy", "ticker": "DOID", "name": "Delta Dunia Makmur", "source_symbol": "DOID.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "energy", "ticker": "ADMR", "name": "Adaro Minerals Indonesia", "source_symbol": "ADMR.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "energy", "ticker": "MBMA", "name": "Merdeka Battery Materials", "source_symbol": "MBMA.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "energy", "ticker": "NCKL", "name": "Trimegah Bangun Persada", "source_symbol": "NCKL.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "energy", "ticker": "PGAS", "name": "Perusahaan Gas Negara", "source_symbol": "PGAS.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "energy", "ticker": "ELSA", "name": "Elnusa", "source_symbol": "ELSA.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "energy", "ticker": "RAJA", "name": "Rukun Raharja", "source_symbol": "RAJA.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "renewables", "ticker": "BRPT", "name": "Barito Pacific", "source_symbol": "BRPT.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "renewables", "ticker": "TPIA", "name": "Chandra Asri Pacific", "source_symbol": "TPIA.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "renewables", "ticker": "ARKO", "name": "Arkora Hydro", "source_symbol": "ARKO.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "renewables", "ticker": "POWR", "name": "Cikarang Listrindo", "source_symbol": "POWR.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "consumer", "ticker": "ROTI", "name": "Nippon Indosari Corpindo", "source_symbol": "ROTI.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "consumer", "ticker": "CMRY", "name": "Cisarua Mountain Dairy", "source_symbol": "CMRY.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "consumer", "ticker": "CLEO", "name": "Sariguna Primatirta", "source_symbol": "CLEO.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "consumer", "ticker": "GOOD", "name": "Garudafood Putra Putri Jaya", "source_symbol": "GOOD.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "consumer", "ticker": "JPFA", "name": "Japfa Comfeed Indonesia", "source_symbol": "JPFA.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "consumer", "ticker": "MAIN", "name": "Malindo Feedmill", "source_symbol": "MAIN.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "consumer", "ticker": "MAPA", "name": "Map Aktif Adiperkasa", "source_symbol": "MAPA.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "consumer", "ticker": "MIDI", "name": "Midi Utama Indonesia", "source_symbol": "MIDI.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "consumer", "ticker": "RALS", "name": "Ramayana Lestari Sentosa", "source_symbol": "RALS.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "consumer", "ticker": "LPPF", "name": "Matahari Department Store", "source_symbol": "LPPF.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "infrastructure", "ticker": "EXCL", "name": "XL Axiata", "source_symbol": "EXCL.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "infrastructure", "ticker": "ISAT", "name": "Indosat", "source_symbol": "ISAT.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "infrastructure", "ticker": "LINK", "name": "Link Net", "source_symbol": "LINK.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "infrastructure", "ticker": "SMGR", "name": "Semen Indonesia", "source_symbol": "SMGR.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "infrastructure", "ticker": "INTP", "name": "Indocement Tunggal Prakarsa", "source_symbol": "INTP.JK", "exchange": "IDX", "country": "ID", "tier": "large"},
    {"sector": "infrastructure", "ticker": "ADHI", "name": "Adhi Karya", "source_symbol": "ADHI.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "infrastructure", "ticker": "WTON", "name": "Wijaya Karya Beton", "source_symbol": "WTON.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "infrastructure", "ticker": "SSIA", "name": "Surya Semesta Internusa", "source_symbol": "SSIA.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "healthcare", "ticker": "TSPC", "name": "Tempo Scan Pacific", "source_symbol": "TSPC.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "healthcare", "ticker": "KAEF", "name": "Kimia Farma", "source_symbol": "KAEF.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "healthcare", "ticker": "INAF", "name": "Indofarma", "source_symbol": "INAF.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "healthcare", "ticker": "SAME", "name": "Sarana Meditama Metropolitan", "source_symbol": "SAME.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "healthcare", "ticker": "SRAJ", "name": "Sejahteraraya Anugrahjaya", "source_symbol": "SRAJ.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "healthcare", "ticker": "SOHO", "name": "Soho Global Health", "source_symbol": "SOHO.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "healthcare", "ticker": "IRRA", "name": "Itama Ranoraya", "source_symbol": "IRRA.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "logistics", "ticker": "WEHA", "name": "WEHA Transportasi Indonesia", "source_symbol": "WEHA.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "logistics", "ticker": "HAIS", "name": "Hasnur Internasional Shipping", "source_symbol": "HAIS.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "logistics", "ticker": "HELI", "name": "Jaya Trishindo", "source_symbol": "HELI.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "logistics", "ticker": "GIAA", "name": "Garuda Indonesia", "source_symbol": "GIAA.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "logistics", "ticker": "SAPX", "name": "Satria Antaran Prima", "source_symbol": "SAPX.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "logistics", "ticker": "MBSS", "name": "Mitrabahtera Segara Sejati", "source_symbol": "MBSS.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "logistics", "ticker": "TPMA", "name": "Trans Power Marine", "source_symbol": "TPMA.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "logistics", "ticker": "WINS", "name": "Wintermar Offshore Marine", "source_symbol": "WINS.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "entertainment", "ticker": "ERAA", "name": "Erajaya Swasembada", "source_symbol": "ERAA.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "entertainment", "ticker": "MAPB", "name": "Map Boga Adiperkasa", "source_symbol": "MAPB.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "entertainment", "ticker": "MSIN", "name": "MNC Digital Entertainment", "source_symbol": "MSIN.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "entertainment", "ticker": "IPTV", "name": "MNC Vision Networks", "source_symbol": "IPTV.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "entertainment", "ticker": "NETV", "name": "Net Visi Media", "source_symbol": "NETV.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "property", "ticker": "BEST", "name": "Bekasi Fajar Industrial Estate", "source_symbol": "BEST.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "property", "ticker": "JRPT", "name": "Jaya Real Property", "source_symbol": "JRPT.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "property", "ticker": "DILD", "name": "Intiland Development", "source_symbol": "DILD.JK", "exchange": "IDX", "country": "ID", "tier": "mid"},
    {"sector": "property", "ticker": "MDLN", "name": "Modernland Realty", "source_symbol": "MDLN.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "property", "ticker": "BKSL", "name": "Sentul City", "source_symbol": "BKSL.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "property", "ticker": "GPRA", "name": "Perdana Gapuraprima", "source_symbol": "GPRA.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "property", "ticker": "RISE", "name": "Jaya Sukses Makmur Sentosa", "source_symbol": "RISE.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
    {"sector": "property", "ticker": "PURI", "name": "Puri Global Sukses", "source_symbol": "PURI.JK", "exchange": "IDX", "country": "ID", "tier": "small"},
]
SECTORS = [
    {"key": "technology", "name": "Technology", "icon": "▚",
     "theme": "AI infra · Digital banking", "constituents": [
        ("DCII", "DCI Indonesia", "DCII.JK", "IDX", "ID", "IDR 290T", "mega"),
        ("EMTK", "Elang Mahkota Teknologi", "EMTK.JK", "IDX", "ID", "IDR 61T", "large"),
        ("TLKM", "Telkom Indonesia", "TLKM.JK", "IDX", "ID", "IDR 200T", "mega"),
        ("GOTO", "GoTo Gojek Tokopedia", "GOTO.JK", "IDX", "ID", "IDR 42T", "large"),
        ("BUKA", "Bukalapak", "BUKA.JK", "IDX", "ID", "IDR 8T", "mid"),
        ("BELI", "Global Digital Niaga (Blibli)", "BELI.JK", "IDX", "ID", "IDR 18T", "mid"),
        ("MTDL", "Metrodata Electronics", "MTDL.JK", "IDX", "ID", "IDR 7T", "mid"),
        ("WIFI", "Solusi Sinergi Digital", "WIFI.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("MLPT", "Multipolar Technology", "MLPT.JK", "IDX", "ID", "IDR 4T", "mid"),
        ("MCAS", "M Cash Integrasi", "MCAS.JK", "IDX", "ID", "IDR 3T", "small"),
        ("NVDA", "Nvidia Corporation", "NVDA", "NASDAQ", "US", "$3.5T", "mega"),
        ("MSFT", "Microsoft Corporation", "MSFT", "NASDAQ", "US", "$3.1T", "mega"),
        ("AAPL", "Apple Inc", "AAPL", "NASDAQ", "US", "$3.3T", "mega"),
        ("META", "Meta Platforms", "META", "NASDAQ", "US", "$1.5T", "mega"),
        ("GOOGL", "Alphabet (Google)", "GOOGL", "NASDAQ", "US", "$2.1T", "mega"),
        ("AMZN", "Amazon", "AMZN", "NASDAQ", "US", "$2.2T", "mega"),
        ("CRM", "Salesforce", "CRM", "NYSE", "US", "$280B", "large"),
        ("AMD", "Advanced Micro Devices", "AMD", "NASDAQ", "US", "$200B", "large"),
        ("ORCL", "Oracle Corporation", "ORCL", "NYSE", "US", "$470B", "large"),
        ("SMCI", "Super Micro Computer", "SMCI", "NASDAQ", "US", "$28B", "mid"),
     ]},
    {"key": "financials", "name": "Financials", "icon": "▤",
     "theme": "BI rate · NIM expansion", "constituents": [
        ("BBCA", "Bank Central Asia", "BBCA.JK", "IDX", "ID", "IDR 1,023T", "mega"),
        ("BBRI", "Bank Rakyat Indonesia", "BBRI.JK", "IDX", "ID", "IDR 456T", "mega"),
        ("BMRI", "Bank Mandiri", "BMRI.JK", "IDX", "ID", "IDR 312T", "mega"),
        ("BBNI", "Bank Negara Indonesia", "BBNI.JK", "IDX", "ID", "IDR 89T", "large"),
        ("BRIS", "Bank Syariah Indonesia", "BRIS.JK", "IDX", "ID", "IDR 65T", "large"),
        ("BTPS", "Bank BTPN Syariah", "BTPS.JK", "IDX", "ID", "IDR 28T", "mid"),
        ("MEGA", "Bank Mega", "MEGA.JK", "IDX", "ID", "IDR 22T", "mid"),
        ("ARTO", "Bank Jago (Digital)", "ARTO.JK", "IDX", "ID", "IDR 30T", "mid"),
        ("BJTM", "Bank Pembangunan Daerah Jatim", "BJTM.JK", "IDX", "ID", "IDR 10T", "mid"),
        ("ADMF", "Adira Dinamika Multi Finance", "ADMF.JK", "IDX", "ID", "IDR 8T", "mid"),
        ("JPM", "JPMorgan Chase", "JPM", "NYSE", "US", "$700B", "mega"),
        ("BAC", "Bank of America", "BAC", "NYSE", "US", "$310B", "mega"),
        ("WFC", "Wells Fargo", "WFC", "NYSE", "US", "$230B", "mega"),
        ("V", "Visa Inc", "V", "NYSE", "US", "$560B", "mega"),
        ("MA", "Mastercard", "MA", "NYSE", "US", "$470B", "mega"),
        ("GS", "Goldman Sachs", "GS", "NYSE", "US", "$185B", "large"),
        ("MS", "Morgan Stanley", "MS", "NYSE", "US", "$195B", "large"),
        ("BLK", "BlackRock", "BLK", "NYSE", "US", "$135B", "large"),
        ("AXP", "American Express", "AXP", "NYSE", "US", "$200B", "large"),
        ("SCHW", "Charles Schwab", "SCHW", "NYSE", "US", "$130B", "large"),
     ]},
    {"key": "energy", "name": "Mining & Energy", "icon": "◭",
     "theme": "Nickel glut · coal cash flow", "constituents": [
        ("BYAN", "Bayan Resources", "BYAN.JK", "IDX", "ID", "IDR 540T", "mega"),
        ("AMMN", "Amman Mineral Internasional", "AMMN.JK", "IDX", "ID", "IDR 650T", "mega"),
        ("ADRO", "Alamtri Resources (Adaro)", "ADRO.JK", "IDX", "ID", "IDR 89T", "large"),
        ("MDKA", "Merdeka Copper Gold", "MDKA.JK", "IDX", "ID", "IDR 45T", "large"),
        ("PTBA", "Bukit Asam", "PTBA.JK", "IDX", "ID", "IDR 28T", "mid"),
        ("INCO", "Vale Indonesia", "INCO.JK", "IDX", "ID", "IDR 22T", "mid"),
        ("ANTM", "Aneka Tambang (Antam)", "ANTM.JK", "IDX", "ID", "IDR 18T", "mid"),
        ("ITMG", "Indo Tambangraya Megah", "ITMG.JK", "IDX", "ID", "IDR 15T", "mid"),
        ("TINS", "Timah (PT Timah Tbk)", "TINS.JK", "IDX", "ID", "IDR 7T", "mid"),
        ("SMMT", "Golden Eagle Energy", "SMMT.JK", "IDX", "ID", "IDR 4T", "small"),
        ("XOM", "ExxonMobil", "XOM", "NYSE", "US", "$480B", "mega"),
        ("CVX", "Chevron", "CVX", "NYSE", "US", "$260B", "mega"),
        ("COP", "ConocoPhillips", "COP", "NYSE", "US", "$130B", "mega"),
        ("FCX", "Freeport-McMoRan", "FCX", "NYSE", "US", "$55B", "large"),
        ("NEM", "Newmont Corporation", "NEM", "NYSE", "US", "$50B", "large"),
        ("SLB", "SLB (Schlumberger)", "SLB", "NYSE", "US", "$58B", "large"),
        ("EOG", "EOG Resources", "EOG", "NYSE", "US", "$65B", "large"),
        ("MPC", "Marathon Petroleum", "MPC", "NYSE", "US", "$60B", "large"),
        ("HAL", "Halliburton", "HAL", "NYSE", "US", "$28B", "mid"),
        ("DVN", "Devon Energy", "DVN", "NYSE", "US", "$22B", "mid"),
     ]},
    {"key": "renewables", "name": "Renewables & Climate-Tech", "icon": "☀",
     "theme": "PLN green capex · geothermal", "constituents": [
        ("BREN", "Barito Renewables Energy", "BREN.JK", "IDX", "ID", "IDR 890T", "mega"),
        ("PGEO", "Pertamina Geothermal Energy", "PGEO.JK", "IDX", "ID", "IDR 42T", "large"),
        ("BATR", "Barito Pacific (BREN parent)", "BATR.JK", "IDX", "ID", "IDR 120T", "mega"),
        ("TOBA", "TBS Energi Utama", "TOBA.JK", "IDX", "ID", "IDR 11T", "mid"),
        ("ESSA", "ESSA Industries", "ESSA.JK", "IDX", "ID", "IDR 8T", "mid"),
        ("KEEN", "Kencana Energi Lestari", "KEEN.JK", "IDX", "ID", "IDR 3T", "small"),
        ("GGRP", "Gunung Raja Paksi", "GGRP.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("CSAP", "Catur Sentosa Adiprana", "CSAP.JK", "IDX", "ID", "IDR 4T", "small"),
        ("VKTR", "VKTR Teknologi Mobilitas", "VKTR.JK", "IDX", "ID", "IDR 3-5T", "small"),
        ("PKPK", "Perdana Karya Perkasa", "PKPK.JK", "IDX", "ID", "IDR 2T", "small"),
        ("NEE", "NextEra Energy", "NEE", "NYSE", "US", "$145B", "mega"),
        ("FSLR", "First Solar", "FSLR", "NASDAQ", "US", "$18B", "mid"),
        ("ENPH", "Enphase Energy", "ENPH", "NASDAQ", "US", "$8B", "mid"),
        ("BEP", "Brookfield Renewable Partners", "BEP", "NYSE", "US", "$16B", "mid"),
        ("CWEN", "Clearway Energy", "CWEN", "NYSE", "US", "$5B", "mid"),
        ("AES", "AES Corporation", "AES", "NYSE", "US", "$14B", "mid"),
        ("RUN", "Sunrun", "RUN", "NASDAQ", "US", "$3B", "small"),
        ("PLUG", "Plug Power", "PLUG", "NASDAQ", "US", "$1.5B", "small"),
        ("ARRY", "Array Technologies", "ARRY", "NASDAQ", "US", "$1.8B", "small"),
        ("SEDG", "SolarEdge Technologies", "SEDG", "NASDAQ", "US", "$1.1B", "small"),
     ]},
    {"key": "consumer", "name": "Consumer & FMCG", "icon": "▦",
     "theme": "Demographic compounding", "constituents": [
        ("ICBP", "Indofood CBP Sukses Makmur", "ICBP.JK", "IDX", "ID", "IDR 89T", "large"),
        ("INDF", "Indofood Sukses Makmur", "INDF.JK", "IDX", "ID", "IDR 55T", "large"),
        ("HMSP", "HM Sampoerna", "HMSP.JK", "IDX", "ID", "IDR 95T", "large"),
        ("GGRM", "Gudang Garam", "GGRM.JK", "IDX", "ID", "IDR 60T", "large"),
        ("AMRT", "Sumber Alfaria Trijaya (Alfamart)", "AMRT.JK", "IDX", "ID", "IDR 75T", "large"),
        ("CPIN", "Charoen Pokphand Indonesia", "CPIN.JK", "IDX", "ID", "IDR 55T", "large"),
        ("MYOR", "Mayora Indah", "MYOR.JK", "IDX", "ID", "IDR 42T", "large"),
        ("UNVR", "Unilever Indonesia", "UNVR.JK", "IDX", "ID", "IDR 28T", "mid"),
        ("ACES", "Ace Hardware Indonesia", "ACES.JK", "IDX", "ID", "IDR 12T", "mid"),
        ("SIDO", "Sido Muncul", "SIDO.JK", "IDX", "ID", "IDR 14T", "mid"),
        ("WMT", "Walmart", "WMT", "NYSE", "US", "$780B", "mega"),
        ("PG", "Procter & Gamble", "PG", "NYSE", "US", "$390B", "mega"),
        ("KO", "Coca-Cola", "KO", "NYSE", "US", "$265B", "mega"),
        ("PEP", "PepsiCo", "PEP", "NASDAQ", "US", "$215B", "mega"),
        ("COST", "Costco Wholesale", "COST", "NASDAQ", "US", "$420B", "mega"),
        ("MCD", "McDonald's", "MCD", "NYSE", "US", "$220B", "mega"),
        ("NKE", "Nike", "NKE", "NYSE", "US", "$90B", "large"),
        ("MDLZ", "Mondelez International", "MDLZ", "NASDAQ", "US", "$80B", "large"),
        ("CL", "Colgate-Palmolive", "CL", "NYSE", "US", "$65B", "large"),
        ("EL", "Estee Lauder", "EL", "NYSE", "US", "$30B", "mid"),
     ]},
    {"key": "infrastructure", "name": "Infrastructure", "icon": "⌗",
     "theme": "IKN phase 2 contracts", "constituents": [
        ("TLKM", "Telkom Indonesia (Infra)", "TLKM.JK", "IDX", "ID", "IDR 200T", "mega"),
        ("TOWR", "Sarana Menara Nusantara", "TOWR.JK", "IDX", "ID", "IDR 24T", "mid"),
        ("TBIG", "Tower Bersama Infrastructure", "TBIG.JK", "IDX", "ID", "IDR 19T", "mid"),
        ("JSMR", "Jasa Marga", "JSMR.JK", "IDX", "ID", "IDR 21T", "mid"),
        ("WIKA", "Wijaya Karya", "WIKA.JK", "IDX", "ID", "IDR 8T", "mid"),
        ("PTPP", "PP (Persero)", "PTPP.JK", "IDX", "ID", "IDR 6T", "mid"),
        ("WSKT", "Waskita Karya", "WSKT.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("KIJA", "Kawasan Industri Jababeka", "KIJA.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("DMAS", "Puradelta Lestari (Deltamas)", "DMAS.JK", "IDX", "ID", "IDR 16T", "mid"),
        ("CTRA", "Ciputra Development", "CTRA.JK", "IDX", "ID", "IDR 28T", "mid"),
        ("AMT", "American Tower", "AMT", "NYSE", "US", "$90B", "large"),
        ("PLD", "Prologis", "PLD", "NYSE", "US", "$130B", "mega"),
        ("CCI", "Crown Castle", "CCI", "NYSE", "US", "$42B", "large"),
        ("EQIX", "Equinix", "EQIX", "NASDAQ", "US", "$80B", "large"),
        ("DLR", "Digital Realty", "DLR", "NYSE", "US", "$55B", "large"),
        ("PWR", "Quanta Services", "PWR", "NYSE", "US", "$40B", "large"),
        ("URI", "United Rentals", "URI", "NYSE", "US", "$46B", "large"),
        ("CARR", "Carrier Global", "CARR", "NYSE", "US", "$60B", "large"),
        ("VMC", "Vulcan Materials", "VMC", "NYSE", "US", "$30B", "mid"),
        ("MLM", "Martin Marietta Materials", "MLM", "NYSE", "US", "$28B", "mid"),
     ]},
    {"key": "healthcare", "name": "Healthcare", "icon": "✛",
     "theme": "Capacity rebuild · BPJS", "constituents": [
        ("KLBF", "Kalbe Farma", "KLBF.JK", "IDX", "ID", "IDR 31T", "mid"),
        ("MIKA", "Mitra Keluarga Hospital Group", "MIKA.JK", "IDX", "ID", "IDR 22T", "mid"),
        ("HEAL", "Medikaloka Hermina (RS Hermina)", "HEAL.JK", "IDX", "ID", "IDR 18T", "mid"),
        ("SILO", "Siloam International Hospitals", "SILO.JK", "IDX", "ID", "IDR 11T", "mid"),
        ("SIDO", "Sido Muncul", "SIDO.JK", "IDX", "ID", "IDR 14T", "mid"),
        ("OMED", "OmniCare Health", "OMED.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("PRDA", "Prodia Widyahusada", "PRDA.JK", "IDX", "ID", "IDR 4T", "small"),
        ("PEHA", "Phapros (Pharos Indonesia)", "PEHA.JK", "IDX", "ID", "IDR 4T", "small"),
        ("DVLA", "Darya-Varia Laboratoria", "DVLA.JK", "IDX", "ID", "IDR 3T", "small"),
        ("MERK", "Merck Indonesia", "MERK.JK", "IDX", "ID", "IDR 3T", "small"),
        ("LLY", "Eli Lilly", "LLY", "NYSE", "US", "$720B", "mega"),
        ("JNJ", "Johnson & Johnson", "JNJ", "NYSE", "US", "$380B", "mega"),
        ("UNH", "UnitedHealth Group", "UNH", "NYSE", "US", "$450B", "mega"),
        ("ABBV", "AbbVie", "ABBV", "NYSE", "US", "$330B", "mega"),
        ("MRK", "Merck & Co", "MRK", "NYSE", "US", "$265B", "mega"),
        ("TMO", "Thermo Fisher Scientific", "TMO", "NYSE", "US", "$200B", "large"),
        ("DHR", "Danaher Corporation", "DHR", "NYSE", "US", "$165B", "large"),
        ("ISRG", "Intuitive Surgical", "ISRG", "NASDAQ", "US", "$175B", "large"),
        ("PFE", "Pfizer", "PFE", "NYSE", "US", "$155B", "mega"),
        ("CVS", "CVS Health", "CVS", "NYSE", "US", "$80B", "large"),
     ]},
    {"key": "logistics", "name": "Logistics", "icon": "⚓",
     "theme": "Red Sea detour normalization", "constituents": [
        ("SMDR", "Samudera Indonesia", "SMDR.JK", "IDX", "ID", "IDR 3T", "small"),
        ("BIRD", "Blue Bird Group", "BIRD.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("TMAS", "Pelayaran Tempuran Emas", "TMAS.JK", "IDX", "ID", "IDR 4T", "small"),
        ("ASSA", "Adi Sarana Armada", "ASSA.JK", "IDX", "ID", "IDR 4T", "small"),
        ("NELY", "Pelayaran Nelly Dwi Putri", "NELY.JK", "IDX", "ID", "IDR 2T", "small"),
        ("SHIP", "Sillo Maritime Perdana", "SHIP.JK", "IDX", "ID", "IDR 3T", "small"),
        ("KPIG", "MNC Land (Logistics Real Estate)", "KPIG.JK", "IDX", "ID", "IDR 3T", "small"),
        ("CMPP", "Indonesia AirAsia (Air Cargo)", "CMPP.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("BPTR", "Bhakti Agung Propertindo (Log)", "BPTR.JK", "IDX", "ID", "IDR 2T", "small"),
        ("IPCM", "Jasa Armada Indonesia", "IPCM.JK", "IDX", "ID", "IDR 3T", "small"),
        ("UPS", "United Parcel Service", "UPS", "NYSE", "US", "$100B", "mega"),
        ("FDX", "FedEx", "FDX", "NYSE", "US", "$70B", "large"),
        ("ODFL", "Old Dominion Freight Line", "ODFL", "NASDAQ", "US", "$45B", "large"),
        ("XPO", "XPO Logistics", "XPO", "NYSE", "US", "$18B", "mid"),
        ("SAIA", "Saia Inc", "SAIA", "NASDAQ", "US", "$10B", "mid"),
        ("CHRW", "C.H. Robinson", "CHRW", "NASDAQ", "US", "$12B", "mid"),
        ("EXPD", "Expeditors Intl of Washington", "EXPD", "NASDAQ", "US", "$15B", "mid"),
        ("GXO", "GXO Logistics", "GXO", "NYSE", "US", "$6B", "mid"),
        ("AMKBY", "Maersk (ADR)", "AMKBY", "OTC", "US", "$26B", "mid"),
        ("JBHT", "J.B. Hunt Transport", "JBHT", "NASDAQ", "US", "$16B", "mid"),
     ]},
    {"key": "entertainment", "name": "Entertainment, Media & Consumer Services", "icon": "◈",
     "theme": "Streaming · creator economy", "constituents": [
        ("SCMA", "Surya Citra Media (EMTK arm)", "SCMA.JK", "IDX", "ID", "IDR 12T", "mid"),
        ("MAPI", "Mitra Adiperkasa", "MAPI.JK", "IDX", "ID", "IDR 15T", "mid"),
        ("MNCN", "Media Nusantara Citra", "MNCN.JK", "IDX", "ID", "IDR 3.5T", "small"),
        ("JIHD", "Jakarta Intl Hotel & Dev", "JIHD.JK", "IDX", "ID", "IDR 8T", "mid"),
        ("PNLF", "Panin Financial (Leisure)", "PNLF.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("FAST", "Rekso Nasional Food (KFC ID)", "FAST.JK", "IDX", "ID", "IDR 4T", "small"),
        ("FILM", "MD Entertainment", "FILM.JK", "IDX", "ID", "IDR 3T", "small"),
        ("ARCI", "Archi Indonesia", "ARCI.JK", "IDX", "ID", "IDR 6T", "mid"),
        ("GMFI", "Garuda Maintenance Facility", "GMFI.JK", "IDX", "ID", "IDR 4T", "small"),
        ("ACES", "Ace Hardware Indonesia", "ACES.JK", "IDX", "ID", "IDR 12T", "mid"),
        ("NFLX", "Netflix", "NFLX", "NASDAQ", "US", "$400B", "mega"),
        ("DIS", "Walt Disney Company", "DIS", "NYSE", "US", "$175B", "mega"),
        ("CMCSA", "Comcast", "CMCSA", "NASDAQ", "US", "$145B", "mega"),
        ("SPOT", "Spotify Technology", "SPOT", "NYSE", "US", "$100B", "large"),
        ("TKO", "TKO Group Holdings (WWE + UFC)", "TKO", "NYSE", "US", "$30B", "mid"),
        ("LYV", "Live Nation Entertainment", "LYV", "NYSE", "US", "$25B", "mid"),
        ("EA", "Electronic Arts", "EA", "NASDAQ", "US", "$35B", "mid"),
        ("TTWO", "Take-Two Interactive", "TTWO", "NASDAQ", "US", "$28B", "mid"),
        ("RBLX", "Roblox Corporation", "RBLX", "NYSE", "US", "$22B", "mid"),
        ("WBD", "Warner Bros. Discovery", "WBD", "NASDAQ", "US", "$22B", "mid"),
     ]},
    {"key": "property", "name": "Property & Real Estate", "icon": "⌂",
     "theme": "PIK2 · rate-cut beneficiary", "constituents": [
        ("PANI", "Pantai Indah Kapuk Dua (PIK2)", "PANI.JK", "IDX", "ID", "IDR 233T", "mega"),
        ("CTRA", "Ciputra Development", "CTRA.JK", "IDX", "ID", "IDR 28T", "mid"),
        ("BSDE", "Bumi Serpong Damai (BSD City)", "BSDE.JK", "IDX", "ID", "IDR 16T", "mid"),
        ("PWON", "Pakuwon Jati", "PWON.JK", "IDX", "ID", "IDR 18T", "mid"),
        ("SMRA", "Summarecon Agung", "SMRA.JK", "IDX", "ID", "IDR 10T", "mid"),
        ("LPKR", "Lippo Karawaci", "LPKR.JK", "IDX", "ID", "IDR 12T", "mid"),
        ("ASRI", "Alam Sutera Realty", "ASRI.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("DMAS", "Puradelta Lestari (Deltamas)", "DMAS.JK", "IDX", "ID", "IDR 16T", "mid"),
        ("APLN", "Agung Podomoro Land", "APLN.JK", "IDX", "ID", "IDR 5T", "mid"),
        ("MTLA", "Metropolitan Land", "MTLA.JK", "IDX", "ID", "IDR 4T", "small"),
        ("WELL", "Welltower", "WELL", "NYSE", "US", "$135B", "mega"),
        ("PLD", "Prologis", "PLD", "NYSE", "US", "$130B", "mega"),
        ("SPG", "Simon Property Group", "SPG", "NYSE", "US", "$76B", "large"),
        ("O", "Realty Income", "O", "NYSE", "US", "$58B", "large"),
        ("PSA", "Public Storage", "PSA", "NYSE", "US", "$50B", "large"),
        ("CBRE", "CBRE Group", "CBRE", "NYSE", "US", "$38B", "large"),
        ("EQR", "Equity Residential", "EQR", "NYSE", "US", "$28B", "mid"),
        ("AVB", "AvalonBay Communities", "AVB", "NYSE", "US", "$30B", "mid"),
        ("INVH", "Invitation Homes", "INVH", "NYSE", "US", "$20B", "mid"),
        ("VICI", "VICI Properties", "VICI", "NYSE", "US", "$30B", "mid"),
     ]},
    {"key": "crypto", "name": "Crypto & Digital Assets", "icon": "₿",
     "theme": "BTC dominance · L1 rotation", "constituents": [
        ("BTC",   "Bitcoin",      "BTC-USD",   "CRYPTO", "CR", "$1.3T", "mega"),
        ("ETH",   "Ethereum",     "ETH-USD",   "CRYPTO", "CR", "$420B", "mega"),
        ("SOL",   "Solana",       "SOL-USD",   "CRYPTO", "CR", "$95B",  "large"),
        ("BNB",   "BNB",          "BNB-USD",   "CRYPTO", "CR", "$95B",  "large"),
        ("XRP",   "XRP",          "XRP-USD",   "CRYPTO", "CR", "$130B", "large"),
        ("ADA",   "Cardano",      "ADA-USD",   "CRYPTO", "CR", "$22B",  "mid"),
        ("DOGE",  "Dogecoin",     "DOGE-USD",  "CRYPTO", "CR", "$28B",  "mid"),
        ("AVAX",  "Avalanche",    "AVAX-USD",  "CRYPTO", "CR", "$15B",  "mid"),
        ("LINK",  "Chainlink",    "LINK-USD",  "CRYPTO", "CR", "$11B",  "mid"),
        ("MATIC", "Polygon",      "MATIC-USD", "CRYPTO", "CR", "$5B",   "small"),
     ]},
]
SECTOR_THEMES = {
    "crypto": [
        "Bitcoin dominance and spot-ETF flows set the regime for the whole complex",
        "Layer-1 rotation (SOL, AVAX) tracks risk appetite; alts lag in risk-off",
        "Regulatory clarity (stablecoins, custody) is the structural unlock for institutional size",
    ],
    "technology": [
        "AI infrastructure capex accelerating — APAC data center power demand surging",
        "OJK digital banking framework revision benefiting Indonesian fintech reclassification",
        "US-China decoupling driving ASEAN semiconductor assembly hub thesis",
    ],
    "financials": [
        "BI rate hold creating NIM expansion window for Indonesian tier-1 banks",
        "BBCA CASA ratio 78% — highest quality compounder in ASEAN; ROE 25%+",
        "US financials re-rating on deregulation; Basel III endgame relief",
    ],
    "energy": [
        "Coal and nickel remain Indonesia's primary USD earners; export premiums persist above spot",
        "ADRO multi-year Korean utility contract backlog extends pricing visibility to 2029",
        "AMMN (Amman Mineral) — Newmont acquisition of Sumbawa; world-class copper-gold asset",
    ],
    "renewables": [
        "PLN 15GW renewable addition target by 2030 drives domestic procurement cycle",
        "BREN/PGEO geothermal baseload: structural edge over solar-only ASEAN peers",
        "VKTR — first listed commercial EV company in ID; Transjakarta fleet anchor contract",
    ],
    "consumer": [
        "Post-Ramadan cycle normalization: seasonal softness is transient, not structural",
        "ICBP noodle pricing power provides inflation pass-through UNVR cannot match",
        "Indonesian modern trade shift: e-commerce now 18% of FMCG distribution",
    ],
    "infrastructure": [
        "IKN Phase 2 contract awards creating multi-year construction revenue pipeline",
        "Data center real estate emerging as highest-yield infrastructure sub-sector",
        "JSMR toll traffic volume recovered to 108% of pre-Covid levels",
    ],
    "healthcare": [
        "BPJS Kesehatan expanding insured population to 280M by 2026 — hospital volume direct beneficiary",
        "GLP-1 drug demand (Eli Lilly, Novo Nordisk) creating structural pharma tailwind globally",
        "Post-pandemic hospital EBITDA recovery; MIKA occupancy back to 78% from 55% trough",
    ],
    "logistics": [
        "Red Sea freight normalization: rate premiums compressing — lower import costs for Indonesian importers",
        "Indonesia archipelago last-mile chronically under-invested vs. scale of need",
        "E-commerce logistics absorbing maritime excess capacity from import slowdown",
    ],
    "entertainment": [
        "Netflix ad-tier + live sports rights driving re-acceleration of subscriber growth globally",
        "Indonesia streaming: Vidio (EMTK), Disney+ Hotstar, Netflix competing for 273M consumers",
        "Gaming sector consolidation: EA, Take-Two benefit from Microsoft-Activision integration distraction",
    ],
    "property": [
        "PANI (PIK2) Mega Cap re-rating: waterfront township land scarcity + Sugianto Kusuma backing",
        "BSDE data center land monetization emerging as new high-value revenue alongside residential sales",
        "BI rate plateau creating mortgage affordability window; first-home demand rebounding in ID",
    ],
}

# ---------------------------------------------------------------- OSINT feeds
# Per-feed failures are tolerated; the hunter keeps whatever parses cleanly.
RSS_FEEDS = {
    "global_macro": [
        ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
        ("CNBC Markets",     "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
        ("FT Home",          "https://www.ft.com/rss/home"),
    ],
    "regional_macro": [
        ("Nikkei Asia",        "https://asia.nikkei.com/rss/feed/nar"),
        ("Business Times SG",  "https://www.businesstimes.com.sg/rss/top-stories"),
        ("Antara Economy",     "https://en.antaranews.com/rss/economy.xml"),
    ],
    "tech_ai": [
        ("TechCrunch",    "https://techcrunch.com/feed/"),
        ("VentureBeat AI","https://venturebeat.com/category/ai/feed/"),
        ("Tech in Asia",  "https://www.techinasia.com/feed"),
    ],
    "policy_sustainability": [
        ("Setkab RI",     "https://setkab.go.id/feed/"),
        ("Mongabay Indonesia", "https://news.mongabay.com/list/indonesia/feed/"),
    ],
}
MAX_HEADLINES_PER_CATEGORY = 6

# ---------------------------------------------------------------- intellectual diet
# Top-tier leadership / deep-thinking podcasts. The Podcast Agent reads new-episode
# show notes and distills a one-paragraph "Core Thesis" to optimize listening time.
# (name, rss_url, host). Per-feed failures tolerated; a curated fallback shows when
# a feed is unreachable so the panel always renders.
# YouTube playlist RSS (no key): youtube.com/feeds/videos.xml?playlist_id=...
def _yt(pid):
    return "https://www.youtube.com/feeds/videos.xml?playlist_id=" + pid

# Two intellectual diets. Each feed: (show, kind, ref, host). kind ∈ playlist (ref=
# playlist_id) | channel (ref=@handle, resolved to channel_id at runtime). Only
# episodes from the last PODCAST_WEEK_DAYS are kept; each carries its publish date.
PODCAST_CATEGORIES = [
    {"key": "brain", "label": "Brain 💪🏼", "feeds": [   # big-idea interviews · science · deep thinking
        ("Lex Fridman Podcast", "channel", "UCSHZKyawb77ixDdsGog4iWA", "Lex Fridman"),
        ("Dwarkesh Podcast", "channel", "UCXl4i9dYBrFOabk0xGmbkRA", "Dwarkesh Patel"),
        ("The Diary of a CEO", "channel", "UCGq-a57w-aPwyi3pW7XLiHw", "Steven Bartlett"),
        ("Endgame", "channel", "UCDaqDYhGmJdrlHr4h9LQ5uw", "Gita Wirjawan"),
        ("Veritasium", "channel", "UCHnyfMqiRRG1u-2MsSQLbXA", "Derek Muller"),
        ("The Overpost", "channel", "UCFWKvu581DpCRFfadjjIy7w", "Leon Hartono"),
        ("Astronacci", "channel", "@astronacciinternational", "Astronacci"),
    ]},
    {"key": "techai", "label": "Tech & AI 🤖", "feeds": [
        ("NVIDIA", "channel", "UCHuiy8bXnmK5nisYHUd1J5g", "NVIDIA"),
        ("AI Explained", "channel", "UCNJ1Ymd5yFuUPtn21xtRbbw", "AI Explained"),
        ("IBM Technology", "channel", "UCKWaEZ-_VweaEx1j62do_vQ", "IBM"),
        ("CXOTalk", "channel", "UCGeqHuR3eUU5tnmgjkqZazw", "Michael Krigsman"),
        ("Nate Herk", "channel", "UC2ojq-nuP8ceeHqiroeKhBA", "AI Automation"),
        ("AI Engineer", "channel", "UCLKPca3kwwd-B59HNr-_lvA", "AI Engineer"),
        ("Nick Saraev", "channel", "UCbo-KbSjJDG6JWQ_MTZ_rNA", "Nick Saraev"),
    ]},
    {"key": "economy", "label": "Economy 📊", "feeds": [   # macro · markets · finance explainers
        ("Patrick Boyle", "channel", "UCASM0cgfkJxQ1ICmRilfHLw", "Patrick Boyle"),
        ("Economics Explained", "channel", "UCZ4AMrDcNrfy3X6nsU8-rPg", "Economics Explained"),
        ("Money & Macro", "channel", "UCCKpicnIwBP3VPxBAZWDeNA", "Joeri Schasfoort"),
        ("The Plain Bagel", "channel", "UCFCEuCsyWP0YkP3CZ3Mr01Q", "Richard Coffin"),
        ("Money Strategist", "channel", "UCJoUwf4OJaRvjSfsDnK-bqw", "Money Strategist"),
        ("Econ", "channel", "UCyHJ94JzwY92NsBVzJ2aE3Q", "econyt"),
    ]},
    {"key": "vc", "label": "VC & Startup 💸", "feeds": [
        ("20VC", "channel", "UCf0PBRjhf0rF8fWBIxTuoWA", "Harry Stebbings"),
        ("All-In", "channel", "UCESLZhusAkFfsNsApnjF_Cg", "Chamath · Sacks · Friedberg · Calacanis"),
        ("Invest Like The Best", "channel", "UCpQBb0fToph3jrDulwz1iUQ", "Patrick O'Shaughnessy"),
        ("a16z", "channel", "UC9cn0TuPq4dnbTY-CBsm8XA", "Andreessen Horowitz"),
        ("Sequoia Capital", "channel", "UCWrF0oN6unbXrWsTN7RctTw", "Sequoia"),
        ("Y Combinator", "channel", "UCcefcZRL2oaA_uBNeo5UOWg", "Y Combinator"),
    ]},
]
PODCAST_WEEK_DAYS = 7        # drop episodes older than this
PODCAST_PER_SHOW = 6         # newest N (non-Shorts) episodes kept per show within the window
PODCAST_FETCH_PER_RUN = 99   # API key is active: fetch all Knowledge Hub sources each run
PODCAST_MIN_DURATION_S = 300 # Knowledge Hub: drop anything under 5 min (clips/Shorts noise; needs API key)
PODCAST_FALLBACK = [
    {"show": "Endgame", "host": "Gita Wirjawan",
     "title": "Why Asia Will Lead the Next Cycle",
     "thesis": "Indonesia's structural current-account surplus is a multi-decade tailwind. "
               "Demographic dividends compound with commodity-export premiums to create a 2030 "
               "inflection point invisible in Western macro models.",
     "url": "https://www.youtube.com/@endgame"},
    {"show": "Dwarkesh Podcast", "host": "Dwarkesh Patel",
     "title": "The Intelligence Explosion and Economic Implications",
     "thesis": "Compute scaling is reshaping the cost curve of cognition itself; the binding "
               "constraint shifts from talent to energy and data-center capacity — a direct read "
               "on the AI-infrastructure capex thesis.",
     "url": "https://www.dwarkesh.com/"},
    {"show": "View From The Top", "host": "Stanford GSB",
     "title": "Portfolio Resilience During Rate Transitions",
     "thesis": "Durable franchises are built by founders who treat capital discipline as a "
               "feature, not a constraint — resilience compounds when conviction survives the "
               "cost-of-capital reset.",
     "url": "https://www.gsb.stanford.edu/insights"},
]

# Jina Reader proxy for non-RSS pages (free markdown conversion).
JINA_READER_PREFIX = "https://r.jina.ai/"

# Tavily deep-search (1,000 free req/mo). Only used when an anomaly fires.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_ENDPOINT = "https://api.tavily.com/search"

# Google News RSS search — keyless, per-entity discovery (any query, full index).
GOOGLE_NEWS = "https://news.google.com/rss/search"
GOOGLE_NEWS_GEO = {"ID": "hl=id&gl=ID&ceid=ID:id", "US": "hl=en-US&gl=US&ceid=US:en"}
NEWS_PER_QUERY = 4          # items kept per index/sector/ticker query
NEWS_WIRE_CAP = 220         # max items in the wire (~100 ID + ~100 US after dedupe)
NEWS_TOPIC_PER_QUERY = 10   # items kept per broad wire-topic query (volume driver)
NEWS_TRUSTED_PER_QUERY = 4  # source-targeted Google News pulls stay small/rate-safe
NEWS_TICKER_QUERY_BUDGET = 60       # gap/stale/priority ticker queries per run
NEWS_TICKER_KEEP_PER_TICKER = 5     # keep best direct stories per ticker in 7d memory
NEWS_TICKER_STALE_HOURS = 72        # tickers older than this are refreshed before covered names

# Trusted-source registry for the news engine. Google News is still the discovery
# layer; these domains/source names receive targeted `site:` passes + ranking boost.
NEWS_TRUSTED_SOURCES = {
    "tier1_global": [
        ("Reuters", "reuters.com"), ("Bloomberg", "bloomberg.com"),
        ("CNBC", "cnbc.com"), ("Yahoo Finance", "finance.yahoo.com"),
        ("MarketWatch", "marketwatch.com"), ("Financial Times", "ft.com"),
        ("Wall Street Journal", "wsj.com"), ("Barron's", "barrons.com"),
        ("Investing.com", "investing.com"), ("TradingView", "tradingview.com"),
        ("Morningstar", "morningstar.com"),
    ],
    "us_equity": [
        ("Seeking Alpha", "seekingalpha.com"), ("Motley Fool", "fool.com"),
        ("PR Newswire", "prnewswire.com"), ("GlobeNewswire", "globenewswire.com"),
    ],
    "apac_sea": [
        ("Nikkei Asia", "asia.nikkei.com"), ("South China Morning Post", "scmp.com"),
        ("The Business Times", "businesstimes.com.sg"), ("The Straits Times", "straitstimes.com"),
        ("Channel NewsAsia", "channelnewsasia.com"), ("DealStreetAsia", "dealstreetasia.com"),
        ("Tech in Asia", "techinasia.com"), ("KrAsia", "kr-asia.com"),
        ("e27", "e27.co"), ("Momentum Works", "momentum.asia"),
    ],
    "indonesia": [
        ("CNBC Indonesia", "cnbcindonesia.com"), ("EmitenNews", "emitennews.com"),
        ("Kabar Bursa", "kabarbursa.com"), ("Ajaib Berita", "ajaib.co.id"),
        ("IDNFinancials", "idnfinancials.com"),
        ("Bloomberg Technoz", "bloombergtechnoz.com"), ("Kontan", "kontan.co.id"), ("Bisnis Indonesia", "bisnis.com"),
        ("Investor Daily", "investor.id"), ("Katadata", "katadata.co.id"),
        ("Antara News", "antaranews.com"), ("IDX Channel", "idxchannel.com"),
        ("Detik Finance", "finance.detik.com"), ("Kompas Money", "money.kompas.com"),
        ("Tempo Bisnis", "tempo.co"), ("Jakarta Globe", "jakartaglobe.id"),
    ],
    "official": [
        ("Bank Indonesia", "bi.go.id"), ("OJK", "ojk.go.id"),
        ("IDX", "idx.co.id"), ("BPS", "bps.go.id"), ("Kemenkeu", "kemenkeu.go.id"),
        ("ESDM", "esdm.go.id"), ("Federal Reserve", "federalreserve.gov"),
        ("US Treasury", "treasury.gov"), ("BLS", "bls.gov"), ("EIA", "eia.gov"),
        ("BOJ", "boj.or.jp"), ("ECB", "ecb.europa.eu"), ("IMF", "imf.org"),
        ("World Bank", "worldbank.org"),
    ],
    "ratings": [
        ("S&P Global Ratings", "spglobal.com"), ("Moody's Ratings", "moodys.com"),
        ("Fitch Ratings", "fitchratings.com"), ("MSCI", "msci.com"),
    ],
    "crypto": [
        ("CoinDesk", "coindesk.com"), ("The Block", "theblock.co"),
        ("Decrypt", "decrypt.co"), ("Cointelegraph", "cointelegraph.com"),
        ("CryptoSlate", "cryptoslate.com"), ("Bitcoin Magazine", "bitcoinmagazine.com"),
        ("Bankless", "bankless.com"), ("CoinGecko News", "coingecko.com"),
        ("Bitcoin.com News", "news.bitcoin.com"), ("BeInCrypto", "beincrypto.com"),
        ("Indodax Academy", "indodax.com"), ("Pluang", "pluang.com"),
        ("Coinvestasi", "coinvestasi.com"), ("SEC", "sec.gov"), ("CFTC", "cftc.gov"),
    ],
}

# Targeted source passes are deliberately compact: trusted source discovery should
# improve quality without turning the 30-min cron into a crawler.
NEWS_SOURCE_TARGETS = {
    "ID": ["cnbcindonesia.com", "emitennews.com", "kabarbursa.com", "idnfinancials.com",
           "bloombergtechnoz.com", "kontan.co.id", "bisnis.com", "ajaib.co.id",
           "katadata.co.id", "antaranews.com", "idxchannel.com"],
    "US": ["reuters.com", "bloomberg.com", "cnbc.com", "finance.yahoo.com",
           "marketwatch.com", "investing.com", "barrons.com"],
    "APAC": ["asia.nikkei.com", "scmp.com", "businesstimes.com.sg",
             "channelnewsasia.com", "dealstreetasia.com", "techinasia.com"],
    "CRYPTO": ["coindesk.com", "theblock.co", "decrypt.co", "cointelegraph.com",
               "cryptoslate.com", "coingecko.com", "news.bitcoin.com",
               "beincrypto.com", "coinvestasi.com", "indodax.com", "pluang.com",
               "sec.gov"],
    "CRYPTO_ID": ["coinvestasi.com", "indodax.com", "pluang.com",
                  "coingecko.com", "news.bitcoin.com", "beincrypto.com"],
    "CRYPTO_GLOBAL": ["coindesk.com", "theblock.co", "decrypt.co", "cointelegraph.com",
                      "cryptoslate.com", "coingecko.com", "news.bitcoin.com",
                      "beincrypto.com", "sec.gov"],
    "OFFICIAL": ["bi.go.id", "ojk.go.id", "idx.co.id", "federalreserve.gov",
                 "treasury.gov", "bls.gov", "eia.gov", "boj.or.jp", "ecb.europa.eu"],
    "RATINGS": ["spglobal.com", "moodys.com", "fitchratings.com", "msci.com"],
}

NEWS_SOURCE_QUERY_TOPICS = [
    ("Bank Indonesia rupiah suku bunga IHSG", "ID", "ECONOMY", "ID"),
    ("Indonesia stocks banking commodities rupiah", "ID", "MARKETS_FINANCE", "ID"),
    ("emiten saham aksi korporasi dividen RUPST IHSG", "ID", "MARKETS_FINANCE", "ID"),
    ("Indonesia startup AI digital economy", "ID", "TECH", "ID"),
    ("Federal Reserve rates inflation jobs yields", "US", "ECONOMY", "US"),
    ("Nasdaq S&P 500 Nvidia earnings yields", "US", "MARKETS_FINANCE", "US"),
    ("AI semiconductors data centers big tech", "US", "TECH", "US"),
    ("ASEAN markets currencies economy", "US", "ECONOMY", "APAC"),
    ("China EV batteries nickel property markets", "US", "MARKETS_FINANCE", "APAC"),
    ("oil gold nickel coal commodities", "US", "MARKETS_FINANCE", "US"),
    ("bitcoin ethereum crypto regulation ETF", "US", "CRYPTO", "CRYPTO_GLOBAL"),
    ("bitcoin kripto exchange Indonesia aset digital", "ID", "CRYPTO", "CRYPTO_ID"),
    ("stablecoin token blockchain ETF crypto exchange", "US", "CRYPTO", "CRYPTO_GLOBAL"),
    ("central bank policy Fed BI BOJ ECB", "US", "ECONOMY", "OFFICIAL"),
    ("Indonesia sovereign rating outlook upgrade downgrade", "ID", "ECONOMY", "RATINGS"),
    ("Indonesia MSCI index review upgrade downgrade foreign inflows", "ID", "MARKETS_FINANCE", "RATINGS"),
    ("Indonesia credit rating S&P Moody's Fitch outlook", "ID", "ECONOMY", "RATINGS"),
]

# Intelligence Wire taxonomy (v3): Economy · Tech · Markets & Finance · Crypto.
# Broad per-geo topic queries fan the wire out to ~100 items/region. (query, category).
WIRE_TOPICS = {
    "ID": [
        ("ekonomi Indonesia pertumbuhan PDB", "ECONOMY"),
        ("Bank Indonesia suku bunga inflasi", "ECONOMY"),
        ("APBN fiskal kebijakan pemerintah Indonesia", "ECONOMY"),
        ("rupiah nilai tukar dollar", "ECONOMY"),
        ("Indonesia sovereign credit rating outlook Moody Fitch S&P", "ECONOMY"),
        ("MSCI Indonesia index review upgrade downgrade rebalancing", "MARKETS_FINANCE"),
        ("IHSG saham bursa efek Indonesia", "MARKETS_FINANCE"),
        ("saham bank BBCA BBRI BMRI emiten", "MARKETS_FINANCE"),
        ("berita emiten aksi korporasi dividen RUPST saham", "MARKETS_FINANCE"),
        ("obligasi surat utang negara investasi", "MARKETS_FINANCE"),
        ("harga komoditas nikel batu bara emas Indonesia", "MARKETS_FINANCE"),
        ("startup Indonesia pendanaan modal ventura", "TECH"),
        ("teknologi AI kecerdasan buatan Indonesia", "TECH"),
        ("GoTo Bukalapak digital ekonomi Indonesia", "TECH"),
        ("kripto bitcoin aset digital Indonesia", "CRYPTO"),
        ("Bitcoin Ethereum bursa kripto Indonesia", "CRYPTO"),
        ("Indodax Pluang Coinvestasi Bitcoin", "CRYPTO"),
    ],
    "US": [
        ("US economy growth jobs report", "ECONOMY"),
        ("Federal Reserve interest rates inflation", "ECONOMY"),
        ("US fiscal policy tariffs trade", "ECONOMY"),
        ("US dollar global economy outlook", "ECONOMY"),
        ("S&P 500 Nasdaq Dow stock market", "MARKETS_FINANCE"),
        ("US bank earnings JPMorgan Goldman Sachs", "MARKETS_FINANCE"),
        ("treasury yields bond market", "MARKETS_FINANCE"),
        ("gold oil commodities prices", "MARKETS_FINANCE"),
        ("AI artificial intelligence Nvidia OpenAI", "TECH"),
        ("startup venture capital funding round", "TECH"),
        ("big tech Apple Microsoft Google Meta", "TECH"),
        ("bitcoin ethereum crypto market regulation", "CRYPTO"),
        ("bitcoin ETF stablecoin crypto exchange", "CRYPTO"),
        ("CoinGecko Bitcoin Ethereum altcoin news", "CRYPTO"),
    ],
}

# ---------------------------------------------------------------- video intelligence
# YouTube market-update channels & playlists for the Intelligence Hub "Videos" pane.
# The Videos agent captures each source's latest uploads (≤1 week) with thumbnail +
# description. Channels are @handles (resolved to channel_id at runtime); playlists
# carry their playlist_id directly. category ∈ market_id|market_us|crypto.
# Channels carry their resolved channel_id directly (kind="channel", ref=UC…) — the
# RSS-by-channel-id endpoint works from CI, whereas resolving @handles via the HTML
# page is bot-blocked on GitHub runners. Playlists carry their playlist_id.
VIDEO_SOURCES = [
    # --- Indonesia market ---
    {"name": "Cuap Cuap Cuan", "kind": "channel", "ref": "UCxytnTZxVm7Y0ZhliKZXrbg", "category": "market_id", "geo": "ID"},
    {"name": "Bloomberg Technoz", "kind": "channel", "ref": "UCQK22ORBCfQdnVim9I0JnJw", "category": "market_id", "geo": "ID"},
    {"name": "Mirae Asset Sekuritas", "kind": "channel", "ref": "UCbgUIA1udecuOCfDaOFkZ1w", "category": "market_id", "geo": "ID"},
    {"name": "Sucor Sekuritas", "kind": "channel", "ref": "UCPBdATHLzMNg4XIXxLf_P7w", "category": "market_id", "geo": "ID"},
    {"name": "Mandiri Sekuritas", "kind": "channel", "ref": "UCsy__Nh0Eh7f6NTMAzvPamA", "category": "market_id", "geo": "ID"},
    {"name": "IDX Channel", "kind": "channel", "ref": "UCQA6NejSxQguRkD3L8eXHzA", "category": "market_id", "geo": "ID"},
    # --- US market ---
    {"name": "Bloomberg Stock Movers", "kind": "playlist", "ref": "PLe4PRejZgr0NxhJreY_kjMBdW8cvmNauU", "category": "market_us", "geo": "US"},
    {"name": "Bloomberg Tech", "kind": "playlist", "ref": "PLe4PRejZgr0P4uqrz5jfGmmshkjmfxd73", "category": "market_us", "geo": "US"},
    {"name": "Bloomberg Daybreak: Asia", "kind": "playlist", "ref": "PLe4PRejZgr0Mvkfte_CsCiKEYuP9DtXN8", "category": "market_us", "geo": "US"},
    {"name": "Bloomberg Daybreak: US", "kind": "playlist", "ref": "PLe4PRejZgr0Pfj-MCX1dSTXnEBCGHl3Yo", "category": "market_us", "geo": "US"},
    {"name": "Reuters Morning Bid", "kind": "playlist", "ref": "PLZhRxE9191zMdTzeumPO39fdnH2UjT1zP", "category": "market_us", "geo": "US"},
    {"name": "Schwab Network", "kind": "channel", "ref": "UCqoSrYgusd8ZddtMoWhjHYA", "category": "market_us", "geo": "US"},
    {"name": "Morgan Stanley", "kind": "channel", "ref": "UCz6RzD6KG_hH_oHb2kyW5jQ", "category": "market_us", "geo": "US"},
    {"name": "Goldman Sachs", "kind": "channel", "ref": "UCyz6-taovlaOkPsPtK4KNEg", "category": "market_us", "geo": "US"},
    {"name": "CNBC Television", "kind": "channel", "ref": "UCrp_UI8XtuYfpiqluWLD7Lw", "category": "market_us", "geo": "US"},
    {"name": "Bloomberg Television", "kind": "channel", "ref": "UCIALMKvObZNtJ6AmdCLP7Lg", "category": "market_us", "geo": "US"},
    {"name": "Kitco News", "kind": "channel", "ref": "UC9ijza42jVR3T6b8bColgvg", "category": "market_us", "geo": "US"},
    {"name": "BBC News", "kind": "channel", "ref": "UC16niRr50-MSBwiO3YDb3RA", "category": "market_us", "geo": "US"},
    # --- Crypto ---
    {"name": "Altcoin Daily", "kind": "channel", "ref": "UCbLhGKVY-bJPcawebgtNfbw", "category": "crypto", "geo": "CR"},
    {"name": "Simply Bitcoin", "kind": "channel", "ref": "UCB6Q0S1gUHXMe5-Jjx0_laQ", "category": "crypto", "geo": "CR"},
    {"name": "Bankless", "kind": "channel", "ref": "UCAl9Ld79qaZxp9JzEOwd3aA", "category": "crypto", "geo": "CR"},
]
VIDEO_CATEGORY_LABELS = {"market_id": "Market ID", "market_us": "Market US", "crypto": "Crypto"}
VIDEO_WEEK_DAYS = 7          # drop uploads older than this
VIDEO_PER_SOURCE = 6         # newest N (non-Shorts) uploads kept per source within the window
SKIP_SHORTS = True           # exclude YouTube Shorts (the substantive content is long-form)
# YouTube throttles GitHub IPs, so each run fetches only the STALEST N sources first
# (missing/oldest prioritized) and lets accumulation maintain the rest — this keeps
# per-run load low so prioritized feeds actually succeed, and converges to full coverage.
VIDEO_FETCH_PER_RUN = 12
# YouTube Data API key (optional). When set, feeds are pulled via the official API
# (not IP-throttled like RSS scraping on GitHub runners) → full coverage every run.
# Falls back to RSS automatically when unset or on any API error. Free key:
# console.cloud.google.com → enable "YouTube Data API v3" → add as repo secret.
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Daily Brief regenerates at these WIB hours; cached between windows to bound DeepSeek cost.
DAILY_BRIEF_HOURS = [0, 3, 6, 9, 12, 15, 18, 21]   # every 3h WIB — tracks both ID & US sessions

# Finnhub — baked into data.json so the client can poll live US quotes (free key,
# US stocks only; IDX stays on Yahoo). Public exposure is acceptable for the free tier.
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# Spotify now-playing (one-time refresh token → access token each run → current track).
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN", "")

# Trending — StockTwits (finance social) + Google Trends daily RSS (no keys).
STOCKTWITS_TRENDING = "https://api.stocktwits.com/api/2/trending/symbols.json"
GOOGLE_TRENDS_RSS = "https://trends.google.com/trending/rss?geo="

# ---------------------------------------------------------------- weather
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
LOCATIONS = {
    "bsd":     {"label": "BSD City", "lat": -6.3019, "lon": 106.6527},
    "jakarta": {"label": "Jakarta",  "lat": -6.2088, "lon": 106.8456},
}

# ---------------------------------------------------------------- LLM routing
# DeepSeek is the intelligence base. Two access paths, picked automatically:
#   1. DEEPSEEK_API_KEY  -> api.deepseek.com        (native, model "deepseek-chat")
#   2. OPENROUTER_API_KEY-> openrouter.ai free tier (model below)
DEEPSEEK_API_KEY   = os.getenv("DEEPSEEK_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEEPSEEK_NATIVE_URL   = "https://api.deepseek.com/chat/completions"
DEEPSEEK_NATIVE_MODEL = os.getenv("COCKPIT_MODEL_NATIVE", "deepseek-chat")
OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("COCKPIT_MODEL", "deepseek/deepseek-v4-flash")
LLM_TIMEOUT_S    = 90
LLM_MAX_TOKENS   = 3000   # headroom so structured JSON (macro/alerts/brief) isn't truncated

# ---------------------------------------------------------------- personal hooks
# Secret iCal address of a Google Calendar (Settings -> Integrate calendar).
GCAL_ICS_URL = os.getenv("GCAL_ICS_URL", "")
# Raw-text endpoint holding the latest personal memo (e.g. a GitHub Gist raw URL
# updated from the phone via the GitHub app / an Apple Shortcut webhook).
NOTE_URL = os.getenv("COCKPIT_NOTE_URL", "")
FALLBACK_NOTE = ("Execution over optimization today. Finalize the fund telemetry "
                 "baseline scripts before the pre-market sync loops execute.")

# ---------------------------------------------------------------- soundtrack
# The orchestrator maps (weather + market state) -> a Spotify focus playlist.
SPOTIFY_PLAYLISTS = {
    "storm_focus": {
        "track_name": "Rain & Deep Focus",
        "embed_url": "https://open.spotify.com/embed/playlist/37i9dQZF1DX8ymr6UES7vc?utm_source=generator",
    },
    "calm_focus": {
        "track_name": "Focus Ambient & Lo-Fi Selection",
        "embed_url": "https://open.spotify.com/embed/playlist/37i9dQZF1DWWQRwui0S6bV?utm_source=generator",
    },
    "volatile_markets": {
        "track_name": "Instrumental Concentration (High-Volatility Desk)",
        "embed_url": "https://open.spotify.com/embed/playlist/37i9dQZF1DX3PFzdbtx1Us?utm_source=generator",
    },
    "evening_wind_down": {
        "track_name": "Evening Jazz & Wind-Down",
        "embed_url": "https://open.spotify.com/embed/playlist/37i9dQZF1DX4wta20PHgwo?utm_source=generator",
    },
}

# ---------------------------------------------------------------- verse rotation
VERSES = [
    "Commit your actions to the Lord, and your plans will succeed. — Proverbs 16:3",
    "Whatever you do, work at it with all your heart, as working for the Lord. — Colossians 3:23",
    "The plans of the diligent lead to profit as surely as haste leads to poverty. — Proverbs 21:5",
    "Be strong and courageous. Do not be afraid; the Lord your God goes with you. — Deuteronomy 31:6",
    "Let all that you do be done in love. — 1 Corinthians 16:14",
    "The heart of man plans his way, but the Lord establishes his steps. — Proverbs 16:9",
    "I can do all things through Christ who strengthens me. — Philippians 4:13",
    "Trust in the Lord with all your heart, and lean not on your own understanding. — Proverbs 3:5",
    "Do not be anxious about anything, but in every situation present your requests to God. — Philippians 4:6",
    "Seek first the kingdom of God and His righteousness, and all these things will be added to you. — Matthew 6:33",
    "He gives strength to the weary and increases the power of the weak. — Isaiah 40:29",
    "In their hearts humans plan their course, but the Lord establishes their steps. — Proverbs 16:9",
    "This is the day the Lord has made; let us rejoice and be glad in it. — Psalm 118:24",
    "For I know the plans I have for you, plans to prosper you and not to harm you. — Jeremiah 29:11",
]

# ---------------------------------------------------------------- output contract
DATA_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data.json")
