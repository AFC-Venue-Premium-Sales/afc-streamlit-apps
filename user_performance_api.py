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

def generate_kpis(filtered_data):
    """Display key performance indicators."""
    total_revenue = filtered_data['TotalPrice'].sum()
    total_packages = len(filtered_data)
    average_revenue_per_package = total_revenue / total_packages if total_packages > 0 else 0
    top_exec = (
        filtered_data.groupby('CreatedBy')['TotalPrice'].sum().idxmax()
        if not filtered_data.empty else "N/A"
    )

    st.write("### Key Metrics")
    st.metric("💷 Total Revenue", f"£{total_revenue:,.2f}")
    st.metric("🎟️ Total Packages Sold", total_packages)
    st.metric("📈 Average Revenue per Package", f"£{average_revenue_per_package:,.2f}")
    st.metric("🏆 Top Exec (Revenue)", top_exec)

def generate_heatmap(filtered_data):
    """Generate a heatmap for sales trends."""
    st.write("### 🔥 Sales Trends Heatmap")
    filtered_data['CreatedDate'] = filtered_data['CreatedOn'].dt.date
    filtered_data['CreatedHour'] = filtered_data['CreatedOn'].dt.hour

    sales_trend = (
        filtered_data.groupby(['CreatedDate', 'CreatedHour'])
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

def generate_revenue_chart(filtered_data):
    """Generate a bar chart for revenue by fixture."""
    st.write("### 📊 Revenue by Fixture")
    revenue_by_fixture = (
        filtered_data.groupby('Fixture Name')['TotalPrice']
        .sum()
        .sort_values(ascending=False)
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    revenue_by_fixture.plot(kind='bar', ax=ax, color='skyblue', edgecolor='black')
    ax.set_title("Revenue by Fixture")
    ax.set_xlabel("Fixture")
    ax.set_ylabel("Total Revenue (£)")
    plt.xticks(rotation=45, ha='right')
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
    loaded_api_df = filtered_df_without_seats 

    if loaded_api_df is not None and not loaded_api_df.empty:
        st.sidebar.success("✅ Data retrieved successfully.")
        display_progress_bar()

        # Sidebar Filters
        st.sidebar.header("Filter Data")
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

        # Sidebar filters for users, events, and competitions
        valid_usernames = [user for user in pd.unique(loaded_api_df['CreatedBy'])]
        filtered_default_users = [user for user in specified_users if user in valid_usernames]
        selected_users = st.sidebar.multiselect("👤 Select Execs", options=valid_usernames, default=filtered_default_users)
        selected_events = st.sidebar.multiselect("🎫 Select Events", options=pd.unique(loaded_api_df['Fixture Name']))
        event_competitions = pd.unique(loaded_api_df['EventCompetition'])
        selected_competitions = st.sidebar.multiselect("🏆 Select Event Competitions", options=event_competitions)

        # Apply Filters
        filtered_data = filter_data_by_date_time(loaded_api_df, min_date, max_date)
        filtered_data = filter_data(filtered_data, selected_users, selected_events, None, selected_competitions)

        # Display Filtered Data and Metrics
        if not filtered_data.empty:
            generate_kpis(filtered_data)
            generate_heatmap(filtered_data)
            generate_revenue_chart(filtered_data)
        else:
            st.warning("⚠️ No data available for the selected filters.")
    else:
        st.warning("⚠️ No data available or data could not be loaded.")

if __name__ == "__main__":
    run_app()
