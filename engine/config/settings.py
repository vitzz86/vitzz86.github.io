"""Project Cockpit — central configuration.

Target tickers, RSS strings, weather coordinates, model routing and
output-contract constants. Everything here is data, no logic.
"""
import os

# ---------------------------------------------------------------- timezone
WIB_UTC_OFFSET = 7  # Asia/Jakarta

# ---------------------------------------------------------------- telemetry
# (yahoo symbol, display label, asset class)
# PRD B3 monitored-asset registry (14 indices & instruments for the marquee +
# telemetry cards). yfinance symbol doubles as the Yahoo Finance source link.
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
    ("^TNX",     "US 10Y Yield",        "rates"),
    ("^VIX",     "CBOE VIX",            "rates"),
]
YF_QUOTE = "https://finance.yahoo.com/quote/"

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
PODCAST_FEEDS = [
    ("Endgame", _yt("PL-hh_bKgnJ6GlNCJYV6LfHL9QcP5q_Z7F"), "Gita Wirjawan"),
    ("Dwarkesh Podcast", _yt("PLd7-bHaQwnthaNDpZ32TtYONGVk95-fhF"), "Dwarkesh Patel"),
    ("View From The Top", _yt("PLxq_lXOUlvQAwaY_9K4ZFH9Xdar9WzCaL"), "Stanford GSB"),
    ("The Diary of a CEO", _yt("PL22egh3ok4cP0T7UZRmP6TMLErZYWMN-l"), "Steven Bartlett"),
    ("Lex Fridman Podcast", _yt("PLrAXtmErZgOdP_8GztsuKi9nrraNbKKp4"), "Lex Fridman"),
]
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
GOOGLE_NEWS_GEO = {"ID": "hl=en-ID&gl=ID&ceid=ID:en", "US": "hl=en-US&gl=US&ceid=US:en"}
NEWS_PER_QUERY = 4          # items kept per index/sector/ticker query
NEWS_WIRE_CAP = 220         # max items in the wire (~100 ID + ~100 US after dedupe)
NEWS_TOPIC_PER_QUERY = 10   # items kept per broad wire-topic query (volume driver)

# Intelligence Wire taxonomy (v3): Economy · Tech · Markets & Finance · Crypto.
# Broad per-geo topic queries fan the wire out to ~100 items/region. (query, category).
WIRE_TOPICS = {
    "ID": [
        ("ekonomi Indonesia pertumbuhan PDB", "ECONOMY"),
        ("Bank Indonesia suku bunga inflasi", "ECONOMY"),
        ("APBN fiskal kebijakan pemerintah Indonesia", "ECONOMY"),
        ("rupiah nilai tukar dollar", "ECONOMY"),
        ("IHSG saham bursa efek Indonesia", "MARKETS_FINANCE"),
        ("saham bank BBCA BBRI BMRI emiten", "MARKETS_FINANCE"),
        ("obligasi surat utang negara investasi", "MARKETS_FINANCE"),
        ("harga komoditas nikel batu bara emas Indonesia", "MARKETS_FINANCE"),
        ("startup Indonesia pendanaan modal ventura", "TECH"),
        ("teknologi AI kecerdasan buatan Indonesia", "TECH"),
        ("GoTo Bukalapak digital ekonomi Indonesia", "TECH"),
        ("kripto bitcoin aset digital Indonesia", "CRYPTO"),
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
    ],
}

# ---------------------------------------------------------------- video intelligence
# YouTube market-update channels & playlists for the Intelligence Hub "Videos" pane.
# The Videos agent captures each source's latest uploads (≤1 week) with thumbnail +
# description. Channels are @handles (resolved to channel_id at runtime); playlists
# carry their playlist_id directly. category ∈ market_id|market_us|crypto.
VIDEO_SOURCES = [
    # --- Indonesia market ---
    {"name": "Cuap Cuap Cuan", "kind": "channel", "ref": "@cuapcuapcuan", "category": "market_id", "geo": "ID"},
    {"name": "Bloomberg Technoz", "kind": "channel", "ref": "@bloombergtechnoz", "category": "market_id", "geo": "ID"},
    {"name": "Mirae Asset Sekuritas", "kind": "channel", "ref": "@MiraeAssetSekuritas", "category": "market_id", "geo": "ID"},
    {"name": "Sucor Sekuritas", "kind": "channel", "ref": "@SucorSekuritasChannel", "category": "market_id", "geo": "ID"},
    {"name": "Mandiri Sekuritas", "kind": "channel", "ref": "@GrowinMandiriSekuritas", "category": "market_id", "geo": "ID"},
    {"name": "IDX Channel", "kind": "channel", "ref": "@IDXChannel", "category": "market_id", "geo": "ID"},
    # --- US market ---
    {"name": "Bloomberg Stock Movers", "kind": "playlist", "ref": "PLe4PRejZgr0NxhJreY_kjMBdW8cvmNauU", "category": "market_us", "geo": "US"},
    {"name": "Bloomberg Tech", "kind": "playlist", "ref": "PLe4PRejZgr0P4uqrz5jfGmmshkjmfxd73", "category": "market_us", "geo": "US"},
    {"name": "Bloomberg Daybreak: Asia", "kind": "playlist", "ref": "PLe4PRejZgr0Mvkfte_CsCiKEYuP9DtXN8", "category": "market_us", "geo": "US"},
    {"name": "Bloomberg Daybreak: US", "kind": "playlist", "ref": "PLe4PRejZgr0Pfj-MCX1dSTXnEBCGHl3Yo", "category": "market_us", "geo": "US"},
    {"name": "Reuters Morning Bid", "kind": "playlist", "ref": "PLZhRxE9191zMdTzeumPO39fdnH2UjT1zP", "category": "market_us", "geo": "US"},
    {"name": "Morgan Stanley", "kind": "channel", "ref": "@morganstanley", "category": "market_us", "geo": "US"},
    {"name": "Goldman Sachs", "kind": "channel", "ref": "@GoldmanSachs", "category": "market_us", "geo": "US"},
    # --- Crypto ---
    {"name": "Altcoin Daily", "kind": "channel", "ref": "@AltcoinDaily", "category": "crypto", "geo": "CR"},
    {"name": "Simply Bitcoin", "kind": "channel", "ref": "@SimplyBitcoin", "category": "crypto", "geo": "CR"},
    {"name": "Bankless", "kind": "channel", "ref": "@Bankless", "category": "crypto", "geo": "CR"},
]
VIDEO_CATEGORY_LABELS = {"market_id": "Market ID", "market_us": "Market US", "crypto": "Crypto"}
VIDEO_WEEK_DAYS = 7          # drop uploads older than this
VIDEO_PER_SOURCE = 3         # newest N uploads kept per source

# Daily Brief regenerates at these WIB hours; cached between windows to bound DeepSeek cost.
DAILY_BRIEF_HOURS = [9, 12, 17, 19]

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
