
import streamlit as st
import pandas as pd
from user_performance_calc import (
    load_data, remove_grand_total_row, filter_columns, clean_numeric_columns, 
    split_created_by_column, 
    add_additional_info, split_guest_column, convert_date_format,
    columns_to_keep, competition_fixture, competition_fixture_df, total_budget_packages_data,
    total_budget_target_data, total_budget_packages_df, total_budget_target_df
)
# Columns to keep
columns_to_keep = ['Order Id', 'Event name', 'Guest', 'Package name', 'Package GL code','Locations', 'Seats', 
                       'Price', 'Discount', 'Discount value', 'Total price', 'Paid', 'Payment time','Payment status', 
                       'Created by', 'Sale location']

# App title
st.title('Exec User Performance Dashboard')

# File uploader
uploaded_file = st.file_uploader("Choose a sales file", type=['xlsx'])

if uploaded_file is not None:
    # Load the data
    raw_data_load = load_data(uploaded_file)
    
    # Remove the last row if it contains "Grand Total"
    last_row_data = remove_grand_total_row(raw_data_load)
    last_row_data = last_row_data.dropna(subset=['Event name'])

    # Clean and preprocess the data
    columns_to_clean = ['Price', 'Discount value', 'Total price']
    
    # Filter to keep specified columns
    data_filtered = filter_columns(last_row_data, columns_to_keep)
    numeric_cleanse = clean_numeric_columns(data_filtered, columns_to_clean)
    split_created_by = split_created_by_column(numeric_cleanse)
    
    # Create fixture, budget pacakges and budget target dataframes 
    competition_fixture_df = pd.DataFrame(competition_fixture)
    total_budget_packages_df = pd.DataFrame(total_budget_packages_data)
    total_budget_target_df = pd.DataFrame(total_budget_target_data)
    
    # Before merging, ensure package, competition, and fixture names are trimmed of extra spaces
    split_created_by['Package name'] = split_created_by['Package name'].str.strip()
    total_budget_packages_df['Package name'] = total_budget_packages_df['Package name'].str.strip()
    competition_fixture_df['Competition'] = competition_fixture_df['Competition'].str.strip()
    total_budget_target_df['Fixture name'] = total_budget_target_df['Fixture name'].str.strip()
    
    # Perform the merge of all additional information and print the merged data
    processed_df_with_additional_info = add_additional_info(split_created_by, total_budget_packages_df, competition_fixture_df, total_budget_target_df)
    

    # Split "Guest" into "Guest_name" and "Guest_email"
    guest_column_split = split_guest_column(processed_df_with_additional_info)
    converted_dates_df = convert_date_format(guest_column_split, 'Created_on')
    
    # Date range selector
    min_date, max_date = st.date_input("Select Date Range", [])
    if min_date and max_date:
        df = converted_dates_df[(converted_dates_df['Created_on'] >= min_date) & (converted_dates_df['Created_on'] <= max_date)]

    # Username filter
    username = st.selectbox("Select User", options=pd.unique(df['Created_by']))
    if username:
        df = df[df['Created_by'] == username]

    # Display tables with metrics
    st.write("### Top Selling Packages Sold by Exec", df.to_html(index=False), unsafe_allow_html=True)
    st.write("### Total Fixtures Sold by Exec", df.to_html(index=False), unsafe_allow_html=True)
    st.write("### Total Quantity of Packages Sold", df.to_html(index=False), unsafe_allow_html=True)
    st.write("### Most Discounts Used", df.to_html(index=False), unsafe_allow_html=True)

    # Allow user to download filtered data
    st.download_button(
        label="Download data as CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name='filtered_sales_data.csv',
        mime='text/csv',
    )
