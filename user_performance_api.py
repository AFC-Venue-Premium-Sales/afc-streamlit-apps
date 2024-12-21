import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import re
from tjt_hosp_api import filtered_df_without_seats


# Helper Functions
def filter_data_by_date(df, date_range):
    """Filter data based on the selected date range."""
    if not date_range:
        return df
    min_date = pd.Timestamp(date_range[0])
    max_date = pd.Timestamp(date_range[1]) if len(date_range) == 2 else min_date
    if not pd.api.types.is_datetime64_any_dtype(df['CreatedOn']):
        df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], errors='coerce')
    df = df.dropna(subset=['CreatedOn'])
    return df[(df['CreatedOn'] >= min_date) & (df['CreatedOn'] <= max_date)]


def filter_data(df, selected_users, selected_events, selected_paid):
    """Apply user, event, and payment status filters."""
    if selected_users:
        df = df[df['CreatedBy'].isin(selected_users)]
    if selected_events:
        df = df[df['Fixture Name'].isin(selected_events)]
    if selected_paid:
        df = df[df['IsPaid'] == selected_paid]
    return df


def display_progress_bar():
    """Display a progress bar in the sidebar."""
    progress_bar = st.sidebar.progress(0)
    progress_steps = [10, 30, 50, 100]
    for step in progress_steps:
        progress_bar.progress(step)


def generate_charts(filtered_data):
    """Generate and display charts based on the filtered data."""
    st.write("### 📊 Total Package Sales by Exec")

    # Chart Configurations
    chart_size = (8, 4)
    font_size_title = 14
    font_size_labels = 10

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

    # Format data for display
    total_sales_by_exec[['TotalPrice', 'OtherPayments', 'TotalWithOtherPayments']] = (
        total_sales_by_exec[['TotalPrice', 'OtherPayments', 'TotalWithOtherPayments']].round(1)
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

    ax1.set_ylabel('Total Sales (£)', fontsize=font_size_labels)
    ax1.set_xlabel('Exec', fontsize=font_size_labels)
    ax1.set_ylim(0)
    ax1.set_title('Total Package Sales (Inc Other Payments) by Exec', fontsize=font_size_title)
    ax1.tick_params(axis='y', labelsize=font_size_labels)
    ax1.tick_params(axis='x', labelsize=font_size_labels)
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
    ax2.set_ylabel('Cumulative Contribution (%)', fontsize=font_size_labels)
    ax2.tick_params(axis='y', labelsize=font_size_labels)
    ax2.set_ylim(0, 110)

    # Add legend
    lines_labels = bars.get_label(), line[0].get_label()
    plt.legend(lines_labels, loc='upper left', fontsize=font_size_labels)
    st.pyplot(fig)

    # Average Sale Value by Exec
    st.write("### 📊 Average Sale Value Per Exec")
    avg_sales_by_exec = filtered_data.groupby('CreatedBy').agg(
        AvgSaleValue=('TotalPrice', 'mean'),
        SalesCount=('CreatedBy', 'size')
    ).reset_index()

    avg_sales_by_exec['AvgSaleValue'] = avg_sales_by_exec['AvgSaleValue'].round(1)
    st.dataframe(avg_sales_by_exec)

    # Grouped Bar Chart for Average Sale Value
    fig, ax = plt.subplots(figsize=chart_size)
    ax.bar(
        avg_sales_by_exec['CreatedBy'],
        avg_sales_by_exec['AvgSaleValue'],
        color='gold',
        label='Avg Sale Value (£)'
    )
    ax.set_title('Average Sale Value per Exec', fontsize=font_size_title)
    ax.set_xlabel('Exec', fontsize=font_size_labels)
    ax.set_ylabel('Avg Sale Value (£)', fontsize=font_size_labels)
    plt.xticks(rotation=45, ha='right')
    plt.legend()
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
        date_range = st.sidebar.date_input("📅 Select Date Range", [], key="user_perf_date_range")
        valid_usernames = [user for user in specified_users if user in pd.unique(loaded_api_df['CreatedBy'])]
        selected_events = st.sidebar.multiselect("🎫 Select Events", options=pd.unique(loaded_api_df['Fixture Name']), default=None)
        selected_users = st.sidebar.multiselect("👤 Select Execs", options=valid_usernames, default=None)
        selected_paid = st.sidebar.selectbox("💰 Filter by IsPaid", options=pd.unique(loaded_api_df['IsPaid']))

        # Apply Filters
        filtered_data = loaded_api_df.copy()
        filtered_data = filter_data_by_date(filtered_data, date_range)
        filtered_data = filter_data(filtered_data, selected_users, selected_events, selected_paid)

        # Display Filtered Data and Charts
        if not filtered_data.empty:
            st.write(f"Filtered Data:", filtered_data)
            generate_charts(filtered_data)
        else:
            st.warning("⚠️ No data available for the selected filters.")
    else:
        st.warning("⚠️ No data available or data could not be loaded.")


if __name__ == "__main__":
    run_app()
