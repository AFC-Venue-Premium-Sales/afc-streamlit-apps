import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import importlib
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from charts_ import generate_event_level_men_cumulative_sales_chart, generate_event_level_women_cumulative_sales_chart, generate_event_level_concert_cumulative_sales_chart
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

    # Budget data for fixtures
    budget_data = {
        "Fixture": [
            "Arsenal v Bayer 04 Leverkusen", "Arsenal v Olympique Lyonnais", "Arsenal Women v Manchester City Women",
            "Arsenal Women v Everton Women", "Arsenal Women v Chelsea Women", "Arsenal Women v Vålerenga Women",
            "Arsenal Women v Brighton Women", "Arsenal Women v Juventus Women", "Arsenal Women v Aston Villa Women",
            "Arsenal Women v FC Bayern Munich Women", "Arsenal Women v Tottenham Hotspur Women", "Arsenal v Wolves",
            "Arsenal v Brighton", "Arsenal v Bolton Wanderers", "Arsenal v Leicester City", "Arsenal v Paris Saint-Germain",
            "Arsenal v Southampton", "Arsenal v Shakhtar Donetsk", "Arsenal v Liverpool", "Arsenal v Nottingham Forest",
            "Arsenal v Manchester United", "Arsenal v AS Monaco", "Arsenal v Everton", "Arsenal v Crystal Palace",
            "Arsenal v Ipswich Town", "Arsenal v Tottenham Hotspur", "Arsenal v Aston Villa", "Arsenal v Dinamo Zagreb",
            "Arsenal v Manchester City", "Arsenal v West Ham United", "Arsenal v Chelsea", "Robbie Williams Live 2025 - Friday",
            "Robbie Williams Live 2025 - Saturday"
        ],
        "Budget": [
            113800, 113800, 43860, 28636, 52632, 10000, 38182, 10000, 38182, 10000, 52632, 469797, 319462, 0, 469797,
            490113, 390059, 394122, 588136, 492653, 588136, 490113, 492653, 0, 390059, 807500, 617500, 285000, 807500,
            617500, 712500, 97412, 97412
        ]
    }

    budget_df = pd.DataFrame(budget_data)

    st.title('💷 MBM Sales 💷')
    
     # Instructions Section
    with st.expander("📖 How to Use This App - Sales Performance"):
        
        st.markdown("""
        ### ℹ️ About
        This app provides sales metrics from TJT's data. 
        You can filter results by date, user, fixture, payment status, and paid status for tailored insights
        
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

        # Merge with budget data
        filtered_data = pd.merge(filtered_data, budget_df, how="left", left_on="Fixture Name", right_on="Fixture")

        # Parse 'KickOffEventStart' with the correct format
        filtered_data['KickOffEventStart'] = pd.to_datetime(
            filtered_data['KickOffEventStart'], format='%d-%m-%Y %H:%M', errors='coerce'
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
        event_categories = pd.unique(filtered_data['EventCompetition'])

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
        mask = ~filtered_data_excluding_packages['Discount'].str.contains('|'.join([re.escape(keyword) for keyword in exclude_keywords]), 
                                                                        case=False, na=False)

        # Filter data to include only rows without excluded keywords
        filtered_data_without_excluded_keywords = filtered_data_excluding_packages[mask]

        # Calculate Other Payments correctly
        total_sold_by_other = filtered_data_without_excluded_keywords['DiscountValue'].sum()
        other_sales_total = dynamic_total + total_sold_by_other

        # Display results
        if not filtered_data.empty:
            st.write("### 💼 Total Accumulated Sales")
            st.write(f"Total Accumulated Sales (Static) since June 18th : **£{static_total:,.2f}** ")

            st.write("### 💼 Filtered Accumulated Sales")
            st.write(f"Total Accumulated Sales (Filtered): **£{dynamic_total:,.2f}** ")

            # Apply discount filter to total_discount_value table
            total_discount_value = filtered_data_without_excluded_keywords.groupby(
                ['Order Id', 'Country Code', 'First Name', 'Surname', 'Fixture Name', 'GLCode', 'CreatedOn']
            )[['Discount', 'DiscountValue', 'TotalPrice']].sum().reset_index()

            # Format the TotalPrice and DiscountValue columns as currency
            total_discount_value['TotalPrice'] = total_discount_value['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
            total_discount_value['DiscountValue'] = total_discount_value['DiscountValue'].apply(lambda x: f"£{x:,.2f}")

            # Total Sales Per Fixture Section
            st.write("### ⚽ Total Sales Summary")
            st.write(f"Accumulated sales with 'Other' payments included: **£{other_sales_total:,.2f}** ")

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

            
            # Apply discount filter to total_discount_value table
            total_discount_value = filtered_data_without_excluded_keywords.groupby(
                ['Order Id', 'Country Code', 'First Name', 'Surname', 'Fixture Name', 'GLCode', 'CreatedOn']
            )[['Discount', 'DiscountValue', 'TotalPrice']].sum().reset_index()

            # Format the TotalPrice and DiscountValue columns as currency
            total_discount_value['TotalPrice'] = total_discount_value['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
            total_discount_value['DiscountValue'] = total_discount_value['DiscountValue'].apply(lambda x: f"£{x:,.2f}")

            # Other Summary Table
            st.write("### Other Payments")
            # Apply discount filter to total_discsount_value table
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

            # Woolwich Restarurant Sales
            st.write("### 🍴 Woolwich Restaurant Sales")

            # Filter the data for Platinum and Woolwich Restaurant packages
            woolwich_restaurant_data = filtered_data[
                (filtered_data['Package Name'].isin(['Platinum', 'Woolwich Restaurant'])) &
                (filtered_data['IsPaid'].astype(str).str.strip().str.upper() == 'TRUE')
            ]

            # Calculate total sales revenue and total covers sold
            total_sales_revenue = woolwich_restaurant_data['TotalPrice'].sum()
            total_covers_sold = woolwich_restaurant_data['Seats'].sum()

            # Display total sales revenue and covers sold
            st.write(f"Total Sales Revenue: **£{total_sales_revenue:,.0f}** ")
            st.write(f"Total Covers Sold: **{int(total_covers_sold)}** ")

            # Group by Fixture Name and KickOffEventStart to calculate Covers Sold and Revenue
            woolwich_sales_summary = woolwich_restaurant_data.groupby(['Fixture Name', 'KickOffEventStart']).agg({
                'Seats': 'sum',
                'TotalPrice': 'sum'
            }).reset_index()

            # Rename columns for clarity
            woolwich_sales_summary = woolwich_sales_summary.rename(columns={
                'Fixture Name': 'Event',
                'KickOffEventStart': 'Event Date',
                'Seats': 'Covers Sold',
                'TotalPrice': 'Revenue'
            })

            # Format Revenue as currency
            woolwich_sales_summary['Revenue'] = woolwich_sales_summary['Revenue'].apply(lambda x: f"£{x:,.0f}")

            # Display the table
            st.dataframe(woolwich_sales_summary)
            
            
            # Generate the cumulative sales chart
            st.header("Cumulative Sales as Percentage of Budget")

            # Generate Men's Cumulative Sales Chart
            st.subheader("Men's Competitions")
            try:
                generate_event_level_men_cumulative_sales_chart(filtered_data)
            except Exception as e:
                st.error(f"Failed to generate the men's cumulative chart: {e}")

            # Generate Women's Cumulative Sales Chart
            st.subheader("Women's Competitions")
            try:
                generate_event_level_women_cumulative_sales_chart(filtered_data)
            except Exception as e:
                st.error(f"Failed to generate the women's cumulative chart: {e}")

            # Generate Concert Cumulative Sales Chart
            st.subheader("Concerts")
            try:
                generate_event_level_concert_cumulative_sales_chart(filtered_data)
            except Exception as e:
                st.error(f"Failed to generate the concert cumulative chart: {e}")


            # 📥 Downloads Section
            st.write("### 📥 Downloads")

            # Download Woolwich Restaurant Data
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

            # Download Filtered Data
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

            # Download RTS Sales Data
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
            st.warning("⚠️ No data available for the selected filters.")
    else:
        st.sidebar.warning("🚨 Please upload a file to proceed.")

if __name__ == "__main__":
    run_app()
