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

import streamlit as st
import requests

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


# ----------------------------------------------------------------------
# 2. ARTWORK  (a friendly bear, drawn as SVG so it renders everywhere)
# ----------------------------------------------------------------------

# A tiny 8-bit-feeling bear built from Unicode block characters.
# Rendered as monospace text inside the brand badge.
BEAR_ASCII = "\
 ▄ ▄ \n\
▐●ᴥ●▌\n\
 ▀▀▀"

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
.brand { display: flex; align-items: center; gap: 16px; margin-bottom: 4px; }
.bear-badge {
    background: var(--surface); border: 1.5px solid var(--border); border-radius: 16px;
    padding: 10px 14px 8px 14px; display: flex; flex-shrink: 0;
    box-shadow: 0 8px 20px -10px rgba(38,34,26,0.30);
}
.bear-ascii {
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    color: #6B4423;            /* warm coffee brown, reads as bear-fur */
    font-size: 18px;
    font-weight: 700;
    line-height: 1.05;
    letter-spacing: 0;
    white-space: pre;
    margin: 0;
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
    <div class="bear-badge"><div class="bear-ascii">{BEAR_ASCII}</div></div>
    <div>
        <div class="eyebrow"><span class="bar"></span>Live FX</div>
        <div class="app-title">Rybear's<br>Currency Converter</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("")

data = get_rates()
rates = data["rates"]

# Status banner — honest about where the numbers came from
if data["live"]:
    st.success("Live exchange rates loaded.")
else:
    st.warning("Couldn't reach the live rates server — using built-in offline rates.")

st.write("")

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

# --- Footer -----------------------------------------------------------
st.write("")
foot_left, foot_right = st.columns([3, 1])
with foot_left:
    if data["updated"]:
        st.caption(f"Rates as of {data['updated']}")
    else:
        st.caption("Source: open.er-api.com")
with foot_right:
    if st.button("↻ Refresh", use_container_width=True):
        get_rates.clear()      # drop the cached result
        st.rerun()             # ...and reload the page

# --- The personal touch -----------------------------------------------
st.markdown(f'<div class="credit">{PAW_SVG}<span>Rybear Tools Unlimited</span></div>',
            unsafe_allow_html=True)
