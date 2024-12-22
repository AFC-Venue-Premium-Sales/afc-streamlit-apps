import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from tjt_hosp_api import filtered_df_without_seats
import re

# Helper Functions
def apply_filters(data, filters):
    """Applies the selected filters to the dataset."""
    # Unpack filters
    min_date, max_date, selected_sale_location, selected_users, selected_categories, selected_events, selected_discounts = filters

    # Date Range Filter
    if min_date and max_date:
        data = data[(data['CreatedOn'] >= min_date) & (data['CreatedOn'] <= max_date)]

    # SaleLocation Filter
    if selected_sale_location:
        data = data[data['SaleLocation'].isin(selected_sale_location)]

    # User Filter
    if selected_users:
        data = data[data['CreatedBy'].isin(selected_users)]

    # Event Category Filter
    if selected_categories:
        data = data[data['EventCompetition'].isin(selected_categories)]

    # Event Filter
    if selected_events:
        data = data[data['Fixture Name'].isin(selected_events)]

    # Discount Filter
    if selected_discounts:
        data = data[data['Discount'].isin(selected_discounts)]

    return data


def calculate_totals(data, exclude_keywords):
    """Calculates dynamic totals and filters out specific keywords."""
    mask = ~data['Discount'].str.contains('|'.join([re.escape(keyword) for keyword in exclude_keywords]), 
                                          case=False, na=False)
    filtered_data = data[mask]

    # Calculate totals
    total_discount_value = filtered_data['DiscountValue'].sum()
    total_sales = filtered_data['TotalPrice'].sum() + total_discount_value

    return total_sales, total_discount_value, filtered_data


def display_summary_tables(filtered_data, exclude_keywords):
    """Generates and displays summary tables."""
    # Dynamic Totals
    dynamic_total, total_discount_value, filtered_without_keywords = calculate_totals(
        filtered_data, exclude_keywords
    )

    # Summary
    st.write("### 💼 Filtered Accumulated Sales")
    st.write(f"Total Accumulated Sales (Filtered): **£{dynamic_total:,.2f}** ")

    # Total Sales Per Fixture
    st.write("### ⚽ Total Sales Summary")
    total_sold_per_match = (
        filtered_without_keywords.groupby("Fixture Name")
        .agg(
            RTS_Sales=("TotalPrice", "sum"),
            Budget=("Budget", "first"),
            CoversSold=("Seats", "sum")
        )
        .reset_index()
    )
    st.dataframe(total_sold_per_match)

    return total_sold_per_match


def handle_downloads(filtered_data, woolwich_data):
    """Handles download buttons for different datasets."""
    # Filtered Data
    if not filtered_data.empty:
        st.download_button(
            label="💾 Download Filtered Data",
            data=filtered_data.to_csv(index=False).encode('utf-8'),
            file_name='filtered_data.csv',
            mime='text/csv',
        )

    # Woolwich Restaurant Data
    if not woolwich_data.empty:
        st.download_button(
            label="💾 Download Woolwich Restaurant Data",
            data=woolwich_data.to_csv(index=False).encode('utf-8'),
            file_name='woolwich_restaurant_data.csv',
            mime='text/csv',
        )


# Main App Function
def run_app():
    st.title('💷 MBM Sales 💷')

    st.markdown("""
    ### ℹ️ About
    This app provides sales metrics from TJT's data. 
    You can filter results by date, user, fixture, payment status, and paid status for tailored insights. 
    """)

    # Fetch Data
    try:
        loaded_data = filtered_df_without_seats.copy()
    except Exception as e:
        st.error(f"❌ Failed to load data: {str(e)}")
        return

    # Sidebar Filters
    st.sidebar.header("Filter Data")
    date_range = st.sidebar.date_input("📅 Select Date Range", [])
    start_time = st.sidebar.time_input("⏰ Start Time", datetime.min.time())
    end_time = st.sidebar.time_input("⏰ End Time", datetime.max.time())

    # Combine date and time into datetime objects
    if len(date_range) == 1:
        min_date = datetime.combine(date_range[0], start_time)
        max_date = datetime.combine(date_range[0], end_time)
    elif len(date_range) == 2:
        min_date = datetime.combine(date_range[0], start_time)
        max_date = datetime.combine(date_range[1], end_time)
    else:
        min_date, max_date = None, None

    # Additional Filters
    valid_users = [user for user in ['User1', 'User2'] if user in loaded_data['CreatedBy'].unique()]
    selected_users = st.sidebar.multiselect("👤 Select Users", options=valid_users)
    selected_sale_location = st.sidebar.multiselect("📍 Select Sale Location", options=loaded_data['SaleLocation'].unique())
    selected_events = st.sidebar.multiselect("🎫 Select Events", options=loaded_data['Fixture Name'].unique())

    # Apply Filters
    filters = (min_date, max_date, selected_sale_location, selected_users, None, selected_events, None)
    filtered_data = apply_filters(loaded_data, filters)

    # Exclude keywords for "Other" calculations
    exclude_keywords = ["credit", "voucher", "gift voucher", "discount", "pldl"]
    total_sales_summary = display_summary_tables(filtered_data, exclude_keywords)

    # Handle Woolwich Restaurant Sales
    woolwich_data = filtered_data[
        filtered_data['Package Name'].isin(['Platinum', 'Woolwich Restaurant'])
    ]
    st.write("### 🍴 Woolwich Restaurant Sales")
    st.dataframe(woolwich_data)

    # Download Buttons
    handle_downloads(filtered_data, woolwich_data)


if __name__ == "__main__":
    run_app()
