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
        response = requests.post(token_url, data=data)
        return response.json().get("access_token") if response.status_code == 200 else None

    @st.cache_data
    def fetch_event_details(headers):
        """Fetch full event details from Events/List, including KickOffEventStart."""
        r = requests.get(events_url, headers=headers)
        if r.status_code != 200:
            return []
        events = r.json().get("Data", {}).get("Events", [])
        # Build list of dictionaries with Id, Name, and KickOffEventStart
        return [
            {
                "EventId": e["Id"],
                "Event": e["Name"].strip(),
                "KickOffEventStart": e.get("KickOffEventStart")
            }
            for e in events if e.get("KickOffEventStart")
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
        df["Total"] = pd.to_numeric(
            df["Total"].astype(str)
            .replace("[\u00a3,]", "", regex=True)
            .replace("", "0"),
            errors="coerce"
        ).fillna(0)
        # Parse Event_Date if it exists in manual file
        if "Event_Date" in df.columns:
            df["Event_Date"] = pd.to_datetime(df["Event_Date"], dayfirst=True, errors="coerce")
        df.drop_duplicates(inplace=True)
        return df

    def process_api_menu(api_df):
        """
        Extract item-level data from the Catering Preorders API.
        Now extracts:
         - OrderedAmount, PricePerUnit, Vat, and calculates ApiPrice.
         Uses "KickOffEventStart" from the API as the event date.
        """
        menu = []
        event_map = {}
        for _, row in api_df.iterrows():
            guest = row.get("Guest", "")
            guest_name = guest.split("(")[0].strip() if "(" in guest else guest
            guest_email = guest.split("(")[-1].replace(")", "").strip().lower() if "(" in guest else None
            loc = str(row.get("Location", "")).strip()
            evt = str(row.get("Event", "")).strip()
            eid = row.get("EventId")
            # Use KickOffEventStart from API as event date; convert to datetime and then to date
            raw_date = row.get("KickOffEventStart")
            event_date_api = pd.to_datetime(raw_date, errors="coerce").date() if raw_date else None
            status = row.get("Status")

            # Build event mapping key: (Location, Event, event_date)
            if eid and loc and evt and event_date_api:
                event_map[(loc, evt, event_date_api)] = str(eid)

            # For Food / Kids Food / Drink / Kids Drink
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
                        "EventId": str(eid),
                        "Location": loc,
                        "Event": evt,
                        "KickOffEventStart": event_date_api,  # This is the API event date
                        "Guest_name": guest_name,
                        "Guest_email": guest_email,
                        "Order_type": menu_type,
                        "Menu_Item": val.get("Name"),
                        "OrderedAmount": ordered_amount,
                        "PricePerUnit": price_per_unit,
                        "ApiPrice": api_price,
                        "Status": status
                    })

            # For Enhancements (PreOrderItems)
            for pit in row.get("PreOrderItems", []):
                price_per_unit = pit.get("Price", 0)
                ordered_amount = pit.get("OrderedAmount", 1)
                api_price = price_per_unit * ordered_amount
                menu.append({
                    "EventId": str(eid),
                    "Location": loc,
                    "Event": evt,
                    "KickOffEventStart": event_date_api,
                    "Guest_name": guest_name,
                    "Guest_email": guest_email,
                    "Order_type": "Enhancement",
                    "Menu_Item": pit.get("ProductName"),
                    "OrderedAmount": ordered_amount,
                    "PricePerUnit": price_per_unit,
                    "ApiPrice": api_price,
                    "Status": status
                })

        df_menu = pd.DataFrame(menu).drop_duplicates(
            subset=["EventId", "Location", "Event", "Guest_name", "Guest_email", "Order_type", "Menu_Item"]
        )
        return df_menu, event_map

    def map_event_id(row, event_map):
        """
        Map the manual row to an EventId using (Location, Event, Event_Date).
        Manual file should have an Event_Date column (datetime).
        """
        evt_name = str(row["Event"]).strip()
        loc = str(row["Location"]).strip()
        # If manual file has Event_Date, convert to date:
        if "Event_Date" in row and pd.notna(row["Event_Date"]):
            evt_date = row["Event_Date"].date()
        else:
            evt_date = None
        return event_map.get((loc, evt_name, evt_date), None)

    def lumpsum_deduping(df, merge_keys):
        if "Ordered_on" in df.columns:
            merge_keys.append("Ordered_on")
        df = df.sort_values(merge_keys)
        def clear_lumpsums(grp):
            if len(grp) > 1:
                grp.iloc[1:, grp.columns.get_loc("Total")] = 0
            return grp
        return df.groupby(merge_keys, group_keys=False).apply(clear_lumpsums).drop_duplicates()

    # --- App Execution ---
    if manual_file:
        st.success("📂 Manual file uploaded!")
        progress_bar = st.progress(0)
        time.sleep(3)

        with st.spinner("🔄 Processing data..."):
            # Step 1: Preprocess Manual
            df_manual = preprocess_manual(manual_file)
            progress_bar.progress(20)

            # Step 2: Get API Token
            token = get_access_token()
            if not token:
                st.error("❌ Failed to retrieve API token.")
                st.stop()
            headers = {"Authorization": f"Bearer {token}"}

            # Step 3: Fetch Events from Events/List
            df_events = pd.DataFrame(fetch_event_details(headers))
            progress_bar.progress(40)
            # Convert df_events into a DataFrame with proper columns
            if not df_events.empty:
                df_events = df_events[["Id", "Name", "KickOffEventStart"]].rename(
                    columns={"Id": "EventId", "Name": "Event"}
                )
                df_events["KickOffEventStart"] = pd.to_datetime(df_events["KickOffEventStart"], errors="coerce").dt.date

            # Step 4: Fetch API Preorders
            event_ids = df_events["EventId"].unique().tolist() if not df_events.empty else []
            df_api_pre = fetch_api_preorders(event_ids, headers)
            progress_bar.progress(60)

            # Step 5: Merge Events into Preorders so each row gets KickOffEventStart
            df_api = df_api_pre.merge(
                df_events,
                how="left",
                left_on="EventId",
                right_on="EventId",
                suffixes=("", "_evt")
            )
            # Use official event name from df_events if available
            df_api["Event"] = df_api["Event_evt"].fillna(df_api["Event"])
            df_api.drop(columns=["Event_evt"], inplace=True)

            progress_bar.progress(80)

            # Step 6: Process API Menu from combined API data
            df_menu, event_map = process_api_menu(df_api)

            # Step 7: Map EventId to manual file using (Location, Event, Event_Date)
            # Ensure manual file's Event_Date is datetime
            if "Event_Date" in df_manual.columns:
                df_manual["Event_Date"] = pd.to_datetime(df_manual["Event_Date"], dayfirst=True, errors="coerce")
            else:
                st.error("Manual file is missing 'Event_Date' column.")
                st.stop()
            df_manual["EventId"] = df_manual.apply(lambda row: map_event_id(row, event_map), axis=1).astype(str).fillna("")

            # Merge manual and API menu data
            merge_keys = ["EventId", "Location", "Event", "Guest_name", "Guest_email", "Order_type"]
            df_merged = df_manual.merge(
                df_menu,
                how="left",
                on=merge_keys,
                suffixes=("_manual", "_api")
            )
            df_merged = lumpsum_deduping(df_merged, merge_keys)

            if df_merged.empty:
                st.warning("⚠ Merged data is empty.")
                st.stop()

            progress_bar.progress(100)
            st.success("✅ Data ready for analysis")
            time.sleep(3)

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

        # --- Metrics ---
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

        with st.expander("📋 Merged Data Table (click to expand)"):
            st.dataframe(df_merged, use_container_width=True)

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

if __name__ == "__main__":
    run()
