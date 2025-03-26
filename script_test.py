import streamlit as st
import pandas as pd
import requests
import time
import math
from datetime import datetime
from io import BytesIO

############################################################################
# Standardize Location Strings
############################################################################
def standardize_location(df, loc_col="Location"):
    """
    Converts the Location column to lowercase, strips leading/trailing spaces,
    and optionally replaces 'exec ' with 'executive '.
    """
    df[loc_col] = (
        df[loc_col].astype(str)
        .str.strip()
        .str.lower()
    )
    # Example: "exec " -> "executive "
    df[loc_col] = df[loc_col].str.replace(r"^exec\s+", "executive ", regex=True)
    return df

############################################################################
# Payment Status logic: Compare box-level total to consolidated amounts
############################################################################
def assign_payment_status(row):
    """
    Compares the box-level total (BoxTotal) with the consolidated Drawdown
    and Credit Card amounts. Rounds both sides to two decimals, then does
    an exact equality check (==). If they match exactly, returns "Drawdown"
    or "Credit Card". Otherwise, returns "".
    """
    total_val = row.get("BoxTotal", 0)
    drawdown_val = row.get("Drawdown", 0)
    credit_val = row.get("Credit Card", 0)

    total_2dec = round(total_val, 2)
    drawdown_2dec = round(drawdown_val, 2)
    credit_2dec = round(credit_val, 2)

    if drawdown_2dec > 0 and total_2dec == drawdown_2dec:
        return "Drawdown"
    elif credit_2dec > 0 and total_2dec == credit_2dec:
        return "Credit Card"
    else:
        return ""

############################################################################
# Main Streamlit App
############################################################################
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
        2. Save the file locally, then upload it via the **sidebar**. Please do not edit or change this file before uploading.
        3. The dashboard will automatically fetch matching data from the TJT API and process everything behind the scenes.

        ### 🎛️ How to Use the Dashboard:
        - Use the filters on the **left-hand side** to select date range, order types, menu items, box locations, and order status.
        - All key metrics will update live — including:
          - Total Spend
          - Top Menu Item
          - Highest Spending Event and Box
          - Menu Category Totals
        - Scroll down to view the full merged dataset or **download it** for deeper analysis.
        ---
        """)

    # --- Sidebar ---
    st.sidebar.header("Upload RTS Pre-Orders File")
    manual_file = st.sidebar.file_uploader("Load RTS Pre-Orders .xls file", type=["xls"])
    st.sidebar.header("Upload Consolidated Payment Report")
    consolidated_file = st.sidebar.file_uploader("Load Consolidated Payment .xls file", type=["xls"])

    selected_event = None
    if consolidated_file:
        try:
            fixture_df = pd.read_excel("/Users/cmunthali/Documents/PYTHON/APPS/fixture_list.xlsx")
            fixture_list = fixture_df["Fixture Name"].tolist()
            selected_event = st.sidebar.selectbox("Select Event for Payment Report", fixture_list)
        except Exception as e:
            st.error("Error loading fixture list: " + str(e))

    st.sidebar.header("Data Filters")
    start_date = st.sidebar.date_input("Start Date", datetime(2024, 6, 18))
    end_date = st.sidebar.date_input("End Date", datetime.now())
    price_type = st.sidebar.radio("Which price column to use:", ["Total", "ApiPrice"])

    # --- API Config ---
    token_url = "https://www.tjhub3.com/export_arsenal/token"
    events_url = "https://www.tjhub3.com/export_arsenal/Events/List"
    preorders_url_template = "https://www.tjhub3.com/export_arsenal/CateringPreorders/List?EventId={}"
    USERNAME = "hospitality"
    PASSWORD = "OkMessageSectionType000!"

    @st.cache_data
    def get_access_token():
        data = {"Username": USERNAME, "Password": PASSWORD, "grant_type": "password"}
        resp = requests.post(token_url, data=data)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        return None

    @st.cache_data
    def fetch_event_details(headers):
        r = requests.get(events_url, headers=headers)
        if r.status_code != 200:
            return []
        events = r.json().get("Data", {}).get("Events", [])
        return [
            {
                "EventId": e["Id"],
                "Event": e["Name"].strip(),
                "KickOffEventStart": e.get("KickOffEventStart")
            }
            for e in events
        ]

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
        df["Location"] = df["Location"].ffill().astype(str).str.strip()
        df = df.dropna(how="all")
        df = df.dropna(subset=["Event", "Order_type"])
        df["Event"] = df["Event"].astype(str).str.strip().str.split(", ")
        df = df.explode("Event")
        df["Guest_email"] = df["Guest_name"].str.extract(r"\(([^)]+)\)")
        df["Guest_name"] = df["Guest_name"].str.extract(r"^(.*?)\s*\(")
        df["Guest_email"] = df["Guest_email"].astype(str).str.lower()
        df["Total"] = (df["Total"].astype(str)
                       .replace("[\u00a3,]", "", regex=True)
                       .replace("", "0"))
        df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
        if "Event_Date" in df.columns:
            df["Event_Date"] = pd.to_datetime(df["Event_Date"], dayfirst=True, errors="coerce")
        df.drop_duplicates(inplace=True)
        return df

    def process_api_menu(df_api):
        menu = []
        event_map = {}
        for _, row in df_api.iterrows():
            guest = row.get("Guest", "") or ""
            guest_name = guest.split("(")[0].strip() if "(" in guest else guest
            guest_email = None
            if "(" in guest and ")" in guest:
                guest_email = guest.split("(")[-1].replace(")", "").strip().lower()
            loc = str(row.get("Location", "")).strip()
            evt = str(row.get("Event", "")).strip()
            eid = row.get("EventId")
            raw_date = row.get("KickOffEventStart")
            event_date_api = pd.to_datetime(raw_date, errors="coerce").date() if raw_date else None
            status = row.get("Status")
            if eid and loc and evt and event_date_api:
                event_map[(loc, evt, event_date_api)] = str(eid)
            for menu_type, key in [
                ("Food", "FoodMenu"),
                ("Kids Food", "KidsFoodMenu"),
                ("Drink", "DrinkMenu"),
                ("Kids Drink", "KidsDrinkMenu")
            ]:
                val = row.get(key)
                if isinstance(val, dict) and val.get("Name"):
                    qty = val.get("Quantity", 1)
                    price = val.get("Price", 0)
                    final_price = price * qty
                    menu.append({
                        "EventId": str(eid),
                        "Location": loc,
                        "Event": evt,
                        "KickOffEventStart": event_date_api,
                        "Guest_name": guest_name,
                        "Guest_email": guest_email,
                        "Order_type": menu_type,
                        "Menu_Item": val.get("Name"),
                        "OrderedAmount": qty,
                        "PricePerUnit": price,
                        "ApiPrice": final_price,
                        "Status": status
                    })
            for pit in row.get("PreOrderItems", []):
                qty = pit.get("OrderedAmount", 1)
                price = pit.get("Price", 0)
                final_price = price * qty
                menu.append({
                    "EventId": str(eid),
                    "Location": loc,
                    "Event": evt,
                    "KickOffEventStart": event_date_api,
                    "Guest_name": guest_name,
                    "Guest_email": guest_email,
                    "Order_type": "Enhancement",
                    "Menu_Item": pit.get("ProductName"),
                    "OrderedAmount": qty,
                    "PricePerUnit": price,
                    "ApiPrice": final_price,
                    "Status": status
                })
        df_menu = pd.DataFrame(menu)
        if not df_menu.empty:
            df_menu.drop_duplicates(
                subset=["EventId", "Location", "Event", "Guest_name", "Guest_email", "Order_type", "Menu_Item"],
                inplace=True
            )
        return df_menu, event_map

    def map_event_id(row, event_map):
        loc = str(row["Location"]).strip()
        evt = str(row["Event"]).strip()
        date_val = None
        if "Event_Date" in row and pd.notna(row["Event_Date"]):
            date_val = row["Event_Date"].date()
        return event_map.get((loc, evt, date_val), None)

    def lumpsum_deduping(df, merge_keys):
        if "Ordered_on" in df.columns:
            merge_keys.append("Ordered_on")
        df = df.sort_values(merge_keys)
        def clear_lumpsums(grp):
            if len(grp) > 1:
                grp.iloc[1:, grp.columns.get_loc("Total")] = 0
            return grp
        return df.groupby(merge_keys, group_keys=False).apply(clear_lumpsums).drop_duplicates()

    @st.cache_data
    def preprocess_consolidated_payment_report(file):
        # 1) Read the sheet so that row 6 is treated as the header row
        df = pd.read_excel(file, skiprows=5, header=0)
        
        # 2) Inspect what columns we have (uncomment the st.write lines if using Streamlit)
        # st.write("Columns in the raw DataFrame:", df.columns)
        # st.write(df.head(20))
        
        # 3) If the file has columns named exactly "Location", "Drawdown", "Credit card",
        #    you can rename them or keep them as-is. Let's unify "Credit card" -> "Credit Card".
        df.rename(columns={"Credit card": "Credit Card"}, inplace=True)
        
        # 4) Keep only the columns you need
        #    Make sure these names match EXACTLY what appears in df.columns after step 2
        keep_cols = ["Location", "Drawdown", "Credit Card"]
        df = df[keep_cols].copy()
        
        # 5) Drop fully empty rows and any "total" rows
        df.dropna(how='all', inplace=True)
        df = df[~df["Location"].astype(str).str.lower().str.contains("total", na=False)]
        
        # 6) Convert currency columns
        for col in ["Drawdown", "Credit Card"]:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("[£,]", "", regex=True)  # remove £ and commas
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        return df


    if manual_file:
        upload_success_placeholder = st.empty()
        upload_progress_placeholder = st.empty()
        upload_success_placeholder.success("📂 Manual file uploaded!")
        upload_progress_bar = upload_progress_placeholder.progress(0)
        for i in range(1, 101, 10):
            upload_progress_bar.progress(i)
            time.sleep(0.05)
        time.sleep(1)
        upload_success_placeholder.empty()
        upload_progress_placeholder.empty()

        with st.spinner("🔄 Processing data..."):
            process_progress_placeholder = st.empty()
            process_success_placeholder = st.empty()
            process_progress_bar = process_progress_placeholder.progress(0)

            # Preprocess manual file
            df_manual = preprocess_manual(manual_file)
            process_progress_bar.progress(20)
            time.sleep(0.2)

            # Get API Token
            token = get_access_token()
            if not token:
                st.error("❌ Failed to retrieve API token.")
                st.stop()
            headers = {"Authorization": f"Bearer {token}"}
            process_progress_bar.progress(30)
            time.sleep(0.2)

            # Fetch event details
            events_list = fetch_event_details(headers)
            df_events = pd.DataFrame(events_list)
            process_progress_bar.progress(40)
            time.sleep(0.2)
            if not df_events.empty:
                df_events["KickOffEventStart"] = pd.to_datetime(df_events["KickOffEventStart"], errors="coerce").dt.date

            # Fetch API Preorders
            event_ids = df_events["EventId"].unique().tolist() if not df_events.empty else []
            df_api_pre = fetch_api_preorders(event_ids, headers)
            process_progress_bar.progress(50)
            time.sleep(0.2)

            # Merge events into preorders
            df_api = df_api_pre.merge(df_events, how="left", on="EventId", suffixes=("", "_evt"))
            if "Event_evt" in df_api.columns:
                df_api["Event"] = df_api["Event_evt"].fillna(df_api["Event"])
                df_api.drop(columns=["Event_evt"], inplace=True)
            process_progress_bar.progress(60)
            time.sleep(0.2)

            # Build df_menu from combined API data
            df_menu, event_map = process_api_menu(df_api)
            if "EventId" in df_menu.columns:
                df_menu["EventId"] = pd.to_numeric(df_menu["EventId"], errors="coerce").fillna(0).astype(int)
            process_progress_bar.progress(70)
            time.sleep(0.2)

            # Map EventId to manual file
            if "Event_Date" not in df_manual.columns:
                st.error("Manual file is missing 'Event_Date' column.")
                st.stop()
            df_manual["Event_Date"] = pd.to_datetime(df_manual["Event_Date"], dayfirst=True, errors="coerce")
            df_manual["EventId"] = df_manual.apply(lambda r: map_event_id(r, event_map), axis=1)
            df_manual["EventId"] = pd.to_numeric(df_manual["EventId"], errors="coerce").fillna(0).astype(int)
            process_progress_bar.progress(80)
            time.sleep(0.2)

            # Merge manual and API menu data
            merge_keys = ["EventId", "Location", "Event", "Guest_name", "Guest_email", "Order_type"]
            df_merged = df_manual.merge(df_menu, how="left", on=merge_keys, suffixes=("_manual", "_api"))
            df_merged = lumpsum_deduping(df_merged, merge_keys)
            if df_merged.empty:
                st.warning("⚠ Merged data is empty.")
                st.stop()

            # Tidy up status columns
            if "Status_manual" in df_merged.columns:
                df_merged.rename(columns={"Status_manual": "Status"}, inplace=True)
            if "Status_api" in df_merged.columns:
                df_merged.drop(columns=["Status_api"], inplace=True)
            process_progress_bar.progress(90)
            time.sleep(0.2)

            # Filter by date range and other sidebar filters
            df_merged["Ordered_on"] = pd.to_datetime(df_merged["Ordered_on"], errors="coerce")
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df_merged = df_merged[(df_merged["Ordered_on"] >= start_dt) & (df_merged["Ordered_on"] <= end_dt)]
            if "Location" in df_merged.columns:
                locs = sorted(df_merged["Location"].dropna().unique())
                selected_locs = st.sidebar.multiselect("Select Location(s):", locs, default=locs)
                df_merged = df_merged[df_merged["Location"].isin(selected_locs)]
            if "Order_type" in df_merged.columns:
                order_types = sorted(df_merged["Order_type"].dropna().unique())
                selected_types = st.sidebar.multiselect("Select Order Type(s):", order_types, default=order_types)
                df_merged = df_merged[df_merged["Order_type"].isin(selected_types)]
            if "Menu_Item" in df_merged.columns:
                items = sorted(df_merged["Menu_Item"].dropna().unique())
                selected_items = st.sidebar.multiselect("Select Menu Item(s):", items, default=items)
                df_merged = df_merged[df_merged["Menu_Item"].isin(selected_items)]
            if "Status" in df_merged.columns:
                statuses = sorted(df_merged["Status"].dropna().unique())
                selected_statuses = st.sidebar.multiselect("Select Status(es):", statuses, default=statuses)
                df_merged = df_merged[df_merged["Status"].isin(selected_statuses)]
            if df_merged.empty:
                st.warning("⚠ No data after filtering.")
                return

            process_progress_bar.progress(100)
            process_success_placeholder.success("✅ Data ready for analysis")
            time.sleep(1)
            process_progress_placeholder.empty()
            process_success_placeholder.empty()

        # --- Metrics Section ---
        st.subheader("📊 Key Metrics")
        total_orders = df_merged.shape[0]
        total_spend = df_merged[price_type].fillna(0).sum()
        food_total = df_merged[df_merged["Order_type"] == "Food"][price_type].sum()
        enhancement_total = df_merged[df_merged["Order_type"] == "Enhancement"][price_type].sum()
        kids_total = df_merged[df_merged["Order_type"] == "Kids Food"][price_type].sum()
        total_boxes = df_merged["Location"].nunique()

        top_item = df_merged.groupby("Menu_Item")[price_type].sum().sort_values(ascending=False)
        if not top_item.empty:
            top_item_name = top_item.index[0]
            top_item_spend = top_item.iloc[0]
        else:
            top_item_name, top_item_spend = "N/A", 0

        top_box = df_merged.groupby("Location")[price_type].sum().sort_values(ascending=False)
        if not top_box.empty:
            top_box_name = top_box.index[0]
            top_box_spend = top_box.iloc[0]
        else:
            top_box_name, top_box_spend = "N/A", 0

        top_event = df_merged.groupby("Event")[price_type].sum().sort_values(ascending=False)
        top_event_name = top_event.index[0] if not top_event.empty else "N/A"

        if not df_merged["Ordered_on"].isna().all():
            avg_spend = df_merged.groupby(df_merged["Ordered_on"].dt.to_period("M"))[price_type].mean().mean()
        else:
            avg_spend = 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total PreOrders", total_orders)
        c2.metric("Total Spend (£)", f"£{total_spend:,.2f}")
        c3.metric("Avg. Monthly Spend", f"£{avg_spend:,.2f}")
        c4.metric("Total Boxes Found", total_boxes)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Food Menu Total", f"£{food_total:,.2f}")
        c2.metric("Enhancement Menu Total", f"£{enhancement_total:,.2f}")
        c3.metric("Kids Menu Total", f"£{kids_total:,.2f}")
        c4.metric("Highest Spending Box", top_box_name)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Top Menu Item", top_item_name)
        c2.metric("Top Item Spend", f"£{top_item_spend:,.2f}")
        c3.metric("Highest Box's Total", f"£{top_box_spend:,.2f}")
        c4.metric("Highest Spending Event", top_event_name)

        rts_total_final = df_merged["Total"].sum()
        api_total_final = df_merged["ApiPrice"].fillna(0).sum()

        toast_placeholder1 = st.empty()
        toast_placeholder2 = st.empty()
        toast_placeholder1.info(f"RTS Total: £{rts_total_final:,.2f}")
        toast_placeholder2.info(f"API Total: £{api_total_final:,.2f}")
        time.sleep(2)
        toast_placeholder1.empty()
        toast_placeholder2.empty()

        with st.expander("📋 Merged Data Table (click to expand)"):
            st.dataframe(df_merged)
            output_merged = BytesIO()
            with pd.ExcelWriter(output_merged, engine="xlsxwriter") as writer:
                df_merged.to_excel(writer, index=False, sheet_name="Merged")
            output_merged.seek(0)
            st.download_button(
                "⬇️ Download Merged Data",
                data=output_merged,
                file_name="merged_rts_api.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        ######################################################################
        # Consolidated Payment Report Processing & Payment Status Assignment
        ######################################################################
        # --- Consolidated Payment Report Processing & Payment Status ---
        if consolidated_file and selected_event:
            st.markdown("### Processing Consolidated Payment Report (Assigning Payment Status)...")
            with st.spinner("Merging Payment Status data..."):
                # 1) Read & preprocess the consolidated payment file
                df_consolidated = preprocess_consolidated_payment_report(consolidated_file)
                st.write(df_consolidated.head(15))
                st.write(df_consolidated.columns)

                
                # 2) Add the 'Event' column so it can be merged by (Location, Event)
                df_consolidated["Event"] = selected_event
                
                # Debug: see what columns we have
                st.write("🔍 FULL CONSOLIDATED DATA AFTER PREPROCESSING:")
                st.dataframe(df_consolidated.head(20))
                
                # 3) Standardize 'Location' and 'Event'
                df_consolidated = standardize_location(df_consolidated, "Location")
                df_consolidated["Event"] = (
                    df_consolidated["Event"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )
                
                # 4) Copy merged data & filter for "Completed" orders
                df_completed = df_merged.copy()
                df_completed = standardize_location(df_completed, "Location")
                df_completed["Event"] = df_completed["Event"].astype(str).str.strip().str.lower()
                df_completed = df_completed[df_completed["Status"] == "Completed"]
                
                # 5) Filter only rows matching the selected event
                selected_event_lower = selected_event.strip().lower()
                df_completed = df_completed[df_completed["Event"] == selected_event_lower]
                
                if df_completed.empty:
                    st.warning("No Completed orders found for the selected event.")
                    st.stop()
                
                # 6) Calculate box-level totals (summing the 'Total' column)
                df_box_totals = (
                    df_completed
                    .groupby(["Location", "Event"], as_index=False)["Total"]
                    .sum()
                    .rename(columns={"Total": "BoxTotal"})
                )
                
                # 7) Merge box totals with consolidated payment data
                df_box_merged = df_box_totals.merge(
                    df_consolidated, how="left", on=["Location", "Event"]
                )
                
                # 8) Assign PaymentStatus based on drawdown vs credit card match
                df_box_merged["PaymentStatus"] = df_box_merged.apply(assign_payment_status, axis=1)
                
                # 9) Merge PaymentStatus back into the completed orders DataFrame
                df_box_merged = df_box_merged[["Location", "Event", "PaymentStatus"]]
                df_completed = df_completed.merge(
                    df_box_merged, on=["Location", "Event"], how="left"
                )
                
                # 10) Reorder columns (create empty columns if missing)
                final_cols = [
                    "Location", "Event", "Event_Date", "Guest_name", "Licence_type",
                    "Ordered_on", "Order_type", "Total", "Status", "Available_card",
                    "Card_payment", "Guest_email", "EventId", "KickOffEventStart",
                    "Menu_Item", "OrderedAmount", "PricePerUnit", "ApiPrice",
                    "PaymentStatus"
                ]
                for col in final_cols:
                    if col not in df_completed.columns:
                        df_completed[col] = ""
                df_completed = df_completed[final_cols]
            
            st.markdown("### Final Data with Payment Status")
            st.dataframe(df_completed, use_container_width=True)

            # Optional: Download button
            output_final = BytesIO()
            with pd.ExcelWriter(output_final, engine="xlsxwriter") as writer:
                df_completed.to_excel(writer, index=False, sheet_name="Final Data")
            output_final.seek(0)
            st.download_button(
                "⬇️ Download Final Data with Payment Status",
                data=output_final,
                file_name="final_merged_with_payment_status.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Please upload a consolidated payment file **and** select an event to process.")



if __name__ == "__main__":
    run()
