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

BEAR_SVG = """
<svg viewBox="0 0 120 112" width="58" height="54" xmlns="http://www.w3.org/2000/svg">
  <!-- Ears (peeking above the head) -->
  <circle cx="30" cy="24" r="16" fill="#E8B97D"/>
  <circle cx="90" cy="24" r="16" fill="#E8B97D"/>
  <circle cx="30" cy="24" r="8" fill="#FFD4C2"/>
  <circle cx="90" cy="24" r="8" fill="#FFD4C2"/>
  <!-- Round, friendly head -->
  <circle cx="60" cy="64" r="40" fill="#E8B97D"/>
  <!-- Soft muzzle -->
  <ellipse cx="60" cy="79" rx="22" ry="16" fill="#FFEDD5"/>
  <!-- Pink blush cheeks -->
  <ellipse cx="32" cy="74" rx="6.5" ry="4.2" fill="#FFA8B5" opacity="0.75"/>
  <ellipse cx="88" cy="74" rx="6.5" ry="4.2" fill="#FFA8B5" opacity="0.75"/>
  <!-- Big shiny eyes -->
  <circle cx="46" cy="61" r="7" fill="#2E2418"/>
  <circle cx="74" cy="61" r="7" fill="#2E2418"/>
  <circle cx="48.4" cy="58.6" r="2.7" fill="#FFFFFF"/>
  <circle cx="76.4" cy="58.6" r="2.7" fill="#FFFFFF"/>
  <circle cx="43.8" cy="63.4" r="1.2" fill="#FFFFFF" opacity="0.7"/>
  <circle cx="71.8" cy="63.4" r="1.2" fill="#FFFFFF" opacity="0.7"/>
  <!-- Little nose -->
  <ellipse cx="60" cy="72" rx="3.6" ry="2.8" fill="#2E2418"/>
  <!-- Happy smile -->
  <path d="M52 78 Q60 86 68 78"
        stroke="#2E2418" stroke-width="2.4" fill="none" stroke-linecap="round"/>
  <!-- Floating heart -->
  <g transform="translate(98 2) scale(0.85)">
    <path d="M12 22 C 2 14, 0 6, 6 4 C 9 3, 12 5, 12 8 C 12 5, 15 3, 18 4 C 24 6, 22 14, 12 22 Z"
          fill="#FF6B9B"/>
  </g>
</svg>
"""

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
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@500;600&display=swap');

.stApp { background: #EBE3D2; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Fraunces', serif !important; color: #26221A; }

/* Buttons — warm green, consistent across the app */
div.stButton > button {
    background: #FBF8F0;
    color: #2A5440;
    border: 1.5px solid #E0D6BF;
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.15s ease;
}
div.stButton > button:hover {
    border-color: #386C4F;
    color: #386C4F;
}

div[data-baseweb="select"] > div, .stNumberInput div[data-baseweb="input"] {
    border-radius: 12px !important;
}

/* Brand header — bear badge + title */
.brand { display: flex; align-items: center; gap: 16px; margin-bottom: 4px; }
.bear-badge {
    background: #FBF8F0; border: 1.5px solid #E0D6BF; border-radius: 20px;
    padding: 9px 9px 5px 9px; display: flex; flex-shrink: 0;
    box-shadow: 0 8px 20px -10px rgba(38,34,26,0.30);
}
.eyebrow {
    color: #386C4F; font-size: 12px; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase;
    display: flex; align-items: center; gap: 8px; margin-bottom: 3px;
}
.eyebrow .bar { width: 22px; height: 2px; background: #386C4F; display: inline-block; }
.app-title {
    font-family: 'Fraunces', serif; font-size: 33px; font-weight: 600;
    color: #26221A; line-height: 1.06; letter-spacing: -0.02em;
}

/* The big green result card */
.result-card { background: #2A5440; border-radius: 16px; padding: 22px 24px; margin: 6px 0 4px 0; }
.result-label {
    color: rgba(255,255,255,0.55); font-size: 11px; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px;
}
.result-amount { font-family: 'Fraunces', serif; color: #fff; font-size: 40px; font-weight: 600; line-height: 1; }
.result-code { color: rgba(255,255,255,0.7); font-size: 17px; font-weight: 600; }
.result-rate {
    margin-top: 10px; font-family: 'JetBrains Mono', monospace;
    font-size: 12px; color: rgba(255,255,255,0.6);
}

/* Footer credit — the little personal touch */
.credit {
    text-align: center; margin-top: 16px; color: #7A7160; font-size: 12.5px;
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
    <div class="bear-badge">{BEAR_SVG}</div>
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
