import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import re
from tjt_hosp_api import fetch_filtered_df_without_seats

def run_app():
    # Your existing User Performance code
    specified_users = ['dcoppin', 'Jedwards', 'jedwards', 'bgardiner', 'BenT', 'jmurphy', 'ayildirim',
                       'MeganS', 'BethNW', 'HayleyA', 'LucyB', 'Conor', 'SavR', 'MillieS', 'dmontague']

    arsenal_gold = '#DAA520'

    st.title('👤AFC Premium Exec Dashboard👤')

    st.markdown("""
    ### ℹ️ About
    This application provides detailed Exec Sales Metrics ONLY, derived from RTS data. The data is retrieved from TJT's MBM sales API. The app allows you to filter results by date, user, and fixture for tailored insights.
    """)

    loaded_api_df = fetch_filtered_df_without_seats

    if loaded_api_df is not None:
        st.sidebar.success("✅ Data retrieved successfully.")
        progress_bar = st.sidebar.progress(0)
        progress_bar.progress(10)
        progress_bar.progress(30)
        progress_bar.progress(50)
        progress_bar.progress(100)

        # Sidebar Features
        date_range = st.sidebar.date_input("📅 Select Date Range", [])
        valid_usernames = [user for user in specified_users if user in pd.unique(loaded_api_df['CreatedBy'])]
        event_names = pd.unique(loaded_api_df['Fixture Name'])
        selected_events = st.sidebar.multiselect("🎫 Select Events", options=event_names, default=event_names)
        selected_users = st.sidebar.multiselect("👤 Select Execs", options=valid_usernames, default=valid_usernames)
        # payment_status_options = pd.unique(loaded_api_df['Payment status'])
        # selected_payment_status = st.sidebar.multiselect("💳 Select Payment Status", options=payment_status_options, default=None)
        paid_options = pd.unique(loaded_api_df['IsPaid'])
        selected_paid = st.sidebar.selectbox("💰 Filter by IsPaid", options=paid_options) 

        # Initialize filtered_data with processed_data to ensure no errors occur if no filters are applied
        filtered_data = loaded_api_df.copy()

        if date_range:
            # Convert date_range to pandas Timestamps
            min_date = pd.Timestamp(date_range[0])
            max_date = pd.Timestamp(date_range[1]) if len(date_range) == 2 else pd.Timestamp(date_range[0])

            # Ensure 'CreatedOn' is in datetime format
            filtered_data['CreatedOn'] = pd.to_datetime(filtered_data['CreatedOn'], errors='coerce')

            # Log the date values for debugging
            st.write(f"Filtering data from {min_date} to {max_date}")
            
            # Drop rows with invalid dates
            filtered_data = filtered_data.dropna(subset=['CreatedOn'])

            # Apply date filtering
            filtered_data = filtered_data[
                (filtered_data['CreatedOn'] >= min_date) & (filtered_data['CreatedOn'] <= max_date)
            ]



        if selected_users:
            filtered_data = filtered_data[filtered_data['CreatedBy'].isin(selected_users)]

        if selected_events:
            filtered_data = filtered_data[filtered_data['Fixture Name'].isin(selected_events)]

        # Apply paid status filter
        if selected_paid:
            filtered_data = filtered_data[filtered_data['IsPaid'] == selected_paid]

        # Apply payment status filter
        # if selected_payment_status:
        #     filtered_data = filtered_data[filtered_data['Payment status'].isin(selected_payment_status)]

    
        if not filtered_data.empty:
            # Chart configurations
            chart_size = (8, 4)
            font_size_title = 14
            font_size_labels = 10

            # Define exclude keywords for filtering the Discount column
            exclude_keywords = ["credit", "voucher", "gift voucher", "discount", "pldl"]
            mask = ~filtered_data['Discount'].str.contains(
                '|'.join([re.escape(keyword) for keyword in exclude_keywords]), case=False, na=False
            )

            # Filter data to include only rows without excluded keywords
            filtered_data_without_excluded_keywords = filtered_data[mask]

            # Calculate Other Payments per Exec (Correctly Aggregated)
            other_payments_by_exec = (
                filtered_data_without_excluded_keywords
                .groupby('CreatedBy', as_index=False)['DiscountValue']
                .sum()
                .rename(columns={'DiscountValue': 'OtherPayments'})
            )

            # Merge Other Payments back to the filtered data
            filtered_data = filtered_data.merge(
                other_payments_by_exec,
                how='left',
                on='CreatedBy'
            )

            # Fill NaN values in 'OtherPayments' with 0
            filtered_data['OtherPayments'] = filtered_data['OtherPayments'].fillna(0)

            # Total Package Sales by Exec
            st.write("### 📊 Total Package Sales by Exec")
            total_package_sales_by_exec = filtered_data.groupby('CreatedBy', as_index=False).agg(
                TotalPrice=('TotalPrice', 'sum'),
                OtherPayments=('OtherPayments', 'first')  # Use the already merged OtherPayments
            )

            # Calculate Total With Other Payments
            total_package_sales_by_exec['TotalWithOtherPayments'] = (
                total_package_sales_by_exec['TotalPrice'] + total_package_sales_by_exec['OtherPayments']
            )

            # Format the columns to one decimal place
            total_package_sales_by_exec['TotalPrice'] = total_package_sales_by_exec['TotalPrice'].round(1)
            total_package_sales_by_exec['OtherPayments'] = total_package_sales_by_exec['OtherPayments'].round(1)
            total_package_sales_by_exec['TotalWithOtherPayments'] = total_package_sales_by_exec['TotalWithOtherPayments'].round(1)

            # Display the table
            st.dataframe(total_package_sales_by_exec)

            # Plot the combination chart
            fig, ax1 = plt.subplots(figsize=(10, 6))

            # Bar chart for Total With Other Payments
            bar_width = 0.6
            bars = ax1.bar(
                total_package_sales_by_exec['CreatedBy'], 
                total_package_sales_by_exec['TotalWithOtherPayments'], 
                color='gold', 
                label='Total Sales (£)', 
                width=bar_width
            )

            # Format y-axis for bar chart
            ax1.set_ylabel('Total Sales (£)', fontsize=font_size_labels)
            ax1.set_xlabel('Exec', fontsize=font_size_labels)
            ax1.set_ylim(0)
            ax1.set_title('Total Package Sales (Inc Other Payments) by Exec', fontsize=font_size_title)
            ax1.tick_params(axis='y', labelsize=font_size_labels)
            ax1.tick_params(axis='x', labelsize=font_size_labels)
            plt.xticks(rotation=45, ha='right')

            # Add cumulative percentage line chart
            ax2 = ax1.twinx()
            cumulative_percentage = (total_package_sales_by_exec['TotalWithOtherPayments'].cumsum() / 
                                    total_package_sales_by_exec['TotalWithOtherPayments'].sum()) * 100
            line = ax2.plot(
                total_package_sales_by_exec['CreatedBy'], 
                cumulative_percentage, 
                color='blue', 
                marker='o', 
                linestyle='-', 
                label='Cumulative Contribution (%)'
            )

            # Format y-axis for line chart
            ax2.set_ylabel('Cumulative Contribution (%)', fontsize=font_size_labels)
            ax2.tick_params(axis='y', labelsize=font_size_labels)
            ax2.set_ylim(0, 110)  # Ensure it includes 100% at the top

            # Add legend
            lines_labels = bars.get_label(), line[0].get_label()
            plt.legend(lines_labels, loc='upper left', fontsize=font_size_labels)

            # Render the chart in Streamlit
            st.pyplot(fig)



            # Average Sale Value Per Exec
            st.write("### 📊 Average Sale Value Per Exec")

            # Calculate average values for TotalPrice and OtherPayments
            avg_sale_value_per_exec = filtered_data.groupby('CreatedBy').agg(
                AveragePrice=('TotalPrice', 'mean'),  # Average of TotalPrice
                OtherPayments=('OtherPayments', 'sum'),  # Total OtherPayments for each Exec
                SalesCount=('CreatedBy', 'size')  # Total number of sales per Exec
            ).reset_index()

            # Calculate the true average for OtherPayments
            avg_sale_value_per_exec['OtherPaymentsAvg'] = avg_sale_value_per_exec['OtherPayments'] / avg_sale_value_per_exec['SalesCount']

            # Rename columns for display
            avg_sale_value_per_exec = avg_sale_value_per_exec.rename(columns={
                'CreatedBy': 'Exec',
                'AveragePrice': 'Avg Sale Value',
                'OtherPaymentsAvg': 'Other Avg Sale Value'
            })

            # Keep only necessary columns
            avg_sale_value_per_exec = avg_sale_value_per_exec[['Exec', 'Avg Sale Value', 'Other Avg Sale Value']]

            # Round values to 1 decimal place
            avg_sale_value_per_exec['Avg Sale Value'] = avg_sale_value_per_exec['Avg Sale Value'].round(1)
            avg_sale_value_per_exec['Other Avg Sale Value'] = avg_sale_value_per_exec['Other Avg Sale Value'].round(1)

            # Display the table
            st.dataframe(avg_sale_value_per_exec)

            # Plot the chart with Avg Sale Value and Other Avg Sale Value
            fig, ax = plt.subplots(figsize=chart_size)

            # Create a grouped bar chart
            x = avg_sale_value_per_exec['Exec']
            bar_width = 0.4

            # Position of bars on X-axis
            r1 = range(len(x))
            r2 = [pos + bar_width for pos in r1]

            # Plot bars
            ax.bar(r1, avg_sale_value_per_exec['Avg Sale Value'], color='gold', width=bar_width, label='Avg Sale Value (£)')
            ax.bar(r2, avg_sale_value_per_exec['Other Avg Sale Value'], color='blue', width=bar_width, label='Other Avg Sale Value (£)')

            # Add labels and title
            ax.set_title('Average Sale Value (Inc Other Payments) per Exec', fontsize=font_size_title)
            ax.set_xlabel('Exec', fontsize=font_size_labels)
            ax.set_ylabel('Average Sales (£)', fontsize=font_size_labels)
            ax.set_xticks([pos + bar_width / 2 for pos in r1])
            ax.set_xticklabels(x, rotation=45, ha='right', fontsize=font_size_labels)
            ax.legend(fontsize=font_size_labels)

            # Render the chart in Streamlit
            st.pyplot(fig)



            # Total Count of Sales By Exec
            st.write("### 🧮 Total Count of Sales by Exec")

            # Filter the data to include only confirmed sales (IsPaid == "TRUE") and exclude rows where TotalPrice and DiscountValue are 0
            confirmed_sales = filtered_data[
                (filtered_data['IsPaid'].astype(str).str.strip().str.upper() == 'TRUE') & 
                ~((filtered_data['TotalPrice'] == 0) & (filtered_data['DiscountValue'] == 0))
            ]

            # Group by CreatedBy and calculate Total Sales and Total Covers Sold
            total_sales_count_by_exec = confirmed_sales.groupby('CreatedBy').agg(
                TotalSales=('CreatedBy', 'size'),  # Total Sales (count)
                TotalCoversSold=('Seats', 'sum')  # Total Covers Sold
            ).reset_index()

            # Handle cases where no seats were sold (fill NaN with 0)
            total_sales_count_by_exec['TotalCoversSold'] = total_sales_count_by_exec['TotalCoversSold'].fillna(0).astype(int)

            # Display the table
            st.dataframe(total_sales_count_by_exec)

            # Plot the chart for Total Count of Sales
            fig, ax = plt.subplots(figsize=chart_size)
            ax.bar(
                total_sales_count_by_exec['CreatedBy'], 
                total_sales_count_by_exec['TotalSales'], 
                color='gold'
            )
            ax.set_title('Total Number of Sales per Exec', fontsize=font_size_title)
            ax.set_xlabel('Exec', fontsize=font_size_labels)
            ax.set_ylabel('Total Sales Count', fontsize=font_size_labels)
            ax.set_ylim(0)
            plt.xticks(rotation=45, ha='right', fontsize=font_size_labels)
            plt.yticks(fontsize=font_size_labels)
            st.pyplot(fig)  # Correct way to render the chart in Streamlit


            # Plot the chart for Total Covers Sold
            fig, ax = plt.subplots(figsize=chart_size)
            ax.bar(
                total_sales_count_by_exec['CreatedBy'], 
                total_sales_count_by_exec['TotalCoversSold'], 
                color='gold'
            )
            ax.set_title('Total Covers Sold per Exec', fontsize=font_size_title)
            ax.set_xlabel('Exec', fontsize=font_size_labels)
            ax.set_ylabel('Total Covers Sold', fontsize=font_size_labels)
            ax.set_ylim(0)
            plt.xticks(rotation=45, ha='right', fontsize=font_size_labels)
            plt.yticks(fontsize=font_size_labels)
            st.pyplot(fig)


            # Revenue Contribution Percentage
            st.write("### 📈 Revenue Contribution Percentage per Exec")
            total_revenue_with_other = total_package_sales_by_exec['TotalWithOtherPayments'].sum()
            total_package_sales_by_exec['Contribution (%)'] = (
                total_package_sales_by_exec['TotalWithOtherPayments'] / total_revenue_with_other * 100
            )

            # Display the table
            total_package_sales_by_exec['Contribution (%)'] = total_package_sales_by_exec['Contribution (%)'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(total_package_sales_by_exec[['CreatedBy', 'Contribution (%)']])

            # Plot the chart for Contribution Percentage
            fig, ax = plt.subplots(figsize=chart_size)
            ax.bar(
                total_package_sales_by_exec['CreatedBy'],
                total_package_sales_by_exec['TotalWithOtherPayments'] / total_revenue_with_other * 100,
                color='gold'
            )
            ax.set_title('Revenue Contribution (Inc Other Payments) per Exec', fontsize=font_size_title)
            ax.set_xlabel('Exec', fontsize=font_size_labels)
            ax.set_ylabel('Contribution (%)', fontsize=font_size_labels)
            ax.set_ylim(0)
            plt.xticks(rotation=45, ha='right', fontsize=font_size_labels)
            plt.yticks(fontsize=font_size_labels)
            st.pyplot(fig)

        else:
            st.warning("⚠️ No data available for the selected filters.")




    else:
        st.sidebar.warning("🚨 Please upload a file to proceed.")

if __name__ == "__main__":
    run_app()
