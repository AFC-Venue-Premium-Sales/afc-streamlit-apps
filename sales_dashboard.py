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
    "dmontague": [155000, 155000, 135000, 110000, 90000, 65000],
    "MeganS": [42500, 42500, 36500, 30500, 24500, 18500],
    "BethNW": [42500, 42500, 36500, 30500, 24500, 18500],
    "HayleyA": [42500, 42500, 36500, 30500, 24500, 18500],
    "jmurphy": [35000, 35000, 30000, 25000, 20000, 15000],
    "BenT": [35000, 35000, 30000, 25000, 20000, 15000],
}).set_index(["Month", "Year"])

# Specify your list of executives
valid_executives = ["dcoppin", "BethNW", "bgardiner", "MeganS", "dmontague", 
                    "jedwards", "HayleyA", "MillieS", "BenT", "jmurphy"]



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

def calculate_monthly_progress(data, start_date, end_date):
    # Map usernames to actual names
    user_name_mapping = {
        "dmontague": "Dan",
        "BethNW": "Beth",
        "jmurphy": "James",
        "bgardiner": "Bobby",
        "dcoppin": "Coppin",
        "MeganS": "Megs",
        "HayleyA": "Hayley",
        "BenT": "Ben",
        "jedwards": "Joey",
        "MillieS": "Millie"
    }

    data["CreatedOn"] = pd.to_datetime(data["CreatedOn"], errors="coerce", dayfirst=True)
    filtered_data = data[
        (data["CreatedOn"] >= pd.to_datetime(start_date)) &
        (data["CreatedOn"] <= pd.to_datetime(end_date))
    ]

    current_month = start_date.strftime("%B")
    current_year = start_date.year

    if (current_month, current_year) not in targets_data.index:
        return None, []

    # Today's sales (based on the end_date of the range)
    today_sales_data = data[data["CreatedOn"].dt.date == pd.Timestamp(end_date).date()]
    today_sales_total = today_sales_data.groupby("CreatedBy")["Price"].sum().reindex(targets_data.columns, fill_value=0)

    # Weekly sales (from Monday to end_date)
    start_of_week = pd.Timestamp(end_date) - pd.Timedelta(days=pd.Timestamp(end_date).weekday())
    weekly_sales_data = data[
        (data["CreatedOn"] >= start_of_week) &
        (data["CreatedOn"] <= pd.to_datetime(end_date))
    ]
    weekly_sales_total = weekly_sales_data.groupby("CreatedBy")["Price"].sum().reindex(targets_data.columns, fill_value=0)

    # Progress calculation
    progress = (
        filtered_data.groupby("CreatedBy")["Price"]
        .sum()
        .reindex(targets_data.columns, fill_value=0)
    )
    monthly_targets = targets_data.loc[(current_month, current_year)]

    progress_data = pd.DataFrame({
        "Sales Exec": progress.index.map(user_name_mapping),
        "Today's Sales": today_sales_total.values,
        "Weekly Sales": weekly_sales_total.values,
        "Current Revenue": progress.values,
        "Target": monthly_targets.values,
        "Variance": (progress - monthly_targets).values,
        "% Sold (Numeric)": (progress / monthly_targets * 100).round(0),
    }).reset_index(drop=True)

    # Calculate totals
    totals_row = pd.DataFrame({
        "Sales Exec": ["Totals"],
        "Today's Sales": [progress_data["Today's Sales"].sum()],
        "Weekly Sales": [progress_data["Weekly Sales"].sum()],
        "Current Revenue": [progress_data["Current Revenue"].sum()],
        "Target": [""],
        "Variance": [""],
        "% Sold (Numeric)": [""],
    })

    # Concatenate the totals row
    progress_data = pd.concat([progress_data, totals_row], ignore_index=True)

    # Format columns for display
    progress_data["Today's Sales"] = progress_data["Today's Sales"].apply(lambda x: f"\u00a3{x:,.0f}" if isinstance(x, (int, float)) else x)
    progress_data["Weekly Sales"] = progress_data["Weekly Sales"].apply(lambda x: f"\u00a3{x:,.0f}" if isinstance(x, (int, float)) else x)
    progress_data["Current Revenue"] = progress_data["Current Revenue"].apply(lambda x: f"\u00a3{x:,.0f}" if isinstance(x, (int, float)) else x)
    progress_data["Variance"] = progress_data["Variance"].apply(
        lambda x: f"({abs(x):,.0f})" if isinstance(x, (int, float)) and x < 0 else f"{x:,.0f}" if isinstance(x, (int, float)) else x
    )

    # Progress to Monthly Target with new logic
    days_in_month = pd.Period(end_date.strftime('%Y-%m')).days_in_month
    days_elapsed = pd.Timestamp(end_date).day
    pace_percentage = (days_elapsed / days_in_month) * 100

    def style_progress(value):
        if value == "":
            return ""
        elif value >= pace_percentage:
            return f"<div style='background-color: green; color: white; font-family: Chapman-Bold; font-size: 24px; padding: 10px;'>{value:.0f}%</div>"
        elif value >= 0.5 * pace_percentage:
            return f"<div style='background-color: orange; color: white; font-family: Chapman-Bold; font-size: 24px; padding: 10px;'>{value:.0f}%</div>"
        else:
            return f"<div style='background-color: red; color: white; font-family: Chapman-Bold; font-size: 24px; padding: 10px;'>{value:.0f}%</div>"

    progress_data["Progress to Monthly Target"] = progress_data["% Sold (Numeric)"].apply(style_progress)
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
    valid_executives = ["dcoppin", "BethNW", "bgardiner", "MeganS", "dmontague", 
                        "jedwards", "HayleyA", "MillieS", "BenT", "jmurphy"]

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
    
    st_autorefresh(interval=300 * 1000, key="auto_refresh")  # Auto-refresh every 2 minutes
    
    st.sidebar.text(f"Refresh Count: {st.session_state['refresh_count']}")
    return refresh_time



def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")
    
# Get the base64 string of the image
crest_base64 = get_base64_image("assets/arsenal_crest_gold.png")

# Run dashboard
def run_dashboard():
    
    # Dashboard Title
    st.markdown(
        f"""
        <style>
        @font-face {{
            font-family: 'Northbank-N7';
            src: url('fonts/Northbank-N7_2789728357.ttf') format('truetype');
        }}
        .custom-title-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: -50px; /* Adjusts the position of the title */
        }}
        .custom-title {{
            font-family: 'Northbank-N7';
            font-size: 60px;
            font-weight: bold;
            color: #E41B17;
            text-align: center; /* Center-align the title */
        }}
        </style>
        <div class="custom-title-container">
            <div class="custom-title">
                ARSENAL PREMIUM SALES
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



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
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("Start Date", value=datetime.now().replace(day=1), label_visibility="collapsed")
    end_date = col2.date_input("End Date", value=datetime.now(), label_visibility="collapsed")

   # Total Sales Section
    total_sales = calculate_total_sales(filtered_df_without_seats)
    st.sidebar.markdown(
        f"""
        <style>
            @font-face {{
                font-family: 'Northbank-N5';
                src: url('fonts/Northbank-N5_2789720163.ttf') format('truetype');
            }}
            .custom-sales-box {{
                padding: 20px 15px; /* Match padding of the other widgets */
                margin-bottom: 30px; /* Space between widgets */
                text-align: center; /* Center align all text */
                font-family: 'Northbank-N5'; /* Apply the custom font */
                font-size: 28px; /* Match font size */
                font-weight: bold; /* Match weight */
                color: #E41B17; /* Match font color */
            }}
            .custom-sales-header {{
                font-size: 25px;
                color: #E41B17;
                text-align: center;
                font-weight: bold;
            }}
            .custom-sales-value {{
                font-size: 28px;
                color: #E41B17;
                text-align: center;
                font-weight: bold;
            }}
        </style>
        <div class="custom-sales-box">
            <span class="custom-sales-header"> 🍯 Sales To Date:</span><br>
            <span class="custom-sales-value">£{total_sales:,.0f}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    
    # Premium Monthly Progress Section
    valid_executives = ["dcoppin", "BethNW", "bgardiner", "MeganS", "dmontague", 
                        "jedwards", "HayleyA", "MillieS", "BenT", "jmurphy"]

    # Filter the data for valid executives
    filtered_executive_data = filtered_df_without_seats[filtered_df_without_seats["CreatedBy"].isin(valid_executives)]

    # Convert the CreatedOn column to datetime format
    filtered_executive_data["CreatedOn"] = pd.to_datetime(
        filtered_executive_data["CreatedOn"], errors="coerce", dayfirst=True
    )

    # Calculate total revenue for the specified date range and valid executives
    total_revenue = filtered_executive_data[
        (filtered_executive_data["CreatedOn"] >= pd.to_datetime(start_date)) &
        (filtered_executive_data["CreatedOn"] <= pd.to_datetime(end_date))
    ]["Price"].sum()

    # Extract the current month and year to find the matching targets
    current_month = start_date.strftime("%B")
    current_year = start_date.year

    # Retrieve monthly targets for the valid executives
    if (current_month, current_year) in targets_data.index:
        monthly_targets = targets_data.loc[(current_month, current_year), valid_executives]
        total_target = monthly_targets.sum()
    else:
        monthly_targets = None
        total_target = 0

    # Calculate progress percentage
    progress_percentage = (total_revenue / total_target * 100) if total_target > 0 else 0

    # Render the widget
    if total_target == 0:
        st.sidebar.markdown(
            """
            <style>
                @font-face {
                    font-family: 'Chapman-Bold';
                    src: url('fonts/Chapman-Bold_2894575986.ttf') format('truetype');
                }
                .custom-out-of-bounds {
                    background-color: #fff0f0;
                    border: 2px solid #E41B17;
                    border-radius: 15px;
                    padding: 20px 15px;
                    margin-bottom: 30px;
                    text-align: center;
                    font-family: 'Chapman-Bold';
                    font-size: 28px;
                    font-weight: bold;
                    color: #E41B17;
                }
            </style>
            <div class="custom-out-of-bounds">
                ⚠️ Selected date range is out of bounds for available targets.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
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
                    padding: 20px 15px;
                    text-align: center;
                    font-family: 'Chapman-Bold';
                    font-size: 28px;
                    font-weight: bold;
                    color: #E41B17;
                }}
                .custom-progress-widget span {{
                    font-size: 22px;
                    color: #0047AB;
                }}
                .custom-progress-widget .highlight {{
                    font-size: 24px;
                    color: #E41B17;
                }}
            </style>
            <div class="custom-progress-widget">
                📊 Monthly Progress Budget Target <br>
                <span>Total Revenue ({start_date.strftime("%B")}):</span><br>
                <span class="highlight">£{total_revenue:,.0f}</span><br>
                <span>Total Target:</span><br>
                <span class="highlight">£{total_target:,.0f}</span><br>
                <span>🌟 Progress Achieved:</span><br>
                <span class="highlight">{progress_percentage:.0f}%</span>
            </div>
            """,
            unsafe_allow_html=True
        )


    # Next Fixture Section
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

        # Calculate budget achieved
        budget_achieved = round((fixture_revenue / budget_target) * 100, 2) if budget_target > 0 else 0

        # Display fixture with event competition
        fixture_display = f"{fixture_name} ({event_competition})"

        # Render the fixture details
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
                padding: 20px 15px;
                text-align: center;
                font-family: 'Chapman-Bold';
                font-size: 28px;
                font-weight: bold;
                color: #E41B17;
            }}
            .next-fixture-widget span {{
                display: block;
                margin-bottom: 10px;
            }}
            .next-fixture-widget .fixture-title {{
                font-size: 22px;
                color: #E41B17;
            }}
            .next-fixture-widget .fixture-info {{
                font-size: 22px;
                color: #0047AB;
            }}
            .next-fixture-widget .fixture-days {{
                font-size: 24px;
                color: #E41B17;
            }}
            </style>
            <div class="next-fixture-widget">
                🏟️ Next Fixture <br>
                <span class="fixture-title">{fixture_display}</span>
                <span class="fixture-info">⏳ Days to Fixture:</span>
                <span class="fixture-days">{days_to_fixture} days</span>
                <span class="fixture-info">🎯 Budget Target Achieved:</span>
                <span class="fixture-days">{budget_achieved}%</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
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
            unsafe_allow_html=True
        )

            
    # Sidebar: Auto-refresh
    refresh_time = auto_refresh()
    st.sidebar.markdown(
        f"""
        <style>
            @font-face {{
                font-family: 'Northbank-N5';
                src: url('fonts/Northbank-N5_2789720163.ttf') format('truetype');
            }}
            .custom-refresh-box {{
                background-color: #fff0f0;
                border: 2px solid #E41B17;
                border-radius: 10px;
                padding: 20px; /* Add extra padding for better spacing */
                margin-bottom: 20px; /* Space below widget */
                font-family: 'Northbank-N5'; /* Custom font applied */
                font-size: 28px; /* Larger font size for visibility */
                color: #E41B17; /* Arsenal red text */
                font-weight: bold; /* Make text bold */
            }}
            .custom-refresh-time {{
                font-size: 20px;
                font-weight: bold;
                color: #E41B17;
            }}
        </style>
        <div class="custom-refresh-box">
            <span>🔄 Latest Data Update:</span><br>
            <span class="custom-refresh-time">{refresh_time}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    
    # Monthly Progress Table
    monthly_progress, sales_made = calculate_monthly_progress(filtered_df_without_seats, start_date, end_date)

    if monthly_progress is not None:
        st.markdown(
            """
            <style>
            @font-face {
                font-family: 'Chapman-Bold';
                src: url('fonts/Chapman-Bold_2894575986.ttf') format('truetype');
            }
            .custom-leaderboard-title {
                font-family: 'Northbank-N5Bold';
                font-size: 40px;
                font-weight: bold;
                color: #E41B17;
                text-align: center;
                margin-top: -30px; /* Moves the leaderboard title closer to the ARSENAL PREMIUM SALES title */
            }
            </style>
            <div class="custom-leaderboard-title">
                MONTHLY PREMIUM LEADERBOARD
            </div>
            """,
            unsafe_allow_html=True,
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
                {monthly_progress.to_html(classes='big-table', escape=False, index=False)}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("Monthly Progress data not available for the selected date range.")

        
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


if __name__ == "__main__":
    run_dashboard()


