import time
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import importlib
from streamlit_autorefresh import st_autorefresh
import base64

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
    "dmontague": [155000, 155000, 135000, 110000, 90000, 65000]
    # "MeganS": [42500, 42500, 36500, 30500, 24500, 18500],
    # "BethNW": [42500, 42500, 36500, 30500, 24500, 18500],
    # "HayleyA": [42500, 42500, 36500, 30500, 24500, 18500],
    # "jmurphy": [35000, 35000, 30000, 25000, 20000, 15000],
    # "BenT": [35000, 35000, 30000, 25000, 20000, 15000],
}).set_index(["Month", "Year"])

# Specify your list of executives
valid_executives = ["dcoppin", "MillieS", "bgardiner", "dmontague", "jedwards"]
                    #  "HayleyA", "BethNW", "BenT", "jmurphy", "MeganS"]

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


def calculate_monthly_progress(data, start_date, end_date):
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)

    # Filter data within the date range
    filtered_data = data[
        (data["CreatedOn"] >= pd.to_datetime(start_date)) &
        (data["CreatedOn"] <= pd.to_datetime(end_date))
    ]

    current_month = start_date.strftime("%B")
    current_year = start_date.year

    if (current_month, current_year) not in targets_data.index:
        return None, []

    # Calculate expected pace
    total_days_in_month = pd.Period(f"{current_year}-{start_date.month}").days_in_month
    days_elapsed = (pd.to_datetime(end_date) - pd.Timestamp(f"{current_year}-{start_date.month}-01")).days + 1
    expected_pace = (days_elapsed / total_days_in_month) * 100
    half_expected_pace = 0.5 * expected_pace

    # Today's sales
    end_date_sales_data = data[data["CreatedOn"].dt.date == pd.to_datetime(end_date).date()]
    end_date_sales = (
        end_date_sales_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )

    # Weekly sales
    start_of_week = pd.to_datetime(end_date) - pd.Timedelta(days=pd.to_datetime(end_date).weekday())
    weekly_sales_data = data[
        (data["CreatedOn"] >= start_of_week) &
        (data["CreatedOn"] <= pd.to_datetime(end_date))
    ]
    weekly_sales = (
        weekly_sales_data.groupby("CreatedBy")["Price"]
        .sum()
        .add(end_date_sales, fill_value=0)  # Ensure today's sales are included
        .reindex(targets_data.columns, fill_value=0)
    )

    # Progress to monthly target
    progress = (
        filtered_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )
    monthly_targets = targets_data.loc[(current_month, current_year)]
    progress_percentage = (progress / monthly_targets * 100).round(0)

    # Build the progress table
    progress_data = pd.DataFrame({
        "Sales Exec": progress.index,
        "Today's Sales": end_date_sales.values,
        "Weekly Sales": weekly_sales.values,
        "Progress To Monthly Target (Numeric)": progress_percentage.values,
    }).reset_index(drop=True)

    # Map usernames to full names
    user_mapping = {
        "dmontague": "Dan",
        "bgardiner": "Bobby",
        "dcoppin": "David",
        "jedwards": "Joey",
        "MillieS": "Millie",
        # "HayleyA": "Hayley",
        # "BethNW": "Beth",
        # "BenT": "Ben",
        # "jmurphy": "James",
        # "MeganS": "Megan"
    }
    progress_data["Sales Exec"] = progress_data["Sales Exec"].map(user_mapping).fillna(progress_data["Sales Exec"])

    # Sort by "Progress To Monthly Target" in descending order
    progress_data = progress_data.sort_values(by="Progress To Monthly Target (Numeric)", ascending=False)

    # Calculate totals dynamically
    total_today_sales = end_date_sales.sum()
    total_weekly_sales = weekly_sales.sum()

    # Add totals row at the end
    totals_row = {
        "Sales Exec": "TOTALS",
        "Today's Sales": total_today_sales,
        "Weekly Sales": total_weekly_sales,
        "Progress To Monthly Target (Numeric)": None
    }
    progress_data = pd.concat([progress_data, pd.DataFrame([totals_row])], ignore_index=True)

    # Highlight the highest Today's Sales and Weekly Sales values
    max_today_sales = progress_data.loc[progress_data["Sales Exec"] != "TOTALS", "Today's Sales"].max()
    max_weekly_sales = progress_data.loc[progress_data["Sales Exec"] != "TOTALS", "Weekly Sales"].max()

    # Styling for "Sales Exec" column
    def style_sales_exec(value, is_total=False):
        if is_total:
            return f"<div style='background-color: green; color: white; font-family: Chapman-Bold; font-size: 28px; padding: 10px; text-align: center;'>{value}</div>"
        return f"<div style='color: black; font-family: Chapman-Bold; font-size: 28px; padding: 10px; text-align: center;'>{value}</div>"

    progress_data["Sales Exec"] = progress_data.apply(
        lambda row: style_sales_exec(
            row["Sales Exec"],
            is_total=(row["Sales Exec"] == "TOTALS")
        ),
        axis=1
    )

    # Styling for "Today's Sales" and "Weekly Sales"
    def style_sales(value, is_highest, is_total=False):
        if is_total:
            return f"<div style='background-color: green; color: white; font-family: Chapman-Bold; font-size: 28px; padding: 10px; text-align: center;'>£{value:,.0f}</div>"
        if is_highest and value > 0:
            return f"<div style='background-color: gold; color: black; font-family: Chapman-Bold; font-size: 28px; padding: 10px; text-align: center;'>⭐ £{value:,.0f}</div>"
        return f"<div style='color: black; font-family: Chapman-Bold; font-size: 28px; padding: 10px; text-align: center;'>£{value:,.0f}</div>"

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

    # Apply Progress To Monthly Target color-coding
    def style_progress(value):
        if value >= expected_pace:
            return f"<div style='background-color: green; color: white; font-family: Chapman-Bold; font-size: 28px; padding: 10px; text-align: center;'>{value:.0f}%</div>"
        elif half_expected_pace <= value < expected_pace:
            return f"<div style='background-color: orange; color: white; font-family: Chapman-Bold; font-size: 28px; padding: 10px; text-align: center;'>{value:.0f}%</div>"
        return f"<div style='background-color: red; color: white; font-family: Chapman-Bold; font-size: 28px; padding: 10px; text-align: center;'>{value:.0f}%</div>"

    progress_data["Progress To Monthly Target"] = progress_data["Progress To Monthly Target (Numeric)"].apply(
        lambda x: style_progress(x) if pd.notnull(x) else f"<div style='color: black; font-family: Chapman-Bold; font-size: 28px; padding: 10px; text-align: center;'></div>"
    )

    # Drop numeric column after styling
    progress_data = progress_data.drop(columns=["Progress To Monthly Target (Numeric)"])

    # Adjust column headers for consistent font size
    styled_columns = {
        "Sales Exec": "Sales Exec",
        "Today's Sales": "Today's Sales",
        "Weekly Sales": "Weekly Sales",
        "Progress To Monthly Target": "Progress To Monthly Target"
    }
    progress_data.columns = [
        f"<div style='font-family: Chapman-Bold; font-size: 28px; text-align: center;'>{col}</div>"
        for col in styled_columns.values()
    ]

    # Return styled table and list of sales made
    styled_table = progress_data.to_html(classes="big-table", escape=False, index=False)
    sales_made = filtered_data["CreatedBy"].unique()
    return styled_table, sales_made



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
        # Filter data by both Fixture Name and EventCompetition
        fixture_data = filtered_df_without_seats[
            (filtered_df_without_seats["Fixture Name"] == fixture_name) &
            (filtered_df_without_seats["EventCompetition"] == event_competition)
        ]

        # Calculate total revenue for the selected fixture
        fixture_revenue = fixture_data["Price"].sum()

        # Calculate days to fixture
        days_to_fixture = (fixture_date - datetime.now()).days

        # Calculate budget achieved
        budget_achieved = round((fixture_revenue / budget_target) * 100, 2) if budget_target > 0 else 0

        # Display fixture with event competition
        fixture_display = f"{fixture_name} ({event_competition})"

        # Generate the message
        next_fixture_message = (
            f"🏟️ Next Fixture: {fixture_display} in {days_to_fixture} day(s) "
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
    valid_executives = ["dcoppin", "MillieS", "bgardiner", "dmontague", 'jedwards']
                        #  "HayleyA", "BethNW", "BenT", "jmurphy", "MeganS"]

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
    
    st_autorefresh(interval=300 * 1000, key="auto_refresh")  # Auto-refresh every 5 minutes
    
    return refresh_time


def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Get the base64 string of the image
crest_base64 = get_base64_image("assets/arsenal_crest_gold.png")



from datetime import datetime
import calendar
# Page navigation using session state
def run_dashboard():
    st.set_page_config(page_title="Hospitality Leadership Board", layout="wide")

    # Initialize page counter in session_state if not already present
    if "page" not in st.session_state:
        st.session_state.page = 0  # 0 for Table Page, 1 for Sidebar Data Page

    # Get the current date
    today = datetime.now()

    # Define start_date (e.g., the first day of the current month)
    start_date = today.replace(day=1)

    # Define end_date (e.g., today's date or last day of the current month)
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    end_date = today.replace(day=last_day_of_month)

    # Sidebar controls for Date Range
    st.sidebar.header("Data Controls")
    start_date_input = st.sidebar.date_input("Start Date", start_date)
    end_date_input = st.sidebar.date_input("End Date", end_date)

    # Refresh data button
    if st.sidebar.button("Refresh Data"):
        st.experimental_rerun()

    # Page navigation with auto-switching (every 15 seconds)
    if time.time() - st.session_state.get("last_switch_time", 0) >= 15:
        st.session_state.page = (st.session_state.page + 1) % 2  # Toggle between 0 and 1
        st.session_state.last_switch_time = time.time()  # Update the time of last switch

    # Page 1 - Monthly Sales Premium Leaderboard (Table)
    if st.session_state.page == 0:
        st.markdown(
            """
            <div style="text-align: center; font-family: 'Chapman-Bold'; font-size: 40px; color: #e41b17;">
                ARSENAL PREMIUM SALES
            </div>
            <div style="text-align: center; font-family: 'Chapman-Bold'; font-size: 30px; color: #0047ab;">
                MONTHLY SALES PREMIUM LEADERBOARD
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Display leaderboard with updated data
        monthly_progress, sales_made = calculate_monthly_progress(filtered_df_without_seats, start_date_input, end_date_input)
        st.markdown(
            f"""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                margin-top: 20px;
                margin-bottom: 20px;
            ">
                {monthly_progress}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Scroll message at the bottom of the page
        # Scrolling Message
        scrolling_message = generate_scrolling_messages(filtered_df_without_seats, budget_df)
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
                    max-width: 80%; /* Keep box width manageable */
                    margin: 0 auto; /* Perfectly centers the box horizontally */
                    background-color: #fff0f0; /* Soft pastel pink */
                    color: #E41B17; /* Arsenal red text */
                    padding: 15px 20px; /* Inner padding */
                    border-radius: 15px; /* Smooth curved corners */
                    font-family: 'Northbank-N5'; /* Custom font */
                    font-size: 25px; /* Large readable text */
                    font-weight: bold; /* Bold font */
                    text-align: center; /* Text centered */
                    border: 2px solid #E41B17; /* Red border for contrast */
                    position: fixed; /* Fixed at the bottom */
                    bottom: 50px; /* Distance from bottom */
                    z-index: 1000; /* Keeps it above other content */
                    box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2); /* Shadow for visibility */
                }}
                body {{
                    padding-bottom: 120px; /* Prevent overlapping */
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


    # Page 2 - Monthly Progress Budget Target and Next Fixture Data
    elif st.session_state.page == 1:
        # Display budget and next fixture data on main page
        total_revenue = filtered_df_without_seats["Price"].sum()
        total_target = 2000000  # Placeholder
        progress_percentage = (total_revenue / total_target) * 100

        st.markdown(
            f"""
            <div style="text-align: center; font-family: 'Chapman-Bold'; font-size: 28px; margin-bottom: 20px;">
                📊 Monthly Progress Budget Target
                <br>
                Total Revenue: £{total_revenue:,.0f} | Total Target: £{total_target:,.0f} | 
                Progress Achieved: {progress_percentage:.0f}%
            </div>
            """,
            unsafe_allow_html=True
        )

        # Placeholder for next fixture data
        fixture_name = "Arsenal vs Chelsea"
        fixture_date = "2025-03-12"
        days_to_fixture = (datetime.strptime(fixture_date, "%Y-%m-%d") - today).days

        st.markdown(
            f"""
            <div style="text-align: center; font-family: 'Chapman-Bold'; font-size: 28px; margin-top: 20px;">
                🏟️ Next Fixture: {fixture_name} <br>
                Days to Fixture: {days_to_fixture} days
            </div>
            """,
            unsafe_allow_html=True
        )

        # Scroll message at the bottom of the page
    scrolling_message = generate_scrolling_messages(filtered_df_without_seats, budget_df)
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
                max-width: 80%; /* Keep box width manageable */
                margin: 0 auto; /* Perfectly centers the box horizontally */
                background-color: #fff0f0; /* Soft pastel pink */
                color: #E41B17; /* Arsenal red text */
                padding: 15px 20px; /* Inner padding */
                border-radius: 15px; /* Smooth curved corners */
                font-family: 'Northbank-N5'; /* Custom font */
                font-size: 25px; /* Large readable text */
                font-weight: bold; /* Bold font */
                text-align: center; /* Text centered */
                border: 2px solid #E41B17; /* Red border for contrast */
                position: fixed; /* Fixed at the bottom */
                bottom: 50px; /* Distance from bottom */
                z-index: 1000; /* Keeps it above other content */
                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2); /* Shadow for visibility */
            }}
            body {{
                padding-bottom: 120px; /* Prevent overlapping */
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


    # Auto-refresh and page change logic
    st_autorefresh(interval=15000, key="auto_refresh")  # Trigger refresh every 15 seconds


if __name__ == "__main__":
    run_dashboard()