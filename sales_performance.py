import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from tjt_hosp_api import filtered_df_without_seats


def run_app():
    specified_users = ['dcoppin', 'Jedwards', 'jedwards', 'bgardiner', 'BenT', 'jmurphy', 'ayildirim',
                       'MeganS', 'BethNW', 'HayleyA', 'LucyB', 'Conor', 'SavR', 'MillieS']

    st.title('💷  AFC Finance x MBM Reconciliation 💷')

    st.markdown("""
    ### ℹ️ About
    This app provides sales metrics derived from MBM sales data to be used for reconciliation with the Finance team after each Home Fixture. 
    
    The app allows you to filter results by date, user, fixture, payment status, and paid status for tailored insights. 
    
    Please note that sales from 'Platinum' package & 'Woolwich Package' sales have been excluded from th
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

        # Dynamically update the discount options based on selected events
        if selected_events:
            available_discounts = pd.unique(filtered_data[filtered_data['Fixture Name'].isin(selected_events)]['Discount'])
        else:
            available_discounts = pd.unique(filtered_data['Discount'])

        # Discount Filter with "Select All" option
        select_all_discounts = st.sidebar.checkbox("Select All Discounts", value=True)
        if select_all_discounts:
            selected_discount_options = available_discounts.tolist()
        else:
            selected_discount_options = st.sidebar.multiselect("🔖 Filter by Discount Type", options=available_discounts, default=available_discounts.tolist())

        # Apply discount filter
        filtered_data = filtered_data[filtered_data['Discount'].isin(selected_discount_options)]

        # Static total: Get accumulated sales from June 18th, 2024 till now
        static_start_date = datetime(2024, 6, 18, 0, 0, 0)
        static_total = loaded_api_df[(loaded_api_df['PaymentTime'] >= static_start_date)]['TotalPrice'].sum()

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

            # Apply discount filter to total_discount_value table
            total_discount_value = filtered_data.groupby(['Order Id', 'Country Code', 'First Name', 'Surname', 'Fixture Name', 'GLCode', 'CreatedOn'])[['Discount', 'DiscountValue', 'TotalPrice']].sum().reset_index()
            total_discount_value['TotalPrice'] = total_discount_value['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
            total_discount_value['DiscountValue'] = total_discount_value['DiscountValue'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_discount_value)

            st.write("### ⚽ Total Sales Per Fixture")
            total_sold_per_match = filtered_data.groupby('Fixture Name')['TotalPrice'].sum().reset_index()
            st.write(f"Total Match Fixture: **£{total_sold_per_match['TotalPrice'].sum():,.2f}**")
            total_sold_per_match['TotalPrice'] = total_sold_per_match['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold_per_match)

            st.write("### 🎟️ Total Sales Per Package")
            total_sold_per_package = filtered_data.groupby('Package Name')['TotalPrice'].sum().reset_index()
            st.write(f"Total Package Sales (Excluding 'Platinum'): **£{total_sold_per_package['TotalPrice'].sum():,.2f}**")
            total_sold_per_package['TotalPrice'] = total_sold_per_package['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold_per_package)

            st.write("### 🏟️ Total Sales Per Location")
            total_sold_per_location = filtered_data.groupby('SaleLocation')['TotalPrice'].sum().reset_index()
            st.write(f"Total Location Sales: **£{total_sold_per_location['TotalPrice'].sum():,.2f}**")
            total_sold_per_location['TotalPrice'] = total_sold_per_location['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold_per_location)

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
