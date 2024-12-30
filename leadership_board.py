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

# Specify your list of executives
valid_executives = ["dcoppin", "BethNW", "bgardiner", "MeganS", "dmontague", 
                    "jedwards", "HayleyA", "MillieS", "BenT", "ayildirim", "jmurphy"]



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

    # Today's sales
    today_sales_data = data[data["CreatedOn"].dt.date == datetime.now().date()]
    today_sales_count = (
        today_sales_data.groupby("CreatedBy")["Price"]
        .count()
        .reindex(targets_data.columns, fill_value=0)
    )

    # Add money bags to represent sales visually
    today_sales_visual = today_sales_count.apply(
        lambda x: f"{'💰' * x} ({x})" if x > 0 else "0"
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
        "Today's Sales": today_sales_visual.values,  # Use the visual sales representation
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

    # Extract unique sales made for the second return value
    sales_made = filtered_data["CreatedBy"].unique()

    return progress_data, sales_made 



def get_next_fixture(data, budget_df):
    # Ensure KickOffEventStart is a proper datetime
    data["KickOffEventStart"] = pd.to_datetime(data["KickOffEventStart"], errors="coerce", dayfirst=True)

    # Debug: Raw data before filtering
    print("Raw Data (Before Filtering):")
    print(data[["Fixture Name", "EventCompetition", "KickOffEventStart", "Price"]])

    # Filter for valid future fixtures
    today = datetime.now()
    future_data = data[data["KickOffEventStart"] > today]

    # Debug: Future fixtures after filtering
    print("Future Data (After Filtering):")
    print(future_data[["Fixture Name", "EventCompetition", "KickOffEventStart", "Price"]])

    # Aggregate data to find the earliest fixture for each unique `Fixture Name` and `EventCompetition`
    aggregated_data = (
        future_data.groupby(["Fixture Name", "EventCompetition"], as_index=False)
        .agg({
            "KickOffEventStart": "min",  # Take the earliest kickoff time
            "Price": "sum",             # Sum all prices for revenue
        })
        .sort_values("KickOffEventStart", ascending=True)  # Sort by earliest kickoff
    )

    # Add a `DaysToFixture` column for convenience
    aggregated_data["DaysToFixture"] = (aggregated_data["KickOffEventStart"] - today).dt.days

    # Debug: Aggregated future fixtures
    print("Aggregated Future Fixtures (Debug):")
    print(aggregated_data)

    # Check if there are any future fixtures
    if not aggregated_data.empty:
        # Select the next fixture based on the earliest kickoff
        next_fixture = aggregated_data.iloc[0]
        fixture_name = next_fixture["Fixture Name"]
        fixture_date = next_fixture["KickOffEventStart"]
        event_competition = next_fixture["EventCompetition"]

        # Retrieve the budget target for the selected fixture
        budget_target_row = budget_df[budget_df["Fixture Name"] == fixture_name]
        budget_target = budget_target_row["Budget Target"].iloc[0] if not budget_target_row.empty else 0

        # Debug: Next fixture and its budget
        print("Next Fixture Selected:", fixture_name, fixture_date, event_competition)
        print("Budget Target for Fixture:", budget_target)

        return fixture_name, fixture_date, budget_target, event_competition

    # If no future fixtures are found
    return None, None, None, None



def generate_scrolling_messages(data, budget_df):
    # Ensure CreatedOn is a proper datetime
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)
    data = data.dropna(subset=["CreatedOn"])  # Remove rows with invalid CreatedOn

    # Latest Sale
    latest_sale = data.sort_values(by="CreatedOn", ascending=False).head(1)

    if not latest_sale.empty:
        source = latest_sale["SaleLocation"].iloc[0].lower() if pd.notna(latest_sale["SaleLocation"].iloc[0]) else "Unknown"
        created_by = latest_sale["CreatedBy"].iloc[0] if pd.notna(latest_sale["CreatedBy"].iloc[0]) else "Unknown"
        total_price = latest_sale["TotalPrice"].iloc[0] if pd.notna(latest_sale["TotalPrice"].iloc[0]) else 0.0

        if source in ["online", "website"]:
            latest_sale_message = f"💻 Online sale with £{total_price:,.2f} generated."
        elif source == "moto":
            if created_by.lower() not in ["sales team", "service team"]:
                latest_sale_message = f"📞 Generated by Moto (Other User: {created_by}) with £{total_price:,.2f} generated"
            else:
                latest_sale_message = f"📞 Generated by Moto ({created_by}) with £{total_price:,.2f} generated"
        else:
            latest_sale_message = (
                f"🎟️ Latest Sale: {int(latest_sale['Seats'].iloc[0])} seat(s) x {latest_sale['Package Name'].iloc[0]} "
                f"for {latest_sale['Fixture Name'].iloc[0]} via {source.capitalize()} @ £{total_price:,.2f}."
            )
    else:
        latest_sale_message = "🚫 No recent sales to display."

    # Next Fixture Section
    fixture_name, fixture_date, budget_target, event_competition = get_next_fixture(filtered_df_without_seats, budget_df)

    if fixture_name:
        # Calculate days to fixture
        days_to_fixture = (fixture_date - datetime.now()).days

        # Calculate total revenue for the selected fixture
        fixture_revenue = filtered_df_without_seats[
            filtered_df_without_seats["Fixture Name"] == fixture_name
        ]["Price"].sum()

        # Calculate budget achieved
        budget_achieved = round((fixture_revenue / budget_target) * 100, 2) if budget_target > 0 else 0

        # Display fixture with event competition
        fixture_display = f"{fixture_name} ({event_competition})"

        # Generate the message
        next_fixture_message = (
            f"🏟️ Next Fixture: {fixture_display} in {days_to_fixture} days "
            f"🎯 Budget Target Achieved: {budget_achieved}%."
        )
    else:
        next_fixture_message = "⚠️ No upcoming fixtures to display."

    # Top Fixture of the Day
    today_sales = data[data["CreatedOn"].dt.date == datetime.now().date()]
    if not today_sales.empty:
        top_fixture = today_sales.groupby("Fixture Name")["Price"].sum().idxmax()
        top_fixture_revenue = today_sales.groupby("Fixture Name")["Price"].sum().max()
        top_fixture_message = f"📈 Top Selling Fixture Today: {top_fixture} with £{top_fixture_revenue:,.2f} generated."
    else:
        top_fixture_message = "📉 No sales recorded today."

# Specify Execs
    valid_executives = ["dcoppin", "BethNW", "bgardiner", "MeganS", "dmontague", 
                        "jedwards", "HayleyA", "MillieS", "BenT", "ayildirim", "jmurphy"]

    # Filter today’s sales to include only valid executives
    exec_sales_today = today_sales[today_sales["CreatedBy"].isin(valid_executives)]

    if not exec_sales_today.empty:
        # Calculate the top-selling executive among the specified list
        top_executive = exec_sales_today.groupby("CreatedBy")["Price"].sum().idxmax()
        top_executive_revenue = exec_sales_today.groupby("CreatedBy")["Price"].sum().max()
        top_executive_message = (
            f"🤵‍♀️ Top Selling Exec Today: 🌟{top_executive}🌟 with £{top_executive_revenue:,.2f} generated.."
        )
    else:
        # If no sales by the specified executives, display a no-sales message
        top_executive_message = "🚫 No Premium Executive sales recorded today."

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

# Run dashboard
def run_dashboard():
    st.set_page_config(page_title="Hospitality Leadership Board", layout="wide")
    
    # Dashboard Title
    st.markdown(
        """
        <div style="text-align: center; margin-top: 20px;">
            <h1 style="color: #2c3e50;">💎 Arsenal Premium Sales 💎</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Sidebar: Auto-refresh
    refresh_time = auto_refresh()
    st.sidebar.markdown(
        f"""
        <div style="
            background-color: #d4edda; /* Soft green */
            border: 1px solid #c3e6cb; /* Light green border */
            border-radius: 8px; /* Rounded corners */
            padding: 10px;
            margin-bottom: 20px; /* Add spacing below the widget */
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #155724; /* Dark green text */
            text-align: center;
        ">
            <strong>Latest Data Update:</strong> {refresh_time}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Sidebar: Date Range Filter
    st.sidebar.markdown("### Date Range Filter")
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("Start Date", value=datetime.now().replace(day=1), label_visibility="collapsed")
    end_date = col2.date_input("End Date", value=datetime.now(), label_visibility="collapsed")

    # Total Sales Section
    total_sales = calculate_total_sales(filtered_df_without_seats)
    st.sidebar.markdown(
        f"""
        <div style="
            background-color: #fff0f0; /* Soft pastel pink background */
            border: 2px solid #E41B17; /* Arsenal red solid border */
            border-radius: 15px; /* Match the scroll message's curved edges */
            padding: 15px 20px; /* Match padding of the scroll message */
            margin-bottom: 20px;
            text-align: center;
            font-family: Arial, sans-serif;
        ">
            <h4 style="color: #0047AB; font-size: 24px; font-weight: bold;">🛒 Total Sales</h4>
            <p style="font-size: 16px; color: #E41B17; font-weight: bold;">Overall Sales Since Go Live:</p>
            <p style="font-size: 22px; color: #E41B17; font-weight: bold;">£{total_sales:,.0f}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Premium Monthly Progress Section
    total_revenue, total_target, progress_percentage = calculate_overall_progress(filtered_df_without_seats, start_date, end_date)
    if total_target == 0:
        st.sidebar.markdown(
            """
            <div style="
                background-color: #fff0f0; /* Light pastel pink background */
                border: 2px solid #E41B17; /* Arsenal red solid border */
                border-radius: 15px; /* Rounded edges */
                padding: 15px;
                margin-bottom: 20px;
                text-align: center;
                font-family: Arial, sans-serif;
            ">
                <p style="color: #E41B17; font-size: 18px; font-weight: bold;">⚠️ Selected date range is out of bounds for available targets.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            f"""
            <div style="
                background-color: #fff0f0; /* Light pastel pink background */
                border: 2px solid #E41B17; /* Arsenal red solid border */
                border-radius: 15px; /* Rounded edges for consistency */
                padding: 15px 20px; /* Match padding of the scroll message */
                margin-bottom: 20px;
                text-align: center;
                font-family: Arial, sans-serif;
            ">
                <h4 style="color: #0047AB; font-size: 24px; font-weight: bold;">📊 Premium Monthly Progress</h4>
                <p style="font-size: 16px; color: #0047AB;">Total Revenue ({start_date.strftime("%B")}):</p>
                <p style="font-size: 22px; color: #E41B17; font-weight: bold;">£{total_revenue:,.0f}</p>
                <p style="font-size: 16px; color: #0047AB;">Total Target:</p>
                <p style="font-size: 22px; color: #E41B17; font-weight: bold;">£{total_target:,.0f}</p>
                <p style="font-size: 16px; color: #0047AB;">🌟 Progress Achieved:</p>
                <p style="font-size: 22px; color: #E41B17; font-weight: bold;">{progress_percentage:.0f}%</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Next Fixture Section
    fixture_name, fixture_date, budget_target, event_competition = get_next_fixture(filtered_df_without_seats, budget_df)
    if fixture_name:
        days_to_fixture = (fixture_date - datetime.now()).days
        fixture_revenue = filtered_df_without_seats[
            filtered_df_without_seats["Fixture Name"] == fixture_name
        ]["Price"].sum()
        budget_achieved = round((fixture_revenue / budget_target) * 100, 2) if budget_target > 0 else 0
        fixture_display = f"{fixture_name} ({event_competition})"
        st.sidebar.markdown(
            f"""
            <div style="
                background-color: #fff0f0; /* Light pastel pink background */
                border: 2px solid #E41B17; /* Arsenal red solid border */
                border-radius: 15px; /* Rounded edges for consistency */
                padding: 15px 20px; /* Match padding of the scroll message */
                margin-bottom: 20px;
                text-align: center;
                font-family: Arial, sans-serif;
            ">
                <h4 style="color: #0047AB; font-size: 24px; font-weight: bold;">🏟️ Next Fixture</h4>
                <p style="font-size: 18px; color: #E41B17; font-weight: bold;">{fixture_display}</p>
                <p style="font-size: 16px; color: #0047AB;">⏳ Days to Fixture:</p>
                <p style="font-size: 22px; color: #E41B17; font-weight: bold;">{days_to_fixture} days</p>
                <p style="font-size: 16px; color: #0047AB;">🎯 Budget Target Achieved:</p>
                <p style="font-size: 22px; color: #E41B17; font-weight: bold;">{budget_achieved}%</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            """
            <div style="
                background-color: #fff0f0; /* Light pastel pink background */
                border: 2px solid #E41B17; /* Arsenal red solid border */
                border-radius: 15px; /* Rounded edges for consistency */
                padding: 15px 20px; /* Match padding of the scroll message */
                margin-bottom: 20px;
                text-align: center;
                font-family: Arial, sans-serif;
            ">
                <p style="font-size: 18px; color: #E41B17; font-weight: bold;">⚠️ No upcoming fixtures found.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Monthly Progress Table
    monthly_progress, sales_made = calculate_monthly_progress(filtered_df_without_seats, start_date, end_date)
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

    # Scrolling Message Section
    scrolling_message = generate_scrolling_messages(filtered_df_without_seats, budget_df)
    st.markdown(
        f"""
        <style>
            .custom-scroll-box {{
                overflow: hidden;
                white-space: nowrap;
                width: 100%;
                background-color: #fff0f0; /* Soft pastel pink background */
                color: #E41B17; /* Arsenal red font color */
                padding: 15px 20px; /* Padding for spacing */
                border-radius: 15px; /* Curved edges */
                font-family: Impact, Arial, sans-serif; /* Bold, blocky font */
                font-size: 25px; /* Extra-large font size */
                font-weight: bold; /* Extra-bold text */
                text-align: center; /* Center-aligned text */
                border: 2px solid #E41B17; /* Red border */
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


if __name__ == "__main__":
    run_dashboard()
