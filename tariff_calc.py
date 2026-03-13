import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="PAIP Water Bill Calculator",
    page_icon="logo_paip.png",
    layout="centered"
)

# =========================================================
# Pahang tariff data
# =========================================================
TARIFFS = {
    "DOMESTIK (METER INDIVIDU)": {
        "type": "block",
        "minimum_charge": 8.00,
        "blocks": [
            {"label": "0–20 m³", "max_usage": 20, "rate": 0.80},
            {"label": ">20–35 m³", "max_usage": 35, "rate": 1.52},
            {"label": ">35 m³", "max_usage": None, "rate": 1.98},
        ],
    },
    "DOMESTIK (METER PUKAL)": {
        "type": "flat",
        "minimum_charge": 17.20,
        "rate": 1.72,
    },
    "BUKAN DOMESTIK": {
        "type": "block",
        "minimum_charge": 30.00,
        "blocks": [
            {"label": "0–35 m³", "max_usage": 35, "rate": 2.02},
            {"label": ">35 m³", "max_usage": None, "rate": 2.67},
        ],
    },
    "RUMAH IBADAT DAN INSTITUSI KEBAJIKAN": {
        "type": "flat",
        "minimum_charge": 8.20,
        "rate": 0.82,
    },
    "PERKAPALAN": {
        "type": "flat",
        "minimum_charge": 80.30,
        "rate": 8.03,
    },
    "PUSAT DATA": {
        "type": "flat",
        "minimum_charge": 53.30,
        "rate": 5.33,
    },
}


# =========================================================
# Utility functions
# =========================================================
def format_rm(value: float) -> str:
    return f"RM {value:,.2f}"


def validate_usage(usage: float) -> None:
    if usage < 0:
        raise ValueError("Water usage cannot be negative.")


def is_number(value) -> bool:
    return isinstance(value, (int, float))


def calculate_block_tariff(usage: float, tariff_config: dict) -> dict:
    validate_usage(usage)

    blocks = tariff_config["blocks"]
    minimum_charge = tariff_config["minimum_charge"]

    breakdown = []
    remaining_usage = usage
    previous_limit = 0.0
    subtotal = 0.0

    for block in blocks:
        block_label = block["label"]
        block_max = block["max_usage"]
        block_rate = block["rate"]

        if remaining_usage <= 0:
            break

        if block_max is None:
            units_in_block = remaining_usage
        else:
            block_width = block_max - previous_limit
            units_in_block = min(remaining_usage, block_width)

        charge = units_in_block * block_rate
        subtotal += charge

        breakdown.append({
            "Block": block_label,
            "Usage (m³)": round(units_in_block, 2),
            "Rate (RM/m³)": round(block_rate, 2),
            "Charge (RM)": round(charge, 2),
        })

        remaining_usage -= units_in_block

        if block_max is not None:
            previous_limit = block_max

    final_total = max(subtotal, minimum_charge)
    minimum_applied = final_total > subtotal

    if usage == 0:
        breakdown = [{
            "Block": "Minimum Charge Applied",
            "Usage (m³)": 0.00,
            "Rate (RM/m³)": "-",
            "Charge (RM)": round(minimum_charge, 2),
        }]

    return {
        "subtotal": round(subtotal, 2),
        "minimum_charge": round(minimum_charge, 2),
        "total": round(final_total, 2),
        "minimum_applied": minimum_applied,
        "breakdown": breakdown,
    }


def calculate_flat_tariff(usage: float, tariff_config: dict) -> dict:
    validate_usage(usage)

    rate = tariff_config["rate"]
    minimum_charge = tariff_config["minimum_charge"]

    subtotal = usage * rate
    final_total = max(subtotal, minimum_charge)
    minimum_applied = final_total > subtotal

    if usage == 0:
        breakdown = [{
            "Block": "Minimum Charge Applied",
            "Usage (m³)": 0.00,
            "Rate (RM/m³)": "-",
            "Charge (RM)": round(minimum_charge, 2),
        }]
    else:
        breakdown = [{
            "Block": "Flat Rate",
            "Usage (m³)": round(usage, 2),
            "Rate (RM/m³)": round(rate, 2),
            "Charge (RM)": round(subtotal, 2),
        }]

    return {
        "subtotal": round(subtotal, 2),
        "minimum_charge": round(minimum_charge, 2),
        "total": round(final_total, 2),
        "minimum_applied": minimum_applied,
        "breakdown": breakdown,
    }


def calculate_bill(category: str, usage: float) -> dict:
    tariff_config = TARIFFS[category]

    if tariff_config["type"] == "block":
        return calculate_block_tariff(usage, tariff_config)
    if tariff_config["type"] == "flat":
        return calculate_flat_tariff(usage, tariff_config)

    raise ValueError(f"Unsupported tariff type for category: {category}")


def render_html_table(
    df: pd.DataFrame,
    money_columns: list[str] | None = None,
    number_columns: list[str] | None = None
) -> str:
    money_columns = money_columns or []
    number_columns = number_columns or []

    header_html = "".join(f"<th>{col}</th>" for col in df.columns)

    body_rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            value = row[col]

            if col in money_columns:
                if is_number(value):
                    cell_text = f"RM {float(value):,.2f}"
                    cell_class = "num"
                else:
                    cell_text = str(value)
                    cell_class = "text-center"
            elif col in number_columns:
                if is_number(value):
                    cell_text = f"{float(value):,.2f}"
                    cell_class = "num"
                else:
                    cell_text = str(value)
                    cell_class = "text-center"
            else:
                cell_text = str(value)
                cell_class = ""

            cells.append(f'<td class="{cell_class}">{cell_text}</td>')

        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    return f"""
    <div class="custom-table-wrap">
        <table class="custom-table">
            <thead>
                <tr>{header_html}</tr>
            </thead>
            <tbody>
                {''.join(body_rows)}
            </tbody>
        </table>
    </div>
    """


# =========================================================
# Styling
# =========================================================
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1000px;
}

/* Main big white pane */
div[data-testid="stVerticalBlock"]:has(#main-pane-marker) {
    background: white;
    border: 1px solid #DCE6F2;
    border-radius: 24px;
    padding: 28px 28px 24px 28px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    margin-bottom: 1rem;
}

/* Force readable text inside pane */
div[data-testid="stVerticalBlock"]:has(#main-pane-marker),
div[data-testid="stVerticalBlock"]:has(#main-pane-marker) * {
    color: #1F2937;
}

/* Header */
.paip-title {
    font-size: 42px;
    font-weight: 800;
    color: #1F2937 !important;
    margin: 0;
    line-height: 1.1;
}

.paip-subtitle {
    font-size: 18px;
    color: #4B5563 !important;
    margin-top: 8px;
    margin-bottom: 8px;
}

.paip-description {
    font-size: 17px;
    color: #374151 !important;
    margin-top: 10px;
    margin-bottom: 0;
}

/* Section title */
.section-title {
    font-size: 26px;
    font-weight: 700;
    color: #1F2937 !important;
    margin-top: 6px;
    margin-bottom: 16px;
}

/* Spacing helper */
.section-gap {
    margin-top: 22px;
}

/* Blue info boxes */
.metric-box {
    background: #F3F8FF;
    border: 1px solid #CFE2FF;
    border-radius: 18px;
    padding: 18px 22px;
    min-height: 118px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.metric-label {
    font-size: 15px;
    color: #5B6472 !important;
    margin-bottom: 8px;
}

.metric-value {
    font-size: 30px;
    font-weight: 800;
    color: #1D5FD0 !important;
    line-height: 1.2;
}

.final-amount-box {
    background: #F3F8FF;
    border: 1px solid #CFE2FF;
    border-radius: 18px;
    padding: 22px;
    margin-top: 14px;
}

.final-amount-label {
    font-size: 15px;
    color: #5B6472 !important;
    margin-bottom: 8px;
}

.final-amount-value {
    font-size: 38px;
    font-weight: 800;
    color: #1D5FD0 !important;
    line-height: 1.2;
}

/* Form cleanup */
div[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* =========================
   SELECTBOX - FORCE WHITE
   ========================= */
div[data-testid="stSelectbox"] > div,
div[data-testid="stSelectbox"] div[data-baseweb="select"],
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stSelectbox"] [role="combobox"],
div[data-baseweb="select"] > div {
    background: #FFFFFF !important;
    color: #1F2937 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
}

/* Select text + placeholder + arrow */
div[data-testid="stSelectbox"] * {
    color: #1F2937 !important;
    fill: #1F2937 !important;
}

div[data-testid="stSelectbox"] svg {
    fill: #1F2937 !important;
    color: #1F2937 !important;
}

/* Dropdown popover/menu */
div[data-baseweb="popover"],
div[data-baseweb="popover"] * {
    background: #FFFFFF !important;
    color: #1F2937 !important;
}

ul[role="listbox"] {
    background: #FFFFFF !important;
    border: 1px solid #D1D5DB !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12) !important;
    overflow: hidden !important;
}

li[role="option"] {
    background: #FFFFFF !important;
    color: #1F2937 !important;
}

li[role="option"]:hover {
    background: #F3F4F6 !important;
    color: #1F2937 !important;
}

/* =========================
   NUMBER INPUT - FORCE WHITE
   ========================= */
div[data-testid="stNumberInput"] input {
    background: #FFFFFF !important;
    color: #1F2937 !important;
    -webkit-text-fill-color: #1F2937 !important;
}

/* Whole input container */
div[data-testid="stNumberInput"] div[data-baseweb="input"] > div {
    background: #FFFFFF !important;
    border: 1px solid #D1D5DB !important;
    border-radius: 12px !important;
    box-shadow: none !important;
}

/* Right-side stepper area */
div[data-testid="stNumberInput"] button {
    background: #FFFFFF !important;
    color: #1F2937 !important;
    border: none !important;
    box-shadow: none !important;
}

div[data-testid="stNumberInput"] button:hover {
    background: #F9FAFB !important;
    color: #1F2937 !important;
}

div[data-testid="stNumberInput"] button svg {
    fill: #1F2937 !important;
    color: #1F2937 !important;
}

/* Specific increment/decrement buttons */
button[aria-label="Increment"],
button[aria-label="Decrement"] {
    background: #FFFFFF !important;
    color: #1F2937 !important;
    border: none !important;
}

button[aria-label="Increment"] svg,
button[aria-label="Decrement"] svg {
    fill: #1F2937 !important;
    color: #1F2937 !important;
}

/* Submit button */
div[data-testid="stFormSubmitButton"] button {
    background: #0B5ED7 !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    min-height: 44px !important;
    font-weight: 600 !important;
}

/* Force button text to white */
div[data-testid="stFormSubmitButton"] button p {
    color: white !important;
}

/* Hover */
div[data-testid="stFormSubmitButton"] button:hover {
    background: #094db1 !important;
}

div[data-testid="stFormSubmitButton"] button:hover p {
    color: white !important;
}

div[data-testid="stFormSubmitButton"] button:hover {
    background: #094db1 !important;
    color: #FFFFFF !important;
}

/* Expander */
div[data-testid="stExpander"] {
    border-radius: 14px !important;
    border: 1px solid #DCE6F2 !important;
    background: #FFFFFF !important;
    overflow: hidden;
}

div[data-testid="stExpander"] summary {
    background: #FFFFFF !important;
    color: #1F2937 !important;
}

/* Alerts readability */
div[data-testid="stAlert"] {
    border-radius: 14px !important;
}

/* Center image */
[data-testid="stImage"] {
    display: flex;
    justify-content: center;
}

/* Custom table */
.custom-table-wrap {
    width: 100%;
    overflow-x: auto;
    border: 1px solid #DCE6F2;
    border-radius: 16px;
    background: #FFFFFF;
}

.custom-table {
    width: 100%;
    border-collapse: collapse;
    background: #FFFFFF;
    color: #1F2937;
    font-size: 16px;
}

.custom-table thead th {
    background: #0B5ED7;
    color: #FFFFFF !important;
    font-weight: 700;
    text-align: left;
    padding: 14px 16px;
    border-bottom: 1px solid #DCE6F2;
}

.custom-table tbody td {
    padding: 14px 16px;
    border-bottom: 1px solid #E5EDF7;
    color: #1F2937 !important;
    background: #FFFFFF !important;
}

.custom-table tbody tr:nth-child(even) td {
    background: #EEF5FF !important;
}

.custom-table tbody tr:nth-child(odd) td {
    background: #FFFFFF !important;
}

.custom-table tbody tr:last-child td {
    border-bottom: none;
}

.custom-table td.num {
    text-align: right;
    white-space: nowrap;
}

.custom-table td.text-center {
    text-align: center;
    white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# Main pane container
# =========================================================
main_pane = st.container()

with main_pane:
    st.markdown('<div id="main-pane-marker"></div>', unsafe_allow_html=True)

    # =========================
    # Header
    # =========================
    logo_path = Path("logo_paip.png")
    col_logo, col_title = st.columns([1.1, 4.9], gap="medium")

    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), width=140)

    with col_title:
        st.markdown(
            """
            <div class="paip-title">PAIP Water Bill Calculator</div>
            <div class="paip-subtitle">Pahang Tariff Calculator</div>
            <div class="paip-description">
                Calculate estimated monthly water bill based on Pahang tariff categories.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    # =========================
    # Calculator section
    # =========================
    st.markdown('<div class="section-title">Bill Calculator</div>', unsafe_allow_html=True)

    with st.form("bill_calculator_form"):
        category = st.selectbox(
            "Select tariff category",
            options=list(TARIFFS.keys())
        )

        usage = st.number_input(
            "Water usage (m³)",
            min_value=0.0,
            step=1.0,
            value=0.0,
            help="Enter the total monthly water consumption in cubic meters (m³)."
        )

        submitted = st.form_submit_button("Calculate Bill", use_container_width=True)

    # =========================
    # Results section
    # =========================
    if submitted:
        try:
            result = calculate_bill(category, usage)

            st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Result Summary</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2, gap="medium")

            with col1:
                st.markdown(
                    f"""
                    <div class="metric-box">
                        <div class="metric-label">Water Usage</div>
                        <div class="metric-value">{usage:,.2f} m³</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col2:
                st.markdown(
                    f"""
                    <div class="metric-box">
                        <div class="metric-label">Total Bill</div>
                        <div class="metric-value">{format_rm(result["total"])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown(
                f"""
                <div class="final-amount-box">
                    <div class="final-amount-label">Final Amount Payable</div>
                    <div class="final-amount-value">{format_rm(result["total"])}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Bill Breakdown</div>', unsafe_allow_html=True)

            breakdown_df = pd.DataFrame(result["breakdown"])
            st.markdown(
                render_html_table(
                    breakdown_df,
                    money_columns=["Rate (RM/m³)", "Charge (RM)"],
                    number_columns=["Usage (m³)"]
                ),
                unsafe_allow_html=True
            )

            st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Summary Details</div>', unsafe_allow_html=True)

            st.write(f"**Category:** {category}")
            st.write(f"**Minimum Charge:** {format_rm(result['minimum_charge'])}")

            if result["minimum_applied"]:
                st.warning("Minimum charge applied because calculated amount is below the minimum charge.")
            else:
                st.info("Minimum charge not applied.")

        except ValueError as e:
            st.error(str(e))

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    # =========================
    # Tariff reference
    # =========================
    with st.expander("View Pahang tariff reference"):
        tariff_reference_df = pd.DataFrame([
            ["DOMESTIK (METER INDIVIDU)", "0–20 m³", 0.80, 8.00],
            ["DOMESTIK (METER INDIVIDU)", ">20–35 m³", 1.52, 8.00],
            ["DOMESTIK (METER INDIVIDU)", ">35 m³", 1.98, 8.00],
            ["DOMESTIK (METER PUKAL)", "Flat Rate", 1.72, 17.20],
            ["BUKAN DOMESTIK", "0–35 m³", 2.02, 30.00],
            ["BUKAN DOMESTIK", ">35 m³", 2.67, 30.00],
            ["RUMAH IBADAT DAN INSTITUSI KEBAJIKAN", "Flat Rate", 0.82, 8.20],
            ["PERKAPALAN", "Flat Rate", 8.03, 80.30],
            ["PUSAT DATA", "Flat Rate", 5.33, 53.30],
        ], columns=["Category", "Block", "Rate (RM/m³)", "Minimum Charge (RM)"])

        st.markdown(
            render_html_table(
                tariff_reference_df,
                money_columns=["Rate (RM/m³)", "Minimum Charge (RM)"]
            ),
            unsafe_allow_html=True
        )