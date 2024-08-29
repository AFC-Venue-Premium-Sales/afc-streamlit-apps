import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from io import BytesIO
from user_performance_calc import (
    load_data, remove_grand_total_row, filter_columns, clean_numeric_columns, 
    split_created_by_column, add_additional_info, split_guest_column, convert_date_format,
    columns_to_keep, competition_fixture, total_budget_packages_data,
    total_budget_target_data
)

# Specified users list
specified_users = ['dcoppin', 'Jedwards', 'jedwards', 'bgardiner', 'BenT', 'jmurphy', 'ayildirim',
                   'MeganS', 'BethNW', 'HayleyA', 'LucyB', 'Conor', 'SavR', 'MillieL']

# Arsenal Gold color in hex
arsenal_gold = '#DAA520'

# App title
st.title('AFC Finance x MBM Reconciliation')

# About section
st.markdown("""
### About
This app provides sales metrics derived from MBM sales data to be used for reconciliation with the Finance team after each Home Fixture. To get started, please download the relevant sales report from [RTS](https://www.tjhub3.com/Rts_Arsenal_Hospitality/Suites/HospitalityPackageSales) and upload it here. The app allows you to filter results by date, user, fixture, payment status, and paid status for tailored insights.
""")

# File uploader in the sidebar
uploaded_file = st.sidebar.file_uploader("Choose a sales file", type=['xlsx'])

if uploaded_file is not None:
    # Show a message indicating the file is loading
    st.sidebar.success("File successfully loaded.")
    
    # Initialize a progress bar
    progress_bar = st.sidebar.progress(0)

    # Load the data with progress
    progress_bar.progress(10)
    raw_data = load_data(uploaded_file)
    
    progress_bar.progress(30)
    processed_data = remove_grand_total_row(raw_data)
    processed_data = processed_data.dropna(subset=['Event name'])

    # Preprocess the data
    progress_bar.progress(50)
    processed_data = filter_columns(processed_data, columns_to_keep)
    processed_data = clean_numeric_columns(processed_data, ['Price', 'Discount value', 'Total price'])
    processed_data = split_created_by_column(processed_data)
    processed_data = split_guest_column(processed_data)
    processed_data = convert_date_format(processed_data, 'Created_on')

    progress_bar.progress(100)  # Complete the progress
    
    # Date range selector in the sidebar
    date_range = st.sidebar.date_input("Select Date Range", [])

    # Ensure only specified users are shown in the user filter
    valid_usernames = [user for user in specified_users if user in pd.unique(processed_data['Created_by'])]

    # Event name filter dropdown in the sidebar
    event_names = pd.unique(processed_data['Event name'])
    selected_events = st.sidebar.multiselect("Select Events", options=event_names, default=None)
    
    # Payment status filter
    payment_status_options = pd.unique(processed_data['Payment status'])
    selected_payment_status = st.sidebar.multiselect("Select Payment Status", options=payment_status_options, default=None)
    
    # Paid filter
    paid_options = pd.unique(processed_data['Paid'])
    selected_paid = st.sidebar.selectbox("Filter by Paid", options=paid_options)
    
    # Discount Filter
    discount_options = pd.unique(processed_data['Discount'])
    selected_discount_options = st.sidebar.multiselect("Filter by Discount (Other payment)", options=discount_options, default=None)
    
    # Username filter dropdown in the sidebar for multiple selections
    selected_users = st.sidebar.multiselect("Select Execs", options=valid_usernames, default=None)

    # Apply filters interactively
    filtered_data = processed_data.copy()

    if date_range:
        min_date, max_date = (pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) if len(date_range) == 2 else pd.Timestamp(date_range[0]))
        filtered_data = filtered_data[(filtered_data['Payment time'] >= min_date) & (filtered_data['Payment time'] <= max_date)]
    
    if selected_users:
        filtered_data = filtered_data[filtered_data['Created_by'].isin(selected_users)]

    if selected_events:
        filtered_data = filtered_data[filtered_data['Event name'].isin(selected_events)]

    if selected_paid:
        filtered_data = filtered_data[filtered_data['Paid'] == selected_paid]

    if selected_payment_status:
        filtered_data = filtered_data[filtered_data['Payment status'].isin(selected_payment_status)]
        
    # Display metrics in the main area
    if not filtered_data.empty:
        
        # Total Accumulated Sales
        st.write("### Total Accumulated Sales Since Going Live")
        total_sold = filtered_data['Total price'].sum()
        st.write(f"Total Accumulated Sales: **£{total_sold:,.2f}**")
        
       # Total Sold By Other Payment
        st.write("### Sales with 'Other' Payment")

        # Filter the rows where 'Discount' is not 'None'
        filtered_discount_data = filtered_data[filtered_data['Discount'] != 'none']

        # Calculate the total sales for 'Other' Payment before any formatting
        total_sold_by_other = filtered_discount_data['Discount value'].sum()
        
        # calculate accumulated sales + 'other' payments
        other_sales_total = total_sold + total_sold_by_other
        st.write(f"Accumulated sales with 'Other' payments included: **£{other_sales_total:,.2f}**")
        
        # Display the total sales by 'Other' Payment
        st.write(f"Invoice & Credit payments are logged under 'Discount' field on RTS as a fix for now. I've classified them as 'Other Payments' for now.")
        st.write(f"Total Sales with 'Other' Payment: **£{total_sold_by_other:,.2f}**")

        # Group by 'Order Id', 'Event name', and 'Payment time' to calculate the total sales for each order
        total_discount_value = filtered_discount_data.groupby(['Order Id', 'Event name', 'Payment time'])[['Discount', 'Discount value', 'Total price']].sum().reset_index()

        # Apply formatting to the 'Total price' column
        total_discount_value['Total price'] = total_discount_value['Total price'].apply(lambda x: f"£{x:,.2f}")
        total_discount_value['Discount value'] = total_discount_value['Discount value'].apply(lambda x: f"£{x:,.2f}")

        # Display the dataframe
        st.dataframe(total_discount_value)

        # Total Sold Per Fixture
        st.write("### Total Sales Per Fixture")
        total_sold_per_match = filtered_data.groupby('Event name')['Total price'].sum().reset_index()
        
        # Calculate and display the total sales per match
        total_sales_per_match = total_sold_per_match['Total price'].sum()
        st.write(f"Total Match Fixture: **£{total_sales_per_match:,.2f}**")
        
        total_sold_per_match['Total price'] = total_sold_per_match['Total price'].apply(lambda x: f"£{x:,.2f}")
        st.dataframe(total_sold_per_match)
        
        # Total Sold Per Package
        st.write("### Total Sales Per Package")
        total_sold_per_package = filtered_data.groupby('Package name')['Total price'].sum().reset_index()
        
        # Calculate and display the total sales per package
        total_sales_per_package = total_sold_per_package['Total price'].sum()
        st.write(f"Total Package Sales: **£{total_sales_per_package:,.2f}**")
        
        total_sold_per_package['Total price'] = total_sold_per_package['Total price'].apply(lambda x: f"£{x:,.2f}")
        st.dataframe(total_sold_per_package)
        
        # Total Sold Per Location
        st.write("### Total Sales Per Location")
        total_sold_per_location = filtered_data.groupby('Locations')['Total price'].sum().reset_index()
        
        # Calculate and display the total sales per location
        total_sales_per_location = total_sold_per_location['Total price'].sum()
        st.write(f"Total Location Sales: **£{total_sales_per_location:,.2f}**")
        
        total_sold_per_location['Total price'] = total_sold_per_location['Total price'].apply(lambda x: f"£{x:,.2f}")
        st.dataframe(total_sold_per_location)
        
        # Save the filtered data to a CSV file in memory
    output = BytesIO()
    output.write(filtered_data.to_csv(index=False).encode('utf-8'))
    output.seek(0)

    # Download button for filtered data
    st.download_button(
        label="Download Filtered Data as CSV",
        data=output,
        file_name='filtered_sales_data.csv',
        mime='text/csv',
    )
