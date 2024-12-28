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

# Calculate total sales (including website)
def calculate_total_sales(data):
    total_sales = data["TotalPrice"].sum()
    return total_sales

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

    # Additional metrics
    num_transactions = (
        filtered_data.groupby("CreatedBy")["Price"]
        .count()
        .reindex(targets_data.columns, fill_value=0)
    )
    avg_revenue_per_transaction = (progress / num_transactions).fillna(0)

    top_package = (
        filtered_data.groupby(["CreatedBy", "Package Name"])["Price"]
        .sum()
        .reset_index()
        .sort_values(by=["CreatedBy", "Price"], ascending=[True, False])
        .groupby("CreatedBy").first()["Package Name"]
        .reindex(targets_data.columns, fill_value="None")
    )

    variance_from_target = (monthly_targets - progress).fillna(0)

    total_sales = progress.sum()
    revenue_percent_of_total = (progress / total_sales * 100).fillna(0)

    # Build progress data
    progress_data = pd.DataFrame({
        "Premium Executive": progress.index,
        "Current Revenue": progress.values,
        "Target": monthly_targets.values,
        "Variance": variance_from_target.values,
        "% Sold (Numeric)": (progress / monthly_targets * 100).round(0),
        "Transactions": num_transactions.values,
        "Avg Revenue/Transaction": avg_revenue_per_transaction.values,
        "Top-Selling Package": top_package.values,
        "Revenue % of Total": revenue_percent_of_total.round(1).values,
    }).reset_index(drop=True)

    # Format columns for display
    progress_data["Current Revenue"] = progress_data["Current Revenue"].apply(lambda x: f"£{x:,.0f}")
    progress_data["Target"] = progress_data["Target"].apply(lambda x: f"£{x:,.0f}")
    progress_data["Variance"] = progress_data["Variance"].apply(lambda x: f"£{x:,.0f}")
    progress_data["Avg Revenue/Transaction"] = progress_data["Avg Revenue/Transaction"].apply(lambda x: f"£{x:,.0f}")
    progress_data["Revenue % of Total"] = progress_data["Revenue % of Total"].apply(lambda x: f"{x:.1f}%")

    # Add conditional colors to % Sold
    def style_percent(value):
        if value >= 80:
            return f"<span style='color: green;'>{value:.0f}%</span>"
        elif 50 <= value < 80:
            return f"<span style='color: orange;'>{value:.0f}%</span>"
        else:
            return f"<span style='color: red;'>{value:.0f}%</span>"

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


def generate_scrolling_messages(data, budget_df):
    # Latest Sale
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)
    latest_sale = data.sort_values(by="CreatedOn", ascending=False).head(1)

    if not latest_sale.empty:
        source = latest_sale["SaleLocation"].iloc[0]
        latest_sale_message = (
            f"{int(latest_sale['Seats'].iloc[0])} seat(s) x {latest_sale['Package Name'].iloc[0]} "
            f"for {latest_sale['Fixture Name'].iloc[0]} sold via {source} @ £{latest_sale['TotalPrice'].iloc[0]:,.2f}"
        )
    else:
        latest_sale_message = "No recent sales to display."

    # Next Fixture
    fixture_name, fixture_date, budget_target = get_next_fixture(data, budget_df)
    if fixture_name:
        days_to_fixture = (fixture_date - datetime.now()).days
        fixture_revenue = data[data["KickOffEventStart"] == fixture_date]["Price"].sum()
        remaining_budget = budget_target - fixture_revenue
        next_fixture_message = (
            f"Next Fixture: {fixture_name} in {days_to_fixture} days. Remaining Budget: £{remaining_budget:,.2f}."
        )
    else:
        next_fixture_message = "No upcoming fixtures to display."

    # Top Fixture of the Day
    today_sales = data[data["CreatedOn"].dt.date == datetime.now().date()]
    if not today_sales.empty:
        top_fixture = (
            today_sales.groupby("Fixture Name")["Price"].sum().idxmax()
        )
        top_fixture_revenue = today_sales.groupby("Fixture Name")["Price"].sum().max()
        top_fixture_message = f"Top Fixture Today: {top_fixture} with £{top_fixture_revenue:,.2f} generated."
    else:
        top_fixture_message = "No sales recorded today."

    # Top Premium Executive of the Day
    if not today_sales.empty:
        top_executive = (
            today_sales.groupby("CreatedBy")["Price"].sum().idxmax()
        )
        top_executive_revenue = today_sales.groupby("CreatedBy")["Price"].sum().max()
        top_executive_message = f"Top Seller Today: {top_executive} with £{top_executive_revenue:,.2f} generated."
    else:
        top_executive_message = "No Premium Executive sales recorded today."

    # Combine all messages
    return f"{latest_sale_message} | {next_fixture_message} | {top_fixture_message} | {top_executive_message}"


# Get the latest sale made
def get_latest_sale(data):
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)
    latest_sale = data.sort_values(by="CreatedOn", ascending=False).head(1)

    if not latest_sale.empty:
        source = latest_sale["SaleLocation"].iloc[0]
        sale_details = {
            "fixture": latest_sale["Fixture Name"].iloc[0],
            "package": latest_sale["Package Name"].iloc[0],
            "price": latest_sale["TotalPrice"].iloc[0],
            "seats": latest_sale["Seats"].iloc[0],
            "created_by": latest_sale["CreatedBy"].iloc[0] if source.lower() == "moto sale team" else None,
            "source": source,
            "date": latest_sale["CreatedOn"].iloc[0].strftime("%d %b %Y %H:%M:%S"),
        }
        return sale_details
    return None

# Auto-refresh functionality with logging
def auto_refresh():
    refresh_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp
    
    if "refresh_count" not in st.session_state:
        st.session_state["refresh_count"] = 0

    st.session_state["refresh_count"] += 1
    st.session_state["refresh_log"] = st.session_state.get("refresh_log", [])
    st.session_state["refresh_log"].append(f"Auto-refresh triggered at {refresh_time}, Count: {st.session_state['refresh_count']}")
    
    st_autorefresh(interval=120 * 1000, key="auto_refresh")  # Auto-refresh every 2 minutes
    
    st.sidebar.text(f"Refresh Count: {st.session_state['refresh_count']}")
    return refresh_time

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

    # Auto-refresh
    refresh_time = auto_refresh()  # Auto-refreshes every 2 minutes

    # Display refresh message in the sidebar
    st.sidebar.markdown(
        f"""
        <div style="
            background-color: #fff0f0;
            border: 1px solid #E41B17;
            border-radius: 5px;
            padding: 10px;
            margin-top: 20px;
            margin-bottom: 20px;
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
    
    # Total Sales Section
    total_sales = calculate_total_sales(filtered_df_without_seats)
    st.sidebar.markdown(
        f"""
        <div style="
            background-color: #fff0f0;
            border: 1px solid #E41B17;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            text-align: center;
        ">
            <h4 style="color: #0047AB; font-size: 18px;">🛒 Total Sales</h4>
            <p><strong>Overall Sales Since Go Live: \u00a3{total_sales:,.0f}</strong></p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Premium Monthly Progress
    total_revenue, total_target, progress_percentage = calculate_overall_progress(filtered_df_without_seats, start_date, end_date)
    if total_target == 0:
        st.sidebar.markdown(
            "<div style='color: red; font-weight: bold;'>Selected date range is out of bounds for available targets.</div>",
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            f"""
            <div style="
                background-color: #fff0f0;
                border: 1px solid #E41B17;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                text-align: center;
            ">
                <h4 style="color: #0047AB; font-size: 18px;">📊 Premium Monthly Progress</h4>
                <p><strong>Total Revenue: \u00a3{total_revenue:,.0f} ({start_date.strftime("%B")})</strong></p>
                <p><strong>Total Target: \u00a3{total_target:,.0f}</strong></p>
                <p>🌟 <strong>Progress Achieved: {progress_percentage:.0f}%</strong></p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Next Fixture in Sidebar
    fixture_name, fixture_date, budget_target = get_next_fixture(filtered_df_without_seats, budget_df)
    if fixture_name:
        days_to_fixture = (fixture_date - datetime.now()).days
        fixture_revenue = filtered_df_without_seats[
            (filtered_df_without_seats["KickOffEventStart"] == fixture_date)
        ]["Price"].sum()
        budget_achieved = round((fixture_revenue / budget_target) * 100, 2)

        st.sidebar.markdown(
            f"""
            <div style="
                background-color: #fff0f0;
                border: 1px solid #E41B17;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                text-align: center;
            ">
                <h4 style="color: #0047AB; font-size: 18px;">🏟️ Next Fixture</h4>
                <p style="font-size: 16px; font-weight: bold;">{fixture_name}</p>
                <p>⏳ <strong>{days_to_fixture} days</strong></p>
                <p>🎯 <strong>Budget Target Achieved:</strong> <strong>{budget_achieved}%</strong></p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown("**No upcoming fixtures found.**")

    # Monthly Progress Table
    monthly_progress, sales_made = calculate_monthly_progress(filtered_df_without_seats, start_date, end_date)

    if monthly_progress is not None:
        st.markdown("<h3 style='color:#b22222; text-align:center;'>Monthly Target Leaderboard</h3>", unsafe_allow_html=True)
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


# Scrolling message section
    scrolling_message = generate_scrolling_messages(filtered_df_without_seats, budget_df)

    st.markdown(
        f"""
        <div style="
            overflow: hidden;
            white-space: nowrap;
            width: 100%;
            background-color: #E57373; /* Lighter Arsenal Red */
            color: white;
            padding: 10px 15px;
            border-radius: 15px;
            font-family: 'Roboto', Arial, sans-serif;
            font-size: 18px;
            font-weight: 600;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
            letter-spacing: 0.5px;
        ">
            <marquee behavior="scroll" direction="left" scrollamount="3">
                {scrolling_message}
            </marquee>
        </div>
        """,
        unsafe_allow_html=True

    )

# # Latest Sale Information
#     latest_sale = get_latest_sale(filtered_df_without_seats)
#     if latest_sale:
#         if latest_sale["source"].lower() == "hospitality website":
#             st.markdown(
#                 f"""
#                 <div style="
#                     background-color: #fff0f0;
#                     border: 1px solid #cfe2ff;
#                     border-radius: 8px;
#                     padding: 15px;
#                     margin-top: 20px;
#                     font-family: Arial, sans-serif;
#                     font-size: 16px;
#                     color: #084298;
#                     text-align: center;
#                 ">
#                     <strong>Latest Sale:</strong> Via Website - <strong>{latest_sale["seats"]} Seats Sold</strong> 
#                     x <strong>{latest_sale["package"]}</strong> for <strong>{latest_sale["fixture"]}</strong> 
#                     @ <strong>£{latest_sale["price"]:,.2f}</strong> on <strong>{latest_sale["date"]}</strong>.
#                 </div>
#                 """,
#                 unsafe_allow_html=True
#             )
#         else:
#             st.markdown(
#                 f"""
#                 <div style="
#                     background-color: #fff0f0;
#                     border: 1px solid #cfe2ff;
#                     border-radius: 8px;
#                     padding: 15px;
#                     margin-top: 20px;
#                     font-family: Arial, sans-serif;
#                     font-size: 16px;
#                     color: #084298;
#                     text-align: center;
#                 ">
#                     <strong>Latest Sale:</strong> Moto sale made by <strong>{latest_sale["created_by"]}</strong> 
#                     for <strong>{latest_sale["package"]}</strong> in <strong>{latest_sale["fixture"]}</strong> 
#                     totaling <strong>£{latest_sale["price"]:,.2f}</strong> with <strong>{latest_sale["seats"]}</strong> seats 
#                     on <strong>{latest_sale["date"]}</strong>.
#                 </div>
#                 """,
#                 unsafe_allow_html=True
#             )
#     else:
#         st.warning("No new sales recorded.")

if __name__ == "__main__":
    run_dashboard()
