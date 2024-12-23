import streamlit as st
import pandas as pd
import logging
from io import StringIO
import matplotlib.pyplot as plt

# Configure logging to Streamlit and a log stream
log_stream = StringIO()
logging.basicConfig(stream=log_stream, level=logging.INFO, format="%(asctime)s - %(message)s")

# Helper function to adjust block names
def adjust_block(block):
    if isinstance(block, str) and block.startswith("C") and block[1:].isdigit():
        block_number = int(block[1:])
        return f"{block_number} Club level"
    elif isinstance(block, str) and block.isdigit():
        block_number = int(block)
        return f"{block_number} Club level"
    return block

# Data preprocessing
def preprocess_data(df):
    """Preprocess the input data: strip spaces, clean duplicates, normalize casing."""
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df.drop_duplicates(inplace=True)
    return df

# Load Seat List and Game Category
def load_seat_list_and_game_category(path):
    """Load the Seat List and Game Category sheets."""
    seat_list = pd.read_excel(path, sheet_name="Seat List")
    game_category = pd.read_excel(path, sheet_name="Game Category")
    seat_list.columns = seat_list.columns.str.strip().str.lower()
    game_category.columns = game_category.columns.str.strip().str.lower()
    seat_list["block"] = seat_list["block"].apply(adjust_block)
    game_category["seat_value"] = pd.to_numeric(game_category["seat_value"], errors="coerce")
    return preprocess_data(seat_list), preprocess_data(game_category)

# Process TX Sales and From Hosp files
def process_files(tx_sales_file, from_hosp_file, seat_list, game_category):
    """Process TX Sales and From Hosp files."""
    tx_sales_data = pd.read_excel(tx_sales_file, sheet_name="TX Sales Data")
    tx_sales_data.columns = tx_sales_data.columns.str.strip().str.replace(" ", "_").str.lower()
    tx_sales_data["block"] = tx_sales_data["block"].apply(adjust_block)
    tx_sales_data["ticket_sold_price"] = pd.to_numeric(tx_sales_data["ticket_sold_price"], errors="coerce")
    tx_sales_data = preprocess_data(tx_sales_data)

    from_hosp = pd.read_excel(from_hosp_file, sheet_name=None)
    from_hosp_combined = pd.concat(from_hosp.values(), ignore_index=True)
    from_hosp_combined.columns = from_hosp_combined.columns.str.strip().str.replace(" ", "_").str.lower()
    from_hosp_combined["block"] = from_hosp_combined["block"].apply(adjust_block)
    from_hosp_combined = from_hosp_combined[from_hosp_combined["crc_desc"].notnull()]
    from_hosp_combined = preprocess_data(from_hosp_combined)

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

    for _, row in from_hosp_combined.iterrows():
        sales_match = tx_sales_data[
            (tx_sales_data["game_name"] == row["game_name"]) &
            (tx_sales_data["block"] == row["block"]) &
            (tx_sales_data["row"] == row["row"]) &
            (tx_sales_data["seat"] == row["seat"])
        ]
        row["found_on_tx_file"] = "Y" if not sales_match.empty else "N"
        row["ticket_sold_price"] = sales_match["ticket_sold_price"].values[0] if not sales_match.empty else None
        release_data.append(row.to_dict())

    # Debugging: Log columns and sample rows
    logging.info("TX Sales Data Columns: %s", tx_sales_data.columns.tolist())
    if matched_data:
        logging.info("Sample Matched Row: %s", matched_data[0])
    else:
        logging.warning("No rows matched during processing.")

    # Default columns if no data is matched
    if not matched_data:
        matched_data = [{"game_name": None, "game_date": None, "block": None, "row": None, "seat": None}]

    matched_df = pd.DataFrame(matched_data).reset_index(drop=True)
    release_df = pd.DataFrame(release_data).pipe(lambda df: df.loc[:, ~df.columns.duplicated()])

    return matched_df, release_df

# Main Streamlit App
def run_app():
    st.title("🏟️ AFC Hospitality Seat Tracker")
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
            st.sidebar.markdown("### Filters")
            if "game_name" in matched_df.columns:
                game_filter = st.sidebar.multiselect("Filter by Game Name", matched_df["game_name"].dropna().unique())
                if game_filter:
                    matched_df = matched_df[matched_df["game_name"].isin(game_filter)]
                    release_df = release_df[release_df["game_name"].isin(game_filter)]

            st.markdown("### Matched Data From Pre-Assigned Club Level Seats")
            st.write(f"**Number of Matched Rows:** {len(matched_df)}")
            st.dataframe(matched_df)

if __name__ == "__main__":
    run_app()
