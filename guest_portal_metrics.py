import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from io import BytesIO

def run():
    st.title("📦 Guest Portal Analysis")
    
    # --- Collapsible About Section ---
    with st.expander("ℹ️ About this Dashboard", expanded=False):
        st.markdown("""
        **Welcome to the Guest Portal Insights Dashboard**  
        This tool combines data from the **RTS Pre-Order Report** with **TJT's Catering Pre-orders API**  
        to give you a consolidated view of activities on the hospitality website's Guest Portal.

        ### 🧠 What it does:
        - Helps the **Premium Service Team** with tracking and processing catering pre-orders.
        - Validates pre-orders across multiple sources.
        - Will soon support tracking of **guest draw-down credit** and **invitation usage**.

        ### 📂 Getting Started:
        1. **Download the RTS Pre-Order Report** from:  
           [RTS Portal – Pre-Orders](https://www.tjhub3.com/Rts_Arsenal_Hospitality/Suites/Reports/PreOrders/Index)
        2. Save the file locally, then upload it via the **sidebar**. Please do not edit or change the file before uploading.
        3. The dashboard will automatically fetch matching data from the TJT API and process everything behind the scenes.

        ### 🎛️ How to Use the Dashboard:
        - Use the filters on the **left-hand side** to select date range, order types, menu items, box locations, and order status.
        - Key metrics (e.g. Total Spend, Top Menu Item, Highest Spending Event/Box) will update live.
        - Scroll down to view the full merged dataset or **download it** for deeper analysis.
        ---
        """)

    # --- Sidebar ---
    st.sidebar.header("Upload Manual File")
    manual_file = st.sidebar.file_uploader("Choose the manual .xls file", type=["xls"])

    st.sidebar.header("Date Filter")
    start_date = st.sidebar.date_input("Start Date", datetime(2024, 6, 18))
    end_date = st.sidebar.date_input("End Date", datetime.now())

    price_type = st.sidebar.radio("Which price column to use:", ["Total", "ApiPrice"])
    
    # --- API Config ---
    token_url = 'https://www.tjhub3.com/export_arsenal/token'
    events_url = "https://www.tjhub3.com/export_arsenal/Events/List"
    preorders_url_template = "https://www.tjhub3.com/export_arsenal/CateringPreorders/List?EventId={}"

    USERNAME = 'hospitality'
    PASSWORD = 'OkMessageSectionType000!'

    @st.cache_data
    def get_access_token():
        data = {'Username': USERNAME, 'Password': PASSWORD, 'grant_type': 'password'}
        response = requests.post(token_url, data=data)
        return response.json().get('access_token') if response.status_code == 200 else None

    @st.cache_data
    def fetch_event_ids(headers):
        r = requests.get(events_url, headers=headers)
        return [evt["Id"] for evt in r.json().get("Data", {}).get("Events", [])] if r.status_code == 200 else []

    @st.cache_data
    def fetch_api_preorders(event_ids, headers):
        all_data = []
        for eid in event_ids:
            r = requests.get(preorders_url_template.format(eid), headers=headers)
            if r.status_code == 200:
                all_data.extend(r.json().get("Data", {}).get("CateringPreorders", []))
        return pd.DataFrame(all_data)

    @st.cache_data
    def preprocess_manual(file):
        df = pd.read_excel(file, header=4)
        df = df.loc[:, ~df.columns.str.contains("Unnamed")]
        df.columns = df.columns.str.strip().str.replace(" ", "_")
        df['Location'] = df['Location'].ffill().astype(str).str.strip()
        df = df.dropna(how='all')
        df = df.dropna(subset=['Event', 'Order_type'])
        # Preserve Event_Date from manual file (assumes column exists)
        df['Event_Date'] = pd.to_datetime(df['Event_Date'], errors='coerce')
        df['Event'] = df['Event'].astype(str).str.strip().str.split(', ')
        df = df.explode('Event')
        df['Guest_email'] = df['Guest_name'].str.extract(r'\(([^)]+)\)')
        df['Guest_name'] = df['Guest_name'].str.extract(r'^(.*?)\s*\(')
        df['Guest_email'] = df['Guest_email'].astype(str).str.lower()
        df['Total'] = pd.to_numeric(df['Total'].astype(str)
                                    .replace('[\u00a3,]', '', regex=True)
                                    .replace('', '0'),
                                    errors='coerce').fillna(0)
        df.drop_duplicates(inplace=True)
        return df

    def process_api_menu(api_df):
        """
        Extract item-level data from the Catering Preorders API.
        Now extracts:
         - OrderedAmount, PricePerUnit, Vat
         and calculates ApiPrice as OrderedAmount * PricePerUnit.
         Also uses "KickOffEventStart" as the event date for mapping.
        """
        menu = []
        event_map = {}
        for _, row in api_df.iterrows():
            guest = row.get('Guest', '')
            guest_name = guest.split("(")[0].strip() if "(" in guest else guest
            guest_email = guest.split("(")[-1].replace(")", "").strip().lower() if "(" in guest else None
            loc = str(row.get('Location', '')).strip()
            evt = str(row.get('Event', '')).strip()
            eid = row.get('EventId')
            # Use KickOffEventStart as event date from API
            event_date_api = row.get("KickOffEventStart")
            if eid and loc and evt:
                event_map[(loc, evt, event_date_api)] = str(eid)
            for menu_type, key in [
                ('Food', 'FoodMenu'),
                ('Kids Food', 'KidsFoodMenu'),
                ('Drink', 'DrinkMenu'),
                ('Kids Drink', 'KidsDrinkMenu')
            ]:
                val = row.get(key)
                if isinstance(val, dict) and val.get('Name'):
                    price_per_unit = val.get('Price', 0)
                    ordered_amount = val.get('Quantity', 1)
                    vat = val.get('Vat', 0)
                    api_price = price_per_unit * ordered_amount
                    menu.append({
                        'EventId': str(eid),
                        'Location': loc,
                        'Event': evt,
                        # We'll merge on the manual file's Event_Date later.
                        'Ordered_Event_Date': event_date_api,
                        'Guest_name': guest_name,
                        'Guest_email': guest_email,
                        'Order_type': menu_type,
                        'Menu_Item': val.get('Name'),
                        'OrderedAmount': ordered_amount,
                        'PricePerUnit': price_per_unit,
                        'Vat': vat,
                        'ApiPrice': api_price,
                        'Status': row.get('Status')
                    })
            for pit in row.get('PreOrderItems', []):
                price_per_unit = pit.get('Price', 0)
                ordered_amount = pit.get('OrderedAmount', 1)
                vat = pit.get('Vat', 0)
                api_price = price_per_unit * ordered_amount
                menu.append({
                    'EventId': str(eid),
                    'Location': loc,
                    'Event': evt,
                    'Ordered_Event_Date': event_date_api,
                    'Guest_name': guest_name,
                    'Guest_email': guest_email,
                    'Order_type': 'Enhancement',
                    'Menu_Item': pit.get('ProductName'),
                    'OrderedAmount': ordered_amount,
                    'PricePerUnit': price_per_unit,
                    'Vat': vat,
                    'ApiPrice': api_price,
                    'Status': row.get('Status')
                })
        df_menu = pd.DataFrame(menu).drop_duplicates(
            subset=['EventId', 'Location', 'Event', 'Guest_name', 'Guest_email', 'Order_type', 'Menu_Item']
        )
        return df_menu, event_map

    def map_event_id(row, event_map):
        # Use the manual file's Event_Date along with Location and Event for mapping.
        manual_date = row.get("Event_Date")
        return event_map.get((str(row['Location']).strip(), str(row['Event']).strip(), manual_date), None)

    def lumpsum_deduping(df, merge_keys):
        if 'Ordered_on' in df.columns:
            merge_keys.append('Ordered_on')
        df = df.sort_values(merge_keys)
        def clear_lumpsums(grp):
            if len(grp) > 1:
                grp.iloc[1:, grp.columns.get_loc('Total')] = 0
            return grp
        return df.groupby(merge_keys, group_keys=False).apply(clear_lumpsums).drop_duplicates()

    # --- App Execution ---
    if manual_file:
        uploaded_msg = st.success("📂 Manual file uploaded!")
        progress_bar = st.progress(0)
        time.sleep(3)
        uploaded_msg.empty()

        with st.spinner("🔄 Processing data..."):
            # Step 1: Preprocess Manual
            df_manual = preprocess_manual(manual_file)
            progress_bar.progress(20)
            step_1 = st.success("✅ Step 1: Manual file processed")
            time.sleep(3)
            step_1.empty()

            # Step 2: Get API Token
            token = get_access_token()
            if not token:
                st.error("❌ Failed to retrieve API token.")
                st.stop()
            headers = {'Authorization': f'Bearer {token}'}

            # Step 3: Fetch Event IDs
            event_ids = fetch_event_ids(headers)
            progress_bar.progress(40)
            step_2 = st.success("✅ Step 2: Event IDs retrieved")
            time.sleep(3)
            step_2.empty()

            # Step 4: Fetch API Preorders
            df_api = fetch_api_preorders(event_ids, headers)
            progress_bar.progress(60)
            step_3 = st.success("✅ Step 3: Preorders fetched")
            time.sleep(3)
            step_3.empty()

            # Step 5: Process API Menus
            df_menu, event_map = process_api_menu(df_api)
            progress_bar.progress(80)
            step_4 = st.success("✅ Step 4: Menu processed")
            time.sleep(3)
            step_4.empty()

            # Step 6: Map Event IDs and Merge
            df_manual['EventId'] = df_manual.apply(lambda row: map_event_id(row, event_map), axis=1).astype(str).fillna('')
            merge_keys = ['EventId', 'Location', 'Event', 'Event_Date', 'Guest_name', 'Guest_email', 'Order_type']
            df_merged = df_manual.merge(
                df_menu,
                how='left',
                on=merge_keys,
                suffixes=('_manual', '_api')
            )
            df_merged = lumpsum_deduping(df_merged, merge_keys)

            if df_merged.empty:
                st.warning("⚠ Merged data is empty.")
                st.stop()

            progress_bar.progress(100)
            final_message = st.success("✅ Data ready for analysis")
            time.sleep(3)
            final_message.empty()

            if 'Status_manual' in df_merged.columns:
                df_merged.rename(columns={'Status_manual': 'Status'}, inplace=True)
            if 'Status_api' in df_merged.columns:
                df_merged.drop(columns=['Status_api'], inplace=True)

            # --- Filtering ---
            df_merged['Ordered_on'] = pd.to_datetime(df_merged['Ordered_on'], errors='coerce')
            df_merged = df_merged[
                (df_merged['Ordered_on'] >= pd.to_datetime(start_date)) &
                (df_merged['Ordered_on'] <= pd.to_datetime(end_date))
            ]

            if 'Location' in df_merged.columns:
                locs = sorted(df_merged['Location'].dropna().unique())
                selected_locs = st.sidebar.multiselect("Select Location(s):", locs, default=locs)
                df_merged = df_merged[df_merged['Location'].isin(selected_locs)]

            if 'Order_type' in df_merged.columns:
                order_types = sorted(df_merged['Order_type'].dropna().unique())
                selected_types = st.sidebar.multiselect("Select Order Type(s):", order_types, default=order_types)
                df_merged = df_merged[df_merged['Order_type'].isin(selected_types)]

            if 'Menu_Item' in df_merged.columns:
                items = sorted(df_merged['Menu_Item'].dropna().unique())
                selected_items = st.sidebar.multiselect("Select Menu Item(s):", items, default=items)
                df_merged = df_merged[df_merged['Menu_Item'].isin(selected_items)]

            if 'Status' in df_merged.columns:
                statuses = sorted(df_merged['Status'].dropna().unique())
                selected_statuses = st.sidebar.multiselect("Select Status(es):", statuses, default=statuses)
                df_merged = df_merged[df_merged['Status'].isin(selected_statuses)]

            if df_merged.empty:
                st.warning("⚠ No data after filtering.")
                return

        # --- Metrics ---
        st.subheader("📊 Key Metrics")
        total_orders = df_merged.shape[0]
        total_spend = df_merged[price_type].fillna(0).sum()
        food_total = df_merged[df_merged['Order_type'] == 'Food'][price_type].sum()
        enhancement_total = df_merged[df_merged['Order_type'] == 'Enhancement'][price_type].sum()
        kids_total = df_merged[df_merged['Order_type'] == 'Kids Food'][price_type].sum()
        total_boxes = df_merged['Location'].nunique()

        top_item = df_merged.groupby('Menu_Item')[price_type].sum().sort_values(ascending=False)
        top_item_name, top_item_spend = (top_item.index[0], top_item.iloc[0]) if not top_item.empty else ("N/A", 0)

        top_box = df_merged.groupby('Location')[price_type].sum().sort_values(ascending=False)
        top_box_name, top_box_spend = (top_box.index[0], top_box.iloc[0]) if not top_box.empty else ("N/A", 0)

        top_event = df_merged.groupby('Event')[price_type].sum().sort_values(ascending=False)
        top_event_name = top_event.index[0] if not top_event.empty else "N/A"

        avg_spend = df_merged.groupby(df_merged['Ordered_on'].dt.to_period('M'))[price_type].mean().mean() if not df_merged['Ordered_on'].isna().all() else 0

        # --- Display Metrics ---
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        r1c1.metric("Total PreOrders", total_orders)
        r1c2.metric("Total Spend (£)", f"£{total_spend:,.2f}")
        r1c3.metric("Avg. Monthly Spend", f"£{avg_spend:,.2f}")
        r1c4.metric("Total Boxes Found", total_boxes)

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        r2c1.metric("Food Menu Total", f"£{food_total:,.2f}")
        r2c2.metric("Enhancement Menu Total", f"£{enhancement_total:,.2f}")
        r2c3.metric("Kids Menu Total", f"£{kids_total:,.2f}")
        r2c4.metric("Highest Spending Box", top_box_name)

        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        r3c1.metric("Top Menu Item", top_item_name)
        r3c2.metric("Top Item Spend", f"£{top_item_spend:,.2f}")
        r3c3.metric("Highest Box's Total", f"£{top_box_spend:,.2f}")
        r3c4.metric("Highest Spending Event", top_event_name)

        # --- Table & Download ---
        with st.expander("📋 Merged Data Table (click to expand)"):
            st.dataframe(df_merged, use_container_width=True)
            
            # Prepare XLSX for download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_merged.to_excel(writer, index=False, sheet_name='Merged Data')
            output.seek(0)
            
            st.download_button(
                label="⬇️ Download Processed Data (XLSX)",
                data=output,
                file_name="processed_merged_orders.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    else:
        st.info("Please upload the RTS Pre-order file to begin analysis.")


if __name__ == "__main__":
    run()
