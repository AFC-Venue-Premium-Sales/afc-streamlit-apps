import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import importlib
import sys
sys.path.append("/Users/cmunthali/Documents/PYTHON/APPS")
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from charts_ import (
    generate_event_level_men_cumulative_sales_chart,
    generate_event_level_women_cumulative_sales_chart,
    generate_event_level_concert_cumulative_sales_chart
)

# Dynamically import tjt_hosp_api
try:
    tjt_hosp_api = importlib.import_module('tjt_hosp_api')
    filtered_df_without_seats = getattr(tjt_hosp_api, 'filtered_df_without_seats', None)
    if filtered_df_without_seats is None:
        raise ImportError("filtered_df_without_seats is not available in tjt_hosp_api.")
except ImportError as e:
    st.error(f"❌ Error importing tjt_hosp_api: {e}")
    filtered_df_without_seats = None

def run_app():
    specified_users = ['dcoppin', 'Jedwards', 'jedwards', 'bgardiner', 'BenT', 'jmurphy', 'ayildirim',
                       'MeganS', 'BethNW', 'HayleyA', 'LucyB', 'Conor', 'SavR', 'MillieS', 'dmontague']
    
        # ─── Load fixture budget targets from Excel ───────────────────────────────────
    budget_file = "budget_target_2425.xlsx"
    budget_df = pd.read_excel(budget_file)
    budget_df.columns = budget_df.columns.str.strip()

    # Ensure our three merge‐keys are normalized
    budget_df["Fixture Name"]      = budget_df["Fixture Name"].str.strip()
    budget_df["EventCompetition"]  = budget_df["EventCompetition"].str.strip()
    budget_df["KickOffEventStart"] = pd.to_datetime(
        budget_df["KickOffEventStart"], dayfirst=True, errors="coerce"
    )
    # ───────────────────────────────────────────────────────────────────────────────




    st.title('💷 MBM Sales 💷')
    
    # Instructions Section
    with st.expander("📖 How to Use This App - Sales Performance"):
        st.markdown("""
        ### ℹ️ About
        This app provides sales metrics from TJT's data. 
        You can filter results by date, user, fixture, payment status, and paid status for tailored insights
        
        **Note:** To access the latest sales updates, please click the 'Refresh Data' button & let it load.
        
        **Step-by-Step Guide:**
        1. **Filter Data**:
           - Use the sidebar to select a **date range** and **time range** for the data.
           - Filter data by **executives**, **events**, or **competitions**.
        2. **View Key Metrics**:
           - See total revenue, packages sold, and top executive performance at a glance including cumulative sales towards budget.
        3. **Refresh Data**:
           - Click the **Refresh Data** button in the sidebar to load the latest updates.
        4. **Export**:
           - Use the available export options to download filtered data or visualizations for further analysis.

        **Helpful Tips:**
        - If no filters are applied, the app displays all available data.
        - Contact [cmunthali@arsenal.co.uk](mailto:cmunthali@arsenal.co.uk) for any issues or inquiries.
        """)

    # Dynamically fetch hospitality data on app start
    loaded_api_df = filtered_df_without_seats

    if loaded_api_df is None or loaded_api_df.empty:
        st.warning("⚠️ No data available. Please refresh to load the latest data.")
        return

    # Display progress bar
    progress_bar = st.sidebar.progress(0)
    for progress in [10, 30, 50, 100]:
        progress_bar.progress(progress)

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
        numeric_columns = ['TotalPrice', 'DiscountValue']
        for column in numeric_columns:
            filtered_data[column] = pd.to_numeric(filtered_data[column], errors='coerce')

        # Convert 'CreatedOn' column to datetime format for both filtered_data and loaded_api_df
        filtered_data['CreatedOn'] = pd.to_datetime(
            filtered_data['CreatedOn'], format='%d-%m-%Y %H:%M', errors='coerce'
        )
        loaded_api_df['CreatedOn'] = pd.to_datetime(
            loaded_api_df['CreatedOn'], format='%d-%m-%Y %H:%M', errors='coerce'
        )

        # ─── First, coerce KickOffEventStart in your sales DataFrame to datetime ──────
        filtered_data['KickOffEventStart'] = pd.to_datetime(
            filtered_data['KickOffEventStart'],
            format='%d-%m-%Y %H:%M', 
            dayfirst=True,
            errors='coerce'
        )

        # ─── Then merge against the budget file (which already has it as datetime) ──────
        filtered_data = pd.merge(
            filtered_data,
            budget_df,
            how="left",
            on=["Fixture Name", "EventCompetition", "KickOffEventStart"]
        )


        # Add 'Days to Fixture' column
        today = pd.Timestamp.now()
        filtered_data['Days to Fixture'] = (filtered_data['KickOffEventStart'] - today).dt.days

        # Handle missing or invalid dates
        filtered_data['Days to Fixture'] = filtered_data['Days to Fixture'].fillna(-1).astype(int)

        # Sidebar filters
        st.sidebar.header("Filter Data by Date and Time")
        date_range = st.sidebar.date_input(
            "📅 Select Date Range", [], key="unique_sales_date_range"
        )
        start_time = st.sidebar.time_input(
            "⏰ Start Time", value=datetime.now().replace(hour=0, minute=0, second=0).time(), key="unique_start_time"
        )
        end_time = st.sidebar.time_input(
            "⏰ End Time", value=datetime.now().replace(hour=23, minute=59, second=59).time(), key="unique_end_time"
        )

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

        # Combine event categories from both 'EventCompetition' and 'EventCategory'
        competition_vals = pd.unique(filtered_data['EventCompetition'])
        if 'EventCategory' in filtered_data.columns:
            category_vals = pd.unique(filtered_data['EventCategory'])
            # Create a union of both arrays and convert to a sorted list
            event_categories = sorted(list(set(competition_vals.tolist() + category_vals.tolist())))
        else:
            event_categories = competition_vals.tolist()

        # Add filters
        selected_categories = st.sidebar.multiselect(
            "Select Event Category",
            options=event_categories,
            default=None,
            key="unique_selected_categories_key"
        )


        sale_location = pd.unique(filtered_data['SaleLocation'])
        selected_events = st.sidebar.multiselect(
            "🎫 Select Events",
            options=event_names,
            default=None,
            key="unique_selected_events_key"
        )

        selected_sale_location = st.sidebar.multiselect(
            "📍 Select SaleLocation",
            options=sale_location,
            default=None,
            key="unique_selected_sale_location_key"
        )

        selected_users = st.sidebar.multiselect(
            "👤 Select Execs",
            options=valid_usernames,
            default=None,
            key="unique_selected_users_key"
        )

        paid_options = pd.unique(filtered_data['IsPaid'])
        selected_paid = st.sidebar.selectbox(
            "💰 Filter by IsPaid",
            options=paid_options,
            key="unique_selected_paid_key"
        )
        

        # ─── NEW: Kickoff‑time filter ───────────────────────────────────────────────
        # grab all unique kickoff times from your filtered_data
        kickoff_times = sorted(
            filtered_data["KickOffEventStart"]
            .dropna()
            .unique()
        )
        # present them in a human‐friendly format
        display_kickoffs = [
            pd.to_datetime(ts).strftime("%Y-%m-%d %H:%M") for ts in kickoff_times
        ]
        selected_kickoffs = st.sidebar.multiselect(
            "⏰ Select Kickoff time",
            options=display_kickoffs,
            default=None,
            key="unique_selected_kickoff_key"
        )
        # if the user picked any, then only keep those rows
        if selected_kickoffs:
            # map the display back to actual timestamps
            selected_ts = [
                kickoff_times[display_kickoffs.index(label)]
                for label in selected_kickoffs
            ]
            filtered_data = filtered_data[
                filtered_data["KickOffEventStart"].isin(selected_ts)
            ]
        # ─────────────────────────────────────────────────────────────────────────────

        # Apply date range filter with time
        if min_date and max_date:
            filtered_data = filtered_data[(filtered_data['CreatedOn'] >= min_date) & (filtered_data['CreatedOn'] <= max_date)]

        # Apply SaleLocation filter
        if selected_sale_location:
            filtered_data = filtered_data[filtered_data['SaleLocation'].isin(selected_sale_location)]

        # Apply user filter
        if selected_users:
            filtered_data = filtered_data[filtered_data['CreatedBy'].isin(selected_users)]

        # Apply event category filter
        if selected_categories:
            filtered_data = filtered_data[filtered_data['EventCompetition'].isin(selected_categories)]

        # Apply event filter
        if selected_events:
            filtered_data = filtered_data[filtered_data['Fixture Name'].isin(selected_events)]

        # Dynamically update the discount options based on selected events
        if selected_events:
            available_discounts = pd.unique(filtered_data[filtered_data['Fixture Name'].isin(selected_events)]['Discount'])
        else:
            available_discounts = pd.unique(filtered_data['Discount'])

        # Discount Filter with "Select All" option
        select_all_discounts = st.sidebar.checkbox("Select All Discounts", value=True, key="unique_select_all_discounts_key")
        if select_all_discounts:
            selected_discount_options = available_discounts.tolist()
        else:
            selected_discount_options = st.sidebar.multiselect(
                "🔖 Filter by Discount Type",
                options=available_discounts,
                default=available_discounts.tolist(),
                key="unique_discount_multiselect_key"
            )

        # Apply discount filter
        filtered_data = filtered_data[filtered_data['Discount'].isin(selected_discount_options)]

        # Filter out "Platinum" and "Woolwich Restaurant" packages
        filtered_data_excluding_packages = filtered_data[
            ~filtered_data['Package Name'].isin(['Platinum', 'Woolwich Restaurant'])
        ]

        # Static total: Get accumulated sales from June 18th, 2024 till now, excluding specific packages
        static_start_date = datetime(2024, 6, 18, 0, 0, 0)
        static_total = loaded_api_df[
            (loaded_api_df['CreatedOn'] >= static_start_date) &
            ~loaded_api_df['Package Name'].isin(['Platinum', 'Woolwich Restaurant'])
        ]['TotalPrice'].sum()

        # Dynamic total: Affected by filters, excluding specific packages
        dynamic_total = filtered_data_excluding_packages['TotalPrice'].sum()

        # Define exclude keywords for filtering the Discount column
        exclude_keywords = ["credit", "voucher", "gift voucher", "discount", "pldl"]
        mask = ~filtered_data_excluding_packages['Discount'].str.contains(
            '|'.join([re.escape(keyword) for keyword in exclude_keywords]), 
            case=False, na=False
        )

        # Filter data to include only rows without excluded keywords
        filtered_data_without_excluded_keywords = filtered_data_excluding_packages[mask]

        # Calculate Other Payments correctly
        total_sold_by_other = filtered_data_without_excluded_keywords['DiscountValue'].sum()
        other_sales_total = dynamic_total + total_sold_by_other

        # --- Metric Cards at the Top ---
        # Payment Channel: Compute top-performing channel based on total sales including other payments.
        raw_total_sold_per_location = filtered_data_excluding_packages.groupby('SaleLocation')['TotalPrice'].sum().reset_index()
        other_payments_per_location = (
            filtered_data_without_excluded_keywords.groupby('SaleLocation')['DiscountValue'].sum().reset_index()
        )
        raw_total_sold_per_location = pd.merge(
            raw_total_sold_per_location,
            other_payments_per_location,
            how="left",
            on="SaleLocation"
        ).rename(columns={"DiscountValue": "OtherPayments"})
        raw_total_sold_per_location['TotalWithOtherPayments'] = (
            raw_total_sold_per_location['TotalPrice'] + raw_total_sold_per_location['OtherPayments'].fillna(0)
        )
        top_channel_row = raw_total_sold_per_location.sort_values(by="TotalWithOtherPayments", ascending=False).iloc[0]
        payment_channel_metric = f"{top_channel_row['SaleLocation']} (Sales: £{top_channel_row['TotalWithOtherPayments']:,.2f})"

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Confirmed Sales", f"£{static_total:,.2f}")
        col2.metric("Filtered Confirmed Sales", f"£{dynamic_total:,.2f}")
        col3.metric("Total Sales (Including Pending payments)", f"£{other_sales_total:,.2f}")
        # col4.metric("Payment Channel", payment_channel_metric)

        # --- The rest of the dashboard remains unchanged ---

        # Other Sales Per Fixture Section
        st.write("### ⚽ Total Sales Summary")
        st.write(f"Table showing total sales generated including pending payments. **RTS sales** are confirmed payments and **OtherSales** are pending payments: **£{other_sales_total:,.2f}** ")

        # Group the data and calculate required metrics
        total_sold_per_match = (
            filtered_data_excluding_packages.groupby("Fixture Name")
            .agg(
                DaysToFixture=("Days to Fixture", "min"),  # Days to Fixture
                KickOffEventStart=("KickOffEventStart", "first"),  # Kickoff Event Start
                RTS_Sales=("TotalPrice", "sum"),  # RTS Sales (TotalPrice)
                Budget=("Budget", "first")  # Budget
            )
            .reset_index()
        )

        # Calculate Other Sales (RTS_Sales + DiscountValue from filtered data)
        other_sales = (
            filtered_data_without_excluded_keywords[
                ~filtered_data_without_excluded_keywords['Package Name'].isin(['Platinum', 'Woolwich Restaurant'])
            ]
            .groupby("Fixture Name")['DiscountValue'].sum()
        )

        # Merge the other_sales into the total_sold_per_match table
        total_sold_per_match = pd.merge(
            total_sold_per_match, 
            other_sales, 
            how="left", 
            on="Fixture Name"
        ).rename(columns={"DiscountValue": "OtherSales"})

        # Fill NaN in OtherSales with 0 (if no filtered DiscountValue exists for a fixture)
        total_sold_per_match['OtherSales'] = total_sold_per_match['OtherSales'].fillna(0)

        # Add RTS_Sales to OtherSales to get the total "Other Sales"
        total_sold_per_match['OtherSales'] += total_sold_per_match['RTS_Sales']

        # Calculate Covers Sold
        covers_sold = (
            filtered_data_excluding_packages.groupby("Fixture Name")['Seats'].sum()
        )

        # Merge Covers Sold into the table
        total_sold_per_match = pd.merge(
            total_sold_per_match,
            covers_sold,
            how="left",
            on="Fixture Name"
        ).rename(columns={"Seats": "CoversSold"})

        # Fill NaN in CoversSold with 0
        total_sold_per_match['CoversSold'] = total_sold_per_match['CoversSold'].fillna(0).astype(int)

        # Calculate Average Spend Per Head
        total_sold_per_match['Avg Spend'] = total_sold_per_match.apply(
            lambda row: row['OtherSales'] / row['CoversSold'] if row['CoversSold'] > 0 else 0,
            axis=1
        )
        # Format Avg Spend to currency format
        total_sold_per_match['Avg Spend'] = total_sold_per_match['Avg Spend'].apply(lambda x: f"£{x:,.2f}")

        # Calculate Budget Percentage using OtherSales
        total_sold_per_match['BudgetPercentage'] = total_sold_per_match.apply(
            lambda row: f"{(row['OtherSales'] / row['Budget'] * 100):.0f}%" 
            if pd.notnull(row['Budget']) and row['Budget'] > 0 else "N/A", 
            axis=1
        )

        # Format columns for display
        total_sold_per_match['RTS_Sales'] = total_sold_per_match['RTS_Sales'].apply(lambda x: f"£{x:,.0f}")
        total_sold_per_match['OtherSales'] = total_sold_per_match['OtherSales'].apply(lambda x: f"£{x:,.0f}")
        total_sold_per_match['Budget Target'] = total_sold_per_match['Budget'].apply(
            lambda x: f"£{x:,.0f}" if pd.notnull(x) else "None"
        )

        # Convert KickOffEventStart to datetime for sorting
        total_sold_per_match['KickOffEventStart'] = pd.to_datetime(total_sold_per_match['KickOffEventStart'], errors='coerce')

        # Sort by KickOffEventStart (latest fixtures first)
        total_sold_per_match = total_sold_per_match.sort_values(by="KickOffEventStart", ascending=False)

        # Reorder columns
        total_sold_per_match = total_sold_per_match[
            ['Fixture Name', 'KickOffEventStart', 'DaysToFixture', 'CoversSold', 'RTS_Sales', 'OtherSales', 'Avg Spend', 'Budget Target', 'BudgetPercentage']
        ]

        # Display the final table
        st.dataframe(total_sold_per_match)

        # Other Summary Table
        st.write("### Table with Pending Payments")
        # Apply discount filter to total_discount_value table
        total_discount_value = filtered_data_without_excluded_keywords.groupby(
            ['Order Id', 'Country Code', 'First Name', 'Surname', 'Fixture Name', 'GLCode', 'CreatedOn']
        )[['Discount', 'DiscountValue', 'TotalPrice']].sum().reset_index()

        # Format the TotalPrice and DiscountValue columns as currency
        total_discount_value['TotalPrice'] = total_discount_value['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
        total_discount_value['DiscountValue'] = total_discount_value['DiscountValue'].apply(lambda x: f"£{x:,.2f}")

        # Display the filtered table
        st.dataframe(total_discount_value)

        # Filter out "Platinum" and "Woolwich Restaurant" packages
        filtered_data_excluding_packages = filtered_data[
            ~filtered_data['Package Name'].isin(['Platinum', 'Woolwich Restaurant'])
        ]

        # Define exclude keywords for filtering the Discount column
        exclude_keywords = ["credit", "voucher", "gift voucher", "discount", "pldl"]
        mask = ~filtered_data_excluding_packages['Discount'].str.contains(
            '|'.join([re.escape(keyword) for keyword in exclude_keywords]), case=False, na=False
        )

        # Filter data to include only rows without excluded keywords
        filtered_data_without_excluded_keywords = filtered_data_excluding_packages[mask]

        # Calculate DiscountValue for Other Payments
        other_payments_per_package = (
            filtered_data_without_excluded_keywords.groupby('Package Name')['DiscountValue'].sum()
        )

        # Total Sales Per Package
        st.write("### 🎟️ MBM Package Sales")
        total_sold_per_package = filtered_data_excluding_packages.groupby('Package Name')['TotalPrice'].sum().reset_index()
        total_sold_per_package = pd.merge(
            total_sold_per_package,
            other_payments_per_package,
            how="left",
            on="Package Name"
        ).rename(columns={"DiscountValue": "OtherPayments"})

        # Calculate total sales with Other Payments
        total_sold_per_package['TotalWithOtherPayments'] = (
            total_sold_per_package['TotalPrice'] + total_sold_per_package['OtherPayments'].fillna(0)
        )

        # Format columns for display
        total_sold_per_package['TotalPrice'] = total_sold_per_package['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
        total_sold_per_package['OtherPayments'] = total_sold_per_package['OtherPayments'].fillna(0).apply(lambda x: f"£{x:,.2f}")
        total_sold_per_package['TotalWithOtherPayments'] = total_sold_per_package['TotalWithOtherPayments'].apply(lambda x: f"£{x:,.2f}")

        # Display Total Sales Per Package table
        st.dataframe(total_sold_per_package)

        # Calculate DiscountValue for Other Payments Per Location
        other_payments_per_location = (
            filtered_data_without_excluded_keywords.groupby('SaleLocation')['DiscountValue'].sum()
        )

        # Total Sales Per Location
        st.write("### 🏟️ Payment Channel")
        total_sold_per_location = filtered_data_excluding_packages.groupby('SaleLocation')['TotalPrice'].sum().reset_index()
        total_sold_per_location = pd.merge(
            total_sold_per_location,
            other_payments_per_location,
            how="left",
            on="SaleLocation"
        ).rename(columns={"DiscountValue": "OtherPayments"})

        # Calculate total sales with Other Payments
        total_sold_per_location['TotalWithOtherPayments'] = (
            total_sold_per_location['TotalPrice'] + total_sold_per_location['OtherPayments'].fillna(0)
        )

        # Format columns for display
        total_sold_per_location['TotalPrice'] = total_sold_per_location['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
        total_sold_per_location['OtherPayments'] = total_sold_per_location['OtherPayments'].fillna(0).apply(lambda x: f"£{x:,.2f}")
        total_sold_per_location['TotalWithOtherPayments'] = total_sold_per_location['TotalWithOtherPayments'].apply(lambda x: f"£{x:,.2f}")

        # Display Total Sales Per Location table
        st.dataframe(total_sold_per_location)

        # Woolwich Restaurant Sales
        st.write("### 🍴 Woolwich Restaurant Sales")
        woolwich_restaurant_data = filtered_data[
            (filtered_data['Package Name'].isin(['Platinum', 'Woolwich Restaurant'])) &
            (filtered_data['IsPaid'].astype(str).str.strip().str.upper() == 'TRUE')
        ]
        total_sales_revenue = woolwich_restaurant_data['TotalPrice'].sum()
        total_covers_sold = woolwich_restaurant_data['Seats'].sum()
        st.write(f"Total Sales Revenue: **£{total_sales_revenue:,.0f}** ")
        st.write(f"Total Covers Sold: **{int(total_covers_sold)}** ")
        woolwich_sales_summary = woolwich_restaurant_data.groupby(['Fixture Name', 'KickOffEventStart']).agg({
            'Seats': 'sum',
            'TotalPrice': 'sum'
        }).reset_index()
        woolwich_sales_summary = woolwich_sales_summary.rename(columns={
            'Fixture Name': 'Event',
            'KickOffEventStart': 'Event Date',
            'Seats': 'Covers Sold',
            'TotalPrice': 'Revenue'
        })
        woolwich_sales_summary['Revenue'] = woolwich_sales_summary['Revenue'].apply(lambda x: f"£{x:,.0f}")
        st.dataframe(woolwich_sales_summary)
        
        # Generate the cumulative sales chart
        st.header("Cumulative Sales as Percentage of Budget")
        st.subheader("Men's Competitions")
        try:
            generate_event_level_men_cumulative_sales_chart(filtered_data)
        except Exception as e:
            st.error(f"Failed to generate the men's cumulative chart: {e}")

        st.subheader("Women's Competitions")
        try:
            generate_event_level_women_cumulative_sales_chart(filtered_data)
        except Exception as e:
            st.error(f"Failed to generate the women's cumulative chart: {e}")

        st.subheader("Concerts (to be fixed soon)")
        try:
            generate_event_level_concert_cumulative_sales_chart(filtered_data)
        except Exception as e:
            st.error(f"Failed to generate the concert cumulative chart: {e}")

        # 📥 Downloads Section
        st.write("### 📥 Downloads")
        if not woolwich_restaurant_data.empty:
            output = BytesIO()
            output.write(woolwich_restaurant_data.to_csv(index=False).encode('utf-8'))
            output.seek(0)
            st.download_button(
                label="💾 Download Woolwich Restaurant Data",
                data=output,
                file_name='woolwich_restaurant_sales_data.csv',
                mime='text/csv',
            )

        if not filtered_data.empty:
            filtered_report = BytesIO()
            filtered_report.write(filtered_data.to_csv(index=False).encode('utf-8'))
            filtered_report.seek(0)
            st.download_button(
                label="💾 Download Filtered Data",
                data=filtered_report,
                file_name='filtered_data.csv',
                mime='text/csv',
            )

        if not loaded_api_df.empty:
            sales_report = BytesIO()
            sales_report.write(loaded_api_df.to_csv(index=False).encode('utf-8'))
            sales_report.seek(0)
            st.download_button(
                label="💾 Download Sales Report",
                data=sales_report,
                file_name='sales_report.csv',
                mime='text/csv',
            )
    else:
        st.sidebar.warning("🚨 Please upload a file to proceed.")

if __name__ == "__main__":
    run_app()
