import streamlit as st
import pandas as pd
from user_performance_calc import (
    load_data, remove_grand_total_row, filter_columns, clean_numeric_columns, 
    split_created_by_column, add_additional_info, split_guest_column, convert_date_format,
    columns_to_keep, competition_fixture, total_budget_packages_data,
    total_budget_target_data
)

# Specified users list
specified_users = ['dcoppin', 'Jedwards', 'jedwards', 'bgardiner', 'BenT', 'jmurphy', 'ayildirim',
                   'MeganS', 'BethNW', 'HayleyA', 'LucyB', 'Conor', 'SavR']

# App title
st.title('Exec User Performance Dashboard')

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

    # Event name filter dropdown in the sidebar
    event_names = pd.unique(processed_data['Event name'])
    selected_events = st.sidebar.multiselect("Select Events", options=event_names, default=event_names)

    # Username filter dropdown in the sidebar for multiple selections
    if not processed_data.empty:
        # Filter usernames based on the specified list
        valid_usernames = [user for user in pd.unique(processed_data['Created_by']) if user in specified_users]
        selected_users = st.sidebar.multiselect("Select Users", options=valid_usernames, default=valid_usernames)

        # Apply filters only if selections are made
        if date_range and selected_users and selected_events:
            min_date, max_date = (date_range[0], date_range[1]) if len(date_range) == 2 else (date_range[0], date_range[0])
            filtered_data = processed_data[
                (processed_data['Created_on'] >= pd.Timestamp(min_date)) &
                (processed_data['Created_on'] <= pd.Timestamp(max_date)) &
                (processed_data['Created_by'].isin(selected_users)) &
                (processed_data['Event name'].isin(selected_events))
            ]

            # Display metrics in the main area
            if not filtered_data.empty:
                st.write("### Top Selling Packages Sold by Exec")
                st.dataframe(filtered_data[['Package name', 'Total price']].groupby('Package name').sum().reset_index())

                st.write("### Total Fixtures Sold by Exec")
                st.dataframe(filtered_data['Package name'].value_counts().reset_index().rename(columns={'index': 'Package', 'Package name': 'Count'}))

                st.write("### Total Quantity of Packages Sold")
                st.dataframe(filtered_data[['Package name', 'Total price']].groupby('Package name').count().rename(columns={'Total price': 'Total Sold'}).reset_index())

                st.write("### Most Discounts Used")
                st.dataframe(filtered_data['Discount'].value_counts().reset_index().rename(columns={'index': 'Discount Type', 'Discount': 'Count'}))

                # Download button for filtered data
                st.download_button(
                    label="Download Filtered Data as CSV",
                    data=filtered_data.to_csv(index=False).encode('utf-8'),
                    file_name='filtered_sales_data.csv',
                    mime='text/csv',
                )
