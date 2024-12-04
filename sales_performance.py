import streamlit as st
import pandas as pd
import numpy as np
import base64
from datetime import datetime
from io import BytesIO
from tjt_hosp_api import filtered_df_without_seats
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re


def load_budget_targets():
    # Load budget targets from the specified Excel file
    file_path = "/Users/cmunthali/Documents/PYTHON/API/TJT/budget_target_2425.xlsx"
    budget_df = pd.read_excel(file_path)
    # Clean 'Budget Target' column to remove currency symbols and convert to numeric
    budget_df.columns = budget_df.columns.str.strip()  # Strip any leading/trailing whitespace from column names
    budget_df['Budget Target'] = budget_df['Budget Target'].replace('[^0-9.]', '', regex=True).astype(float)
    # Clean 'EventCompetition' column to remove any extra whitespace
    budget_df['EventCompetition'] = budget_df['EventCompetition'].str.strip()
    return budget_df

def generate_event_level_men_cumulative_sales_chart(df, start_date, end_date):
    """
    Generate a cumulative percentage-to-target sales chart for Champions League and Premier League fixtures.
    X-axis is directly based on 'KickOffEventStart' dates.
    """
    # Load the budget targets data
    budget_df = load_budget_targets()

    # Clean columns to remove any whitespace in both the main dataframe and budget dataframe
    df.columns = df.columns.str.strip()
    df['EventCompetition'] = df['EventCompetition'].str.strip()
    df['Fixture Name'] = df['Fixture Name'].str.strip()

    # Merge budget targets with the main DataFrame
    df = df.merge(budget_df, on=['Fixture Name', 'EventCompetition'], how='left')

    # Ensure 'PaymentTime' and 'KickOffEventStart' are datetime
    df['PaymentTime'] = pd.to_datetime(df['PaymentTime'], errors='coerce')
    df['KickOffEventStart'] = pd.to_datetime(df['KickOffEventStart'], errors='coerce')

    # Check if 'Budget Target' exists in the DataFrame after merging
    if 'Budget Target' not in df.columns:
        raise ValueError("The 'Budget Target' column is missing from the merged DataFrame. Please check the input budget file.")

    df['IsPaid'] = df['IsPaid'].astype(str).fillna('FALSE')

    # Filter for Premier League and Champions League fixtures between start_date and end_date
    allowed_competitions = ['Premier League', 'UEFA Champions League', 'Carabao Cup', 'Emirates Cup']
    filtered_data = df[
        (df['PaymentTime'] >= start_date) &
        (df['PaymentTime'] <= end_date) &
        (df['IsPaid'].str.upper() == 'TRUE') &
        (df['EventCompetition'].isin(allowed_competitions))
    ]

    # Normalize Discount column to lowercase for consistency
    filtered_data['Discount'] = filtered_data['Discount'].astype(str).str.lower().str.strip()

    # Exclude rows based on keywords in Discount
    exclude_keywords = ["credit", "voucher", "gift voucher", "discount", "pldl"]
    mask = ~filtered_data['Discount'].str.contains('|'.join([re.escape(keyword) for keyword in exclude_keywords]), case=False, na=False)

    # Filter out unwanted rows based on keywords in Discount column
    filtered_data = filtered_data[mask]

    # Calculate TotalEffectivePrice using numpy where for vectorized calculation
    filtered_data['TotalEffectivePrice'] = np.where(
        filtered_data['TotalPrice'] > 0,
        filtered_data['TotalPrice'],
        np.where(filtered_data['DiscountValue'].notna(), filtered_data['DiscountValue'], 0)
    )

    # Group by fixture and PaymentTime to calculate cumulative sales
    grouped_data = (
        filtered_data.groupby(['Fixture Name', 'PaymentTime'])
        .agg(
            DailySales=('TotalEffectivePrice', 'sum'),
            KickOffDate=('KickOffEventStart', 'first'),  # Use the first occurrence of the kickoff date
            BudgetTarget=('Budget Target', 'first')
        )
        .reset_index()
    )

    # Sort the grouped data by 'PaymentTime' to ensure proper chronological order before calculating cumulative sales
    grouped_data = grouped_data.sort_values(by=['Fixture Name', 'PaymentTime'])
    grouped_data['CumulativeSales'] = grouped_data.groupby('Fixture Name')['DailySales'].cumsum()
    grouped_data['RevenuePercentage'] = (grouped_data['CumulativeSales'] / grouped_data['BudgetTarget']) * 100

    # Map competition to colors
    competition_colors = {
        'Premier League': 'green',
        'UEFA Champions League': 'gold',
        'Carabao Cup': 'blue',
        'Emirates Cup': 'purple'
    }
    abbreviations = {
        "Chelsea": "CHE", "Tottenham": "TOT", "Manchester United": "MANU",
        "West Ham": "WES", "Paris Saint-Germain": "PSG", "Liverpool": "LIV",
        "Brighton": "BRI", "Leicester": "LEI", "Wolves": "WOL", "Everton": "EVE",
        "Nottingham Forest": "NFO", "Aston Villa": "AST", "Shakhtar Donetsk": "SHA",
        "Dinamo Zagreb": "DIN", "Monaco": "MON", "Manchester City": "MCI"
    }

    # Create the plot with a black background
    fig, ax = plt.subplots(figsize=(18, 12))

    # Set the background color to black
    fig.patch.set_facecolor('#121212')  # Dark background for the figure
    ax.set_facecolor('#121212')  # Dark background for the axis
    ax.tick_params(axis='x', colors='white')  # White x-axis tick labels
    ax.tick_params(axis='y', colors='white')  # White y-axis tick labels
    ax.spines['bottom'].set_color('white')  # White bottom axis line
    ax.spines['left'].set_color('white')  # White left axis line

    # Plot each fixture
    for fixture_name, fixture_data in grouped_data.groupby('Fixture Name'):
        opponent = fixture_name.split(' v ')[-1]  # Extract the opponent's name
        abbrev = abbreviations.get(opponent, opponent[:3].upper())
        color = competition_colors.get(filtered_data[filtered_data['Fixture Name'] == fixture_name]['EventCompetition'].iloc[0], 'blue')

        # Sort data by PaymentTime for proper plotting
        fixture_data = fixture_data.sort_values('PaymentTime')

        # Determine if the fixture has been played using end_date
        kick_off_date = fixture_data['KickOffDate'].iloc[0]
        cumulative_percentage = fixture_data['RevenuePercentage'].iloc[-1]
        if kick_off_date < pd.Timestamp.now():  # Fixture has been played
            abbrev += f"(p, {cumulative_percentage:.0f}%)"
            annotation_color = 'red'
            annotation_weight = 'bold'
        else:  # Fixture is upcoming
            days_left = (kick_off_date - pd.Timestamp.now()).days
            abbrev += f"({days_left} days, {cumulative_percentage:.0f}%)"
            annotation_color = 'white'  # White for upcoming fixtures
            annotation_weight = 'normal'

        # Plotting the cumulative line
        ax.plot(
            fixture_data['PaymentTime'].dt.date,  # Use only dates on the x-axis
            fixture_data['RevenuePercentage'],
            label=abbrev,
            color=color,
            linewidth=1  # Increase linewidth for better visibility
        )

        # Annotate with an arrow for specific opponents to avoid clutter
        if opponent in ["Manchester City", "Aston Villa"]:
            ax.annotate(
                abbrev, 
                xy=(fixture_data['PaymentTime'].dt.date.iloc[-1], fixture_data['RevenuePercentage'].iloc[-1]),
                xytext=(fixture_data['PaymentTime'].dt.date.iloc[-1], fixture_data['RevenuePercentage'].iloc[-1] + 5),
                arrowprops=dict(arrowstyle="->", lw=0.5, color=annotation_color),
                fontsize=12,  # Increase font size for annotations
                color=annotation_color,
                weight=annotation_weight
            )
        else:
            ax.text(
                fixture_data['PaymentTime'].dt.date.iloc[-1],
                fixture_data['RevenuePercentage'].iloc[-1],
                abbrev,
                fontsize=12,  # Increase font size for annotations
                color=annotation_color,
                weight=annotation_weight
            )

    # Format the plot
    ax.set_title("AFC Men's Cumulative Revenue 24/25", fontsize=16, color='white')
    ax.set_xlabel("Date", fontsize=14, color='white')
    ax.set_ylabel("Revenue (% of Budget Target)", fontsize=14, color='white')
    ax.axhline(y=100, color='red', linestyle='--', linewidth=1)
    ax.grid(False)

    # Manually set the x-axis limits to be within the actual data range
    min_date = start_date.date()
    max_date = grouped_data['PaymentTime'].max().date() if not grouped_data.empty else end_date.date()
    ax.set_xlim([min_date, max_date])

    # Format x-axis to show only the date without time and set interval to every 10 days
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()

    # Set y-axis to show values as percentages (20%, 40%, etc.)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))

    # Add color legend for all competitions
    handles = [
        plt.Line2D([0], [0], color='green', lw=2, label='Premier League'),
        plt.Line2D([0], [0], color='gold', lw=2, label='Champions League'),
        plt.Line2D([0], [0], color='blue', lw=2, label='Carabao Cup'),
        plt.Line2D([0], [0], color='purple', lw=2, label='Emirates Cup'),
        plt.Line2D([], [], color='red', linestyle='--', linewidth=2, label='Budget Target (100%)')
    ]
    
    # Set legend at the bottom with better positioning to avoid overlap
    ax.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, -0.25), fontsize=10, frameon=False, facecolor='black', labelcolor='white', ncol=3)

    # Save the chart as a PNG with high DPI and return the base64 encoded version
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300)  # Increase DPI for better resolution
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')



import streamlit as st
import pandas as pd
import numpy as np
import base64
from datetime import datetime
from io import BytesIO
from tjt_hosp_api import filtered_df_without_seats
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re


# Ensure the load_budget_targets and generate_event_level_men_cumulative_sales_chart are defined or imported here.

def run_app():
    specified_users = ['dcoppin', 'Jedwards', 'jedwards', 'bgardiner', 'BenT', 'jmurphy', 'ayildirim',
                       'MeganS', 'BethNW', 'HayleyA', 'LucyB', 'Conor', 'SavR', 'MillieS']

    st.title('💷  AFC Finance x MBM Reconciliation 💷')

    st.markdown("""
    ### ℹ️ About
    This app provides sales metrics from TJT's data export API. 
    
    The app allows you to filter results by date, user, fixture, payment status, and paid status for tailored insights. 
    
    Please note that sales from 'Platinum' package & 'Woolwich Package' sales have been excluded from this.
    """)

    loaded_api_df = filtered_df_without_seats

    if loaded_api_df is not None:
        st.sidebar.success("✅ Data retrieved successfully.")
        progress_bar = st.sidebar.progress(0)
        progress_bar.progress(10)
        progress_bar.progress(30)
        progress_bar.progress(50)
        progress_bar.progress(100)

        # Initialize filtered_data with processed_data
        filtered_data = loaded_api_df.copy()

        # Ensure 'Discount' column is treated as strings
        filtered_data['Discount'] = filtered_data['Discount'].astype(str)

        # Ensure 'DiscountValue' is treated as numeric, converting invalid entries to NaN
        filtered_data['DiscountValue'] = pd.to_numeric(filtered_data['DiscountValue'], errors='coerce')

        # Ensure other numeric columns like 'TotalPrice' are also correctly treated as numeric
        numeric_columns = ['TotalPrice', 'DiscountValue']  # Add any other numeric columns if necessary
        for column in numeric_columns:
            filtered_data[column] = pd.to_numeric(filtered_data[column], errors='coerce')

        # Convert 'CreatedOn' column to datetime format for both filtered_data and loaded_api_df
        filtered_data['CreatedOn'] = pd.to_datetime(filtered_data['CreatedOn'], errors='coerce')
        loaded_api_df['CreatedOn'] = pd.to_datetime(loaded_api_df['CreatedOn'], errors='coerce')

        # Filtered data based on excluding 'Platinum' package
        filtered_data = filtered_data[filtered_data['Package Name'] != 'Platinum']

        # Sidebar filters
        st.sidebar.header("Filter Data by Date and Time")
        date_range = st.sidebar.date_input("📅 Select Date Range", [])
        start_time = st.sidebar.time_input("⏰ Start Time", value=datetime.now().replace(hour=0, minute=0, second=0).time())
        end_time = st.sidebar.time_input("⏰ End Time", value=datetime.now().replace(hour=23, minute=59, second=59).time())

        # Combine date and time inputs into full datetime objects
        if len(date_range) == 1:
            min_date = datetime.combine(date_range[0], start_time)
            max_date = datetime.combine(date_range[0], end_time)
        elif len(date_range) == 2:
            min_date = datetime.combine(date_range[0], start_time)
            max_date = datetime.combine(date_range[1], end_time)
        else:
            min_date, max_date = None, None

        valid_usernames = [user for user in specified_users if user in pd.unique(filtered_data['CreatedBy'])]
        event_names = pd.unique(filtered_data['Fixture Name'])
        sale_location = pd.unique(filtered_data['SaleLocation'])
        selected_events = st.sidebar.multiselect("🎫 Select Events", options=event_names, default=None)
        selected_sale_location = st.sidebar.multiselect("📍 Select SaleLocation", options=sale_location, default=None)
        selected_users = st.sidebar.multiselect("👤 Select Execs", options=valid_usernames, default=None)
        paid_options = pd.unique(filtered_data['IsPaid'])
        selected_paid = st.sidebar.selectbox("💰 Filter by IsPaid", options=paid_options)

        # Apply date range filter with time
        if min_date and max_date:
            filtered_data = filtered_data[(filtered_data['CreatedOn'] >= min_date) & (filtered_data['CreatedOn'] <= max_date)]

        # Apply SaleLocation filter
        if selected_sale_location:
            filtered_data = filtered_data[filtered_data['SaleLocation'].isin(selected_sale_location)]

        # Apply user filter
        if selected_users:
            filtered_data = filtered_data[filtered_data['CreatedBy'].isin(selected_users)]

        # Apply event filter
        if selected_events:
            filtered_data = filtered_data[filtered_data['Fixture Name'].isin(selected_events)]

        # Discount Filter with "Select All" option
        select_all_discounts = st.sidebar.checkbox("Select All Discounts", value=True)
        if select_all_discounts:
            selected_discount_options = pd.unique(filtered_data['Discount']).tolist()
        else:
            selected_discount_options = st.sidebar.multiselect("🔖 Filter by Discount Type", options=pd.unique(filtered_data['Discount']), default=pd.unique(filtered_data['Discount']).tolist())

        # Apply discount filter
        filtered_data = filtered_data[filtered_data['Discount'].isin(selected_discount_options)]

        # Static total: Get accumulated sales from June 18th, 2024 till now
        static_start_date = datetime(2024, 6, 18, 0, 0, 0)
        static_total = loaded_api_df[(loaded_api_df['CreatedOn'] >= static_start_date)]['TotalPrice'].sum()

        # Dynamic total: Affected by filters
        dynamic_total = filtered_data['TotalPrice'].sum()

        # Display results
        if not filtered_data.empty:
            st.write("### 💼 Total Accumulated Sales")
            st.write(f"Total Accumulated Sales (Static) since June 18th : **£{static_total:,.2f}** 🎉")

            st.write("### 💼 Filtered Accumulated Sales")
            st.write(f"Total Accumulated Sales (Filtered): **£{dynamic_total:,.2f}** 🎉")

            st.write("### 💳 Sales with 'Other' Payment")
            total_sold_by_other = filtered_data['DiscountValue'].sum()
            other_sales_total = dynamic_total + total_sold_by_other
            st.write(f"Accumulated sales with 'Other' payments included: **£{other_sales_total:,.2f}**")

            # Total Sales Per Package
            st.write("### 🎟️ Total Sales Per Package")
            total_sold_per_package = filtered_data.groupby('Package Name')['TotalPrice'].sum().reset_index()
            total_sold_per_package['TotalPrice'] = total_sold_per_package['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold_per_package)

            # Add cumulative sales chart after Total Sales Per Package
            st.write("### 📊 Men's Cumulative Revenue Chart")
            cumulative_chart_data = generate_event_level_men_cumulative_sales_chart(filtered_data, min_date, max_date)
            st.image(BytesIO(base64.b64decode(cumulative_chart_data)), use_column_width=True)

            # Other existing sections for Total Sales Per Fixture, Total Sales Per Location, etc.
            # Add them as needed after this section

            # Download button for filtered data
            output = BytesIO()
            output.write(filtered_data.to_csv(index=False).encode('utf-8'))
            output.seek(0)

            st.download_button(
                label="💾 Download Filtered Data For Further Analysis",
                data=output,
                file_name='filtered_sales_data.csv',
                mime='text/csv',
            )

        else:
            st.warning("⚠️ No data available for the selected filters.")
    else:
        st.sidebar.warning("🚨 Please upload a file to proceed.")


if __name__ == "__main__":
    run_app()
