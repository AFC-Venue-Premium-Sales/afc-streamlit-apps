import time
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import importlib

# Import live data
try:
    tjt_hosp_api = importlib.import_module("tjt_hosp_api")
    filtered_df_without_seats = getattr(tjt_hosp_api, "filtered_df_without_seats", None)
    if filtered_df_without_seats is None:
        raise ImportError("filtered_df_without_seats is not available in tjt_hosp_api.")
except ImportError as e:
    st.error(f"Error importing tjt_hosp_api: {e}")
    filtered_df_without_seats = pd.DataFrame(columns=["CreatedBy", "Price", "CreatedOn", "ExecType", "KickOffEventStart", "Fixture Name"])

# Targets data
targets_data = pd.DataFrame({
    "Month": ["December", "January", "February", "March", "April", "May"],
    "Year": [2024, 2025, 2025, 2025, 2025, 2025],
    "bgardiner": [155000, 155000, 135000, 110000, 90000, 65000],
    "dcoppin": [155000, 155000, 135000, 110000, 90000, 65000],
    "jedwards": [155000, 155000, 135000, 110000, 90000, 65000],
    "MillieS": [155000, 155000, 135000, 110000, 90000, 65000],
    "dmontague": [155000, 155000, 135000, 110000, 90000, 65000],
    "MeganS": [42500, 42500, 36500, 30500, 24500, 18500],
    "BethNW": [42500, 42500, 36500, 30500, 24500, 18500],
    "HayleyA": [42500, 42500, 36500, 30500, 24500, 18500],
    "jmurphy": [35000, 35000, 30000, 25000, 20000, 15000],
    "BenT": [35000, 35000, 30000, 25000, 20000, 15000],
    "ayildirim": [19000, 19000, 16500, 14000, 11000, 8500],
}).set_index(["Month", "Year"])

# Load budget targets
def load_budget_targets():
    file_path = os.path.join(os.path.dirname(__file__), 'budget_target_2425.xlsx')
    try:
        budget_df = pd.read_excel(file_path)
        budget_df.columns = budget_df.columns.str.strip()
        return budget_df
    except FileNotFoundError:
        st.error(f"Budget file not found at {file_path}. Ensure it is correctly placed.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred while loading the budget file: {e}")
        return pd.DataFrame()

budget_df = load_budget_targets()

# Calculate monthly progress
def calculate_monthly_progress(data, start_date, end_date):
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)
    filtered_data = data[
        (data["CreatedOn"] >= pd.to_datetime(start_date)) &
        (data["CreatedOn"] <= pd.to_datetime(end_date))
    ]

    current_month = start_date.strftime("%B")
    current_year = start_date.year

    if (current_month, current_year) not in targets_data.index:
        return None

    progress = (
        filtered_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )

    monthly_targets = targets_data.loc[(current_month, current_year)]

    progress_data = pd.DataFrame({
        "Premium Executive": progress.index,
        "Current Revenue": progress.values,
        "Target": monthly_targets.values,
        "% Sold (Numeric)": (progress / monthly_targets * 100).round(2),
        "Today's Date": datetime.now().strftime("%d/%m/%Y")
    }).reset_index(drop=True)

    return progress_data

# Render Monthly Progress Table
def render_monthly_progress_table(progress_data):
    table_html = """
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 16px;
            text-align: left;
        }
        th, td {
            padding: 12px;
            border: 1px solid #ddd;
        }
        th {
            background-color: #f4f4f4;
            font-weight: bold;
        }
        .green { color: green; }
        .orange { color: orange; }
        .red { color: red; }
    </style>
    <table>
        <tr>
            <th>Premium Executive</th>
            <th>Current Revenue</th>
            <th>Target</th>
            <th>% Sold</th>
        </tr>
    """
    for _, row in progress_data.iterrows():
        percent_class = (
            "green" if float(row["% Sold (Numeric)"]) >= 80
            else "orange" if float(row["% Sold (Numeric)"]) >= 50
            else "red"
        )
        table_html += f"""
        <tr>
            <td>{row['Premium Executive']}</td>
            <td>£{row['Current Revenue']:,.0f}</td>
            <td>£{row['Target']:,.0f}</td>
            <td class="{percent_class}">{row['% Sold (Numeric)']:.2f}%</td>
        </tr>
        """
    table_html += "</table>"
    return table_html

# Next fixture information
def get_next_fixture(data, budget_df):
    data["KickOffEventStart"] = pd.to_datetime(data["KickOffEventStart"], errors="coerce")
    today = datetime.now()
    next_fixture = data[data["KickOffEventStart"] > today].sort_values("KickOffEventStart").head(1)

    if next_fixture.empty:
        return None, None, None

    fixture_name = next_fixture["Fixture Name"].iloc[0]
    fixture_date = next_fixture["KickOffEventStart"].iloc[0]
    budget_target = budget_df[budget_df["Fixture Name"] == fixture_name]["Budget Target"].values[0]

    return fixture_name, fixture_date, budget_target

# Auto-refresh functionality
def auto_refresh():
    st.experimental_set_query_params(refresh=str(int(time.time())))
    current_time = datetime.now().strftime('%H:%M:%S')
    return current_time

# Main dashboard
def run_dashboard():
    st.set_page_config(page_title="Hospitality Leadership Board", layout="wide")
    st.title("Arsenal Hospitality Leadership Board")

    # Sidebar
    st.sidebar.markdown("### Filter Options")
    start_date = st.sidebar.date_input("Start Date", value=datetime.now().replace(day=1))
    end_date = st.sidebar.date_input("End Date", value=datetime.now())

    # Auto-refresh
    refresh_time = auto_refresh()

    st.sidebar.markdown(
        f"""
        <div style="
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 5px;
            padding: 10px;
            margin-top: 20px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #155724;
            text-align: center;
        ">
            <strong>Latest Data Update:</strong> {refresh_time}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Next Fixture
    fixture_name, fixture_date, budget_target = get_next_fixture(filtered_df_without_seats, budget_df)
    if fixture_name:
        days_to_fixture = (fixture_date - datetime.now()).days
        st.sidebar.markdown(
            f"""
            <div style="
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                text-align: center;
            ">
                <h4 style="color: #0047AB;">🏟️ Next Fixture</h4>
                <p><strong>{fixture_name}</strong></p>
                <p>⏳ <strong>{days_to_fixture} days</strong></p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown("**No upcoming fixtures found.**")

    # Monthly Progress
    st.markdown("<h3 style='color:#b22222;'>Monthly Progress</h3>", unsafe_allow_html=True)
    monthly_progress = calculate_monthly_progress(filtered_df_without_seats, start_date, end_date)

    if monthly_progress is None or monthly_progress.empty:
        st.warning("Targets are not available for the selected dates.")
    else:
        st.markdown(render_monthly_progress_table(monthly_progress), unsafe_allow_html=True)

if __name__ == "__main__":
    run_dashboard()
