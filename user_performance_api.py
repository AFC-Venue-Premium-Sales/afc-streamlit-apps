import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import re
from datetime import datetime
import seaborn as sns
from tjt_hosp_api import filtered_df_without_seats

# Helper Functions
def filter_data_by_date_time(df, min_date, max_date):
    """Filter data based on the selected date and time range."""
    if not min_date or not max_date:
        return df

    if not pd.api.types.is_datetime64_any_dtype(df['CreatedOn']):
        df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], errors='coerce')
    df = df.dropna(subset=['CreatedOn'])
    return df[(df['CreatedOn'] >= min_date) & (df['CreatedOn'] <= max_date)]

def filter_data(df, selected_users, selected_events, selected_paid, selected_competitions):
    """Apply user, event, payment status, and competition filters."""
    if selected_users:
        df = df[df['CreatedBy'].isin(selected_users)]
    if selected_events:
        df = df[df['Fixture Name'].isin(selected_events)]
    if selected_paid:
        df = df[df['IsPaid'] == selected_paid]
    if selected_competitions:
        df = df[df['EventCompetition'].isin(selected_competitions)]
    return df

def display_progress_bar():
    """Display a progress bar in the sidebar."""
    progress_bar = st.sidebar.progress(0)
    progress_steps = [10, 30, 50, 100]
    for step in progress_steps:
        progress_bar.progress(step)

def refresh_data():
    """Fetch the latest data for User Performance."""
    try:
        with st.spinner("Fetching latest data..."):
            updated_data = filtered_df_without_seats  # Fetch latest data
            st.session_state["user_data"] = updated_data
            st.success("✅ User performance data refreshed successfully!")
    except Exception as e:
        st.error(f"❌ Failed to refresh user performance data: {str(e)}")

def generate_kpis(filtered_data):
    """Display key performance indicators."""
    # Ensure TotalWithOtherPayments exists
    if 'TotalWithOtherPayments' not in filtered_data.columns:
        if 'TotalPrice' in filtered_data.columns and 'OtherPayments' in filtered_data.columns:
            filtered_data['TotalWithOtherPayments'] = (
                filtered_data['TotalPrice'] + filtered_data['OtherPayments'].fillna(0)
            )
        else:
            st.warning("⚠️ Missing columns for TotalWithOtherPayments calculation.")
            filtered_data['TotalWithOtherPayments'] = 0

    # Calculate KPIs
    total_revenue = filtered_data['TotalWithOtherPayments'].sum()
    total_packages = len(filtered_data)
    average_revenue_per_package = total_revenue / total_packages if total_packages > 0 else 0
    top_exec = (
        filtered_data.groupby('CreatedBy')['TotalWithOtherPayments'].sum().idxmax()
        if not filtered_data.empty else "N/A"
    )

    st.write("### Key Performance Indicators (KPIs)")
    st.metric("💷 Total Revenue", f"£{total_revenue:,.2f}")
    st.metric("🎟️ Total Packages Sold", total_packages)
    st.metric("📈 Average Revenue per Package", f"£{average_revenue_per_package:,.2f}")
    st.metric("🏆 Top Exec (Revenue)", top_exec)


def generate_charts(filtered_data):
    """Generate and display charts based on the filtered data."""
    st.write("### 📊 Total Package Sales by Exec")

    # Filter out excluded keywords from the Discount column
    exclude_keywords = ["credit", "voucher", "gift voucher", "discount", "pldl"]
    mask = ~filtered_data['Discount'].str.contains('|'.join([re.escape(k) for k in exclude_keywords]), case=False, na=False)
    filtered_data_without_excluded_keywords = filtered_data[mask]

    # Aggregate Other Payments by Exec
    other_payments_by_exec = (
        filtered_data_without_excluded_keywords.groupby('CreatedBy', as_index=False)['DiscountValue']
        .sum()
        .rename(columns={'DiscountValue': 'OtherPayments'})
    )

    # Merge Other Payments back into filtered data
    filtered_data = filtered_data.merge(other_payments_by_exec, how='left', on='CreatedBy')
    filtered_data['OtherPayments'] = filtered_data['OtherPayments'].fillna(0)

    # Aggregate Total Sales by Exec
    total_sales_by_exec = filtered_data.groupby('CreatedBy', as_index=False).agg(
        TotalPrice=('TotalPrice', 'sum'),
        OtherPayments=('OtherPayments', 'first')  # Already merged OtherPayments
    )
    total_sales_by_exec['TotalWithOtherPayments'] = (
        total_sales_by_exec['TotalPrice'] + total_sales_by_exec['OtherPayments']
    )

    # Display DataFrame
    st.dataframe(total_sales_by_exec)

    # Bar Chart: Total Sales with Other Payments
    fig, ax1 = plt.subplots(figsize=(10, 6))
    bar_width = 0.6

    # Plot bar chart
    bars = ax1.bar(
        total_sales_by_exec['CreatedBy'], 
        total_sales_by_exec['TotalWithOtherPayments'], 
        color='gold', 
        label='Total Sales (£)', 
        width=bar_width
    )

    ax1.set_ylabel('Total Sales (£)', fontsize=10)
    ax1.set_xlabel('Exec', fontsize=10)
    ax1.set_ylim(0)
    ax1.set_title('Total Package Sales (Inc Other Payments) by Exec', fontsize=14)
    ax1.tick_params(axis='y', labelsize=10)
    ax1.tick_params(axis='x', labelsize=10)
    plt.xticks(rotation=45, ha='right')

    # Cumulative Contribution Line Chart
    ax2 = ax1.twinx()
    cumulative_percentage = (total_sales_by_exec['TotalWithOtherPayments'].cumsum() / 
                             total_sales_by_exec['TotalWithOtherPayments'].sum()) * 100
    line = ax2.plot(
        total_sales_by_exec['CreatedBy'], 
        cumulative_percentage, 
        color='blue', 
        marker='o', 
        linestyle='-', 
        label='Cumulative Contribution (%)'
    )
    ax2.set_ylabel('Cumulative Contribution (%)', fontsize=10)
    ax2.tick_params(axis='y', labelsize=10)
    ax2.set_ylim(0, 110)

    # Add legend
    lines_labels = bars.get_label(), line[0].get_label()
    plt.legend(lines_labels, loc='upper left', fontsize=10)
    st.pyplot(fig)

def generate_heatmap(filtered_data):
    """Generate a heatmap for sales trends."""
    st.write("### 🔥 Sales Trends Heatmap")
    sales_trend = (
        filtered_data.groupby([filtered_data['CreatedOn'].dt.date, filtered_data['CreatedOn'].dt.hour])
        ['TotalPrice']
        .sum()
        .unstack(fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(sales_trend, cmap="YlGnBu", ax=ax)
    ax.set_title("Sales Trends (Date vs. Hour)")
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Date")
    st.pyplot(fig)

def run_app():
    """Main application function."""
    specified_users = ['dcoppin', 'Jedwards', 'jedwards', 'bgardiner', 'BenT', 'jmurphy', 'ayildirim',
                       'MeganS', 'BethNW', 'HayleyA', 'LucyB', 'Conor', 'SavR', 'MillieS', 'dmontague']

    st.title('👤AFC Premium Exec Dashboard👤')

    st.markdown("""
    ### ℹ️ About
    This application provides detailed Exec Sales Metrics ONLY, derived from RTS data. The data is retrieved from TJT's MBM sales API.
    """)

    # Load data
    try:
        loaded_api_df = filtered_df_without_seats  # Dynamically fetch data
        st.sidebar.success("✅ Data retrieved successfully.")
    except Exception as e:
        st.sidebar.error(f"🚨 Failed to load initial data: {str(e)}")
        loaded_api_df = pd.DataFrame()  # Fallback to an empty DataFrame

    if loaded_api_df is not None and not loaded_api_df.empty:
        st.sidebar.success("✅ Data retrieved successfully.")
        display_progress_bar()

        # Sidebar Filters
        st.sidebar.header("Filter Data by Date and Time")
        date_range = st.sidebar.date_input("📅 Select Date Range", [], key="unique_date_range_key")
        start_time = st.sidebar.time_input("⏰ Start Time", value=datetime.now().replace(hour=0, minute=0, second=0).time(), key="unique_start_time_key")
        end_time = st.sidebar.time_input("⏰ End Time", value=datetime.now().replace(hour=23, minute=59, second=59).time(), key="unique_end_time_key")

        # Combine date and time inputs into full datetime objects
        if len(date_range) == 1:
            min_date = datetime.combine(date_range[0], start_time)
            max_date = datetime.combine(date_range[0], end_time)
        elif len(date_range) == 2:
            min_date = datetime.combine(date_range[0], start_time)
            max_date = datetime.combine(date_range[1], end_time)
        else:
            min_date, max_date = None, None

        # Define valid and default users for the multiselect widget
        valid_usernames = [user for user in pd.unique(loaded_api_df['CreatedBy'])]  # Extract valid execs from the data
        default_selected_users = [user for user in specified_users if user in valid_usernames]  # Filter specified_users

        # Multiselect for executives with filtered defaults
        selected_users = st.sidebar.multiselect(
            "👤 Select Execs",
            options=valid_usernames,
            default=default_selected_users  # Use the filtered list as default
        )

        selected_events = st.sidebar.multiselect("🎫 Select Events", options=pd.unique(loaded_api_df['Fixture Name']), default=None)
        selected_paid = st.sidebar.selectbox("💰 Filter by IsPaid", options=pd.unique(loaded_api_df['IsPaid']))

        # Add EventCompetition filter
        event_competitions = pd.unique(loaded_api_df['EventCompetition'])
        selected_competitions = st.sidebar.multiselect(
            "🏆 Select Event Competitions",
            options=event_competitions,
            default=None
        )

        # Apply Filters
        filtered_data = loaded_api_df.copy()
        filtered_data = filter_data_by_date_time(filtered_data, min_date, max_date)
        filtered_data = filter_data(filtered_data, selected_users, selected_events, selected_paid, selected_competitions)

        # Display Filtered Data and Metrics
        if not filtered_data.empty:
            generate_kpis(filtered_data)
            generate_charts(filtered_data)
            generate_heatmap(filtered_data)
        else:
            st.warning("⚠️ No data available for the selected filters.")
    else:
        st.warning("⚠️ No data available or data could not be loaded.")

if __name__ == "__main__":
    run_app()
