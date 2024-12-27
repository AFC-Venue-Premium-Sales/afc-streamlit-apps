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
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

    df.drop_duplicates(inplace=True)
    return df

# Load Seat List and Game Category
@st.cache_data
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
@st.cache_data
def process_files(tx_sales_file, from_hosp_file, seat_list, game_category):
    """Process TX Sales and From Hosp files."""
    cols_to_load = ["block", "row", "seat", "game_name", "game_date", "price_band", "ticket_sold_price"]
    tx_sales_data = pd.read_excel(tx_sales_file, sheet_name="TX Sales Data", usecols=cols_to_load)
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

    # Vectorized merging for faster matching
    tx_sales_data = tx_sales_data.merge(seat_list, how="left", on=["block", "row", "seat"])
    tx_sales_data = tx_sales_data.merge(
        game_category,
        how="left",
        left_on=["game_name", "game_date", "price_band"],
        right_on=["game_name", "game_date", "price_band"]
    )

    # Calculate value generated
    tx_sales_data["value_generated"] = tx_sales_data["ticket_sold_price"] - tx_sales_data["seat_value"]

    # Separate matched and unmatched rows
    matched_df = tx_sales_data.dropna(subset=["seat_value"]).reset_index(drop=True)
    missing_df = tx_sales_data[tx_sales_data["seat_value"].isna()].reset_index(drop=True)

    # Process From Hosp data for matching
    release_data = []
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

    release_df = pd.DataFrame(release_data).pipe(lambda df: df.loc[:, ~df.columns.duplicated()])

    print("Returning values from process_files: tx_sales_data, matched_df, release_df, missing_df")
    return tx_sales_data, matched_df, release_df, missing_df

# Main Streamlit App
def run_app():
    st.title("🏟️ AFC Hospitality Ticket Exchange Inventory Tracker")
    
    st.sidebar.title("File Uploads")
    seat_list_game_cat_path = "seat_list_game_cat.xlsx"
    tx_sales_file = st.sidebar.file_uploader("Upload TX Sales File", type=["xlsx"])
    from_hosp_file = st.sidebar.file_uploader("Upload From Hosp File", type=["xlsx"])

    with st.spinner("Loading Seat List and Game Category..."):
        seat_list, game_category = load_seat_list_and_game_category(seat_list_game_cat_path)
        st.sidebar.success("Seat List and Game Category loaded successfully.")

    if not tx_sales_file or not from_hosp_file:
        st.sidebar.info("Please upload all required files to proceed.")
        return

    with st.spinner("Processing files..."):
        print("Unpacking values from process_files...")
        tx_sales_data, matched_df, release_df, missing_df = process_files(tx_sales_file, from_hosp_file, seat_list, game_category)

    # Metrics
    st.sidebar.markdown("### Metrics")
    total_matched = len(matched_df)
    total_missing = len(missing_df)

    st.sidebar.metric("Total Matched Rows", total_matched)
    st.sidebar.metric("Total Missing Rows", total_missing)

    # Display DataFrames
    st.markdown("### Matched Data")
    st.dataframe(matched_df.head(100))  # Display the first 100 rows for performance
    st.download_button("Download Matched Data", matched_df.to_csv(index=False), "matched_data.csv")

    st.markdown("### Missing Data")
    st.dataframe(missing_df.head(100))  # Display the first 100 rows for performance
    st.download_button("Download Missing Data", missing_df.to_csv(index=False), "missing_data.csv")

if __name__ == "__main__":
    run_app()
