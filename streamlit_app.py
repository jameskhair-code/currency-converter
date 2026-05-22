"""
Currency Converter — Streamlit edition
--------------------------------------
A polished take on a classic first project.

Run it with:
    pip install streamlit requests
    streamlit run currency_converter.py

Live rates come from open.er-api.com (no API key needed).
If the internet is unavailable, the app falls back to built-in
approximate rates so it never fully breaks.
"""

import streamlit as st
import requests

# ----------------------------------------------------------------------
# 1. CONFIG & DATA
# ----------------------------------------------------------------------

st.set_page_config(page_title="Currency Converter", page_icon="💱", layout="centered")

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
# 2. STYLING (a little CSS to lift the default Streamlit look)
# ----------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@500;600&display=swap');

.stApp { background: #EBE3D2; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* Headings in a characterful serif */
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

/* Input + selectbox rounding */
div[data-baseweb="select"] > div, .stNumberInput div[data-baseweb="input"] {
    border-radius: 12px !important;
}

/* The eyebrow label above the title */
.eyebrow {
    color: #386C4F; font-size: 12px; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase;
    display: flex; align-items: center; gap: 8px; margin-bottom: 2px;
}
.eyebrow .bar { width: 22px; height: 2px; background: #386C4F; display: inline-block; }

/* The big green result card */
.result-card {
    background: #2A5440; border-radius: 16px;
    padding: 22px 24px; margin: 6px 0 4px 0;
}
.result-label {
    color: rgba(255,255,255,0.55); font-size: 11px; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px;
}
.result-amount {
    font-family: 'Fraunces', serif; color: #ffffff;
    font-size: 40px; font-weight: 600; line-height: 1;
}
.result-code { color: rgba(255,255,255,0.7); font-size: 17px; font-weight: 600; }
.result-rate {
    margin-top: 10px; font-family: 'JetBrains Mono', monospace;
    font-size: 12px; color: rgba(255,255,255,0.6);
}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# 3. STATE  (remembers the chosen currencies between clicks)
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
# 4. THE PAGE
# ----------------------------------------------------------------------

st.markdown('<div class="eyebrow"><span class="bar"></span>Live FX</div>',
            unsafe_allow_html=True)
st.title("Currency Converter")

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
