# ╔══════════════════════════════════════════════════════════╗
# ║   RTFC Cost-per-Certificate Calculator (CFO view)        ║
# ╚══════════════════════════════════════════════════════════╝
import streamlit as st
import pandas as pd

# ─── PIN-gate (add immediately after the imports) ───────────────────────────
# Hard-code one or more valid 4-digit PINs here.
VALID_PINS = {"2025"}           # <= change to whatever you want

# Use Streamlit session_state so the user only enters the PIN once per session.
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False

if not st.session_state.unlocked:
    pin = st.text_input("Enter 4-digit PIN", type="password", max_chars=4)
    
    if pin and len(pin) == 4:
        if pin in VALID_PINS:
            st.session_state.unlocked = True
            st.experimental_rerun()        # reload and show the app
        else:
            st.error("Incorrect PIN. Try again.")
    st.stop()                              # halt the script until unlocked
# ────────────────────────────────────────────────────────────────────────────

# ─── 1.  Default fuel quotes ────────────────────────────────
FUEL_CATALOG = {
    "HVO Class-2 waste-oil": dict(price=1180, unit="USD/m3", currency="USD",
                                  density=0.78, rtfc_multiplier=2, energy_ratio=1.00),
    "UCOME FAME 0 °C":       dict(price=830, unit="USD/t",  currency="USD",
                                  density=0.88, rtfc_multiplier=2, energy_ratio=1.00),
    "RME (crop FAME)":       dict(price=726, unit="USD/t",  currency="USD",
                                  density=0.88, rtfc_multiplier=1, energy_ratio=1.00),
    "HVO Class-4 (tallow)":  dict(price=1_235, unit="USD/t", currency="USD",
                                  density=0.79, rtfc_multiplier=1, energy_ratio=1.00),
}

# ─── 2.  Sidebar – FX only ─────────────────────────────────
st.sidebar.header("Market FX")
fx = st.sidebar.number_input("USD per GBP", value=1.3463, step=0.0001, format="%.4f")

# ─── 3.  Main pane – fuel quote & shipping premium ─────────
st.title("RTFC Cost-per-Certificate Calculator")

fuel_name = st.selectbox("Fuel", list(FUEL_CATALOG.keys()), index=0)
defaults  = FUEL_CATALOG[fuel_name]

col1, col2, col3 = st.columns(3)
with col1:
    price   = st.number_input("Price", value=float(defaults["price"]))
    density = st.number_input("Density (t / m³)", value=float(defaults["density"]), step=0.01)
with col2:
    unit     = st.selectbox("Unit", ["USD/m3","USD/t","GBP/m3","GBP/t"],
                            index=["USD/m3","USD/t","GBP/m3","GBP/t"].index(defaults["unit"]))
    currency = st.selectbox("Currency", ["USD","GBP"],
                            index=0 if defaults["currency"]=="USD" else 1)
with col3:
    multiplier   = st.selectbox("RTFC multiplier", [1,2],
                                index=0 if defaults["rtfc_multiplier"]==1 else 1)
    energy_ratio = st.number_input("Energy ratio", value=float(defaults["energy_ratio"]), step=0.01)

st.markdown("---")

ship_col1, ship_col2, ship_col3 = st.columns(3)
with ship_col1:
    ship_val = st.number_input("Shipping premium", value=30.0, step=0.50)
with ship_col2:
    ship_unit = st.selectbox("Ship unit", ["per m3", "per tonne"], index=0)
with ship_col3:
    ship_curr = st.selectbox("Ship currency", ["USD", "GBP"], index=0)

# ─── 4.  Helper functions ─────────────────────────────────
def to_gbp(val, curr, fx_rate):
    return val if curr == "GBP" else val / fx_rate

def to_ppl(price_gbp, unit_txt, dens):
    if unit_txt.endswith("/m3"):
        return (price_gbp / 1_000) * 100              # £/m³ → £/l → p/l
    litres_per_ton = 1_000 / dens
    return (price_gbp / litres_per_ton) * 100         # £/t → £/l → p/l

def premium_to_ppl(value, unit_txt, curr, dens, fx_rate):
    if value == 0:
        return 0.0
    gbp_val = value if curr == "GBP" else value / fx_rate
    if unit_txt == "per m3":
        return (gbp_val / 1_000) * 100
    litres_per_ton = 1_000 / dens
    return (gbp_val / litres_per_ton) * 100

# ─── 5.  Core calculation ─────────────────────────────────
gbp_price   = to_gbp(price, currency, fx)
ppl_raw     = to_ppl(gbp_price, unit, density)
ship_ppl    = premium_to_ppl(ship_val, ship_unit, ship_curr, density, fx)
ppl_energy  = (ppl_raw + ship_ppl) / energy_ratio
rtfc_ppl    = ppl_energy / multiplier

# ─── 6.  Narrative explanation (classic, step-by-step) ─────
shipping_line = (
    f"* **Shipping premium** – adding **{ship_ppl:.2f} p** per litre for "
    f"freight/storage brings the total to **{ppl_energy:.2f} p**.\n"
    if ship_val else ""
)

st.markdown(f"""
### Walk-through

For **{fuel_name}**, if the indicative quote is **{price:,.2f} {unit.upper()}** priced in **{currency}**:

* **FX conversion** – using £1 = ${fx:.4f}, that equals **£{gbp_price:,.2f} per {unit.split('/')[-1]}**.

* **Unit conversion** – on a litre basis one litre costs **{ppl_raw:,.2f} p**{" (energy-adjusted)" if energy_ratio != 1 else ""}.

{shipping_line}* **Certificate split** – this pathway earns **{multiplier} RTFC{'s' if multiplier > 1 else ''} per litre**, so the **all-in cost is {rtfc_ppl:,.2f} pence per certificate**.
""")


# ─── 7.  Summary table ────────────────────────────────────
summary = pd.DataFrame({
    "pence / litre (base)": [round(ppl_raw, 2)],
    "shipping p/l":         [round(ship_ppl, 2)],
    "pence / litre total":  [round(ppl_energy, 2)],
    "pence / RTFC":         [round(rtfc_ppl, 2)],
    "RTFCs per litre":      [multiplier]
}, index=[fuel_name])

st.table(summary)

