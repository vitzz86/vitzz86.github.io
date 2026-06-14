"""Project Cockpit — central configuration.

Target tickers, RSS strings, weather coordinates, model routing and
output-contract constants. Everything here is data, no logic.
"""
import os

# ---------------------------------------------------------------- timezone
WIB_UTC_OFFSET = 7  # Asia/Jakarta

# ---------------------------------------------------------------- telemetry
# (yahoo symbol, display label, asset class)
TICKERS = [
    ("^JKSE",    "JCI / IHSG",          "index"),
    ("^GSPC",    "S&P 500",             "index"),
    ("^IXIC",    "Nasdaq",              "index"),
    ("^DJI",     "Dow Jones",           "index"),
    ("USDIDR=X", "USD/IDR",             "fx"),
    ("CL=F",     "Crude Oil (WTI)",     "commodity"),
    ("S=F",      "Soybean (Agri)",      "commodity"),
    ("ITMG.JK",  "Coal proxy (ITMG)",   "commodity"),
    ("INCO.JK",  "Nickel proxy (INCO)", "commodity"),
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
SECTORS = [
    {"key": "technology", "name": "Technology", "icon": "▚",
     "theme": "AI infra · Digital banking",
     "constituents": [
        ("DCII", "DCI Indonesia",        "DCII.JK", "IDX",    "ID", "IDR 290T", "mega"),
        ("TLKM", "Telkom Indonesia",     "TLKM.JK", "IDX",    "ID", "IDR 200T", "mega"),
        ("GOTO", "GoTo Gojek Tokopedia", "GOTO.JK", "IDX",    "ID", "IDR 42T",  "large"),
        ("NVDA", "Nvidia Corp",          "NVDA",    "NASDAQ", "US", "$3.5T",    "mega"),
        ("MSFT", "Microsoft Corp",       "MSFT",    "NASDAQ", "US", "$3.1T",    "mega"),
        ("BUKA", "Bukalapak",            "BUKA.JK", "IDX",    "ID", "IDR 8T",   "mid"),
     ]},
    {"key": "financials", "name": "Financials", "icon": "▤",
     "theme": "BI rate hold · NIM expansion",
     "constituents": [
        ("BBCA", "Bank Central Asia",    "BBCA.JK", "IDX",    "ID", "IDR 1,023T", "mega"),
        ("BMRI", "Bank Mandiri",         "BMRI.JK", "IDX",    "ID", "IDR 600T",   "mega"),
        ("BBRI", "Bank Rakyat Indonesia","BBRI.JK", "IDX",    "ID", "IDR 650T",   "mega"),
        ("JPM",  "JPMorgan Chase",       "JPM",     "NYSE",   "US", "$680B",      "mega"),
        ("V",    "Visa Inc",             "V",       "NYSE",   "US", "$560B",      "mega"),
        ("ARTO", "Bank Jago",            "ARTO.JK", "IDX",    "ID", "IDR 30T",    "mid"),
     ]},
    {"key": "energy", "name": "Mining & Energy", "icon": "◭",
     "theme": "Nickel glut · coal cash flow",
     "constituents": [
        ("ADRO", "Adaro Energy",         "ADRO.JK", "IDX",    "ID", "IDR 89T",  "large"),
        ("ITMG", "Indo Tambangraya",     "ITMG.JK", "IDX",    "ID", "IDR 28T",  "mid"),
        ("INCO", "Vale Indonesia",       "INCO.JK", "IDX",    "ID", "IDR 45T",  "mid"),
        ("XOM",  "ExxonMobil",           "XOM",     "NYSE",   "US", "$520B",    "mega"),
        ("CVX",  "Chevron",              "CVX",     "NYSE",   "US", "$290B",    "mega"),
        ("ANTM", "Aneka Tambang",        "ANTM.JK", "IDX",    "ID", "IDR 38T",  "mid"),
     ]},
    {"key": "renewables", "name": "Renewables", "icon": "☀",
     "theme": "PLN green capex · geothermal",
     "constituents": [
        ("PGEO", "Pertamina Geothermal", "PGEO.JK", "IDX",    "ID", "IDR 42T",  "mid"),
        ("BREN", "Barito Renewables",    "BREN.JK", "IDX",    "ID", "IDR 890T", "mega"),
        ("NEE",  "NextEra Energy",       "NEE",     "NYSE",   "US", "$150B",    "mega"),
        ("FSLR", "First Solar",          "FSLR",    "NASDAQ", "US", "$22B",     "large"),
        ("VKTR", "VKTR Teknologi Mobilitas","VKTR.JK","IDX",  "ID", "IDR 6T",   "mid", "spec"),
        ("ENPH", "Enphase Energy",       "ENPH",    "NASDAQ", "US", "$9B",      "mid"),
     ]},
    {"key": "consumer", "name": "Consumer & FMCG", "icon": "▦",
     "theme": "Demographic compounding",
     "constituents": [
        ("ICBP", "Indofood CBP",         "ICBP.JK", "IDX",    "ID", "IDR 130T", "large"),
        ("UNVR", "Unilever Indonesia",   "UNVR.JK", "IDX",    "ID", "IDR 70T",  "large"),
        ("MYOR", "Mayora Indah",         "MYOR.JK", "IDX",    "ID", "IDR 60T",  "large"),
        ("PG",   "Procter & Gamble",     "PG",      "NYSE",   "US", "$390B",    "mega"),
        ("KO",   "Coca-Cola",            "KO",      "NYSE",   "US", "$270B",    "mega"),
        ("AMRT", "Sumber Alfaria (Alfamart)","AMRT.JK","IDX", "ID", "IDR 120T", "large"),
     ]},
    {"key": "healthcare", "name": "Healthcare", "icon": "✛",
     "theme": "Capacity rebuild · BPJS",
     "constituents": [
        ("KLBF", "Kalbe Farma",          "KLBF.JK", "IDX",    "ID", "IDR 75T",  "large"),
        ("SIDO", "Sido Muncul",          "SIDO.JK", "IDX",    "ID", "IDR 18T",  "mid"),
        ("MIKA", "Mitra Keluarga",       "MIKA.JK", "IDX",    "ID", "IDR 40T",  "mid"),
        ("LLY",  "Eli Lilly",            "LLY",     "NYSE",   "US", "$780B",    "mega"),
        ("UNH",  "UnitedHealth",         "UNH",     "NYSE",   "US", "$520B",    "mega"),
        ("HEAL", "Medikaloka Hermina",   "HEAL.JK", "IDX",    "ID", "IDR 22T",  "mid"),
     ]},
]
SECTOR_THEMES = {
    "technology": [
        "AI infrastructure capex accelerating — APAC data-center power demand surging",
        "OJK digital-banking framework revision opens Indonesian fintech reclassification",
        "US-China decoupling drives the ASEAN semiconductor assembly-hub thesis",
    ],
    "financials": [
        "BI rate path creating a NIM-expansion window for tier-1 Indonesian banks",
        "Household debt-to-GDP near 17% vs 75%+ in developed markets — long lending runway",
        "Digital-bank reclassification (ARTO) reprices the growth tail of the sector",
    ],
    "energy": [
        "Energy-transition dual-track: legacy fossil cash flows fund the green pivot",
        "Indonesian coal and nickel remain the primary USD earner for the current account",
        "Nickel oversupply pressures spot, but downstream EV-battery demand underwrites volume",
    ],
    "renewables": [
        "PLN green capex: 15GW renewable addition target by 2030",
        "Geothermal baseload gives Indonesia a structural edge over solar-only peers",
        "Barito Renewables × Masdar unlocks a utility-scale solar pipeline in Sumatra",
    ],
    "consumer": [
        "270M-population demographic tailwind underwrites long-duration FMCG compounding",
        "Modern-trade channel shift: e-commerce now ~18% of FMCG distribution",
        "Input-cost (CPO) normalization eases margin pressure into next cycle",
    ],
    "healthcare": [
        "Post-pandemic hospital-capacity rebuild plus BPJS coverage expansion",
        "GLP-1 demand (LLY) anchors the US growth narrative; ID names trade on volume",
        "Branded-generics pricing power (KLBF, SIDO) cushions FX-driven input costs",
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

# Jina Reader proxy for non-RSS pages (free markdown conversion).
JINA_READER_PREFIX = "https://r.jina.ai/"

# Tavily deep-search (1,000 free req/mo). Only used when an anomaly fires.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_ENDPOINT = "https://api.tavily.com/search"

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
LLM_MAX_TOKENS   = 1400

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
