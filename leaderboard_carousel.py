import time
import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import time
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
    "dmontague": [155000, 155000, 135000, 110000, 90000, 65000],
    "MeganS": [42500, 42500, 36500, 30500, 24500, 18500],
    "BethNW": [42500, 42500, 36500, 30500, 24500, 18500],
    "HayleyA": [42500, 42500, 36500, 30500, 24500, 18500],
    "jmurphy": [35000, 35000, 30000, 25000, 20000, 15000],
    "BenT": [35000, 35000, 30000, 25000, 20000, 15000],
}).set_index(["Month", "Year"])

# Specify your list of executives
valid_sales_executives = ["dcoppin", "MillieS", "bgardiner", "dmontague", "jedwards"]
valid_services_executives = ["HayleyA", "BethNW", "BenT", "jmurphy", "MeganS"]

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

def calculate_monthly_progress(data, start_date, end_date, valid_executives):
    # Ensure 'CreatedOn' is in datetime format
    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)

    # Filter data within the date range and for the specified executives
    filtered_data = data[
        (data["CreatedOn"] >= pd.to_datetime(start_date)) &
        (data["CreatedOn"] <= pd.to_datetime(end_date)) &
        (data["CreatedBy"].isin(valid_executives))
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

    # Today's sales: ensure this reflects sales on the selected `end_date`
    end_date_sales_data = filtered_data[filtered_data["CreatedOn"].dt.date == pd.to_datetime(end_date).date()]
    end_date_sales = (
        end_date_sales_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(valid_executives, fill_value=0)  # Reindex to include only valid executives
    )

    # Weekly sales: filtered for the full week up until the selected end date
    start_of_week = pd.to_datetime(end_date) - pd.Timedelta(days=pd.to_datetime(end_date).weekday())
    weekly_sales_data = filtered_data[
        (filtered_data["CreatedOn"] >= start_of_week) &
        (filtered_data["CreatedOn"] <= pd.to_datetime(end_date))
    ]
    weekly_sales = (
        weekly_sales_data.groupby("CreatedBy")["Price"]
        .sum()
        .add(end_date_sales, fill_value=0)  # Ensure today's sales are included
        .reindex(valid_executives, fill_value=0)  # Reindex to valid_executives
    )

    # Progress to monthly target (based on the filtered data)
    progress = (
        filtered_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(valid_executives, fill_value=0)  # Reindex to valid_executives
    )

    # Slice monthly_targets to valid_executives as well
    monthly_targets = targets_data.loc[(current_month, current_year), valid_executives]
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
        "HayleyA": "Hayley",
        "BethNW": "Beth",
        "BenT": "Ben",
        "jmurphy": "James",
        "MeganS": "Megan"
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

    # Apply styles for display
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



def run_dashboard():
    st.set_page_config(page_title="Hospitality Leadership Board", layout="wide")

    # Define valid executives for sales and services at the top of the function
    valid_sales_executives = ["dcoppin", "MillieS", "bgardiner", "dmontague", "jedwards"]
    valid_services_executives = ["HayleyA", "BethNW", "BenT", "jmurphy", "MeganS"]

    # Map usernames to full names
    user_mapping = {
        "dmontague": "Dan",
        "bgardiner": "Bobby",
        "dcoppin": "David",
        "jedwards": "Joey",
        "MillieS": "Millie",
        "HayleyA": "Hayley",
        "BethNW": "Beth",
        "BenT": "Ben",
        "jmurphy": "James",
        "MeganS": "Megan"
    }

    # Initialize page counter in session_state if not already present
    if "page" not in st.session_state:
        st.session_state.page = 0  # 0 for Sales Page, 1 for Services Page, 2 for Next Fixture Page

    # Sidebar: Date Range Filter
    st.sidebar.markdown(
        """
        <style>
            @font-face {
                font-family: 'Northbank-N5';
                src: url('fonts/Northbank-N5_2789720163.ttf') format('truetype');
            }
            .custom-date-range-title {
                text-align: center; 
                font-family: 'Northbank-N5'; /* Apply the custom font */
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

    # Set the default start and end dates
    today = datetime.today()
    start_date = today.replace(day=1)  # First day of the current month
    end_date = today  # Today's date as the default end date

    # Sidebar controls for Date Range
    col1, col2 = st.sidebar.columns(2)
    start_date_input = col1.date_input("Start Date", value=start_date, label_visibility="collapsed")
    end_date_input = col2.date_input("End Date", value=end_date, label_visibility="collapsed")

    # Sidebar: Budget Progress Widget for Sales Exec and Services Exec
    def render_budget_progress_widget(data, valid_executives, title):
        total_revenue = data["Price"].sum()
        current_month = start_date.strftime("%B")
        current_year = start_date.year
        monthly_targets = targets_data.loc[(current_month, current_year), valid_executives]
        total_target = monthly_targets.sum() if total_revenue > 0 else 0
        progress_percentage = (total_revenue / total_target * 100) if total_target > 0 else 0

        st.sidebar.markdown(
            f"""
            <style>
                @font-face {{
                    font-family: 'Chapman-Bold';
                    src: url('fonts/Chapman-Bold_2894575986.ttf') format('truetype');
                }}
                .custom-progress-widget {{
                    background-color: #fff0f0;
                    border: 2px solid #E41B17;
                    border-radius: 15px;
                    margin-top: 10px;
                    padding: 20px 15px;
                    text-align: center;
                    font-family: 'Chapman-Bold';
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

    # Filter data for sales and services based on the valid executives
    filtered_sales_data = filtered_df_without_seats[
        (filtered_df_without_seats["CreatedBy"].isin(valid_sales_executives)) &
        (pd.to_datetime(filtered_df_without_seats["CreatedOn"], errors="coerce", dayfirst=True) >= pd.to_datetime(start_date)) &
        (pd.to_datetime(filtered_df_without_seats["CreatedOn"], errors="coerce", dayfirst=True) <= pd.to_datetime(end_date))
    ]

    filtered_services_data = filtered_df_without_seats[
        (filtered_df_without_seats["CreatedBy"].isin(valid_services_executives)) &
        (pd.to_datetime(filtered_df_without_seats["CreatedOn"], errors="coerce", dayfirst=True) >= pd.to_datetime(start_date)) &
        (pd.to_datetime(filtered_df_without_seats["CreatedOn"], errors="coerce", dayfirst=True) <= pd.to_datetime(end_date))
    ]

    # Page navigation with auto-switching (every 15 seconds)
    if time.time() - st.session_state.get("last_switch_time", 0) >= 15:
        st.session_state.page = (st.session_state.page + 1) % 3  # Toggle between 0, 1, 2 (Sales, Services, Next Fixture)
        st.session_state.last_switch_time = time.time()  # Update the time of last switch

    # Page 1 - Sales Team Leaderboard
    if st.session_state.page == 0:
        st.markdown(
            """
            <style>
            @font-face {
                font-family: 'Northbank-N7';
                src: url('fonts/Northbank-N7_2789728357.ttf') format('truetype');
            }
            .custom-title {
                font-family: 'Northbank-N7';
                font-size: 80px;
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

        # Display leaderboard with updated data for the sales team (filtered by valid sales executives)
        monthly_progress, sales_made = calculate_monthly_progress(
            filtered_sales_data, start_date_input, end_date_input, valid_sales_executives
        )
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

        # Sidebar: Budget Progress for Sales Exec
        render_budget_progress_widget(filtered_sales_data, valid_sales_executives, "Sales Exec")

    # Page 2 - Services Team Leaderboard
    elif st.session_state.page == 1:
        st.markdown(
            """
            <style>
            @font-face {
                font-family: 'Northbank-N7';
                src: url('fonts/Northbank-N7_2789728357.ttf') format('truetype');
            }
            .custom-title {
                font-family: 'Northbank-N7';
                font-size: 80px;
                font-weight: bold;
                color: #E41B17;
                text-align: center;
            }
            </style>
            <div class="custom-title">
                ARSENAL PREMIUM SERVICES
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Display leaderboard with updated data for the services team (filtered by valid services executives)
        monthly_progress, sales_made = calculate_monthly_progress(
            filtered_services_data, start_date_input, end_date_input, valid_services_executives
        )
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

        # Sidebar: Budget Progress for Services Exec
        render_budget_progress_widget(filtered_services_data, valid_services_executives, "Services Exec")

    # Page 3 - Next Fixture Info
    elif st.session_state.page == 2:
        st.markdown(
            """
            <style>
            @font-face {
                font-family: 'Northbank-N7';
                src: url('fonts/Northbank-N7_2789728357.ttf') format('truetype');
            }
            .custom-title {
                font-family: 'Northbank-N7';
                font-size: 48px;
                font-weight: bold;
                color: #E41B17;
                text-align: center;
                margin-bottom: 40px;
            }
            .next-fixture-widget {
                background-color: #fff0f0; /* Soft pastel pink */
                border: 2px solid #E41B17; /* Red border for contrast */
                border-radius: 15px;
                padding: 20px 15px;
                text-align: center;
                font-family: 'Chapman-Bold';
                font-size: 28px;
                font-weight: bold;
                color: #E41B17;
            }
            .next-fixture-widget .highlight {
                font-size: 26px;
                color: #0047AB; /* Blue color for highlight */
            }
            </style>
            <div class="custom-title">
                NEXT HOME FIXTURE
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Fetch and display the next fixture information
        fixture_name, fixture_date, budget_target, event_competition = get_next_fixture(filtered_df_without_seats, budget_df)

        if fixture_name:
            # Filter data based on both Fixture Name and Event Competition
            filtered_fixture_data = filtered_df_without_seats[
                (filtered_df_without_seats["Fixture Name"] == fixture_name) &
                (filtered_df_without_seats["EventCompetition"] == event_competition)
            ]

            # Calculate days to fixture
            days_to_fixture = (fixture_date - datetime.now()).days

            # Calculate total revenue for the selected fixture
            fixture_revenue = filtered_fixture_data["Price"].sum()

            # Calculate budget achieved for the fixture
            budget_achieved = round((fixture_revenue / budget_target) * 100, 2) if budget_target > 0 else 0

            # Display fixture with event competition
            fixture_display = f"{fixture_name} ({event_competition})"

            st.markdown(
                f"""
                <div class="next-fixture-widget">
                    Next Fixture: <br>
                    <span class="highlight">{fixture_display}</span><br>
                    Days to Fixture: <span class="highlight">{days_to_fixture} days</span><br>
                    Budget Target Achieved: <span class="highlight">{budget_achieved}%</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="text-align: center; font-family: 'Chapman-Bold'; font-size: 40px; color: #e41b17;">
                    No upcoming fixtures found.
                </div>
                """,
                unsafe_allow_html=True
            )

    # Scrolling message at the bottom of the page (for all pages)
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
