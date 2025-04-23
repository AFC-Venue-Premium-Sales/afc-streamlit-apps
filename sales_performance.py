import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import importlib
import sys
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.append("/Users/cmunthali/Documents/PYTHON/APPS")
from charts_ import (
    generate_event_level_men_cumulative_sales_chart,
    generate_event_level_women_cumulative_sales_chart,
    generate_event_level_concert_cumulative_sales_chart
)

# ─── Dynamically import tjt_hosp_api ────────────────────────────────────────────
try:
    tjt_hosp_api = importlib.import_module('tjt_hosp_api')
    filtered_df_without_seats = getattr(tjt_hosp_api, 'filtered_df_without_seats', None)
    if filtered_df_without_seats is None:
        raise ImportError("filtered_df_without_seats is not available in tjt_hosp_api.")
except ImportError as e:
    st.error(f"❌ Error importing tjt_hosp_api: {e}")
    filtered_df_without_seats = None


def load_budget_targets():
    """
    Reads the external Excel file for fixture-based budgets,
    parses KickOffEventStart as datetime (dayfirst),
    strips whitespace and renames 'Budget Target'→'Budget'.
    """
    df = pd.read_excel(
        "budget_target_2425.xlsx",
        parse_dates=["KickOffEventStart"],
        # dayfirst=True
    )
    df.columns = df.columns.str.strip()
    df["Fixture Name"] = df["Fixture Name"].str.strip()
    df["EventCompetition"] = df["EventCompetition"].str.strip()
    df.rename(columns={"Budget Target": "Budget"}, inplace=True)
    return df


def run_app():
    specified_users = [
        'dcoppin','Jedwards','jedwards','bgardiner','BenT','jmurphy','ayildirim',
        'MeganS','BethNW','HayleyA','LucyB','Conor','SavR','MillieS','dmontague'
    ]

    # ─── Load fixture budget targets from Excel ───────────────────────────────────
    budget_df = load_budget_targets()

    st.title('💷 MBM Sales 💷')

    # Instructions Section
    with st.expander("📖 How to Use This App - Sales Performance"):
        st.markdown("""
        ### ℹ️ About
        This app provides sales metrics from TJT's data. 
        You can filter results by date, user, fixture, payment status, and paid status for tailored insights
        
        **Note:** To access the latest sales updates, please click the 'Refresh Data' button & let it load.
        
        **Step-by-Step Guide:**
        1. **Filter Data**:
           - Use the sidebar to select a **date range** and **time range** for the data.
           - Filter data by **executives**, **events**, or **competitions**.
        2. **View Key Metrics**:
           - See total revenue, packages sold, and top executive performance at a glance including cumulative sales towards budget.
        3. **Refresh Data**:
           - Click the **Refresh Data** button in the sidebar to load the latest updates.
        4. **Export**:
           - Use the available export options to download filtered data or visualizations for further analysis.

        **Helpful Tips:**
        - If no filters are applied, the app displays all available data.
        - Contact [cmunthali@arsenal.co.uk](mailto:cmunthali@arsenal.co.uk) for any issues or inquiries.
        """)

    # Dynamically fetch hospitality data on app start
    loaded_api_df = filtered_df_without_seats
    if loaded_api_df is None or loaded_api_df.empty:
        st.warning("⚠️ No data available. Please refresh to load the latest data.")
        return

    # Display progress bar
    progress_bar = st.sidebar.progress(0)
    for pct in [10, 30, 50, 100]:
        progress_bar.progress(pct)

    if loaded_api_df is not None:
        st.sidebar.success("✅ Data retrieved successfully.")
        for pct in [10, 30, 50, 100]:
            st.sidebar.progress(pct)

        # Initialize filtered_data
        filtered_data = loaded_api_df.copy()
        
        filtered_data['Discount'] = filtered_data['Discount'].astype(str)
        filtered_data['IsPaid']   = filtered_data['IsPaid'].astype(str)
        filtered_data['DiscountValue'] = pd.to_numeric(filtered_data['DiscountValue'], errors='coerce')
        for col in ['TotalPrice', 'DiscountValue']:
            filtered_data[col] = pd.to_numeric(filtered_data[col], errors='coerce')

        # Convert 'CreatedOn'
        filtered_data['CreatedOn'] = pd.to_datetime(
            filtered_data['CreatedOn'], format='%d-%m-%Y %H:%M', errors='coerce'
        )
        loaded_api_df['CreatedOn'] = pd.to_datetime(
            loaded_api_df['CreatedOn'], format='%d-%m-%Y %H:%M', errors='coerce'
        )

        # ─── STEP 1: Coerce KickOffEventStart in sales DataFrame to datetime ────────
        filtered_data['KickOffEventStart'] = pd.to_datetime(
            filtered_data['KickOffEventStart'],
            format='%d-%m-%Y %H:%M',
            # dayfirst=True,
            errors='coerce'
        )

        # ─── STEP 2: Merge against budget file ───────────────────────────────────────
        filtered_data = pd.merge(
            filtered_data,
            budget_df,
            how="left",
            on=["Fixture Name", "EventCompetition", "KickOffEventStart"]
        )

        # Add 'Days to Fixture'
        today = pd.Timestamp.now()
        filtered_data['Days to Fixture'] = (
            filtered_data['KickOffEventStart'] - today
        ).dt.days.fillna(-1).astype(int)

        # Sidebar filters: Date & Time
        st.sidebar.header("Filter Data by Date and Time")
        date_range = st.sidebar.date_input("📅 Select Date Range", [])
        start_time = st.sidebar.time_input("⏰ Start Time", datetime.now().replace(hour=0, minute=0).time())
        end_time = st.sidebar.time_input("⏰ End Time", datetime.now().replace(hour=23, minute=59).time())

        if len(date_range) == 1:
            min_dt = datetime.combine(date_range[0], start_time)
            max_dt = datetime.combine(date_range[0], end_time)
        elif len(date_range) == 2:
            min_dt = datetime.combine(date_range[0], start_time)
            max_dt = datetime.combine(date_range[1], end_time)
        else:
            min_dt = max_dt = None

        # Sidebar filters: Users, Events, Categories, Locations, Paid
        valid_usernames = [u for u in specified_users if u in filtered_data['CreatedBy'].unique()]
        event_names = filtered_data['Fixture Name'].unique().tolist()
        competition_vals = filtered_data['EventCompetition'].unique().tolist()
        if 'EventCategory' in filtered_data.columns:
            competition_vals = sorted(set(competition_vals + filtered_data['EventCategory'].unique().tolist()))

        selected_categories = st.sidebar.multiselect("Select Event Category", options=competition_vals)
        selected_events = st.sidebar.multiselect("🎫 Select Events", options=event_names)
        selected_sale_location = st.sidebar.multiselect("📍 Select SaleLocation", options=filtered_data['SaleLocation'].unique())
        selected_users = st.sidebar.multiselect("👤 Select Execs", options=valid_usernames)
        paid_options = filtered_data['IsPaid'].unique().tolist()
        selected_paid = st.sidebar.selectbox("💰 Filter by IsPaid", options=paid_options)

        # ─── APPLY the above filters to filtered_data ────────────────────────────────
        if min_dt and max_dt:
            filtered_data = filtered_data[(filtered_data['CreatedOn'] >= min_dt) & (filtered_data['CreatedOn'] <= max_dt)]
        if selected_sale_location:
            filtered_data = filtered_data[filtered_data['SaleLocation'].isin(selected_sale_location)]
        if selected_users:
            filtered_data = filtered_data[filtered_data['CreatedBy'].isin(selected_users)]
        if selected_categories:
            filtered_data = filtered_data[filtered_data['EventCompetition'].isin(selected_categories)]
        if selected_events:
            filtered_data = filtered_data[filtered_data['Fixture Name'].isin(selected_events)]
        if selected_paid:
            filtered_data = filtered_data[filtered_data['IsPaid'] == selected_paid]

        # ─── NEW: Kickoff-time filter ───────────────────────────────────────────────
        kickoff_times = sorted(filtered_data["KickOffEventStart"].dropna().unique())
        display_kickoffs = [ts.strftime("%Y-%m-%d %H:%M") for ts in kickoff_times]
        selected_kickoffs = st.sidebar.multiselect("⏰ Select Kickoff time", options=display_kickoffs)
        if selected_kickoffs:
            keep_ts = [kickoff_times[display_kickoffs.index(label)] for label in selected_kickoffs]
            filtered_data = filtered_data[filtered_data["KickOffEventStart"].isin(keep_ts)]

        # ─── Continue with Discount filter and exclusions ────────────────────────────
        # Dynamically update discount options
        if selected_events:
            available_discounts = filtered_data[filtered_data['Fixture Name'].isin(selected_events)]['Discount'].unique()
        else:
            available_discounts = filtered_data['Discount'].unique()
        select_all_discounts = st.sidebar.checkbox("Select All Discounts", value=True)
        if select_all_discounts:
            selected_discount_options = available_discounts.tolist()
        else:
            selected_discount_options = st.sidebar.multiselect(
                "🔖 Filter by Discount Type",
                options=available_discounts,
                default=available_discounts.tolist()
            )
        filtered_data = filtered_data[filtered_data['Discount'].isin(selected_discount_options)]

        # Exclude Platinum & Woolwich Restaurant
        filtered_data_excluding_packages = filtered_data[
            ~filtered_data['Package Name'].isin(['Platinum', 'Woolwich Restaurant'])
        ]

        mask = ~filtered_data_excluding_packages['Discount'].str.contains(
            '|'.join([re.escape(k) for k in ["credit","voucher","gift voucher","discount","pldl"]]),
            case=False, na=False
        )
        filtered_data_without_excluded_keywords = filtered_data_excluding_packages[mask]

        # Static and dynamic totals
        static_start_date = datetime(2024, 6, 18)
        static_total = loaded_api_df[
            (loaded_api_df['CreatedOn'] >= static_start_date) &
            ~loaded_api_df['Package Name'].isin(['Platinum', 'Woolwich Restaurant'])
        ]['TotalPrice'].sum()
        dynamic_total = filtered_data_excluding_packages['TotalPrice'].sum()
        other_sales_total = dynamic_total + filtered_data_without_excluded_keywords['DiscountValue'].sum()

        # Metric cards
        raw_loc = filtered_data_excluding_packages.groupby('SaleLocation')['TotalPrice'].sum().reset_index()
        other_loc = filtered_data_without_excluded_keywords.groupby('SaleLocation')['DiscountValue'].sum().reset_index()
        raw_loc = pd.merge(raw_loc, other_loc, on='SaleLocation', how='left').rename(columns={'DiscountValue': 'OtherPayments'})
        raw_loc['TotalWithOtherPayments'] = raw_loc['TotalPrice'] + raw_loc['OtherPayments'].fillna(0)
        top_channel = raw_loc.sort_values('TotalWithOtherPayments', ascending=False).iloc[0]
        payment_channel_metric = f"{top_channel['SaleLocation']} (Sales: £{top_channel['TotalWithOtherPayments']:,.2f})"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Confirmed Sales", f"£{static_total:,.2f}")
        c2.metric("Filtered Confirmed Sales", f"£{dynamic_total:,.2f}")
        c3.metric("Total Sales (Including Pending payments)", f"£{other_sales_total:,.2f}")
        # c4.metric("Payment Channel", payment_channel_metric)

        # ⚽ Total Sales Summary table
        st.write("### ⚽ Total Sales Summary")
        st.write(f"RTS sales = confirmed, OtherSales = pending: **£{other_sales_total:,.2f}**")
        
        # restrict to the upcoming kickoff per fixture
        df = filtered_data_excluding_packages.copy()
        latest_kos = df.groupby("Fixture Name")["KickOffEventStart"].transform("max")
        df = df[df["KickOffEventStart"] == latest_kos]
        
        # build the summary off of df, not the full history
        total_sold_per_match = (
            filtered_data_excluding_packages.groupby("Fixture Name")
            .agg(
                DaysToFixture=("Days to Fixture", "min"),
                KickOffEventStart=("KickOffEventStart", "first"),
                RTS_Sales=("TotalPrice", "sum"),
                Budget=("Budget", "first")
            )
            .reset_index()
        )
        
        # pending sales
        other_sales = (
            filtered_data_without_excluded_keywords.groupby("Fixture Name")['DiscountValue'].sum()
        )
        total_sold_per_match = pd.merge(total_sold_per_match, other_sales, on="Fixture Name", how="left").rename(columns={'DiscountValue':'OtherSales'})
        
        # combine confirmed + pending
        total_sold_per_match['OtherSales'] = total_sold_per_match['OtherSales'].fillna(0) + total_sold_per_match['RTS_Sales']
        
        # covers sold
        covers = filtered_data_excluding_packages.groupby("Fixture Name")['Seats'].sum().reset_index().rename(columns={'Seats':'CoversSold'})
        total_sold_per_match = pd.merge(total_sold_per_match, covers, on="Fixture Name", how="left")
        total_sold_per_match['CoversSold'] = total_sold_per_match['CoversSold'].fillna(0).astype(int)
        
        # avg spend
        total_sold_per_match['Avg Spend'] = total_sold_per_match.apply(
            lambda r: r['OtherSales']/r['CoversSold'] if r['CoversSold']>0 else 0, axis=1
        ).apply(lambda x: f"£{x:,.2f}")
        
        # budget %
        total_sold_per_match['BudgetPercentage'] = total_sold_per_match.apply(
            lambda r: f"{(r['OtherSales']/r['Budget']*100):.0f}%" if pd.notnull(r['Budget']) and r['Budget']>0 else "N/A", axis=1
        )
        
        
# formatting        
        total_sold_per_match['RTS_Sales'] = total_sold_per_match['RTS_Sales'].apply(lambda x: f"£{x:,.0f}")
        total_sold_per_match['OtherSales'] = total_sold_per_match['OtherSales'].apply(lambda x: f"£{x:,.0f}")
        total_sold_per_match['Budget Target'] = total_sold_per_match['Budget'].apply(lambda x: f"£{x:,.0f}" if pd.notnull(x) else "None")
        total_sold_per_match['KickOffEventStart'] = pd.to_datetime(total_sold_per_match['KickOffEventStart'], errors='coerce')
        total_sold_per_match = total_sold_per_match.sort_values(by="KickOffEventStart", ascending=False)
        total_sold_per_match = total_sold_per_match[
            ['Fixture Name','KickOffEventStart','DaysToFixture','CoversSold','RTS_Sales','OtherSales','Avg Spend','Budget Target','BudgetPercentage']
        ]
        st.dataframe(total_sold_per_match)

        # Table with Pending Payments
        st.write("### Table with Pending Payments")
        total_discount_value = filtered_data_without_excluded_keywords.groupby(
            ['Order Id','Country Code','First Name','Surname','Fixture Name','GLCode','CreatedOn']
        )[['Discount','DiscountValue','TotalPrice']].sum().reset_index()
        total_discount_value['TotalPrice'] = total_discount_value['TotalPrice'].apply(lambda x: f"£{x:,.2f}")
        total_discount_value['DiscountValue'] = total_discount_value['DiscountValue'].apply(lambda x: f"£{x:,.2f}")
        st.dataframe(total_discount_value)

        # Package Sales
        st.write("### 🎟️ MBM Package Sales")
        other_pkg = filtered_data_without_excluded_keywords.groupby('Package Name')['DiscountValue'].sum().reset_index()
        pkg = filtered_data_excluding_packages.groupby('Package Name')['TotalPrice'].sum().reset_index()
        total_sold_per_package = pd.merge(pkg, other_pkg, on='Package Name', how='left').rename(columns={'DiscountValue':'OtherPayments'})
        total_sold_per_package['TotalWithOtherPayments'] = total_sold_per_package['TotalPrice'] + total_sold_per_package['OtherPayments'].fillna(0)
        for col in ['TotalPrice','OtherPayments','TotalWithOtherPayments']:
            total_sold_per_package[col] = total_sold_per_package[col].apply(lambda x: f"£{x:,.2f}")
        st.dataframe(total_sold_per_package)

        # Payment Channel table
        st.write("### 🏟️ Payment Channel")
        other_loc = filtered_data_without_excluded_keywords.groupby('SaleLocation')['DiscountValue'].sum().reset_index()
        loc = filtered_data_excluding_packages.groupby('SaleLocation')['TotalPrice'].sum().reset_index()
        total_sold_per_location = pd.merge(loc, other_loc, on='SaleLocation', how='left').rename(columns={'DiscountValue':'OtherPayments'})
        total_sold_per_location['TotalWithOtherPayments'] = total_sold_per_location['TotalPrice'] + total_sold_per_location['OtherPayments'].fillna(0)
        for col in ['TotalPrice','OtherPayments','TotalWithOtherPayments']:
            total_sold_per_location[col] = total_sold_per_location[col].apply(lambda x: f"£{x:,.2f}")
        st.dataframe(total_sold_per_location)

        # Woolwich Restaurant Sales
        st.write("### 🍴 Woolwich Restaurant Sales")
        wool = filtered_data[
            (filtered_data['Package Name'].isin(['Platinum','Woolwich Restaurant'])) &
            (filtered_data['IsPaid'].str.upper()=='TRUE')
        ]
        total_sales_revenue = wool['TotalPrice'].sum()
        total_covers_sold  = wool['Seats'].sum()
        st.write(f"Total Sales Revenue: **£{total_sales_revenue:,.0f}**")
        st.write(f"Total Covers Sold: **{int(total_covers_sold)}**")
        wool_summary = wool.groupby(['Fixture Name','KickOffEventStart']).agg({'Seats':'sum','TotalPrice':'sum'}).reset_index()
        wool_summary = wool_summary.rename(columns={
            'Fixture Name':'Event','KickOffEventStart':'Event Date','Seats':'Covers Sold','TotalPrice':'Revenue'
        })
        wool_summary['Revenue'] = wool_summary['Revenue'].apply(lambda x: f"£{x:,.0f}")
        st.dataframe(wool_summary)

        # Cumulative sales charts
        st.header("Cumulative Sales as Percentage of Budget")
        st.subheader("Men's Competitions")
        try:
            generate_event_level_men_cumulative_sales_chart(filtered_data)
        except Exception as e:
            st.error(f"Failed to generate the men's cumulative chart: {e}")

        st.subheader("Women's Competitions")
        try:
            generate_event_level_women_cumulative_sales_chart(filtered_data)
        except Exception as e:
            st.error(f"Failed to generate the women's cumulative chart: {e}")

        st.subheader("Concerts (to be fixed soon)")
        try:
            generate_event_level_concert_cumulative_sales_chart(filtered_data)
        except Exception as e:
            st.error(f"Failed to generate the concert cumulative chart: {e}")

        # 📥 Downloads Section
        if not wool_summary.empty:
            output = BytesIO()
            output.write(wool.to_csv(index=False).encode('utf-8'))
            output.seek(0)
            st.download_button("💾 Download Woolwich Restaurant Data", data=output, file_name='woolwich_restaurant_sales_data.csv', mime='text/csv')
        if not filtered_data.empty:
            fd = BytesIO()
            fd.write(filtered_data.to_csv(index=False).encode('utf-8'))
            fd.seek(0)
            st.download_button("💾 Download Filtered Data", data=fd, file_name='filtered_data.csv', mime='text/csv')
        if not loaded_api_df.empty:
            sd = BytesIO()
            sd.write(loaded_api_df.to_csv(index=False).encode('utf-8'))
            sd.seek(0)
            st.download_button("💾 Download Sales Report", data=sd, file_name='sales_report.csv', mime='text/csv')

    else:
        st.sidebar.warning("🚨 Please upload a file to proceed.")


if __name__ == "__main__":
    run_app()
