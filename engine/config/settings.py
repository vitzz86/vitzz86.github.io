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
