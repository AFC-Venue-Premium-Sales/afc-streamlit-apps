import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import importlib
from st_aggrid import AgGrid, GridOptionsBuilder

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
        raise
    except Exception as e:
        st.error(f"An error occurred while loading the budget file: {e}")
        raise

budget_df = load_budget_targets()

# Calculate monthly progress
def calculate_monthly_progress(data, start_date, end_date):
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce")
    filtered_data = data[
        (data["CreatedOn"] >= pd.to_datetime(start_date)) &
        (data["CreatedOn"] <= pd.to_datetime(end_date))
    ]

    current_month = start_date.strftime("%B")
    current_year = start_date.year

    # Check if the month/year combination exists in targets
    if (current_month, current_year) not in targets_data.index:
        return None  # Return None if no targets found

    progress = (
        filtered_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )

    monthly_targets = targets_data.loc[(current_month, current_year)]

    progress_data = pd.DataFrame({
        "Premium Executive": progress.index,  # Rename column
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

    # Sidebar: Date range filter
    st.sidebar.markdown("### Filter by Date")
    start_date = st.sidebar.date_input("Start Date", value=datetime.now().replace(day=1))
    end_date = st.sidebar.date_input("End Date", value=datetime.now())

    # Monthly progress
    st.markdown("<h3 style='color:#b22222;'>Monthly Progress</h3>", unsafe_allow_html=True)
    monthly_progress = calculate_monthly_progress(filtered_df_without_seats, start_date, end_date)

    if monthly_progress is None:
        st.warning("Targets are not available for the selected dates.")
    else:
        # AgGrid Configuration
        gb = GridOptionsBuilder.from_dataframe(monthly_progress)
        gb.configure_pagination(paginationAutoPageSize=True)  # Add pagination
        gb.configure_side_bar()  # Enable sidebar
        gb.configure_default_column(editable=False, groupable=True)  # Columns config
        grid_options = gb.build()

        # Render AgGrid
        AgGrid(
            monthly_progress,
            gridOptions=grid_options,
            height=400,
            width='100%',
            theme="material"
        )

    # Next fixture countdown
    st.markdown("<h3 style='color:#b22222;'>Next Fixture Countdown</h3>", unsafe_allow_html=True)
    fixture_name, fixture_date, budget_target = get_next_fixture(filtered_df_without_seats, budget_df)
    if fixture_name:
        days_to_fixture = (fixture_date - datetime.now()).days
        fixture_revenue = filtered_df_without_seats[
            (filtered_df_without_seats["KickOffEventStart"] == fixture_date)
        ]["Price"].sum()

        st.metric("Fixture Name", fixture_name)
        st.metric("Days to Fixture", f"{days_to_fixture} days")
        st.metric("Budget Target Achieved", f"{(fixture_revenue / budget_target) * 100:.2f}%")
    else:
        st.markdown("No upcoming fixtures found.")

if __name__ == "__main__":
    run_dashboard()
