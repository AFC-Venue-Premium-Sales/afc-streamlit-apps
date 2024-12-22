import pandas as pd
import streamlit as st
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Helper function to adjust block names
def adjust_block(block):
    if isinstance(block, str) and block.startswith("C") and block[1:].isdigit():
        block_number = int(block[1:])  # Remove leading zeros
        return f"{block_number} Club level"  # Normalize casing
    elif isinstance(block, str) and block.isdigit():
        block_number = int(block)
        return f"{block_number} Club level"
    return block

def load_seat_list_and_game_category(path):
    """Loads Seat List and Game Category sheets."""
    try:
        seat_list = pd.read_excel(path, sheet_name="Seat List")
        game_category = pd.read_excel(path, sheet_name="Game Category")

        # Log column names for debugging
        logging.info(f"Seat List columns: {seat_list.columns.tolist()}")
        logging.info(f"Game Category columns: {game_category.columns.tolist()}")

        # Adjust block column if it exists
        if "block" in seat_list.columns:
            seat_list["block"] = seat_list["block"].apply(adjust_block)
        else:
            raise ValueError("'block' column missing in Seat List.")

        if "block" in game_category.columns:
            game_category["block"] = game_category["block"].apply(adjust_block)
        else:
            raise ValueError("'block' column missing in Game Category.")

        # Ensure seat_value column is numeric
        game_category["seat_value"] = pd.to_numeric(game_category["seat_value"], errors="coerce")
        return seat_list, game_category
    except Exception as e:
        raise Exception(f"Error loading Seat List and Game Category: {e}")

def process_files(tx_sales_file, from_hosp_file, seat_list, game_category):
    """Processes the uploaded TX Sales and From Hosp files."""
    try:
        # Load TX Sales file
        tx_sales_data = pd.read_excel(tx_sales_file, sheet_name="TX Sales Data")
        tx_sales_data.columns = tx_sales_data.columns.str.strip().str.replace(" ", "_").str.lower()
        tx_sales_data["block"] = tx_sales_data["block"].apply(adjust_block)
        tx_sales_data["ticket_sold_price"] = pd.to_numeric(tx_sales_data["ticket_sold_price"], errors="coerce")

        # Load From Hosp file
        from_hosp = pd.read_excel(from_hosp_file, sheet_name=None)  # Load all sheets
        from_hosp_combined = pd.concat(from_hosp.values(), ignore_index=True)  # Combine all sheets
        from_hosp_combined.columns = from_hosp_combined.columns.str.strip().str.replace(" ", "_").str.lower()
        from_hosp_combined["block"] = from_hosp_combined["block"].apply(adjust_block)

        # Matched data processing
        matched_data = []
        release_data = []

        # Match TX Sales Data with Seat List and Game Category
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

        # Match From Hosp with TX Sales Data
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

        # Convert results to DataFrames
        matched_df = pd.DataFrame(matched_data)
        release_df = pd.DataFrame(release_data)

        return matched_df, release_df
    except Exception as e:
        raise Exception(f"Error processing files: {e}")

def run_app():
    """Main app function."""
    st.title("🏟️ AFC Hospitality Seat Tracker")
    st.markdown("Upload your TX Sales file and From Hosp file to process and analyze seating data.")

    # File uploaders
    tx_sales_file = st.file_uploader("Upload TX Sales File", type=["xlsx"])
    from_hosp_file = st.file_uploader("Upload From Hosp File", type=["xlsx"])

    # Path to Seat List and Game Category file
    seat_list_game_cat_path = "seat_list_game_cat.xlsx"

    # Load Seat List and Game Category
    try:
        seat_list, game_category = load_seat_list_and_game_category(seat_list_game_cat_path)
        st.success("✅ Seat List and Game Category loaded successfully.")
    except Exception as e:
        st.error(f"❌ {e}")
        logging.error(e)
        return

    # Process files when both are uploaded
    if tx_sales_file and from_hosp_file:
        try:
            matched_df, release_df = process_files(tx_sales_file, from_hosp_file, seat_list, game_category)

            # Display results
            st.markdown("### Matched Data")
            st.dataframe(matched_df)

            st.markdown("### From Hosp Results")
            st.dataframe(release_df)

            # Download option
            output_file = "processed_data.xlsx"
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                matched_df.to_excel(writer, sheet_name="Matched Data", index=False)
                release_df.to_excel(writer, sheet_name="From Hosp", index=False)
            with open(output_file, "rb") as f:
                st.download_button("Download Processed Data", f, file_name=output_file)
        except Exception as e:
            st.error(f"❌ {e}")
            logging.error(e)
    else:
        st.info("Please upload both the TX Sales file and From Hosp file to proceed.")

if __name__ == "__main__":
    run_app()
