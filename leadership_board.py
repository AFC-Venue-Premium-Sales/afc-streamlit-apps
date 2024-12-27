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
    filtered_df_without_seats = pd.DataFrame(columns=["CreatedBy", "Price", "PaymentTime", "ExecType", "KickOffEventStart", "Fixture Name"])

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
        raise
    except Exception as e:
        st.error(f"An error occurred while loading the budget file: {e}")
        raise

budget_df = load_budget_targets()

# Calculate monthly progress
def calculate_monthly_progress(data, month, year):
    data["PaymentTime"] = pd.to_datetime(data["PaymentTime"], errors="coerce")
    filtered_data = data[data["PaymentTime"].dt.month == month]

    progress = (
        filtered_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )

    monthly_targets = targets_data.loc[(datetime(year, month, 1).strftime("%B"), year)]

    progress_data = pd.DataFrame({
        "Member": progress.index,
        "Current Revenue": progress.values,
        "Target": monthly_targets.values,
        "% Sold": (progress / monthly_targets * 100).round(2),
    }).reset_index(drop=True)

    return progress_data.sort_values(by="% Sold", ascending=False)

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

# Main dashboard
def run_dashboard():
    st.title("Arsenal Hospitality Leadership Board")

    # Create two columns
    col1, col2 = st.columns(2)

    # Left column: Monthly progress
    with col1:
        st.markdown("<h3 style='color:#b22222;'>Monthly Progress</h3>", unsafe_allow_html=True)

        current_month = datetime.now().month
        current_year = datetime.now().year
        monthly_progress = calculate_monthly_progress(filtered_df_without_seats, current_month, current_year)

        st.dataframe(
            monthly_progress.style.format({
                "Current Revenue": "£{:,.0f}",
                "Target": "£{:,.0f}",
                "% Sold": "{:.2f}%"
            }).background_gradient(subset=["% Sold"], cmap="Reds"),
            use_container_width=True
        )

    # Right column: Next fixture countdown
    with col2:
        st.markdown("<h3 style='color:#b22222;'>Next Fixture Countdown</h3>", unsafe_allow_html=True)

        fixture_name, fixture_date, budget_target = get_next_fixture(filtered_df_without_seats, budget_df)
        if fixture_name:
            days_to_fixture = (fixture_date - datetime.now()).days
            total_revenue = filtered_df_without_seats["Price"].sum()

            st.metric("Fixture Name", fixture_name)
            st.metric("Days to Fixture", f"{days_to_fixture} days")
            st.metric("Budget Target Achieved", f"{(total_revenue / budget_target) * 100:.2f}%")
        else:
            st.markdown("No upcoming fixtures found.")

if __name__ == "__main__":
    run_dashboard()
