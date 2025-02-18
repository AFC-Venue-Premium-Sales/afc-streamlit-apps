import time
import os
import base64
import importlib
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

################################################################################
# 1. Load live sales data from tjt_hosp_api and merged inventory data
################################################################################

def load_live_data():
    """
    Dynamically reloads tjt_hosp_api and accesses filtered_df_without_seats.
    Returns a DataFrame of live hospitality sales data.
    """
    try:
        tjt_hosp_api = importlib.reload(importlib.import_module("tjt_hosp_api"))
        filtered_df_without_seats = getattr(tjt_hosp_api, "filtered_df_without_seats", None)

        if filtered_df_without_seats is None:
            raise ImportError("filtered_df_without_seats is not available in tjt_hosp_api.")
        return filtered_df_without_seats

    except ImportError as e:
        st.error(f"Error reloading tjt_hosp_api: {e}")
        return pd.DataFrame(columns=[
            "CreatedBy", "Price", "CreatedOn", "SaleLocation",
            "KickOffEventStart", "Fixture Name", "Package Name",
            "TotalPrice", "Seats"
        ])

def load_inventory_data():
    """
    Dynamically reloads tjt_inventory.py and runs get_inventory_data()
    to retrieve merged (events + stock) data. Returns a DataFrame.
    """
    try:
        tjt_inventory = importlib.reload(importlib.import_module("tjt_inventory"))
        if hasattr(tjt_inventory, "get_inventory_data"):
            return tjt_inventory.get_inventory_data()
        else:
            st.warning("No function 'get_inventory_data()' found in tjt_inventory.py")
            return pd.DataFrame()
    except ImportError as e:
        st.error(f"Error reloading tjt_inventory: {e}")
        return pd.DataFrame()

# ------------------------------------------------------------------------------
# NOTE: We comment out these two lines below so they DON'T run globally
# That way, data is instead re-loaded INSIDE run_dashboard() on each refresh.
# ------------------------------------------------------------------------------
filtered_df_without_seats = load_live_data()
df_inventory = load_inventory_data()

################################################################################
# 2. Additional Setup (Executives, Targets, Budget)
################################################################################

# Hardcoded monthly targets example
targets_data = pd.DataFrame({
    "Month": ["December", "January", "February", "March", "April", "May"],
    "Year": [2024, 2025, 2025, 2025, 2025, 2025],
    "bgardiner": [155000, 155000, 135000, 110000, 90000, 65000],
    "dcoppin":   [155000, 155000, 135000, 110000, 90000, 65000],
    "jedwards":  [155000, 155000, 135000, 110000, 90000, 65000],
    "millies":   [155000, 155000, 135000, 110000, 90000, 65000],
    "dmontague": [155000, 155000, 135000, 110000, 90000, 65000],
    # "MeganS":    [42500, 42500, 36500, 30500, 24500, 18500],
    # "BethNW":    [42500, 42500, 36500, 30500, 24500, 18500],
    # "HayleyA":   [42500, 42500, 36500, 30500, 24500, 18500],
    # "jmurphy":   [35000, 35000, 30000, 25000, 20000, 15000],
    # "BenT":      [35000, 35000, 30000, 25000, 20000, 15000],
}).set_index(["Month", "Year"])

valid_sales_executives =  ["dcoppin", "millies", "bgardiner", "dmontague", "jedwards"]
# valid_services_executives = ["HayleyA", "BethNW", "BenT", "jmurphy", "MeganS"]

def load_budget_targets():
    """
    Reads the external Excel file (budget_target_2425.xlsx) for fixture-based budgets.
    """
    file_path = os.path.join(os.path.dirname(__file__), 'budget_target_2425.xlsx')
    try:
        budget_df = pd.read_excel(file_path)
        budget_df.columns = budget_df.columns.str.strip()
        return budget_df
    except FileNotFoundError:
        st.error(f"Budget file not found at {file_path}. Ensure it is placed correctly.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading budget file: {e}")
        return pd.DataFrame()

budget_df = load_budget_targets()

################################################################################
# 3. Leaderboard Calculation & Rendering Functions
################################################################################

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_monthly_progress(data, start_date, end_date, targets_data):
    """
    Calculates the monthly progress for specified executives within a date range.
    Returns an HTML-styled leaderboard and an array of executives who made sales.
    """

    # ✅ Convert 'CreatedOn' to datetime safely
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)

    # ✅ Ensure correct filtering within the provided date range
    filtered_data = data[
        (data["CreatedOn"] >= start_date) & (data["CreatedOn"] <= end_date)
    ]

    # ✅ Extract current month and year
    current_month = start_date.strftime("%B")
    current_year = start_date.year

    # ✅ Ensure the month exists in targets_data before proceeding
    if (current_month, current_year) not in targets_data.index:
        return None, []

    # ✅ Calculate expected sales pace dynamically
    total_days_in_month = pd.Period(f"{current_year}-{start_date.month}").days_in_month
    days_elapsed = (end_date - start_date).days + 1
    expected_pace = (days_elapsed / total_days_in_month) * 100
    half_expected_pace = 0.5 * expected_pace

    # ✅ Set today’s start and end time correctly
    today_start = pd.to_datetime(datetime.now().date())  # Midnight today
    today_end = today_start + pd.Timedelta(days=1)  # Midnight next day

    # ✅ Ensure today's sales are correctly filtered
    today_sales_data = data[
        (data["CreatedOn"] >= today_start) & (data["CreatedOn"] < today_end)
    ]
    today_sales = (
        today_sales_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )

    # ✅ Calculate start of the current week (Monday)
    start_of_week = today_start - pd.Timedelta(days=today_start.weekday())

    # ✅ Ensure weekly sales include today
    weekly_sales_data = data[
        (data["CreatedOn"] >= start_of_week) & (data["CreatedOn"] < today_end)
    ]
    weekly_sales = (
        weekly_sales_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )

    # ✅ Calculate total progress per executive
    progress = (
        filtered_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )

    # ✅ Retrieve correct monthly targets
    monthly_targets = targets_data.loc[(current_month, current_year)]
    progress_percentage = (progress / monthly_targets * 100).round(0)

    # ✅ Replace NaN values with 0
    progress_data = pd.DataFrame({
        "Sales Exec": progress.index,
        "Today's Sales": today_sales.values,
        "Weekly Sales": weekly_sales.values,
        "Progress To Monthly Target (Numeric)": progress_percentage.values,
    }).fillna(0).reset_index(drop=True)

    # ✅ Map usernames to full names
    user_mapping = {
        "dmontague": "Dan",
        "bgardiner": "Bobby",
        "dcoppin": "David",
        "jedwards": "Joey",
        "millies": "Millie",
    }
    progress_data["Sales Exec"] = progress_data["Sales Exec"].map(user_mapping).fillna(progress_data["Sales Exec"])

    # ✅ Sort correctly, keeping TOTALS at the bottom
    progress_data = progress_data.sort_values(by="Progress To Monthly Target (Numeric)", ascending=False, na_position='last')

    # ✅ Add totals row at the end
    totals_row = {
        "Sales Exec": "TOTALS",
        "Today's Sales": today_sales.sum(),
        "Weekly Sales": weekly_sales.sum(),
        "Progress To Monthly Target (Numeric)": None
    }
    if any(totals_row.values()):  # Ensure totals_row is not empty or all-NA
        progress_data = pd.concat([progress_data, pd.DataFrame([totals_row])], ignore_index=True)
        
    max_today_sales = progress_data.loc[progress_data["Sales Exec"] != "TOTALS", "Today's Sales"].max()
    max_weekly_sales = progress_data.loc[progress_data["Sales Exec"] != "TOTALS", "Weekly Sales"].max()


    # ✅ Styling for "Sales Exec" column
    def style_sales_exec(value, is_total=False):
        if is_total:
            return f"<div style='background-color: green; color: white; font-family: Chapman-Bold; font-size: 22px; padding: 10px; text-align: center;'>{value}</div>"
        return f"<div style='color: black; font-family: Chapman-Bold; font-size: 22px; padding: 10px; text-align: center;'>{value}</div>"

    progress_data["Sales Exec"] = progress_data.apply(
        lambda row: style_sales_exec(row["Sales Exec"], is_total=(row["Sales Exec"] == "TOTALS")),
        axis=1
    )

    # ✅ Styling for "Today's Sales" and "Weekly Sales"
    def style_sales(value, is_highest, is_total=False):
        if is_total:
            return f"<div style='background-color: green; color: white; font-family: Chapman-Bold; font-size: 22px; padding: 10px; text-align: center;'>£{value:,.0f}</div>"
        if is_highest and value > 0:
            return f"<div style='background-color: gold; color: black; font-family: Chapman-Bold; font-size: 22px; padding: 10px; text-align: center;'>⭐ £{value:,.0f}</div>"
        return f"<div style='color: black; font-family: Chapman-Bold; font-size: 22px; padding: 10px; text-align: center;'>£{value:,.0f}</div>"

    # max_today_sales = progress_data.loc[progress_data["Sales Exec"] != "TOTALS", "Today's Sales"].max()
    # max_weekly_sales = progress_data.loc[progress_data["Sales Exec"] != "TOTALS", "Weekly Sales"].max()

    progress_data["Today's Sales"] = progress_data.apply(
        lambda row: style_sales(
            row["Today's Sales"],
            row["Today's Sales"] == max_today_sales and row["Sales Exec"] != "TOTALS",
            is_total=(row["Sales Exec"] == "TOTALS")
        ),
        axis=1
    )

    progress_data["Weekly Sales"] = progress_data.apply(
        lambda row: style_sales(
            row["Weekly Sales"],
            row["Weekly Sales"] == max_weekly_sales and row["Sales Exec"] != "TOTALS",
            is_total=(row["Sales Exec"] == "TOTALS")
        ),
        axis=1
    )

    # ✅ Apply Progress To Monthly Target color-coding
    def style_progress(value):
        if value >= expected_pace:
            return f"<div style='background-color: green; color: white; font-family: Chapman-Bold; font-size: 22px; padding: 10px; text-align: center;'>{value:.0f}%</div>"
        elif half_expected_pace <= value < expected_pace:
            return f"<div style='background-color: orange; color: white; font-family: Chapman-Bold; font-size: 22px; padding: 10px; text-align: center;'>{value:.0f}%</div>"
        return f"<div style='background-color: red; color: white; font-family: Chapman-Bold; font-size: 22px; padding: 10px; text-align: center;'>{value:.0f}%</div>"

    progress_data["Progress To Monthly Target"] = progress_data["Progress To Monthly Target (Numeric)"].apply(
        lambda x: style_progress(x) if pd.notnull(x) else "<div></div>"
    )

    # ✅ Drop numeric column after styling
    progress_data = progress_data.drop(columns=["Progress To Monthly Target (Numeric)"])

    # ✅ Adjust column headers for consistent font size
    styled_columns = {
        "Sales Exec": "Sales Exec",
        "Today's Sales": "Today's Sales",
        "Weekly Sales": "Weekly Sales",
        "Progress To Monthly Target": "Progress To Monthly Target"
    }
    progress_data.columns = [
        f"<div style='font-family: Chapman-Bold; font-size: 22px; text-align: center;'>{col}</div>"
        for col in styled_columns.values()
    ]

    # ✅ Return styled table and list of sales made
    styled_table = progress_data.to_html(classes="big-table", escape=False, index=False)
    sales_made = filtered_data["CreatedBy"].unique()
    return styled_table, sales_made




################################################################################
# 4. Additional Helpers for Fixtures, Scrolling Messages, etc.
################################################################################

def get_next_fixture(data, budget_df):
    """
    Finds the earliest upcoming fixture based on 'KickOffEventStart'.
    Returns (fixture_name, fixture_date, budget_target, event_competition).
    """
    data["KickOffEventStart"] = pd.to_datetime(data["KickOffEventStart"], errors="coerce")
    today = datetime.now()
    
    # Filter future fixtures
    future_data = data[data["KickOffEventStart"] > today].copy()

    # Sort fixtures by the soonest kickoff time
    future_data = future_data.sort_values(by="KickOffEventStart", ascending=True)

    if future_data.empty:
        return None, None, None, None

    # Get the next fixture details
    next_fixture = future_data.iloc[0]
    fixture_name = next_fixture["Fixture Name"]  # Should match filtered_df_without_seats column
    fixture_date = next_fixture["KickOffEventStart"]
    event_competition = next_fixture["EventCompetition"]

    # Retrieve the budget target from budget_df
    budget_target_row = budget_df[budget_df["Fixture Name"] == fixture_name]
    budget_target = budget_target_row["Budget Target"].iloc[0] if not budget_target_row.empty else 0

    return fixture_name, fixture_date, budget_target, event_competition



def generate_scrolling_messages(data, budget_df, df_inventory):
    """
    Combines multiple short messages (latest sale, next fixture status, top fixture, top exec)
    into a single scrolling marquee string.
    """
    data = data.copy()  # Ensure it's a copy before modifying
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)
    data = data.dropna(subset=["CreatedOn"])  # Drop invalid date rows

    # 🔹 **Latest Sale**
    latest_sale = data.sort_values(by="CreatedOn", ascending=False).head(1)
    if not latest_sale.empty:
        source = str(latest_sale["SaleLocation"].iloc[0]).lower()
        created_by = str(latest_sale["CreatedBy"].iloc[0])
        total_price = float(latest_sale["TotalPrice"].iloc[0]) if not pd.isnull(latest_sale["TotalPrice"].iloc[0]) else 0.0

        if source in ["online", "website"]:
            latest_sale_message = f"💻 Online sale with £{total_price:,.2f} generated."
        elif source == "moto":
            latest_sale_message = f"📞 Generated by Moto ({created_by}) with £{total_price:,.2f} generated"
        else:
            seats = int(latest_sale["Seats"].iloc[0]) if not pd.isnull(latest_sale["Seats"].iloc[0]) else 0
            package_name = latest_sale["Package Name"].iloc[0]
            fixture_name = latest_sale["Fixture Name"].iloc[0]
            latest_sale_message = f"🎟️ Latest Sale: {seats} seat(s) x {package_name} for {fixture_name} via {source.capitalize()} @ £{total_price:,.2f}."
    else:
        latest_sale_message = "🚫 No recent sales to display."

    # 🔹 **Ensure Correct Next Fixture Selection**
    upcoming_fixtures = get_upcoming_fixtures(df_inventory, n=1)

    if not upcoming_fixtures.empty:
        next_fixture_row = upcoming_fixtures.iloc[0]
        next_fixture_name = next_fixture_row["EventName"]
        next_fixture_date = pd.to_datetime(next_fixture_row["KickOffEventStart"], errors="coerce")
        next_event_competition = next_fixture_row["EventCompetition"]

        # Get budget target if available
        budget_target_row = budget_df.loc[
            (budget_df["Fixture Name"] == next_fixture_name) &
            (budget_df["EventCompetition"] == next_event_competition)
        ]
        next_budget_target = budget_target_row["Budget Target"].values[0] if not budget_target_row.empty else 0
    else:
        next_fixture_name, next_fixture_date, next_budget_target, next_event_competition = None, None, 0, None

    # ✅ **Generate Next Fixture Message**
    if next_fixture_name and pd.notnull(next_fixture_date):
        fixture_data = data[
            (data["Fixture Name"] == next_fixture_name) &
            (data["EventCompetition"] == next_event_competition)
        ]
        fixture_revenue = fixture_data["Price"].sum()
        days_to_fixture = (next_fixture_date - datetime.now()).days
        budget_achieved = round((fixture_revenue / next_budget_target) * 100, 2) if next_budget_target > 0 else 0
        fixture_display = f"{next_fixture_name} ({next_event_competition})"

        next_fixture_message = (
            f"🏟️ Next Fixture: {fixture_display} in {days_to_fixture} day(s) 🎯 Budget Target Achieved: {budget_achieved}%."
        )
    else:
        next_fixture_message = "⚠️ No upcoming fixtures to display."

    # ✅ **Top Fixture of the Day**
    today_sales = data[data["CreatedOn"].dt.floor('D') == pd.to_datetime(datetime.now().date())]
    if not today_sales.empty:
        top_fixture = today_sales.groupby("Fixture Name")["Price"].sum().idxmax()
        top_fixture_revenue = today_sales.groupby("Fixture Name")["Price"].sum().max()
        top_fixture_message = f"📈 Top Selling Fixture Today: {top_fixture} with £{top_fixture_revenue:,.2f} generated."
    else:
        top_fixture_message = "📉 No sales recorded today."

    # ✅ **Top Selling Exec with Name Mapping**
    valid_executives = ["dcoppin", "millies", "bgardiner", "dmontague", "jedwards"]

    # Apply user mapping
    user_mapping = {
        "dmontague": "Dan",
        "bgardiner": "Bobby",
        "dcoppin":   "David",
        "jedwards":  "Joey",
        "millies":   "Millie",
        # "HayleyA":   "Hayley",
        # "BethNW":    "Beth",
        # "BenT":      "Ben",
        # "jmurphy":   "James",
        # "MeganS":    "Megan"
    }

    # Filter sales data for valid executives
    exec_sales_today = today_sales[today_sales["CreatedBy"].isin(valid_executives)]

    if not exec_sales_today.empty:
        # Get the top-selling executive (username)
        top_executive_username = exec_sales_today.groupby("CreatedBy")["Price"].sum().idxmax()
        top_executive_revenue = exec_sales_today.groupby("CreatedBy")["Price"].sum().max()

        # Convert username to full name using mapping
        top_executive_name = user_mapping.get(top_executive_username, top_executive_username)

        top_executive_message = (
            f"🤵📞 Top Selling Exec Today: 🌟{top_executive_name}🌟 with £{top_executive_revenue:,.2f} generated."
        )
    else:
        top_executive_message = "🚫 No Premium Executive sales recorded today."

    # ✅ **Return Combined Messages**
    return f"{latest_sale_message} | {next_fixture_message} | {top_fixture_message} | {top_executive_message}"



def get_base64_image(image_path):
    """
    Reads an image file from disk, returns its base64 string for embedding.
    """
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except FileNotFoundError:
        return ""

crest_base64 = get_base64_image("assets/arsenal_crest_gold.png")


def get_upcoming_fixtures(inventory_df, n=3):
    """
    Identify the next N upcoming fixtures from the MERGED inventory DataFrame,
    sorted by KickOffEventStart ascending.
    Ensures duplicate fixtures don't repeat and the soonest matches are displayed.
    """

    # Ensure KickOffEventStart is in datetime format
    inventory_df["KickOffDT"] = pd.to_datetime(inventory_df["KickOffEventStart"], errors="coerce")

    # Get today's date
    now = datetime.now()

    # Filter out only future fixtures
    future_df = inventory_df[inventory_df["KickOffDT"] > now].copy()

    # Sort by KickOffDT to ensure closest fixtures appear first
    future_df = future_df.sort_values(by="KickOffDT", ascending=True)

    # Drop duplicates based on EventName + Competition, keeping the soonest kickoff
    unique_fixtures = future_df.drop_duplicates(subset=["EventName", "EventCompetition"], keep="first")

    # Return only the top N fixtures
    return unique_fixtures.head(n)



def format_date_suffix(day):
    """Returns day with proper suffix (1st, 2nd, 3rd, 4th, etc.)."""
    if 10 <= day <= 20:
        return f"{day}th"
    suffixes = {1: "st", 2: "nd", 3: "rd"}
    return f"{day}{suffixes.get(day % 10, 'th')}"

def display_inventory_details(fixture_row, merged_inventory, full_sales_data):
    """
    Displays the inventory details for upcoming fixtures including package stock, prices, and remaining seats.
    Ensures that stock is calculated properly by subtracting actual sales. It calculates Seats sold minus Available stock at the time of the pull.
    """
    st.markdown(
        """
        <style>
            /* Import Fonts */
            @font-face {
                font-family: 'Chapman-Bold';
                src: url('fonts/Chapman-Bold_2894575986.ttf') format('truetype');
            }
            @font-face {
                font-family: 'Northbank-N7';
                src: url('fonts/Northbank-N7_2789728357.ttf') format('truetype');
            }

            /* Reset margin & padding for body */
            body, html {
                margin: 0;
                padding: 0;
                height: 100%;
                width: 100%;
            }

            /* Title styling: Uses Northbank-N7 */
            .fixture-title {
                font-family: 'Northbank-N7';
                font-size: 42px;
                color: #E41B17;
                font-weight: bold;
                text-align: center;
                margin: 0;
                padding: 10px 0;
                width: 100%;
            }

            /* Table Wrapper */
            .fixture-content {
                margin-top: 0px;
                padding-top: 10px;
            }

            /* Table: Clean modern design */
            .fixture-table {
                width: 100%;
                margin-top: 10px;
                border-collapse: collapse;
                table-layout: fixed;
                background-color: white;
            }

            /* Header Styling: Light grey background + bigger text */
            .fixture-table th {
                font-family: 'Chapman-Bold'; /* Apply Chapman-Bold for headers */
                font-size: 20px;
                text-align: center;
                font-weight: bold;
                padding: 12px;
                border-bottom: 2px solid black;  /* Thin bottom border only */
                background-color: #EAEAEA;  /* Light grey background */
                color: black;
            }

            /* Table Cells: Clean design with thin borders */
            .fixture-table td {
                font-family: 'Chapman-Bold'; /* Apply Chapman-Bold for table body */
                font-size: 18px;
                text-align: center;
                font-weight: bold;
                padding: 10px;
                border-bottom: 1px solid #ddd; /* Lighter, thin borders for a clean look */
                background-color: white;
            }

            /* No alternating grey rows */
            .fixture-table tr:nth-child(even) {
                background-color: white !important;
            }

            /* Hover Effect: Subtle highlight */
            .fixture-table tr:hover {
                background-color: #f5f5f5;
            }

            /* Ensure table fits properly */
            .fixture-table th:nth-child(1), .fixture-table td:nth-child(1) { width: 20%; }
            .fixture-table th:nth-child(2), .fixture-table td:nth-child(2) { width: 15%; }
            .fixture-table th:nth-child(3), .fixture-table td:nth-child(3) { width: 15%; }
            .fixture-table th:nth-child(4), .fixture-table td:nth-child(4) { width: 15%; }
            .fixture-table th:nth-child(5), .fixture-table td:nth-child(5) { width: 15%; }
        </style>
        """,
    unsafe_allow_html=True
)




    # 1. Filter inventory data for the selected fixture and event competition
    df_fixture = merged_inventory[
        (merged_inventory["EventName"] == fixture_row["EventName"]) &
        (merged_inventory["EventCompetition"] == fixture_row.get("EventCompetition", "")) &
        (merged_inventory["KickOffEventStart"] == fixture_row["KickOffEventStart"])
    ].copy()

    # # 2. Exclude specific packages from the dataframe
    # df_fixture = df_fixture[~df_fixture['PackageName'].isin([
    #     'INTERNAL MBM BOX', 
    #     'Woolwich Restaurant', 
    #     'AWFC Executive Box - Ticket Only', 
    #     'AWFC Executive Box - Ticket + F&B',
    #     'AWFC Box Arsenal'
    # ])]

    # 3. Ensure "Stock Available" is numeric
    if "Stock Available" not in df_fixture.columns:
        st.error("⚠️ 'Stock Available' column is missing in df_fixture!")
        st.write("Columns in df_fixture:", df_fixture.columns.tolist())
        return

    df_fixture["Stock Available"] = (
        df_fixture["Stock Available"]
        .astype(str)  # Convert everything to string first
        .str.extract(r"(\d+)")  # Extract only numbers
        .fillna(0)  # Handle missing values
        .astype(int)  # Convert to integer
    )

    # 4. Convert Price to numeric safely
    df_fixture["Price"] = pd.to_numeric(df_fixture["Price"], errors="coerce").fillna(0)

    # 5. Aggregate the sales data (Seats Sold) by PackageName and EventCompetition
    df_sales_for_fixture = full_sales_data[
        (full_sales_data["Fixture Name"] == fixture_row["EventName"]) &
        (full_sales_data["EventCompetition"] == fixture_row.get("EventCompetition", ""))
    ]
    
    if df_sales_for_fixture.empty:
        df_fixture["Seats Sold"] = 0
    else:
        sales_agg = (
            df_sales_for_fixture
            .groupby(["Package Name", "EventCompetition"])["Seats"]
            .sum()
            .reset_index()
            .rename(columns={"Seats": "Seats Sold"})
        )
        
        # Merge sales with inventory (PackageName from inventory, "Package Name" from sales)
        df_fixture = pd.merge(
            df_fixture,
            sales_agg,
            left_on="PackageName",
            right_on="Package Name",
            how="left"
        )
        df_fixture.drop(columns="Package Name", inplace=True, errors="ignore")

        df_fixture["Seats Sold"] = pd.to_numeric(df_fixture["Seats Sold"], errors="coerce").fillna(0).astype(int)

    # 6. Compute Stock Remaining and ensure **no negative values**
    df_fixture["Stock Remaining"] = (df_fixture["Stock Available"] - df_fixture["Seats Sold"]).clip(lower=0)

    # 7. Rename 'Price' to 'Current Price' and format it
    df_fixture["Current Price"] = df_fixture["Price"].apply(lambda x: f"£{x:,.2f}")

    # 8. Deduplicate the data based on PackageName and EventCompetition
    df_fixture = df_fixture.drop_duplicates(subset=["PackageName", "Current Price"])

    # 9. Sort the table by 'Current Price' in descending order
    df_fixture = df_fixture.sort_values(by="Price", ascending=False)
    
    # 2. Exclude specific packages from the dataframe
    df_fixture['PackageName'] = df_fixture['PackageName'].str.strip()
    df_fixture = df_fixture[~df_fixture['PackageName'].isin([
        'INTERNAL MBM BOX', 
        'Woolwich Restaurant', 
        'AWFC Executive Box - Ticket Only', 
        'AWFC Executive Box - Ticket + F&B',
        'AWFC Box Arsenal'
    ])]

    # 10. Generate the HTML table
    html_table = df_fixture[["PackageName", "Stock Available", "Seats Sold", "Stock Remaining", "Current Price"]].to_html(
        classes='fixture-table', index=False, escape=False
    )

    # --- 11) Display Fixture Name & Kickoff Time at Top ---
    fixture_day = fixture_row["KickOffEventStart"]
    fixture_datetime = pd.to_datetime(fixture_day, errors="coerce")
    formatted_kickoff = "TBC"
    
    if pd.notnull(fixture_datetime):
        day_suffix = format_date_suffix(fixture_datetime.day)
        formatted_kickoff = fixture_datetime.strftime(f"%A, {day_suffix} %B - %H:%M Kick-Off")

    st.markdown(
    f"""
    <div class="fixture-title">{fixture_row['EventName']}</div>
    {html_table}
    """,
    unsafe_allow_html=True
)

################################################################################
# 5. MAIN Streamlit App
################################################################################

def run_dashboard():
    """
    Renders a 5-page rotating dashboard:
      - Page 1: Sales Leaderboard
      - Page 2: 1st Upcoming Fixture
      - Page 3: 2nd Upcoming Fixture
      - Page 4: 3rd Upcoming Fixture
    Each page auto-cycles every 15 seconds.
    """
    st.set_page_config(page_title="Hospitality Leadership Board", layout="wide")

    # --------------------------------------------------------------------------
    #  MOVE OUR LOAD FUNCTIONS HERE so that each refresh re-runs them:
    # --------------------------------------------------------------------------
    filtered_df_without_seats = load_live_data()
    df_inventory = load_inventory_data()
    # --------------------------------------------------------------------------

    # For sales + services
    valid_sales_executives = ["dcoppin", "millies", "bgardiner", "dmontague", "jedwards"]
    # valid_services_executives = ["HayleyA", "BethNW", "BenT", "jmurphy", "MeganS"]

    
    # Page state initialization
    if "page" not in st.session_state:
        st.session_state.page = 1

    # Initialize the time for the first time
    if "last_switch_time" not in st.session_state:
        st.session_state.last_switch_time = time.time()

    # Check if 15 seconds have passed since the last switch time
    if time.time() - st.session_state.last_switch_time >= 15:
        st.session_state.page = (st.session_state.page % 4) + 1
        st.session_state.last_switch_time = time.time()  # Update the last switch time

    # Sidebar - Date Filter
    st.sidebar.markdown(
        """
        <style>
            @font-face {
                font-family: 'Northbank-N5';
                src: url('fonts/Northbank-N5_2789720163.ttf') format('truetype');
            }
            .custom-date-range-title {
                text-align: center; 
                font-family: 'Northbank-N5';
                font-size: 18px; 
                font-weight: bold; 
                color: #E41B17; 
                margin-bottom: 10px;
            }
        </style>
        <div class="custom-date-range-title">
            Date Range Filter
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Ensure `filtered_data` exists
    filtered_data = filtered_df_without_seats.copy()
    
    # Convert 'CreatedOn' to datetime safely
    filtered_data["CreatedOn"] = pd.to_datetime(filtered_data["CreatedOn"], errors="coerce", dayfirst=True)
    
    filtered_data = filtered_data[filtered_data["CreatedBy"].isin(valid_sales_executives)]

    # -------------------------
    # ✅ **Sidebar - Date Filter**
    # -------------------------
    # ✅ Ensure start_date is always the 1st day of the selected month
    col1, col2 = st.sidebar.columns(2)
    selected_start_date = col1.date_input("Start Date", value=datetime.now().replace(day=1), label_visibility="collapsed")
    selected_end_date = col2.date_input("End Date", value=datetime.now(), label_visibility="collapsed")

    # ✅ Convert user selection to datetime
    start_date = pd.to_datetime(selected_start_date).replace(day=1)  # Always first day of the month
    end_date = pd.to_datetime(selected_end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)  # Full last day

    # ✅ Apply correct date filtering for sales data
    filtered_data = filtered_data[
        (filtered_data["CreatedOn"] >= start_date) &
        (filtered_data["CreatedOn"] <= end_date)
    ]


    # -------------------------
    # ✅ **Render Budget Progress and Next Fixture Side bar**
    # -------------------------
    
    def render_budget_progress_widget(data, valid_executives, title, start_date, end_date, targets_data):
        """
        Renders a sidebar widget showing total revenue vs. target within the selected date range.
        Includes a download button to export filtered sales data.
        """
        # ✅ Ensure 'CreatedOn' is datetime
        data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)

        # ✅ Apply the same date filtering as calculate_monthly_progress()
        executive_data = data[
            (data["CreatedOn"] >= start_date) &
            (data["CreatedOn"] <= end_date) &
            (data["CreatedBy"].isin(valid_executives))
        ]

        # ✅ Calculate total revenue for selected range
        total_revenue = executive_data["Price"].sum()

        # ✅ Retrieve correct target
        current_month = start_date.strftime("%B")
        current_year = start_date.year
        if (current_month, current_year) in targets_data.index:
            valid_execs_in_targets = [exec for exec in valid_executives if exec in targets_data.columns]
            monthly_targets = targets_data.loc[(current_month, current_year), valid_execs_in_targets]
            total_target = monthly_targets.sum()
        else:
            total_target = 0

        # ✅ Fix Progress Percentage Calculation
        progress_percentage = (total_revenue / total_target * 100) if total_target > 0 else 0

        # ✅ Render the sidebar widget
        st.sidebar.markdown(
            f"""
            <style>
                .custom-progress-widget {{
                    background-color: #fff0f0;
                    border: 2px solid #E41B17;
                    border-radius: 15px;
                    margin-top: 10px;
                    padding: 20px 15px;
                    text-align: center;
                    font-size: 28px;
                    font-weight: bold;
                    color: #E41B17;
                }}
                .custom-progress-widget span {{
                    font-size: 26px;
                    color: #0047AB;
                }}
                .custom-progress-widget .highlight {{
                    font-size: 28px;
                    color: #E41B17;
                }}
            </style>
            <div class="custom-progress-widget">
                📊 {title} Progress <br>
                <span>Total Revenue ({start_date.strftime("%B")}):</span><br>
                <span class="highlight">£{total_revenue:,.0f}</span><br>
                <span>Total Target:</span><br>
                <span class="highlight">£{total_target:,.0f}</span><br>
                <span>🌟 Progress Achieved:</span><br>
                <span class="highlight">{progress_percentage:.0f}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ✅ Sidebar Download Button (Filtered Data Export)
        if not executive_data.empty:
            csv_data = executive_data.to_csv(index=False)
            st.sidebar.download_button(
                label="📥 Download Sales Data",
                data=csv_data,
                file_name=f"sales_data_{current_month}_{current_year}.csv",
                mime="text/csv"
            )



    # -------------------------
    # ✅ **Filter Sales & Services Data Properly**
    # -------------------------
    mask_sales = (
        filtered_data["CreatedBy"].isin(valid_sales_executives) &
        (pd.to_datetime(filtered_data["CreatedOn"], errors="coerce", dayfirst=True) >= start_date) &
        (pd.to_datetime(filtered_data["CreatedOn"], errors="coerce", dayfirst=True) <= end_date)
    )
    filtered_sales_data = filtered_data[mask_sales]

    # mask_services = (
    #     filtered_data["CreatedBy"].isin(valid_services_executives) &
    #     (pd.to_datetime(filtered_data["CreatedOn"], errors="coerce", dayfirst=True) >= start_date) &
    #     (pd.to_datetime(filtered_data["CreatedOn"], errors="coerce", dayfirst=True) <= end_date)
    # )
    # filtered_services_data = filtered_data[mask_services]
    
    
    def render_next_fixture_sidebar(fixture_row, filtered_data, budget_df):
        """
        Renders a quick summary widget in the sidebar for the given fixture.
        THIS IS ONLY FOR THE REMAINING INVENTORY PAGES
        """
        if fixture_row.empty:
            st.sidebar.markdown(
                """
                <style>
                    @font-face {{
                        font-family: 'Chapman-Bold';
                        src: url('fonts/Chapman-Bold_2894575986.ttf') format('truetype');
                    }}
                    .no-fixture-widget {{
                        background-color: #fff0f0;
                        border: 2px solid #E41B17;
                        border-radius: 15px;
                        padding: 20px 15px;
                        text-align: center;
                        font-family: 'Chapman-Bold';
                        font-size: 28px;
                        font-weight: bold;
                        color: #E41B17;
                    }}
                </style>
                <div class="no-fixture-widget">
                    ⚠️ No upcoming fixtures found.
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        fixture_name = fixture_row["EventName"]
        event_competition = fixture_row["EventCompetition"]
        fixture_date = pd.to_datetime(fixture_row["KickOffEventStart"], errors="coerce")

        # ✅ Calculate fixture details
        days_to_fixture = (fixture_date - datetime.now()).days if pd.notnull(fixture_date) else "TBC"

        # ✅ Ensure correct lookup in budget_df
        if isinstance(budget_df, pd.DataFrame):
            matching_row = budget_df[
                (budget_df["Fixture Name"].str.strip().str.lower() == fixture_name.strip().lower()) &
                (budget_df["EventCompetition"].str.strip().str.lower() == event_competition.strip().lower())
            ]
            budget_target = matching_row["Budget Target"].values[0] if not matching_row.empty else 0
        else:
            budget_target = budget_df.get((fixture_name, event_competition), 0)

        # ✅ Ensure budget_target is numeric
        budget_target = float(str(budget_target).replace("£", "").replace(",", "").strip()) if budget_target else 0

        # ✅ FIX: Filter correct sales data
        fixture_data = filtered_df_without_seats[
            (filtered_df_without_seats["Fixture Name"].str.strip().str.lower() == fixture_name.strip().lower()) &
            (filtered_df_without_seats["EventCompetition"].str.strip().str.lower() == event_competition.strip().lower())
        ]

        # ✅ Ensure numeric conversion
        if not fixture_data.empty:
            fixture_data["Price"] = pd.to_numeric(fixture_data["Price"], errors="coerce").fillna(0)
            fixture_revenue = fixture_data["Price"].sum()  # ✅ CORRECT Calculation
        else:
            fixture_revenue = 0

        # ✅ Compute budget percentage achieved
        budget_achieved = round((fixture_revenue / budget_target) * 100, 2) if budget_target > 0 else 0

        # ✅ Debugging Output
        print("\n🔍 DEBUG: Fixture Revenue Calculation")
        print(f"Fixture: {fixture_name} | Competition: {event_competition}")
        print(f"Total Rows Matched: {len(fixture_data)}")
        print(f"🎯 Budget Target: £{budget_target:,.0f}")
        print(f"💰 FIXED Fixture Revenue: £{fixture_revenue:,.0f}")
        print(f"📊 Budget Target Achieved: {budget_achieved:.2f}%")

        # Sidebar Widget
        st.sidebar.markdown(
            f"""
            <style>
                @font-face {{
                    font-family: 'Chapman-Bold';
                    src: url('fonts/Chapman-Bold_2894575986.ttf') format('truetype');
                }}
                .next-fixture-widget {{
                    background-color: #fff0f0;
                    border: 2px solid #E41B17;
                    border-radius: 15px;
                    margin-top: 10px;
                    padding: 15px;
                    text-align: center;
                    font-family: 'Chapman-Bold';
                    font-size: 24px;
                    font-weight: bold;
                    color: #E41B17;
                }}
                .next-fixture-widget span {{
                    display: block;
                    margin-bottom: 5px;
                }}
                .next-fixture-widget .fixture-title {{
                    font-size: 22px;
                    color: #E41B17;
                    margin-bottom: 10px;
                }}
                .next-fixture-widget .fixture-info {{
                    font-size: 20px;
                    color: #0047AB;
                    margin-bottom: 5px;
                }}
                .next-fixture-widget .fixture-days {{
                    font-size: 20px;
                    color: #E41B17;
                    margin-bottom: 5px;
                }}
            </style>
            <div class="next-fixture-widget">
                🏟️ Next Fixture Details <br>
                <span class="fixture-info">⏳ Days to Fixture:</span>
                <span class="fixture-days">{days_to_fixture} days</span>
                <span class="fixture-info">🎯 Budget Target:</span>
                <span class="fixture-days">£{budget_target:,.0f}</span>
                <span class="fixture-info">✅ Budget Target Achieved:</span>
                <span class="fixture-days">{budget_achieved:.2f}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )



    ############################################################################
    # PAGES: 1 =SALES ; 2/3/4 = UPCOMING FIXTURES
    ############################################################################

    
    # PAGE 1: Sales Leaderboard
    if st.session_state.page == 1:
        st.markdown(
            """
            <style>
            @font-face {
                font-family: 'Northbank-N7';
                src: url('fonts/Northbank-N7_2789728357.ttf') format('truetype');
            }
            .custom-title {
                font-family: 'Northbank-N7';
                font-size: 45px;
                font-weight: bold;
                color: #E41B17;
                text-align: center;
            }
            </style>
            <div class="custom-title">
                ARSENAL PREMIUM SALES
            </div>
            """,
            unsafe_allow_html=True,
        )
        monthly_progress, sales_made = calculate_monthly_progress(
            filtered_sales_data, start_date, end_date, targets_data
        )
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; margin-top: 20px; margin-bottom: 20px;">
                {monthly_progress}
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_budget_progress_widget(filtered_sales_data, valid_sales_executives, "Sales Exec", start_date, end_date, targets_data)


    # PAGE 1: 1st Upcoming Fixture
    elif st.session_state.page == 2:
        next_fixtures = get_upcoming_fixtures(df_inventory, n=3)
        if len(next_fixtures) >= 1:
            fixture_1 = next_fixtures.iloc[0]
            render_next_fixture_sidebar(fixture_1, filtered_data, budget_df)
            display_inventory_details(fixture_1, df_inventory, filtered_df_without_seats)
        else:
            st.write("No upcoming fixtures found.")

    # PAGE 2: 2nd Upcoming Fixture
    elif st.session_state.page == 3:
        next_fixtures = get_upcoming_fixtures(df_inventory, n=3)
        if len(next_fixtures) >= 2:
            fixture_2 = next_fixtures.iloc[1]
            render_next_fixture_sidebar(fixture_2, filtered_data, budget_df)
            display_inventory_details(fixture_2, df_inventory, filtered_df_without_seats)
        else:
            st.write("No second upcoming fixture found.")

    # PAGE 3: 3rd Upcoming Fixture
    elif st.session_state.page == 4:
        next_fixtures = get_upcoming_fixtures(df_inventory, n=3)
        if len(next_fixtures) >= 3:
            fixture_3 = next_fixtures.iloc[2]
            render_next_fixture_sidebar(fixture_3, filtered_data, budget_df)
            display_inventory_details(fixture_3, df_inventory, filtered_df_without_seats)
        else:
            st.write("No third upcoming fixture found.")



    ############################################################################
    # Scrolling Marquee & Auto-refresh
    ############################################################################
    scrolling_message = generate_scrolling_messages(filtered_df_without_seats, budget_df, df_inventory)
    st.markdown(
        f"""
        <style>
            @font-face {{
                font-family: 'Northbank-N5';
                src: url('fonts/Northbank-N5_2789720163.ttf') format('truetype');
            }}
            .custom-scroll-box {{
                overflow: hidden;
                white-space: nowrap;
                max-width: 100%;
                margin: 0 auto;
                background-color: #fff0f0;
                color: #E41B17;
                padding: 10px 12px;
                border-radius: 10px;
                font-family: 'Northbank-N5';
                font-size: 20px;
                font-weight: bold;
                text-align: center;
                border: 1px solid #E41B17;
                position: fixed;
                bottom: 0px;
                bottom: 0;
                left: 0; /* Ensure it starts at the left edge */
                width: 100%;
                z-index: 1000;
                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            }}
            body {{
                padding-bottom: 90px;
            }}
        </style>
        <div class="custom-scroll-box">
            <marquee behavior="scroll" direction="left" scrollamount="4">
                {scrolling_message}
            </marquee>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Automatically refresh the page every 5 minutes (300,000 milliseconds)
    st_autorefresh(interval=15000, key="auto_refresh")  # Refresh every 5 minutes

################################################################################
# 6. Main Entry Point
################################################################################

if __name__ == "__main__":
    run_dashboard()
