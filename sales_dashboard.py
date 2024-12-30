import time
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import importlib
from streamlit_autorefresh import st_autorefresh

# Import live data and reload the module
def load_live_data():
    try:
        tjt_hosp_api = importlib.reload(importlib.import_module("tjt_hosp_api"))
        filtered_df_without_seats = getattr(tjt_hosp_api, "filtered_df_without_seats", None)
        if filtered_df_without_seats is None:
            raise ImportError("filtered_df_without_seats is not available in tjt_hosp_api.")
        return filtered_df_without_seats
    except ImportError as e:
        st.error(f"Error reloading tjt_hosp_api: {e}")
        return pd.DataFrame(columns=["CreatedBy", "Price", "CreatedOn", "SaleLocation", "KickOffEventStart", "Fixture Name", "Package Name", "TotalPrice", "Seats"])

# Load data
filtered_df_without_seats = load_live_data()

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

# Calculate overall progress
def calculate_overall_progress(data, start_date, end_date):
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)
    filtered_data = data[
        (data["CreatedOn"] >= pd.to_datetime(start_date)) &
        (data["CreatedOn"] <= pd.to_datetime(end_date))
    ]

    total_revenue = filtered_data["Price"].sum()
    try:
        total_target = targets_data.loc[(start_date.strftime("%B"), start_date.year)].sum()
        progress_percentage = (total_revenue / total_target) * 100 if total_target > 0 else 0
    except KeyError:
        total_target = 0
        progress_percentage = 0

    return total_revenue, total_target, progress_percentage

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

    # Count today's sales for each executive
    today = datetime.now().date()
    today_sales = filtered_data[filtered_data["CreatedOn"].dt.date == today]
    sales_count = (
        today_sales.groupby("CreatedBy")["Price"].count()
        .reindex(targets_data.columns, fill_value=0)
    )

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
        "Variance": (progress - monthly_targets).values,
        "% Sold (Numeric)": (progress / monthly_targets * 100).round(0),
        "Today's Sales": sales_count.values  # Add today's sales column
    }).reset_index(drop=True)

    # Format columns for display
    progress_data["Current Revenue"] = progress_data["Current Revenue"].apply(lambda x: f"£{x:,.0f}")
    progress_data["Target"] = progress_data["Target"].apply(lambda x: f"£{x:,.0f}")
    progress_data["Variance"] = progress_data["Variance"].apply(lambda x: f"({abs(x):,.0f})" if x < 0 else f"{x:,.0f}")

    # Sort by % Sold (numeric) before styling
    progress_data = progress_data.sort_values(by="% Sold (Numeric)", ascending=False)

    # Add conditional box colors to % Sold
    def style_box_color(value):
        if value >= 80:
            return f"<div style='background-color: green; color: white; padding: 5px;'>{value:.0f}%</div>"
        elif 50 <= value < 80:
            return f"<div style='background-color: orange; color: white; padding: 5px;'>{value:.0f}%</div>"
        else:
            return f"<div style='background-color: red; color: white; padding: 5px;'>{value:.0f}%</div>"

    # Apply styling to the sorted data
    progress_data["% Sold"] = progress_data["% Sold (Numeric)"].apply(style_box_color)

    # Drop numeric % Sold column after sorting and styling
    progress_data = progress_data.drop(columns=["% Sold (Numeric)"])

    return progress_data

# Corrected Next Fixture Logic
def get_next_fixture(data, budget_df):
    data["KickOffEventStart"] = pd.to_datetime(data["KickOffEventStart"], errors="coerce", dayfirst=True)

    future_data = data[data["KickOffEventStart"] > datetime.now()]
    if future_data.empty:
        return None, None, None

    next_fixture = future_data.sort_values("KickOffEventStart").iloc[0]
    fixture_name = next_fixture["Fixture Name"]
    fixture_date = next_fixture["KickOffEventStart"]

    budget_target_row = budget_df[budget_df["Fixture Name"] == fixture_name]
    budget_target = budget_target_row["Budget Target"].iloc[0] if not budget_target_row.empty else 0

    return fixture_name, fixture_date, budget_target

# Main dashboard
def run_dashboard():
    st.set_page_config(page_title="Hospitality Leadership Board", layout="wide")
    st.markdown(
    """
    <div style="text-align: center; margin-top: 20px;">
        <h1 style="color: #2c3e50;">💎 Arsenal Premium Sales 💎</h1>
    </div>
    """,
    unsafe_allow_html=True
    )

    # Sidebar
    st.sidebar.markdown("### Date Range Filter")
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("Start Date", value=datetime.now().replace(day=1), label_visibility="collapsed")
    end_date = col2.date_input("End Date", value=datetime.now(), label_visibility="collapsed")

    # Monthly Progress Table
    monthly_progress = calculate_monthly_progress(filtered_df_without_seats, start_date, end_date)

    if monthly_progress is not None:
        st.markdown("<h3 style='color:#E41B17; text-align:center;'>Monthly Premium Leaderboard</h3>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                margin-top: 20px;
                margin-bottom: 20px;
            ">
                {monthly_progress.to_html(escape=False, index=False)}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("Monthly Progress data not available for the selected date range.")

    # Next Fixture Section
    next_fixture_name, next_fixture_date, next_budget_target = get_next_fixture(filtered_df_without_seats, budget_df)
    if next_fixture_name:
        days_to_fixture = (next_fixture_date - datetime.now()).days
        st.markdown(
            f"""
            <div style="
                background-color: #FAF3F3;
                border: 2px solid #E41B17;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 20px;
                text-align: center;
                font-family: Arial, sans-serif;
            ">
                <h4 style="color: #E41B17; font-size: 20px; font-weight: bold;">🏟️ Next Fixture</h4>
                <p style="font-size: 16px; color: #0047AB; font-weight: bold;">{next_fixture_name}</p>
                <p style="font-size: 16px; color: #0047AB;">⏳ Days to Fixture:</p>
                <p style="font-size: 18px; color: #0047AB; font-weight: bold;">{days_to_fixture} days</p>
                <p style="font-size: 16px; color: #0047AB;">🎯 Budget Target:</p>
                <p style="font-size: 18px; color: #0047AB; font-weight: bold;">£{next_budget_target:,.0f}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.warning("No upcoming fixtures found.")

if __name__ == "__main__":
    run_dashboard()
