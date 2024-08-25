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
st.title('AFC Premium Exec Dashboard')

# About section
st.markdown("""
### About
This application provides defined metrics derived from MBM sales data. To get started, please download the relevant sales report from [RTS](https://www.tjhub3.com/Rts_Arsenal_Hospitality/Suites/HospitalityPackageSales) and upload it here. The app allows you to filter results by date, user, and fixture for tailored insights.
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
    selected_events = st.sidebar.multiselect("Select Events", options=event_names, default=event_names)
    
    # Username filter dropdown in the sidebar for multiple selections
    selected_users = st.sidebar.multiselect("Select Execs", options=valid_usernames, default=valid_usernames)

    # Apply filters only if selections are made
    if date_range and selected_users and selected_events:
        min_date, max_date = (pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) if len(date_range) == 2 else pd.Timestamp(date_range[0]))
        filtered_data = processed_data[
            (processed_data['Created_on'] >= min_date) &
            (processed_data['Created_on'] <= max_date) &
            (processed_data['Created_by'].isin(selected_users)) &
            (processed_data['Event name'].isin(selected_events))
        ]
        
        # Display metrics in the main area
        if not filtered_data.empty:
            # Total Accumulated Sales
            st.write("### Total Accumulated Sales Since going Live")
            total_sold = filtered_data['Total price'].sum()
            total_sold['Total price'] = total_sold['Total price'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold)
            
            # Total Sold Per Fixture
            st.write("### Total Sales Per Match")
            total_sold_per_match = filtered_data.groupby('Event name')['Total price'].sum().reset_index()
            total_sold_per_match['Total price'] = total_sold_per_match['Total price'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold_per_match)
            
             # Total Sold Per Package
            st.write("### Total Sales Per Package")
            total_sold_per_match = filtered_data.groupby('Package name')['Total price'].sum().reset_index()
            total_sold_per_match['Total price'] = total_sold_per_match['Total price'].apply(lambda x: f"£{x:,.2f}")
            st.dataframe(total_sold_per_match)
            
             # Total Sold Per Location
            st.write("### Total Sales Per Location")
            total_sold_per_location = filtered_data.groupby('Location')['Total price'].sum().reset_index()
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
            