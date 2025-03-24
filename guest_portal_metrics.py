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
    st.sidebar.header("Upload Manual File")
    manual_file = st.sidebar.file_uploader("Choose the manual .xls file", type=["xls"])

    st.sidebar.header("Date Filter")
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
    def fetch_events(headers):
        """Fetch all events from Events/List, storing EventId, Name, KickOffEventStart."""
        resp = requests.get(events_url, headers=headers)
        if resp.status_code != 200:
            return pd.DataFrame()
        events = resp.json().get("Data", {}).get("Events", [])
        rows = []
        for e in events:
            rows.append({
                "EventId": e["Id"],
                "Event": e["Name"].strip(),
                # 'KickOffEventStart' is the correct field for date/time
                "KickOffEventStart": e.get("KickOffEventStart")
            })
        return pd.DataFrame(rows)

    @st.cache_data
    def fetch_api_preorders(event_ids, headers):
        """Fetch CateringPreorders for all Event IDs, combine into a single DataFrame."""
        all_data = []
        for eid in event_ids:
            url = preorders_url_template.format(eid)
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                items = r.json().get("Data", {}).get("CateringPreorders", [])
                all_data.extend(items)
        return pd.DataFrame(all_data)

    @st.cache_data
    def preprocess_manual(file):
        df = pd.read_excel(file, header=4)
        df = df.loc[:, ~df.columns.str.contains("Unnamed")]
        df.columns = df.columns.str.strip().str.replace(" ", "_")
        df["Location"] = df["Location"].ffill().astype(str).str.strip()
        df = df.dropna(how="all")
        df = df.dropna(subset=["Event", "Order_type"])
        # Explode if multiple events are in one cell
        df["Event"] = df["Event"].astype(str).str.strip().str.split(", ")
        df = df.explode("Event")
        # Extract guest email from guest_name
        df["Guest_email"] = df["Guest_name"].str.extract(r"\(([^)]+)\)")
        df["Guest_name"] = df["Guest_name"].str.extract(r"^(.*?)\s*\(")
        df["Guest_email"] = df["Guest_email"].astype(str).str.lower()
        # Clean up 'Total'
        df["Total"] = (
            df["Total"]
            .astype(str)
            .replace("[\u00a3,]", "", regex=True)
            .replace("", "0")
        )
        df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)
        # If there's an Event_Date column, parse it
        if "Event_Date" in df.columns:
            df["Event_Date"] = pd.to_datetime(df["Event_Date"], errors="coerce")
        df.drop_duplicates(inplace=True)
        return df

    def combine_events_and_preorders(df_events, df_preorders):
        """
        Merge the events DataFrame (with KickOffEventStart) 
        into the preorders DataFrame on EventId, so each preorder row 
        has a KickOffEventStart and Event name from the events data.
        """
        # Convert KickOffEventStart to datetime in events
        df_events["KickOffEventStart"] = pd.to_datetime(df_events["KickOffEventStart"], errors="coerce")

        # Merge preorders with events on 'EventId'
        df_combined = df_preorders.merge(
            df_events,
            how="left",
            left_on="EventId",
            right_on="EventId",
            suffixes=("", "_evt")
        )
        # So now each row in df_combined has columns: 
        #   'Event' (from preorders?), 'Event_evt' (from events?), 'KickOffEventStart', etc.

        # If the preorders also have an 'Event' field, let's unify:
        # Usually the preorders also have 'Event' name. We can decide which to keep.
        # For now, keep the 'Event' from the events table:
        df_combined["Event"] = df_combined["Event_evt"].fillna(df_combined["Event"])
        df_combined.drop(columns=["Event_evt"], inplace=True)

        return df_combined

    def process_api_menu(df):
        """
        Transform the combined DataFrame (which has columns from both 
        preorders and events) into item-level rows, including:
         - OrderedAmount
         - PricePerUnit
         - ApiPrice
        """
        menu = []
        for _, row in df.iterrows():
            # Basic row info
            event_id = row.get("EventId")
            event_name = row.get("Event", "").strip()
            location = str(row.get("Location", "")).strip()
            guest_raw = row.get("Guest", "") or ""
            guest_name = guest_raw.split("(")[0].strip() if "(" in guest_raw else guest_raw
            guest_email = None
            if "(" in guest_raw and ")" in guest_raw:
                guest_email = guest_raw.split("(")[-1].replace(")", "").strip().lower()
            # KickOffEventStart
            kickoff_dt = row.get("KickOffEventStart", None)
            # Status
            status = row.get("Status")

            # For Food, KidsFood, Drink, KidsDrink
            for menu_type, key in [
                ("Food", "FoodMenu"),
                ("Kids Food", "KidsFoodMenu"),
                ("Drink", "DrinkMenu"),
                ("Kids Drink", "KidsDrinkMenu")
            ]:
                val = row.get(key)
                if isinstance(val, dict) and val.get("Name"):
                    price_per_unit = val.get("Price", 0)
                    ordered_amount = val.get("Quantity", 1)
                    api_price = price_per_unit * ordered_amount
                    menu.append({
                        "EventId": str(event_id),
                        "Event": event_name,
                        "KickOffEventStart": kickoff_dt,
                        "Location": location,
                        "Guest_name": guest_name,
                        "Guest_email": guest_email,
                        "Order_type": menu_type,
                        "Menu_Item": val.get("Name"),
                        "OrderedAmount": ordered_amount,
                        "PricePerUnit": price_per_unit,
                        "ApiPrice": api_price,
                        "Status": status
                    })

            # Enhancements
            pre_items = row.get("PreOrderItems", [])
            if isinstance(pre_items, list):
                for pit in pre_items:
                    price_per_unit = pit.get("Price", 0)
                    ordered_amount = pit.get("OrderedAmount", 1)
                    api_price = price_per_unit * ordered_amount
                    menu.append({
                        "EventId": str(event_id),
                        "Event": event_name,
                        "KickOffEventStart": kickoff_dt,
                        "Location": location,
                        "Guest_name": guest_name,
                        "Guest_email": guest_email,
                        "Order_type": "Enhancement",
                        "Menu_Item": pit.get("ProductName"),
                        "OrderedAmount": ordered_amount,
                        "PricePerUnit": price_per_unit,
                        "ApiPrice": api_price,
                        "Status": status
                    })

        df_menu = pd.DataFrame(menu)
        if not df_menu.empty:
            df_menu.drop_duplicates(subset=[
                "EventId","Location","Event","Guest_name","Guest_email","Order_type","Menu_Item"
            ], inplace=True)
        return df_menu

    def map_event_id(row, event_map):
        """
        If you want to unify on (Location, Event, KickOffEventStart) from the manual file,
        you'd need to store the event_date in the manual file and match it with KickOffEventStart. 
        For now, we assume we only match on (Location, Event) if we are ignoring date.
        """
        # or we can just keep the 'EventId' we already merged in process_api_menu
        pass

    def lumpsum_deduping(df, merge_keys):
        if "Ordered_on" in df.columns:
            merge_keys.append("Ordered_on")
        df = df.sort_values(merge_keys)
        def clear_lumpsums(grp):
            if len(grp) > 1:
                grp.iloc[1:, grp.columns.get_loc("Total")] = 0
            return grp
        return df.groupby(merge_keys, group_keys=False).apply(clear_lumpsums).drop_duplicates()

    # --- MAIN APP EXECUTION ---
    if manual_file:
        st.success("📂 Manual file uploaded!")
        progress_bar = st.progress(0)
        time.sleep(3)

        with st.spinner("🔄 Processing data..."):
            # Step 1: Manual
            df_manual = preprocess_manual(manual_file)
            progress_bar.progress(20)

            # Step 2: API Token
            token = get_access_token()
            if not token:
                st.error("❌ Failed to retrieve API token.")
                st.stop()
            headers = {"Authorization": f"Bearer {token}"}

            # Step 3: Fetch Events
            df_events = pd.DataFrame(fetch_events(headers))
            progress_bar.progress(40)

            # Convert df_events into a DataFrame with columns: EventId, Event, KickOffEventStart
            # This might vary based on your actual JSON fields
            if not df_events.empty:
                df_events = df_events[["Id", "Name", "KickOffEventStart"]].rename(
                    columns={"Id": "EventId", "Name": "Event"}
                )
                df_events["KickOffEventStart"] = pd.to_datetime(df_events["KickOffEventStart"], errors="coerce")

            # Step 4: Preorders
            event_ids = df_events["EventId"].unique().tolist() if not df_events.empty else []
            df_api_pre = fetch_api_preorders(event_ids, headers)
            progress_bar.progress(60)

            # Step 5: Combine events with preorders
            # so each row has KickOffEventStart, event name, etc.
            df_combined = df_api_pre.merge(
                df_events,
                how="left",
                on="EventId",
                suffixes=("", "_evt")
            )
            # Now df_combined has columns like:
            #   'EventId', 'Event' (from preorders?), 'Event_evt' (from df_events),
            #   'KickOffEventStart', etc.
            # Use the official name from df_events
            df_combined["Event"] = df_combined["Event_evt"].fillna(df_combined["Event"])
            df_combined.drop(columns=["Event_evt"], inplace=True)

            progress_bar.progress(80)

            # Step 6: Process item-level menu from combined data
            df_menu = process_api_menu(df_combined)

            # Step 7: Merge manual with df_menu
            # Build a (Location, Event, Guest_name, Guest_email, Order_type, etc.) or (EventId, ...) match
            # For now, we do (EventId, Location, Event, Guest_name, Guest_email, Order_type)
            # If your manual data doesn't have an 'EventId', we map it by (Location, Event) only?
            # We'll do a naive approach: if 'EventId' not in df_manual, we try to map via (Location, Event)
            if "EventId" not in df_manual.columns:
                # Try to map by (Location, Event) ignoring date/time
                # or skip if we have no date
                pass

            # For demonstration, let's do:
            df_manual["EventId"] = None
            # Then build a dictionary from df_menu: (Location, Event) -> EventId
            # But if you have multiple matches, you'd need date/time logic
            event_map = {}
            for _, row in df_menu.iterrows():
                loc_evt = (row["Location"], row["Event"])
                # We'll store the last seen EventId
                event_map[loc_evt] = row["EventId"]

            def map_eventid_manual(r):
                loc_evt = (r["Location"], r["Event"])
                return event_map.get(loc_evt, None)

            df_manual["EventId"] = df_manual.apply(map_eventid_manual, axis=1).fillna("")
            df_manual["EventId"] = df_manual["EventId"].astype(str)

            # Now merge
            merge_keys = ["EventId","Location","Event","Guest_name","Guest_email","Order_type"]
            df_merged = df_manual.merge(df_menu, how="left", on=merge_keys, suffixes=("_manual","_api"))

            # Lumpsum dedup
            df_merged = lumpsum_deduping(df_merged, merge_keys)

            if df_merged.empty:
                st.warning("⚠ Merged data is empty.")
                st.stop()

            progress_bar.progress(100)
            st.success("✅ Data ready for analysis")

            # Additional housekeeping if needed
            if "Status_manual" in df_merged.columns:
                df_merged.rename(columns={"Status_manual": "Status"}, inplace=True)
            if "Status_api" in df_merged.columns:
                df_merged.drop(columns=["Status_api"], inplace=True)

            # --- Filtering ---
            df_merged["Ordered_on"] = pd.to_datetime(df_merged["Ordered_on"], errors="coerce")
            df_merged = df_merged[
                (df_merged["Ordered_on"] >= pd.to_datetime(start_date)) &
                (df_merged["Ordered_on"] <= pd.to_datetime(end_date))
            ]

            # Filter by Location
            if "Location" in df_merged.columns:
                locs = sorted(df_merged["Location"].dropna().unique())
                selected_locs = st.sidebar.multiselect("Select Location(s):", locs, default=locs)
                df_merged = df_merged[df_merged["Location"].isin(selected_locs)]

            # Filter by Order_type
            if "Order_type" in df_merged.columns:
                order_types = sorted(df_merged["Order_type"].dropna().unique())
                selected_types = st.sidebar.multiselect("Select Order Type(s):", order_types, default=order_types)
                df_merged = df_merged[df_merged["Order_type"].isin(selected_types)]

            # Filter by Menu_Item
            if "Menu_Item" in df_merged.columns:
                items = sorted(df_merged["Menu_Item"].dropna().unique())
                selected_items = st.sidebar.multiselect("Select Menu Item(s):", items, default=items)
                df_merged = df_merged[df_merged["Menu_Item"].isin(selected_items)]

            # Filter by Status
            if "Status" in df_merged.columns:
                statuses = sorted(df_merged["Status"].dropna().unique())
                selected_statuses = st.sidebar.multiselect("Select Status(es):", statuses, default=statuses)
                df_merged = df_merged[df_merged["Status"].isin(selected_statuses)]

            if df_merged.empty:
                st.warning("⚠ No data after filtering.")
                return

        # --- METRICS ---
        st.subheader("📊 Key Metrics")
        total_orders = df_merged.shape[0]
        total_spend = df_merged[price_type].fillna(0).sum()
        food_total = df_merged.loc[df_merged["Order_type"]=="Food", price_type].sum()
        enhancement_total = df_merged.loc[df_merged["Order_type"]=="Enhancement", price_type].sum()
        kids_total = df_merged.loc[df_merged["Order_type"]=="Kids Food", price_type].sum()
        total_boxes = df_merged["Location"].nunique()

        # Top item
        top_item_series = df_merged.groupby("Menu_Item")[price_type].sum().sort_values(ascending=False)
        if not top_item_series.empty:
            top_item_name = top_item_series.index[0]
            top_item_spend = top_item_series.iloc[0]
        else:
            top_item_name, top_item_spend = "N/A", 0

        # Top box
        top_box_series = df_merged.groupby("Location")[price_type].sum().sort_values(ascending=False)
        if not top_box_series.empty:
            top_box_name = top_box_series.index[0]
            top_box_spend = top_box_series.iloc[0]
        else:
            top_box_name, top_box_spend = "N/A", 0

        # Top event
        top_event_series = df_merged.groupby("Event")[price_type].sum().sort_values(ascending=False)
        if not top_event_series.empty:
            top_event_name = top_event_series.index[0]
        else:
            top_event_name = "N/A"

        # average monthly
        if "Ordered_on" in df_merged.columns and not df_merged["Ordered_on"].isna().all():
            avg_spend = df_merged.groupby(df_merged["Ordered_on"].dt.to_period("M"))[price_type].mean().mean()
        else:
            avg_spend = 0

        # Display
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

        # Final table
        with st.expander("📋 Merged Data Table (click to expand)"):
            st.dataframe(df_merged, use_container_width=True)

            # Prepare XLSX
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_merged.to_excel(writer, index=False, sheet_name="Merged Data")
            output.seek(0)

            st.download_button(
                label="⬇️ Download Processed Data",
                data=output,
                file_name="processed_merged_orders.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    else:
        st.info("Please upload the RTS Pre-order file to begin analysis.")

# --- ENTRY POINT ---
if __name__ == "__main__":
    run()
