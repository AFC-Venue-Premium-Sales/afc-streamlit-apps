import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import importlib
import os

# Import live data from `tjt_hosp_api`
try:
    tjt_hosp_api = importlib.import_module('tjt_hosp_api')
    filtered_df_without_seats = getattr(tjt_hosp_api, 'filtered_df_without_seats', None)
    if filtered_df_without_seats is None:
        raise ImportError("filtered_df_without_seats is not available in tjt_hosp_api.")
except ImportError as e:
    st.error(f"❌ Error importing tjt_hosp_api: {e}")
    filtered_df_without_seats = None

# Define monthly targets
monthly_targets = pd.DataFrame({
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

# Helper Functions
def calculate_metrics(filtered_data, targets, team_members, working_days_so_far, remaining_working_days):
    results = []
    for member in team_members:
        target = targets.get(member, 0)
        member_data = filtered_data[filtered_data["CreatedBy"] == member]
        current_revenue = member_data["Price"].sum()

        variance = current_revenue - target
        pace_per_day = current_revenue / working_days_so_far if working_days_so_far > 0 else 0
        projected_revenue = current_revenue + (pace_per_day * remaining_working_days)
        percent_sold = (current_revenue / target * 100) if target > 0 else 0

        results.append({
            "Member": member,
            "Current Revenue": current_revenue,
            "Target": target,
            "Variance": variance,
            "Pace per Day": pace_per_day,
            "Projected Revenue": projected_revenue,
            "% Sold": percent_sold,
        })

    return pd.DataFrame(results)

def display_sidebar_summary(filtered_data, budget_df):
    st.sidebar.header("📊 Summary for Today")
    today = datetime.now().date()
    filtered_data["PaymentTime"] = pd.to_datetime(filtered_data["PaymentTime"], format="%d-%m-%Y %H:%M", errors="coerce")
    today_data = filtered_data[filtered_data["PaymentTime"].dt.date == today]

    if today_data.empty:
        st.sidebar.warning("No sales data available for today.")
        st.sidebar.metric("Total Sales Today", "£0.00")
        st.sidebar.metric("Most Sold Game", "N/A")
        st.sidebar.metric("Most Sold Package", "N/A")
    else:
        total_sales_today = today_data["Price"].sum()
        st.sidebar.metric("Total Sales Today", f"£{total_sales_today:,.2f}")

        top_game = today_data.groupby("Fixture Name")["Price"].sum().idxmax()
        st.sidebar.metric("Most Sold Game", top_game)

        top_package = today_data.groupby("Package Name")["Price"].sum().idxmax()
        st.sidebar.metric("Most Sold Package", top_package)

    filtered_data["KickOffEventStart"] = pd.to_datetime(filtered_data["KickOffEventStart"], errors="coerce")
    next_fixtures = filtered_data[filtered_data["KickOffEventStart"] > datetime.now()].sort_values("KickOffEventStart")

    if next_fixtures.empty:
        st.sidebar.metric("Next Fixture", "N/A")
        st.sidebar.metric("Budget Target", "N/A")
    else:
        next_fixture = next_fixtures.iloc[0]
        next_fixture_name = next_fixture["Fixture Name"]
        budget_target_row = budget_df[budget_df["Fixture Name"] == next_fixture_name]
        next_budget_target = budget_target_row["Budget Target"].values[0] if not budget_target_row.empty else 0
        days_to_fixture = (next_fixture["KickOffEventStart"].date() - today).days

        st.sidebar.metric("Next Fixture", next_fixture_name)
        st.sidebar.metric("Budget Target", f"£{next_budget_target:,.2f}")
        st.sidebar.metric("Days to Fixture", f"{days_to_fixture} days")

# Main App
def run_app():
    st.title("AFC Sales Dashboard")

    with st.expander("ℹ️ About This Dashboard"):
        st.write("This dashboard provides real-time updates on sales performance.")
        st.write("**How to Use:** View metrics and performance insights.")

    if filtered_df_without_seats is None:
        st.error("No data available to display.")
        return

    budget_df = load_budget_targets()

    today = datetime.now()
    current_month = today.strftime("%B")
    current_year = today.year
    start_of_month = datetime(today.year, today.month, 1)

    # Handle end of month transition
    if today.month == 12:
        next_month_start = f"{today.year + 1}-01-01"
    else:
        next_month_start = f"{today.year}-{today.month + 1}-01"

    working_days_so_far = len(pd.date_range(start=start_of_month, end=today, freq="B"))
    remaining_working_days = len(pd.date_range(start=today + pd.Timedelta(days=1), end=next_month_start, freq="B"))

    try:
        targets = monthly_targets.loc[(current_month, current_year)].to_dict()
    except KeyError:
        st.error("No targets found for the current month and year.")
        return

    # Sidebar Filters
    st.sidebar.header("Filters")
    specified_users = ["bgardiner", "dcoppin", "jedwards", "MillieS", "dmontague", 
                       "MeganS", "BethNW", "HayleyA", "jmurphy", "BenT", "ayildirim"]
    selected_fixture = st.sidebar.multiselect("Filter by Fixture", options=filtered_df_without_seats["Fixture Name"].unique(),
                                              default=filtered_df_without_seats["Fixture Name"].unique())
    selected_date_range = st.sidebar.date_input("Date Range", value=(start_of_month, today))
    selected_users = st.sidebar.multiselect("Select Users", options=specified_users, default=specified_users)

    # Apply filters
    filtered_data = filtered_df_without_seats.copy()
    if selected_users:
        filtered_data = filtered_data[filtered_data["CreatedBy"].isin(selected_users)]
    if selected_fixture:
        filtered_data = filtered_data[filtered_data["Fixture Name"].isin(selected_fixture)]
    if selected_date_range:
        filtered_data = filtered_data[
            (pd.to_datetime(filtered_data["PaymentTime"], format="%d-%m-%Y %H:%M", errors="coerce") >= pd.to_datetime(selected_date_range[0])) &
            (pd.to_datetime(filtered_data["PaymentTime"], format="%d-%m-%Y %H:%M", errors="coerce") <= pd.to_datetime(selected_date_range[1]))
        ]

    # Display Sidebar Summary
    display_sidebar_summary(filtered_data, budget_df)

    # Team Members
    sales_team = ["bgardiner", "dcoppin", "jedwards", "MillieS", "dmontague"]
    services_team = ["MeganS", "BethNW", "HayleyA", "jmurphy", "BenT", "ayildirim"]

    # Calculate Metrics
    st.subheader("Sales Team")
    sales_metrics = calculate_metrics(filtered_data, targets, sales_team, working_days_so_far, remaining_working_days)
    st.dataframe(sales_metrics.style.format({
        "Current Revenue": "£{:,.2f}",
        "Target": "£{:,.2f}",
        "Variance": "£{:,.2f}",
        "Pace per Day": "£{:,.2f}",
        "Projected Revenue": "£{:,.2f}",
        "% Sold": "{:.2f}%",
    }))

    st.subheader("Services Team")
    services_metrics = calculate_metrics(filtered_data, targets, services_team, working_days_so_far, remaining_working_days)
    st.dataframe(services_metrics.style.format({
        "Current Revenue": "£{:,.2f}",
        "Target": "£{:,.2f}",
        "Variance": "£{:,.2f}",
        "Pace per Day": "£{:,.2f}",
        "Projected Revenue": "£{:,.2f}",
        "% Sold": "{:.2f}%",
    }))

    # Visualizations
    st.subheader("Team Progress")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(["Sales Team", "Services Team"], [sales_metrics["Current Revenue"].sum(), services_metrics["Current Revenue"].sum()], color=["blue", "green"])
    ax.axhline(sum(targets.values()), color="red", linestyle="--", label="Target")
    ax.set_title("Overall Team Progress")
    ax.set_ylabel("Revenue (£)")
    ax.legend()
    st.pyplot(fig)

if __name__ == "__main__":
    run_app()
