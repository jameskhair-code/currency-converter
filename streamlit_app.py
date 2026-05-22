"""
Rybear's Currency Converter — Streamlit edition
-----------------------------------------------
A polished currency converter, made special for Ryleigh ("Rybear").

Run it locally with:
    pip install streamlit requests
    streamlit run streamlit_app.py

Rates come from the European Central Bank via the free, no-key
Frankfurter API (api.frankfurter.dev). ECB publishes updated rates
every business day around 16:00 CET. If the network is down or
the API hiccups, the app falls back to built-in approximate rates
so it never fully breaks.
"""

import base64
import zlib
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
import requests

# Rybear lives in Salt Lake City — display rate timestamps in her
# local timezone. America/Denver covers Mountain Time and handles
# the MDT/MST switch automatically.
SLC_TZ = ZoneInfo("America/Denver")

# ----------------------------------------------------------------------
# 1. CONFIG & DATA
# ----------------------------------------------------------------------

st.set_page_config(page_title="Rybear's Currency Converter",
                   page_icon="🐻", layout="centered")

# code -> flag, display name, symbol, decimals. Order here is also the
# dropdown order — most familiar to Rybear first, then the rest.
# All listed codes must be supported by Frankfurter (ECB tracks ~30).
CURRENCIES = {
    "USD": {"flag": "🇺🇸", "name": "US Dollar",          "symbol": "$",  "decimals": 2},
    "KRW": {"flag": "🇰🇷", "name": "South Korean Won",   "symbol": "₩",  "decimals": 0},
    "JPY": {"flag": "🇯🇵", "name": "Japanese Yen",       "symbol": "¥",  "decimals": 0},
    "EUR": {"flag": "🇪🇺", "name": "Euro",               "symbol": "€",  "decimals": 2},
    "GBP": {"flag": "🇬🇧", "name": "British Pound",      "symbol": "£",  "decimals": 2},
    "CAD": {"flag": "🇨🇦", "name": "Canadian Dollar",    "symbol": "$",  "decimals": 2},
    "AUD": {"flag": "🇦🇺", "name": "Australian Dollar",  "symbol": "$",  "decimals": 2},
    "CNY": {"flag": "🇨🇳", "name": "Chinese Yuan",       "symbol": "¥",  "decimals": 2},
    "MXN": {"flag": "🇲🇽", "name": "Mexican Peso",       "symbol": "$",  "decimals": 2},
    "INR": {"flag": "🇮🇳", "name": "Indian Rupee",       "symbol": "₹",  "decimals": 2},
    "CHF": {"flag": "🇨🇭", "name": "Swiss Franc",        "symbol": "Fr", "decimals": 2},
    "HKD": {"flag": "🇭🇰", "name": "Hong Kong Dollar",   "symbol": "$",  "decimals": 2},
    "SGD": {"flag": "🇸🇬", "name": "Singapore Dollar",   "symbol": "$",  "decimals": 2},
    "THB": {"flag": "🇹🇭", "name": "Thai Baht",          "symbol": "฿",  "decimals": 2},
    "NZD": {"flag": "🇳🇿", "name": "New Zealand Dollar", "symbol": "$",  "decimals": 2},
    "BRL": {"flag": "🇧🇷", "name": "Brazilian Real",     "symbol": "R$", "decimals": 2},
    "SEK": {"flag": "🇸🇪", "name": "Swedish Krona",      "symbol": "kr", "decimals": 2},
    "NOK": {"flag": "🇳🇴", "name": "Norwegian Krone",    "symbol": "kr", "decimals": 2},
    "DKK": {"flag": "🇩🇰", "name": "Danish Krone",       "symbol": "kr", "decimals": 2},
    "ZAR": {"flag": "🇿🇦", "name": "South African Rand", "symbol": "R",  "decimals": 2},
    "PLN": {"flag": "🇵🇱", "name": "Polish Złoty",       "symbol": "zł", "decimals": 2},
    "TRY": {"flag": "🇹🇷", "name": "Turkish Lira",       "symbol": "₺",  "decimals": 2},
}

# Used only if the live request fails — approximate, USD-based.
# Doesn't need to be precise: it's a "never fully break" safety net.
FALLBACK_RATES = {
    "USD": 1.0,   "KRW": 1380.0, "JPY": 156.0, "EUR": 0.92,  "GBP": 0.79,
    "CAD": 1.37,  "AUD": 1.52,   "CNY": 7.24,  "MXN": 18.6,  "INR": 83.4,
    "CHF": 0.88,  "HKD": 7.81,   "SGD": 1.34,  "THB": 36.0,  "NZD": 1.65,
    "BRL": 5.10,  "SEK": 10.60,  "NOK": 10.70, "DKK": 6.90,  "ZAR": 18.50,
    "PLN": 3.95,  "TRY": 32.00,
}


@st.cache_data(ttl=3600)
def get_history(from_code, to_code, days=30):
    """Fetch the last `days` of daily rates for from_code -> to_code from
    Frankfurter. Returns a list of (iso_date, rate) tuples, oldest first,
    or [] on failure or for the trivial same-currency case."""
    from datetime import date, timedelta
    if from_code == to_code:
        return []
    end = date.today()
    start = end - timedelta(days=days + 10)  # extra buffer for weekends/holidays
    try:
        url = f"https://api.frankfurter.dev/v1/{start.isoformat()}..{end.isoformat()}"
        resp = requests.get(url, params={"base": from_code, "symbols": to_code}, timeout=8)
        data = resp.json()
        rates_by_day = data.get("rates") or {}
        series = []
        for dstr in sorted(rates_by_day.keys()):
            value = rates_by_day[dstr].get(to_code)
            if value is not None:
                series.append((dstr, value))
        return series[-days:]  # newest `days` business-day entries
    except Exception:
        return []


def make_sparkline_svg(values, width=240, height=42, color="#386C4F"):
    """Render a minimal inline SVG sparkline — no axes, no labels — given
    a non-empty list of numeric values. Returns an SVG string."""
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) if hi > lo else 1.0
    pad = 3
    inner_w, inner_h = width - 2 * pad, height - 2 * pad
    step = inner_w / (len(values) - 1)
    points = [
        (pad + i * step, pad + inner_h - ((v - lo) / span) * inner_h)
        for i, v in enumerate(values)
    ]
    line = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    last_x, last_y = points[-1]
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="none">'
        f'<path d="{line}" stroke="{color}" stroke-width="1.8" fill="none" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.5" fill="{color}"/>'
        f'</svg>'
    )


@st.cache_data(ttl=3600)  # remember the result for 1 hour so we don't hammer the API
def get_rates():
    """Fetch the ECB's latest rates from Frankfurter and normalize to USD-base.

    Frankfurter quotes everything against EUR by default; we divide through
    by USD-per-EUR so callers can keep using the cross-rate formula
    `rate(A -> B) = rates[B] / rates[A]` unchanged. Falls back to the
    built-in approximate rates if the network is unavailable.
    """
    try:
        resp = requests.get("https://api.frankfurter.dev/v1/latest", timeout=8)
        data = resp.json()
        eur_rates = data.get("rates")
        if eur_rates and "USD" in eur_rates:
            eur_rates["EUR"] = 1.0  # base isn't included in the response
            usd_per_eur = eur_rates["USD"]
            usd_rates = {code: value / usd_per_eur for code, value in eur_rates.items()}
            usd_rates["USD"] = 1.0
            return {
                "rates":   usd_rates,
                "updated": data.get("date", ""),   # ISO date, e.g. "2026-05-22"
                "live":    True,
            }
    except Exception:
        pass  # network down, blocked, or API hiccup — fall through
    return {"rates": FALLBACK_RATES, "updated": "", "live": False}


def fmt(value, decimals):
    """Format a number with thousands separators and the right decimal places."""
    return f"{value:,.{decimals}f}"


# "Rybear says…" purchasing-power phrase bank.
#
# Each tier has a list of universal phrases plus an optional dict of
# currency-flavored phrases keyed by ISO code. When the converted amount
# falls into a tier, we build the candidate list = universal + flavor for
# either the source or target currency, then pick stably based on a hash
# of (amount, from_code, to_code) — so the phrase varies with input but
# doesn't flicker on every keystroke.
RYBEAR_TIERS = [
    {
        "ceiling": 0.25,
        "universal": [
            "not even a piece of gum 🍬",
            "couch-cushion change 🛋️",
            "smaller than a vending-machine coin 🪙",
            "barely worth bending down to pick up 🦴",
            "less than a 1980s payphone call ☎️",
        ],
        "by_currency": {},
    },
    {
        "ceiling": 1,
        "universal": [
            "a high-five worth of money ✋",
            "a small candy bar 🍬",
            "a fortune cookie's worth 🥠",
            "tip-jar tier 🫙",
            "what you find in a clean laundry load 🧦",
        ],
        "by_currency": {
            "JPY": ["barely a vending-machine snack in Tokyo 🍡"],
            "KRW": ["a single triangle kimbap at a Seoul GS25 🍙"],
        },
    },
    {
        "ceiling": 3,
        "universal": [
            "a candy bar 🍫",
            "two scoops of bulk-bin candy 🍭",
            "a small-arcade game token 🕹️",
            "a 7-Eleven hot dog 🌭",
            "a kid's juice box and pretzels 🧃",
        ],
        "by_currency": {
            "JPY": ["a Family Mart onigiri 🍙"],
            "INR": ["two cups of chai at a roadside stall 🍵"],
            "THB": ["a small mango sticky rice ice cream 🥭"],
        },
    },
    {
        "ceiling": 10,
        "universal": [
            "lunch at a food truck 🌮",
            "a pint of decent ice cream 🍦",
            "a fancy coffee with all the upgrades ☕",
            "two cans of imported soda 🥤",
            "a used paperback at the bookstore 📚",
            "a movie-theater popcorn (large) 🍿",
        ],
        "by_currency": {
            "KRW": ["a piping-hot bowl of kimchi jjigae 🥘"],
            "JPY": ["convenience-store onigiri lunch with a drink 🍙"],
            "INR": ["a proper street-thali with sweet lassi 🍛"],
            "THB": ["pad thai with iced tea by the river 🍜"],
            "MXN": ["tacos al pastor for two 🌮"],
            "CNY": ["scallion-pancake breakfast for two 🥞"],
        },
    },
    {
        "ceiling": 30,
        "universal": [
            "a movie ticket 🎬",
            "a tank of gas for a small car ⛽",
            "a really nice cocktail with tip 🍸",
            "an arcade afternoon for one 🎮",
            "video-game DLC and a snack 🎮",
            "a paperback at the airport bookstore 📕",
        ],
        "by_currency": {
            "KRW": ["lunch + iced Americano on Garosu-gil ☕"],
            "JPY": ["a bento and a draft beer at an izakaya 🍱"],
            "EUR": ["a Parisian crêpe and an espresso 🥐"],
            "GBP": ["a London pub round (one round) 🍺"],
            "CNY": ["hot-pot solo lunch in Chengdu 🍲"],
            "MXN": ["a long boozy taco lunch in CDMX 🌮"],
        },
    },
    {
        "ceiling": 80,
        "universal": [
            "dinner out for two 🍝",
            "a basic concert ticket 🎤",
            "a really decent bottle of wine 🍷",
            "an Uber across town and back 🚕",
            "the new hardcover the week it drops 📕",
            "two seats at the Saturday matinee + popcorn 🍿",
        ],
        "by_currency": {
            "KRW": ["Korean BBQ for two with extra side dishes 🥩"],
            "JPY": ["all-you-can-eat sushi for one 🍣"],
            "INR": ["a fancy thali for the whole family 🍛"],
            "THB": ["rooftop dinner in Bangkok 🌃"],
            "EUR": ["a real dinner in a small Italian trattoria 🍝"],
            "GBP": ["a Sunday roast in a proper pub 🥩"],
        },
    },
    {
        "ceiling": 200,
        "universal": [
            "a week of groceries 🛒",
            "a new pair of jeans 👖",
            "the better headphones at Target 🎧",
            "a half-tank of gas + a nice dinner 🚗",
            "a board game and a tray of snacks 🎲",
            "a thoughtful birthday gift 🎁",
            "a really nice book + a long coffee-shop afternoon 📚",
        ],
        "by_currency": {
            "JPY": ["an omakase sushi lunch in Tsukiji 🍣"],
            "EUR": ["Eurail day pass + a great Florence dinner 🚆"],
            "GBP": ["a fancy West End theatre ticket 🎭"],
        },
    },
    {
        "ceiling": 600,
        "universal": [
            "a new pair of sneakers 👟",
            "a decent thrift-store bike 🚲",
            "the iPad mini if it's on sale 🍎",
            "groceries for the month 🛒",
            "a nice weekend ski-rental setup 🎿",
            "a wedding-guest outfit, head to toe 👗",
        ],
        "by_currency": {
            "KRW": ["round-trip KTX Seoul→Busan + good food 🚄"],
            "CNY": ["high-speed rail through Yunnan 🚄"],
        },
    },
    {
        "ceiling": 2_000,
        "universal": [
            "a weekend getaway ✈️",
            "a really nice mountain bike 🚵",
            "a used DSLR with a lens 📷",
            "a serious gaming PC build 🎮",
            "a half-month of San Francisco rent 🏙️",
            "a custom-tailored suit 🤵",
        ],
        "by_currency": {},
    },
    {
        "ceiling": 10_000,
        "universal": [
            "a really nice laptop 💻",
            "an older but solid used car 🚗",
            "a two-week trip almost anywhere 🌴",
            "a year of an okay gym membership 💪",
            "the world's nicest mattress 🛏️",
            "a fancy wedding's flower budget 💐",
        ],
        "by_currency": {},
    },
    {
        "ceiling": 40_000,
        "universal": [
            "a used car 🚗",
            "a year of community college 🎓",
            "starter wedding fund 💍",
            "a really nice motorcycle 🏍️",
            "a small kitchen remodel 🍳",
        ],
        "by_currency": {},
    },
    {
        "ceiling": 200_000,
        "universal": [
            "a small down payment on a house 🏠",
            "tuition at a fancy private college, for one year 🎓",
            "a brand-new Tesla 🚙",
            "a year of really nice rent in San Francisco 🏙️",
        ],
        "by_currency": {},
    },
    {
        "ceiling": 5_000_000,
        "universal": [
            "a small house in many US cities 🏘️",
            "a tiny used yacht ⛵",
            "K-12 private-school tuition for one kid 🎓",
            "more money than most people see in a lifetime 🤯",
        ],
        "by_currency": {},
    },
]

# Anything above the last tier ceiling falls into this catch-all bucket.
RYBEAR_ASTRONOMICAL = [
    "an astonishing amount of money 🌟",
    "old-money fortune tier 💎",
    "rocket-launch budget 🚀",
    "casually-buying-a-small-island money 🏝️",
]


def rybear_says(amount_usd, from_code, to_code):
    """Pick a playful purchasing-power phrase, stably per (amount, pair).

    Phrases vary as the amount changes, but the same amount + currency
    pair always picks the same phrase — so re-renders triggered by
    unrelated UI changes don't make the line flicker.
    """
    amount_usd = abs(amount_usd)
    pool = RYBEAR_ASTRONOMICAL
    for tier in RYBEAR_TIERS:
        if amount_usd < tier["ceiling"]:
            pool = list(tier["universal"])
            for ccy in (from_code, to_code):
                pool.extend(tier["by_currency"].get(ccy, []))
            break
    seed = f"{amount_usd:.4f}|{from_code}|{to_code}".encode()
    return pool[zlib.crc32(seed) % len(pool)]


def friendly_time(raw):
    """Convert an API timestamp/date into Salt Lake City local time.

    Frankfurter returns an ISO date like '2026-05-22' (no time). ECB
    publishes around 16:00 CET, so we anchor the date there and convert
    to SLC time — typically lands around 8 AM MDT/MST.

    Older callers may pass an RFC 2822 timestamp ('Fri, 22 May 2026
    00:02:32 +0000'); we handle that too so the function is robust to
    a future source swap.
    """
    if not raw:
        return ""
    try:
        if len(raw) == 10 and raw.count("-") == 2:
            from datetime import datetime, time as dtime
            day = datetime.strptime(raw, "%Y-%m-%d")
            ecb_publish = day.replace(hour=16, minute=0, tzinfo=ZoneInfo("Europe/Berlin"))
            dt = ecb_publish.astimezone(SLC_TZ)
        else:
            dt = parsedate_to_datetime(raw).astimezone(SLC_TZ)
        date_part = dt.strftime("%a, %b %d").replace(" 0", " ")  # drop leading 0 on day
        time_part = dt.strftime("%I:%M %p").lstrip("0")           # drop leading 0 on hour
        return f"{date_part} · {time_part} {dt.strftime('%Z')}"
    except Exception:
        return raw  # if parsing fails, just show the raw string


# ----------------------------------------------------------------------
# 2. ARTWORK
# ----------------------------------------------------------------------

# The brand bear lives in ./static/bear.png. We read it at startup,
# detect its real format from the magic bytes (so PNG/JPEG/WEBP all
# work even if the filename's extension lies), and inline it as a
# data: URI in the brand <img>. This sidesteps Streamlit's
# static-serving quirks entirely.
def _detect_image_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):           return "image/png"
    if data.startswith(b"\xff\xd8\xff"):      return "image/jpeg"
    if data.startswith(b"GIF8"):              return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":  return "image/webp"
    return "image/png"  # reasonable default


@st.cache_data(show_spinner=False)
def load_bear_data_uri():
    p = Path(__file__).parent / "static" / "bear.png"
    if not p.exists():
        return ""
    data = p.read_bytes()
    return f"data:{_detect_image_mime(data)};base64," + base64.b64encode(data).decode()

BEAR_IMG = load_bear_data_uri()

PAW_SVG = """
<svg viewBox="0 0 24 24" width="15" height="15" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="12" cy="16.5" rx="6" ry="5" fill="#B07A3E"/>
  <circle cx="5.5" cy="9.5" r="2.5" fill="#B07A3E"/>
  <circle cx="11" cy="6.8" r="2.7" fill="#B07A3E"/>
  <circle cx="16.8" cy="8.6" r="2.6" fill="#B07A3E"/>
  <circle cx="20" cy="13.4" r="2.2" fill="#B07A3E"/>
</svg>
"""


# ----------------------------------------------------------------------
# 3. STYLING (a little CSS to lift the default Streamlit look)
# ----------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&family=Noto+Color+Emoji&display=swap');

/* ---- Palette tokens (kept here so they're easy to tweak) ---- */
:root {
    --bg:        #EBE3D2;   /* page */
    --surface:   #FBF8F0;   /* inputs / cards */
    --border:    #D9CFB5;   /* warm tan border */
    --ink:       #26221A;   /* primary text */
    --ink-soft:  #5C5444;   /* secondary text / captions */
    --green:     #386C4F;   /* accent */
    --green-dk:  #2A5440;   /* result card */
}

.stApp { background: var(--bg); }
/* Font stack ends with 'Noto Color Emoji' so flag emojis (🇺🇸 etc.)
   render on Windows, whose default Segoe UI Emoji omits flag glyphs.
   The browser does per-character fallback: letters use 'DM Sans',
   emoji codepoints fall through to the webfont. */
html, body, [class*="css"] {
    font-family: 'DM Sans', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif;
    color: var(--ink);
}
h1, h2, h3 { font-family: 'Fraunces', serif !important; color: var(--ink); }
/* Force the emoji-capable stack inside the selectbox/dropdown internals,
   which Streamlit otherwise styles with its own font. */
div[data-baseweb="select"] *,
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] li * {
    font-family: 'DM Sans', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif !important;
}

/* ---- Readable labels & captions ---- */
[data-testid="stWidgetLabel"] p,
.stSelectbox label, .stNumberInput label {
    color: var(--ink) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.02em;
}
[data-testid="stCaptionContainer"], .stCaption, .stCaption p {
    color: var(--ink-soft) !important;
    font-weight: 500;
}

/* ---- Input fields: cream surface, warm border, dark ink ---- */
.stNumberInput div[data-baseweb="input"],
.stNumberInput div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 0 rgba(38,34,26,0.03);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.stNumberInput input,
div[data-baseweb="select"] input,
div[data-baseweb="select"] div[role="combobox"] {
    background: transparent !important;
    color: var(--ink) !important;
    font-weight: 500;
}
.stNumberInput div[data-baseweb="input"]:focus-within,
div[data-baseweb="select"] > div:focus-within {
    border-color: var(--green) !important;
    box-shadow: 0 0 0 3px rgba(56,108,79,0.18) !important;
}
/* Number input +/- steppers */
.stNumberInput button {
    background: var(--surface) !important;
    color: var(--green) !important;
    border-left: 1.5px solid var(--border) !important;
}
/* Selectbox dropdown menu */
div[data-baseweb="popover"] li {
    background: var(--surface) !important;
    color: var(--ink) !important;
}
div[data-baseweb="popover"] li:hover {
    background: #F2EAD6 !important;
}

/* ---- Buttons: cream chip with green ink ---- */
div.stButton > button {
    background: var(--surface);
    color: var(--green);
    border: 1.5px solid var(--border);
    border-radius: 10px;
    font-weight: 600;
    padding: 0.45rem 0.9rem;
    transition: all 0.15s ease;
    box-shadow: 0 1px 0 rgba(38,34,26,0.03);
}
div.stButton > button:hover {
    border-color: var(--green);
    color: var(--green);
    background: #F5EFDD;
}
div.stButton > button:focus { box-shadow: 0 0 0 3px rgba(56,108,79,0.18); }

/* ---- Status banners: soften Streamlit's defaults to fit the palette ---- */
[data-testid="stAlert"] {
    border-radius: 12px;
    border: 1.5px solid var(--border);
}

/* ---- Brand header ---- */
.brand { display: flex; align-items: center; gap: 18px; margin-bottom: 4px; }
.bear-img {
    width: 96px; height: 96px;
    border-radius: 22px;
    object-fit: cover;
    flex-shrink: 0;
    box-shadow: 0 10px 24px -12px rgba(38,34,26,0.40);
}

/* ---- Footer status indicator ---- */
.status-block { padding-top: 4px; }
.status-line {
    display: flex; align-items: center; gap: 9px;
    color: var(--ink-soft); font-size: 12.5px; font-weight: 500;
}
.status-frequency {
    color: var(--ink-soft);
    opacity: 0.65;
    font-size: 11px;
    font-style: italic;
    padding-left: 18px;   /* line up under the text, past the dot */
    margin-top: 2px;
}
.source-link {
    color: var(--ink-soft) !important;
    text-decoration: underline;
    text-decoration-color: rgba(38,34,26,0.25);
    text-underline-offset: 2px;
    transition: color 0.15s ease, text-decoration-color 0.15s ease;
}
.source-link:hover {
    color: var(--green) !important;
    text-decoration-color: var(--green);
}
.status-dot {
    width: 9px; height: 9px; border-radius: 50%;
    display: inline-block; flex-shrink: 0;
}
.status-dot.live {
    background: #2BA76B;
    box-shadow: 0 0 0 3px rgba(43,167,107,0.20);
    animation: livepulse 2.2s ease-in-out infinite;
}
.status-dot.offline {
    background: #D97757;
    box-shadow: 0 0 0 3px rgba(217,119,87,0.20);
}
@keyframes livepulse {
    0%, 100% { box-shadow: 0 0 0 3px rgba(43,167,107,0.20); }
    50%      { box-shadow: 0 0 0 7px rgba(43,167,107,0.06); }
}
.eyebrow {
    color: var(--green); font-size: 12px; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase;
    display: flex; align-items: center; gap: 8px; margin-bottom: 3px;
}
.eyebrow .bar { width: 22px; height: 2px; background: var(--green); display: inline-block; }
.app-title {
    font-family: 'Fraunces', serif; font-size: 33px; font-weight: 600;
    color: var(--ink); line-height: 1.06; letter-spacing: -0.02em;
}

/* ---- The big green result card ---- */
.result-card {
    background: var(--green-dk); border-radius: 16px;
    padding: 22px 24px; margin: 6px 0 4px 0;
    box-shadow: 0 12px 28px -16px rgba(42,84,64,0.55);
}
.result-label {
    color: rgba(255,255,255,0.7); font-size: 11px; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px;
}
.result-amount { font-family: 'Fraunces', serif; color: #fff; font-size: 40px; font-weight: 600; line-height: 1; }
.result-code { color: rgba(255,255,255,0.78); font-size: 17px; font-weight: 600; }
.result-rate {
    margin-top: 10px; font-family: 'JetBrains Mono', monospace;
    font-size: 12px; color: rgba(255,255,255,0.72);
}

/* ---- "Rybear says…" callout ---- */
.bear-says {
    margin-top: 12px;
    padding: 12px 16px;
    background: rgba(56,108,79,0.07);
    border-left: 3px solid var(--green);
    border-radius: 10px;
    font-size: 14px;
    color: var(--ink);
    display: flex; align-items: center; gap: 12px;
    line-height: 1.4;
}
.bear-says-emoji { font-size: 22px; flex-shrink: 0; }
.bear-says strong {
    color: var(--green);
    font-weight: 700;
}

/* ---- 30-day sparkline (sits inline under the result card) ---- */
.sparkline-row {
    display: flex; align-items: center; gap: 14px;
    padding: 10px 4px 0 4px;
}
.sparkline-cap {
    color: var(--ink-soft); font-size: 11px; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase;
    flex-shrink: 0;
}
.sparkline-svg { flex: 1; line-height: 0; }
.sparkline-pct {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600; font-size: 12px; flex-shrink: 0;
}

/* ---- Footer credit ---- */
.credit {
    text-align: center; margin-top: 16px; color: var(--ink-soft); font-size: 12.5px;
    font-weight: 500;
    display: flex; align-items: center; justify-content: center; gap: 7px;
}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# 4. STATE  (remembers the chosen currencies between clicks)
# ----------------------------------------------------------------------

if "from_cur" not in st.session_state:
    st.session_state.from_cur = "USD"
if "to_cur" not in st.session_state:
    st.session_state.to_cur = "KRW"


def swap_currencies():
    st.session_state.from_cur, st.session_state.to_cur = (
        st.session_state.to_cur, st.session_state.from_cur,
    )


def set_pair(from_code, to_code):
    st.session_state.from_cur = from_code
    st.session_state.to_cur = to_code


# ----------------------------------------------------------------------
# 5. THE PAGE
# ----------------------------------------------------------------------

# --- Brand header: friendly bear + title ------------------------------
st.markdown(f"""
<div class="brand">
    <img class="bear-img" src="{BEAR_IMG}" alt="Rybear">
    <div>
        <div class="eyebrow"><span class="bar"></span>FX Rates</div>
        <div class="app-title">Rybear's<br>Currency Converter</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("")

data = get_rates()
rates = data["rates"]

# --- Amount -----------------------------------------------------------
amount = st.number_input(
    "Amount",
    min_value=0.0,
    value=100.0,
    step=10.0,
    help="How much money you want to convert.",
)

# --- From / Swap / To -------------------------------------------------
def label_for(code):
    info = CURRENCIES[code]
    return f"{info['flag']}  {code} — {info['name']}"

col_from, col_swap, col_to = st.columns([5, 1, 5])

with col_from:
    st.selectbox("From", options=list(CURRENCIES.keys()),
                 format_func=label_for, key="from_cur")

with col_swap:
    st.write("")
    st.write("")
    st.button("⇄", on_click=swap_currencies, use_container_width=True,
              help="Swap the two currencies")

with col_to:
    st.selectbox("To", options=list(CURRENCIES.keys()),
                 format_func=label_for, key="to_cur")

from_code = st.session_state.from_cur
to_code = st.session_state.to_cur

# --- The conversion ---------------------------------------------------
# Every rate is relative to USD, so we get any pair with a "cross-rate":
#     rate(A -> B) = rate(USD -> B) / rate(USD -> A)
rate = rates[to_code] / rates[from_code]
converted = amount * rate

to_decimals = CURRENCIES[to_code]["decimals"]
rate_decimals = 6 if rate < 1 else (2 if to_decimals == 0 else 4)

# --- Result card ------------------------------------------------------
st.markdown(f"""
<div class="result-card">
    <div class="result-label">{from_code} &rarr; {to_code}</div>
    <span class="result-amount">{fmt(converted, to_decimals)}</span>
    <span class="result-code">&nbsp;{to_code}</span>
    <div class="result-rate">
        1 {from_code} = {fmt(rate, rate_decimals)} {to_code}
    </div>
</div>
""", unsafe_allow_html=True)

# --- 30-day sparkline -------------------------------------------------
# A minimal inline trend line under the result card. Hidden when the
# series can't be fetched, when the pair is trivial (same currency),
# or when fewer than two data points are available.
history = get_history(from_code, to_code, days=30)
if len(history) >= 2:
    history_values = [rate for _, rate in history]
    pct_change = (history_values[-1] - history_values[0]) / history_values[0] * 100
    is_up = pct_change >= 0
    spark_color = "#2BA76B" if is_up else "#D97757"
    arrow = "▲" if is_up else "▼"
    spark_svg = make_sparkline_svg(history_values, color=spark_color)
    st.markdown(
        f'<div class="sparkline-row">'
        f'  <span class="sparkline-cap">30-day trend</span>'
        f'  <span class="sparkline-svg">{spark_svg}</span>'
        f'  <span class="sparkline-pct" style="color:{spark_color};">'
        f'{arrow} {abs(pct_change):.2f}%</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# --- Rybear says... ---------------------------------------------------
# Translate the converted amount into a concrete mental picture via
# its USD equivalent. Rates are USD-based, so USD value of `amount` of
# `from_code` is simply amount / rates[from_code].
amount_usd = amount / rates[from_code] if rates.get(from_code) else 0
if amount_usd > 0:
    phrase = rybear_says(amount_usd, from_code, to_code)
    st.markdown(
        f'<div class="bear-says">'
        f'<span class="bear-says-emoji">🐻</span>'
        f'<span><strong>Rybear says</strong> &mdash; that\'s {phrase}!</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# --- Quick pairs ------------------------------------------------------
st.write("")
st.caption("Quick conversions")
quick = [("USD", "KRW"), ("USD", "JPY"), ("KRW", "USD"), ("JPY", "USD")]
cols = st.columns(len(quick))
for col, (f, t) in zip(cols, quick):
    with col:
        st.button(f"{f} → {t}", key=f"q_{f}{t}",
                  on_click=set_pair, args=(f, t),
                  use_container_width=True)

# --- Footer status ----------------------------------------------------
# (No refresh button: open.er-api.com updates ~once per day, and
# Streamlit caches our fetch for an hour. Clicking refresh wouldn't
# get you fresher numbers, so the button was just noise.)
st.write("")
if data["live"]:
    when = friendly_time(data["updated"])
    timestamp_part = f"{when} · " if when else ""
    status_html = (
        f'<div class="status-block">'
        f'  <div class="status-line">'
        f'    <span class="status-dot live"></span>'
        f'    <span>Latest rates · {timestamp_part}'
        f'<a class="source-link" href="https://www.frankfurter.dev" '
        f'target="_blank" rel="noopener">Frankfurter (ECB)</a></span>'
        f'  </div>'
        f'  <div class="status-frequency">Updated on business days, around 8 AM MT</div>'
        f'</div>'
    )
else:
    status_html = (
        '<div class="status-block">'
        '  <div class="status-line">'
        '    <span class="status-dot offline"></span>'
        '    <span>Offline · using built-in fallback rates</span>'
        '  </div>'
        '  <div class="status-frequency">Will reconnect when the network is available</div>'
        '</div>'
    )
st.markdown(status_html, unsafe_allow_html=True)

# --- The personal touch -----------------------------------------------
st.markdown(f'<div class="credit">{PAW_SVG}<span>Rybear Tools Unlimited</span></div>',
            unsafe_allow_html=True)
