"""
Rybear's Currency Converter — Streamlit edition
-----------------------------------------------
A polished currency converter, made special for Ryleigh ("Rybear").

Run it locally with:
    pip install streamlit requests
    streamlit run streamlit_app.py

Live rates come from open.er-api.com (no API key needed).
If the internet is unavailable, the app falls back to built-in
approximate rates so it never fully breaks.
"""

import base64
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

# code -> display name, symbol, and how many decimals make sense
CURRENCIES = {
    "USD": {"name": "US Dollar",         "symbol": "$",  "decimals": 2},
    "KRW": {"name": "South Korean Won",  "symbol": "₩",  "decimals": 0},
    "JPY": {"name": "Japanese Yen",      "symbol": "¥",  "decimals": 0},
    "EUR": {"name": "Euro",              "symbol": "€",  "decimals": 2},
    "GBP": {"name": "British Pound",     "symbol": "£",  "decimals": 2},
    "CAD": {"name": "Canadian Dollar",   "symbol": "$",  "decimals": 2},
    "AUD": {"name": "Australian Dollar", "symbol": "$",  "decimals": 2},
    "CNY": {"name": "Chinese Yuan",      "symbol": "¥",  "decimals": 2},
    "MXN": {"name": "Mexican Peso",      "symbol": "$",  "decimals": 2},
    "INR": {"name": "Indian Rupee",      "symbol": "₹",  "decimals": 2},
}

# Used only if the live request fails — approximate, USD-based.
FALLBACK_RATES = {
    "USD": 1.0, "KRW": 1380.0, "JPY": 156.0, "EUR": 0.92, "GBP": 0.79,
    "CAD": 1.37, "AUD": 1.52, "CNY": 7.24, "MXN": 18.6, "INR": 83.4,
}


@st.cache_data(ttl=3600)  # remember the result for 1 hour so we don't hammer the API
def get_rates():
    """Fetch live USD-based exchange rates, with a graceful offline fallback."""
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        data = resp.json()
        if data.get("result") == "success":
            return {
                "rates": data["rates"],
                "updated": data.get("time_last_update_utc", ""),
                "live": True,
            }
    except Exception:
        pass  # network down, blocked, or API hiccup — fall through
    return {"rates": FALLBACK_RATES, "updated": "", "live": False}


def fmt(value, decimals):
    """Format a number with thousands separators and the right decimal places."""
    return f"{value:,.{decimals}f}"


def friendly_time(raw):
    """Convert the API's UTC timestamp into Salt Lake City local time.
    'Fri, 22 May 2026 00:02:32 +0000' -> 'Thu, May 21 · 6:02 PM MDT'.
    Outside DST it'll read 'MST' — handled automatically by zoneinfo."""
    if not raw:
        return ""
    try:
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
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

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
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
h1, h2, h3 { font-family: 'Fraunces', serif !important; color: var(--ink); }

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
.status-line {
    display: flex; align-items: center; gap: 9px;
    color: var(--ink-soft); font-size: 12.5px; font-weight: 500;
    padding-top: 4px;
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
    return f"{code} — {CURRENCIES[code]['name']}"

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
    status_label = f"Today's rates · {when}" if when else "Today's rates · open.er-api.com"
    status_html = (
        f'<div class="status-line">'
        f'<span class="status-dot live"></span>'
        f'<span>{status_label}</span>'
        f'</div>'
    )
else:
    status_html = (
        '<div class="status-line">'
        '<span class="status-dot offline"></span>'
        '<span>Offline · using built-in fallback rates</span>'
        '</div>'
    )
st.markdown(status_html, unsafe_allow_html=True)

# --- The personal touch -----------------------------------------------
st.markdown(f'<div class="credit">{PAW_SVG}<span>Rybear Tools Unlimited</span></div>',
            unsafe_allow_html=True)
