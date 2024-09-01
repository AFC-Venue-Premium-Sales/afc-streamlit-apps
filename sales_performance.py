import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from user_performance_calc import (
    load_data, remove_grand_total_row, filter_columns, clean_numeric_columns, 
    split_created_by_column, add_additional_info, split_guest_column, convert_date_format,
    columns_to_keep, competition_fixture, total_budget_packages_data,
    total_budget_target_data
)

def run_app():
    specified_users = ['dcoppin', 'Jedwards', 'jedwards', 'bgardiner', 'BenT', 'jmurphy', 'ayildirim',
                       'MeganS', 'BethNW', 'HayleyA', 'LucyB', 'Conor', 'SavR', 'MillieL']

    st.title('AFC Finance x MBM Reconciliation')

    st.markdown("""
    ### About
    This app provides sales metrics derived from MBM sales data to be used for reconciliation with the Finance team after each Home Fixture. To get started, please download the relevant sales report from [RTS](https://www.tjhub3.com/Rts_Arsenal_Hospitality/Suites/HospitalityPackageSales) and upload it here. The app allows you to filter results by date, user, fixture, payment status, and paid status for tailored insights.
    """)

    uploaded_file = st.sidebar.file_uploader("Choose a sales file", type=['xlsx'])

    if uploaded_file is not None:
        st.sidebar.success("File successfully loaded.")
        progress_bar = st.sidebar.progress(0)
        progress_bar.progress(10)
        raw_data = load_data(uploaded_file)
        progress_bar.progress(30)
        processed_data = remove_grand_total_row(raw_data)
        processed_data = processed_data.dropna(subset=['Event name'])
        progress_bar.progress(50)
        processed_data = filter_columns(processed_data, columns_to_keep)
        processed_data = clean_numeric_columns(processed_data, ['Price', 'Discount value', 'Total price'])
        processed_data = split_created_by_column(processed_data)
        processed_data = split_guest_column(processed_data)
        processed_data = convert_date_format(processed_data, 'Created_on')
        progress_bar.progress(100)

        # Sidebar filters
        date_range = st.sidebar.date_input("Select Date Range", [])
        valid_usernames = [user for user in specified_users if user in pd.unique(processed_data['Created_by'])]
        event_names = pd.unique(processed_data['Event name'])
        sale_location = pd.unique(processed_data['Sale location'])
        selected_events = st.sidebar.multiselect("Select Events", options=event_names, default=None)
        selected_sale_location = st.sidebar.multiselect("Select Sale Location", options=sale_location, default=None)
        selected_users = st.sidebar.multiselect("Select Execs", options=valid_usernames, default=None)
        payment_status_options = pd.unique(processed_data['Payment status'])
        selected_payment_status = st.sidebar.multiselect("Select Payment Status", options=payment_status_options, default=None)
        paid_options = pd.unique(processed_data['Paid'])
        selected_paid = st.sidebar.selectbox("Filter by Paid", options=paid_options)
        discount_options = pd.unique(processed_data['Discount'])
        selected_discount_options = st.sidebar.multiselect("Filter by Discount (Other payment)", options=discount_options, default=None)

        filtered_data = processed_data.copy()

        # Apply date range filter
        if date_range:
            min_date, max_date = (pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) if len(date_range) == 2 else pd.Timestamp(date_range[0]))
            filtered_data = filtered_data[(filtered_data['Payment time'] >= min_date) & (filtered_data['Payment time'] <= max_date)]

        # Apply sale location filter
        if selected_sale_location:
            # Include sales from both "Hospitality website" and selected sale locations if "Hospitality website" is selected
            if 'Hospitality website' in selected_sale_location and not selected_users:
                filtered_data = filtered_data[filtered_data['Sale location'].isin(selected_sale_location)]
            else:
                filtered_data = filtered_data[filtered_data['Sale location'].isin(selected_sale_location)]

        # Apply user filter
        if selected_users:
            filtered_data = filtered_data[filtered_data['Created_by'].isin(selected_users)]

        # Apply event filter
        if selected_events:
            filtered_data = filtered_data[filtered_data['Event name'].isin(selected_events)]

        # Apply paid status filter
        if selected_paid:
            filtered_data = filtered_data[filtered_data['Paid'] == selected_paid]

        # Apply payment status filter
        if selected_payment_status:
            filtered_data = filtered_data[filtered_data['Payment status'].isin(selected_payment_status)]

        # Apply discount filter
        filtered_discount_data = filtered_data[filtered_data['Discount'] != 'none']
        if selected_discount_options:
            filtered_discount_data = filtered_discount_data[filtered_discount_data['Discount'].isin(selected_discount_options)]

        # Display results
        if not filtered_data.empty:
            st.write("### Total Accumulated Sales Since Going Live")
            total_sold = filtered_data['Total price'].sum()
            st.write(f"Total Accumulated Sales: **£{total_sold:,.2f}**")
            
            st.write("### Sales with 'Other' Payment")
            total_sold_by_other = filtered_discount_data['Discount value'].sum()
            other_sales_total = total_sold + total_sold_by_other
            st.write(f"Accumulated sales with 'Other' payments included: **£{other_sales_total:,.2f}**")
            st.write(f"Total Sales with 'Other' Payment: **£{total_sold_by_other:,.2f}**")

            # Apply discount filter to total_discount_value table
            total_discount_value = filtered_discount_data.groupby(['Order Id', 'Event name', 'Payment time'])[['Discount', 'Discount value', 'Total price']].sum().reset_index()
            total_discount_value['Total price'] = total_discount_value['Total price'].apply(lambda x: f"£{x:,.2f}")
            total_discount_value['Discount value'] = total_discount_value['Discount value'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_discount_value)

            st.write("### Total Sales Per Fixture")
            total_sold_per_match = filtered_data.groupby('Event name')['Total price'].sum().reset_index()
            st.write(f"Total Match Fixture: **£{total_sold_per_match['Total price'].sum():,.2f}**")
            total_sold_per_match['Total price'] = total_sold_per_match['Total price'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold_per_match)

            st.write("### Total Sales Per Package")
            total_sold_per_package = filtered_data.groupby('Package name')['Total price'].sum().reset_index()
            st.write(f"Total Package Sales: **£{total_sold_per_package['Total price'].sum():,.2f}**")
            total_sold_per_package['Total price'] = total_sold_per_package['Total price'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold_per_package)

            st.write("### Total Sales Per Location")
            total_sold_per_location = filtered_data.groupby('Locations')['Total price'].sum().reset_index()
            st.write(f"Total Location Sales: **£{total_sold_per_location['Total price'].sum():,.2f}**")
            total_sold_per_location['Total price'] = total_sold_per_location['Total price'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold_per_location)

        # Download button for filtered data
        output = BytesIO()
        output.write(filtered_data.to_csv(index=False).encode('utf-8'))
        output.seek(0)

        st.download_button(
            label="Download Filtered Data as CSV",
            data=output,
            file_name='filtered_sales_data.csv',
            mime='text/csv',
        )
