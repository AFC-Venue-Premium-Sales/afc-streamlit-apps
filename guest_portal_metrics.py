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
    def fetch_event_details(headers):
        """Fetch full event details from Events/List, including KickOffEventStart."""
        r = requests.get(events_url, headers=headers)
        if r.status_code != 200:
            return []
        events = r.json().get("Data", {}).get("Events", [])
        # Return "EventId", "Event", "KickOffEventStart"
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

        # Explode if multiple events in one cell
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

    def process_api_menu(df_api):
        """
        Convert the combined preorders + events data
        into item-level rows, each with Price, Qty, etc.
        """
        menu = []
        event_map = {}

        for _, row in df_api.iterrows():
            guest_raw = row.get("Guest", "") or ""
            guest_name = guest_raw.split("(")[0].strip() if "(" in guest_raw else guest_raw
            guest_email = None
            if "(" in guest_raw and ")" in guest_raw:
                guest_email = guest_raw.split("(")[-1].replace(")", "").strip().lower()

            loc = str(row.get("Location", "")).strip()
            evt = str(row.get("Event", "")).strip()
            eid = row.get("EventId")

            # Convert KickOffEventStart to date
            raw_date = row.get("KickOffEventStart")
            event_date_api = pd.to_datetime(raw_date, errors="coerce").date() if raw_date else None

            # Build event_map for (Location, Event, date) -> EventId
            if eid and loc and evt and event_date_api:
                event_map[(loc, evt, event_date_api)] = str(eid)

            status = row.get("Status")

            # Food, KidsFood, Drink, KidsDrink
            for menu_type, key in [
                ("Food", "FoodMenu"),
                ("Kids Food", "KidsFoodMenu"),
                ("Drink", "DrinkMenu"),
                ("Kids Drink", "KidsDrinkMenu"),
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

            # Enhancements (PreOrderItems)
            pre_items = row.get("PreOrderItems", [])
            if isinstance(pre_items, list):
                for pit in pre_items:
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
                subset=["EventId","Location","Event","Guest_name","Guest_email","Order_type","Menu_Item"],
                inplace=True
            )
        return df_menu, event_map

    def map_event_id(row, event_map):
        """
        Use the manual file's (Location, Event, Event_Date)
        to find the correct EventId from event_map.
        """
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

    # --- MAIN EXECUTION ---
    if manual_file:
        st.success("📂 Manual file uploaded!")
        progress_bar = st.progress(0)
        time.sleep(3)

        with st.spinner("🔄 Processing data..."):
            # 1) Preprocess manual
            df_manual = preprocess_manual(manual_file)
            progress_bar.progress(20)

            # 2) Token
            token = get_access_token()
            if not token:
                st.error("❌ Failed to retrieve API token.")
                st.stop()
            headers = {"Authorization": f"Bearer {token}"}

            # 3) Fetch event details
            events_list = fetch_event_details(headers)  # returns a list of dict
            df_events = pd.DataFrame(events_list)
            progress_bar.progress(40)

            # If df_events is not empty, parse KickOffEventStart
            if not df_events.empty:
                df_events["KickOffEventStart"] = pd.to_datetime(df_events["KickOffEventStart"], errors="coerce").dt.date

            # 4) Fetch API Preorders
            event_ids = df_events["EventId"].unique().tolist() if not df_events.empty else []
            df_api_pre = fetch_api_preorders(event_ids, headers)
            progress_bar.progress(60)

            # 5) Merge events + preorders on EventId
            # So each row has KickOffEventStart from events
            df_api = df_api_pre.merge(
                df_events,
                how="left",
                left_on="EventId",
                right_on="EventId",
                suffixes=("", "_evt")
            )
            # If there's an "Event_evt", let's use it as the official name
            if "Event_evt" in df_api.columns:
                df_api["Event"] = df_api["Event_evt"].fillna(df_api["Event"])
                df_api.drop(columns=["Event_evt"], inplace=True)

            progress_bar.progress(80)

            # 6) Build df_menu from combined data
            df_menu, event_map = process_api_menu(df_api)

            # 7) Map EventId to manual
            if "Event_Date" not in df_manual.columns:
                st.error("Manual file is missing 'Event_Date' column.")
                st.stop()

            df_manual["Event_Date"] = pd.to_datetime(df_manual["Event_Date"], dayfirst=True, errors="coerce")
            df_manual["EventId"] = df_manual.apply(lambda r: map_event_id(r, event_map), axis=1).astype(str).fillna("")

            # 8) Merge
            merge_keys = ["EventId","Location","Event","Guest_name","Guest_email","Order_type"]
            df_merged = df_manual.merge(
                df_menu,
                how="left",
                on=merge_keys,
                suffixes=("_manual","_api")
            )
            df_merged = lumpsum_deduping(df_merged, merge_keys)

            if df_merged.empty:
                st.warning("⚠ Merged data is empty.")
                st.stop()

            progress_bar.progress(100)
            st.success("✅ Data ready for analysis")
            time.sleep(3)

            # Tidy up statuses
            if "Status_manual" in df_merged.columns:
                df_merged.rename(columns={"Status_manual":"Status"}, inplace=True)
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
