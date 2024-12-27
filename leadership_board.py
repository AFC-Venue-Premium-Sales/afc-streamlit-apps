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
        raise
    except Exception as e:
        st.error(f"An error occurred while loading the budget file: {e}")
        raise

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
        return None, []

    progress = (
        filtered_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )

    sales_made = filtered_data["CreatedBy"].unique()

    monthly_targets = targets_data.loc[(current_month, current_year)]

    progress_data = pd.DataFrame({
        "Premium Executive": progress.index,
        "Current Revenue": progress.values,
        "Target": monthly_targets.values,
        "% Sold (Numeric)": (progress / monthly_targets * 100).round(2),  # Keep a numeric column for sorting
    }).reset_index(drop=True)

    # Format columns for display
    progress_data["Current Revenue"] = progress_data["Current Revenue"].apply(lambda x: f"£{x:,.0f}")
    progress_data["Target"] = progress_data["Target"].apply(lambda x: f"£{x:,.0f}")

    # Add conditional colors to % Sold
    def style_percent(value):
        if value >= 80:
            return f"<span style='color: green;'>{value:.2f}%</span>"
        elif 50 <= value < 80:
            return f"<span style='color: orange;'>{value:.2f}%</span>"
        else:
            return f"<span style='color: red;'>{value:.2f}%</span>"

    progress_data["% Sold"] = progress_data["% Sold (Numeric)"].apply(style_percent)

    # Sort by the numeric % Sold column
    progress_data = progress_data.sort_values(by="% Sold (Numeric)", ascending=False)

    return progress_data.drop(columns=["% Sold (Numeric)"]), sales_made

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
    st.set_page_config(page_title="Hospitality Leadership Board", layout="wide")
    st.title("Arsenal Hospitality Leadership Board")

    # Sidebar
    st.sidebar.markdown("### Filter Options")
    start_date = st.sidebar.date_input("Start Date", value=datetime.now().replace(day=1))
    end_date = st.sidebar.date_input("End Date", value=datetime.now())

    # Expander for instructions
    with st.sidebar.expander("How Date Filters and Targets Work"):
        st.write("""
        - The **date filter** allows you to view sales progress for a specific time period.
        - Each month has predefined sales targets for every Premium Executive.
        - Selecting a range of dates aggregates the total revenue generated during that period.
        - The leaderboard updates in real-time based on the filtered dates.
        """)

    # Next Fixture in Sidebar
    fixture_name, fixture_date, budget_target = get_next_fixture(filtered_df_without_seats, budget_df)
    if fixture_name:
        days_to_fixture = (fixture_date - datetime.now()).days
        fixture_revenue = filtered_df_without_seats[
            (filtered_df_without_seats["KickOffEventStart"] == fixture_date)
        ]["Price"].sum()
        st.sidebar.markdown(
            f"""
            <div style="
                background-color: #f7f7f7;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                font-family: Arial, sans-serif;
            ">
                <h4 style="color: #0047AB; font-size: 18px; margin-bottom: 10px;">🏟️ Next Fixture</h4>
                <p style="font-size: 16px; margin: 5px 0; font-weight: bold;">{fixture_name}</p>
                
                <h4 style="color: #0047AB; font-size: 18px; margin-top: 15px;">⏳ Days to Fixture</h4>
                <p style="font-size: 16px; margin: 5px 0; font-weight: bold;">{days_to_fixture} days</p>
                
                <h4 style="color: #0047AB; font-size: 18px; margin-top: 15px;">🎯 Budget Target Achieved</h4>
                <p style="font-size: 16px; color: green; margin: 5px 0; font-weight: bold;">{round((fixture_revenue / budget_target) * 100, 2)}%</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    else:
        st.sidebar.markdown("**No upcoming fixtures found.**")

    # Monthly Progress
    st.markdown("<h3 style='color:#b22222;'>Monthly Progress</h3>", unsafe_allow_html=True)
    monthly_progress, sales_made = calculate_monthly_progress(filtered_df_without_seats, start_date, end_date)

    if monthly_progress is None:
        st.warning("Targets are not available for the selected dates.")
    else:
        st.markdown(monthly_progress.to_html(escape=False, index=False), unsafe_allow_html=True)

if __name__ == "__main__":
    run_dashboard()
