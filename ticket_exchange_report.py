import streamlit as st
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Helper function to adjust block names
def adjust_block(block):
    if isinstance(block, str) and block.startswith("C") and block[1:].isdigit():
        block_number = int(block[1:])
        return f"{block_number} Club level"
    elif isinstance(block, str) and block.isdigit():
        block_number = int(block)
        return f"{block_number} Club level"
    return block

# Load Seat List and Game Category
def load_seat_list_and_game_category(path):
    seat_list = pd.read_excel(path, sheet_name="Seat List")
    game_category = pd.read_excel(path, sheet_name="Game Category")
    seat_list.columns = seat_list.columns.str.strip().str.lower()
    game_category.columns = game_category.columns.str.strip().str.lower()
    seat_list["block"] = seat_list["block"].apply(adjust_block)
    game_category["seat_value"] = pd.to_numeric(game_category["seat_value"], errors="coerce")
    return seat_list, game_category

# Process TX Sales and From Hosp files
def process_files(tx_sales_file, from_hosp_file, seat_list, game_category):
    try:
        tx_sales_data = pd.read_excel(tx_sales_file, sheet_name="TX Sales Data")
        tx_sales_data.columns = tx_sales_data.columns.str.strip().str.replace(" ", "_").str.lower()
        tx_sales_data["block"] = tx_sales_data["block"].apply(adjust_block)
        tx_sales_data["ticket_sold_price"] = pd.to_numeric(tx_sales_data["ticket_sold_price"], errors="coerce")

        from_hosp = pd.read_excel(from_hosp_file, sheet_name=None)
        from_hosp_combined = pd.concat(from_hosp.values(), ignore_index=True)
        from_hosp_combined.columns = from_hosp_combined.columns.str.strip().str.replace(" ", "_").str.lower()
        from_hosp_combined["block"] = from_hosp_combined["block"].apply(adjust_block)

        # Match TX Sales with Seat List and Game Category
        matched_data = []
        release_data = []
        for _, row in tx_sales_data.iterrows():
            matching_seat = seat_list[
                (seat_list["block"] == row["block"]) &
                (seat_list["row"] == row["row"]) &
                (seat_list["seat"] == row["seat"])
            ]
            if not matching_seat.empty:
                row["crc_desc"] = matching_seat["crc_desc"].values[0]
                row["price_band"] = matching_seat["price_band"].values[0]
                matching_game = game_category[
                    (game_category["game_name"] == row["game_name"]) &
                    (game_category["game_date"] == row["game_date"]) &
                    (game_category["price_band"] == matching_seat["price_band"].values[0])
                ]
                if not matching_game.empty:
                    row["category"] = matching_game["category"].values[0]
                    row["seat_value"] = matching_game["seat_value"].values[0]
                    row["value_generated"] = row["ticket_sold_price"] - matching_game["seat_value"].values[0]
                    matched_data.append(row)

        # Match From Hosp with TX Sales
        for _, row in from_hosp_combined.iterrows():
            sales_match = tx_sales_data[
                (tx_sales_data["game_name"] == row["game_name"]) &
                (tx_sales_data["block"] == row["block"]) &
                (tx_sales_data["row"] == row["row"]) &
                (tx_sales_data["seat"] == row["seat"])
            ]
            row["matched_yn"] = "Y" if not sales_match.empty else "N"
            row["ticket_sold_price"] = sales_match["ticket_sold_price"].values[0] if not sales_match.empty else None
            release_data.append(row)

        # Convert to DataFrame
        matched_df = pd.DataFrame(matched_data).reset_index(drop=True)
        release_df = pd.DataFrame(release_data).reset_index(drop=True)

        return matched_df, release_df
    except Exception as e:
        st.error(f"Error processing files: {e}")
        logging.error(f"Error processing files: {e}")
        return None, None

# Calculate metrics
def calculate_metrics(matched_df, release_df, game_category):
    try:
        # 1) Total Tickets Released
        total_tickets_released = release_df.shape[0]

        # 2) Total Tickets Sold on Exchange
        tickets_sold_on_exchange = release_df[release_df["matched_yn"] == "Y"].shape[0]

        # 3) Value Generated from Tickets Sold
        value_generated = release_df["ticket_sold_price"].sum()

        # 4) Average Sale Price of Tickets Sold
        avg_sale_price = release_df["ticket_sold_price"].mean()

        metrics = {
            "Total Tickets Released": total_tickets_released,
            "Tickets Sold on Exchange": tickets_sold_on_exchange,
            "Value Generated (Total)": f"£{value_generated:.2f}" if pd.notna(value_generated) else "N/A",
            "Average Sale Price": f"£{avg_sale_price:.2f}" if pd.notna(avg_sale_price) else "N/A",
        }
        return metrics
    except Exception as e:
        logging.error(f"Error calculating metrics: {e}")
        return {}

# Main Streamlit App
def run_app():
    st.title("AFC Hospitality Seat Tracker")
    st.markdown("Upload your TX Sales file and From Hosp file to analyze seating data.")

    tx_sales_file = st.file_uploader("Upload TX Sales File", type=["xlsx"])
    from_hosp_file = st.file_uploader("Upload From Hosp File", type=["xlsx"])

    seat_list_game_cat_path = "seat_list_game_cat.xlsx"
    with st.spinner("Loading Seat List and Game Category..."):
        try:
            seat_list, game_category = load_seat_list_and_game_category(seat_list_game_cat_path)
            st.success("Seat List and Game Category loaded successfully.")
        except Exception as e:
            st.error(f"Failed to load Seat List and Game Category: {e}")
            return

    if tx_sales_file and from_hosp_file:
        with st.spinner("Processing files..."):
            matched_df, release_df = process_files(tx_sales_file, from_hosp_file, seat_list, game_category)

        if matched_df is not None and release_df is not None:
            # Display tabs
            st.markdown("### Matched Data")
            st.dataframe(matched_df, width=1200, height=500)
            st.markdown("### From Hosp Results")
            st.dataframe(release_df, width=1200, height=500)

            # Calculate and display metrics
            st.markdown("### Metrics")
            metrics = calculate_metrics(matched_df, release_df, game_category)
            for metric, value in metrics.items():
                st.metric(label=metric, value=value)
        else:
            st.error("No data to display.")

if __name__ == "__main__":
    run_app()
