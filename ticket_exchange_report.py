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

    matched_df = pd.DataFrame(matched_data).reset_index(drop=True)
    release_df = pd.DataFrame(release_data).pipe(lambda df: df.loc[:, ~df.columns.duplicated()])

    return tx_sales_data, matched_df, release_df

# Main Streamlit App
def run_app():
    st.title("🏟️ AFC Hospitality Seat Tracker")
    
    # Instructions
    st.markdown(
        """
        ### Welcome to the AFC Hospitality Seat Tracker App!
        
        This app helps you analyze and track seat data for AFC Hospitality:
        - **TX Sales File**: Contains data about ticket sales on the exchange.
        - **Hospitality Ticket Releases File**: Includes tickets released by Hospitality.
        - **Seat List & Game Category File**: Preloaded with data on predefined seat allocations and game categories.

        ### How to Use
        1. **Upload your files**:
            - **TX Sales File**: Upload your sales data (`TX Sales Data` tab).
            - **From Hosp File**: Upload the hospitality ticket releases file.
        2. **View results**:
            - Matched rows from predefined seats and released tickets.
            - Metrics, charts, and export options.
        3. **Use filters** in the sidebar to narrow down results by game or CRC description.

        **Note**: Ensure the files are in `.xlsx` format and match the required structure.
        """
    )

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
        tx_sales_data, matched_df, release_df = process_files(tx_sales_file, from_hosp_file, seat_list, game_category)

    # Metrics
    st.sidebar.markdown("### Metrics")
    total_matched = len(matched_df)
    avg_value_generated = matched_df["value_generated"].mean() if not matched_df.empty else 0
    total_value_generated = matched_df["value_generated"].sum() if not matched_df.empty else 0
    matched_on_tx = release_df[release_df["found_on_tx_file"] == "Y"]
    total_on_tx = len(matched_on_tx)
    total_tx_value = matched_on_tx["ticket_sold_price"].sum() if not matched_on_tx.empty else 0

    st.sidebar.metric("Total Matched Rows", total_matched)
    st.sidebar.metric("Avg Value Generated", f"£{avg_value_generated:.2f}")
    st.sidebar.metric("Total Value Generated", f"£{total_value_generated:.2f}")
    st.sidebar.metric("Total Rows Found on TX", total_on_tx)
    st.sidebar.metric("Total Value Generated (TX)", f"£{total_tx_value:.2f}")

    # Filters
    st.sidebar.markdown("### Filters")
    all_games = pd.concat([tx_sales_data["game_name"], release_df["game_name"]]).drop_duplicates()
    game_filter = st.sidebar.multiselect("Filter by Game Name", all_games)
    crc_filter = st.sidebar.multiselect("Filter by CRC Description", release_df["crc_desc"].unique())

    # Apply Filters
    if game_filter:
        tx_sales_data = tx_sales_data[tx_sales_data["game_name"].isin(game_filter)]
        matched_df = matched_df[matched_df["game_name"].isin(game_filter)]
        release_df = release_df[release_df["game_name"].isin(game_filter)]
    if crc_filter:
        matched_df = matched_df[matched_df["crc_desc"].isin(crc_filter)]
        release_df = release_df[release_df["crc_desc"].isin(crc_filter)]

    # TX Sales Data
    st.markdown("### TX Sales Data")
    st.write(f"**Number of Rows in TX Sales Data:** {len(tx_sales_data)}")
    st.dataframe(tx_sales_data)
    st.download_button(
        label="📥 Download TX Sales Data",
        data=tx_sales_data.to_csv(index=False),
        file_name="tx_sales_data.csv",
        mime="text/csv",
    )

    # Matched Data from Pre-Assigned Seats
    st.markdown("### Matched Data From Pre-Assigned Club Level Seats")
    st.write(f"**Number of Matched Rows:** {len(matched_df)}")
    st.dataframe(matched_df)
    st.download_button(
        label="📥 Download Matched Data From Pre-Assigned Club Level Seats",
        data=matched_df.to_csv(index=False),
        file_name="matched_data_club_level.csv",
        mime="text/csv",
    )

    # Chart for Pre-Assigned Seats
    st.markdown("### Value Generated by Category (Pre-Assigned Seats)")
    if matched_df.empty:
        st.write("No data available to generate this chart.")
    else:
        fig, ax = plt.subplots()
        matched_df.groupby("category")["value_generated"].sum().plot(kind="bar", ax=ax)
        ax.set_title("Value Generated by Category")
        ax.set_xlabel("Category")
        ax.set_ylabel("Total Value Generated")
        st.pyplot(fig)

    # Matched Data from Hospitality Releases
    st.markdown("### Matched Data from Hospitality Ticket Releases")
    st.write(f"**Number of Matched Rows:** {len(matched_on_tx)}")
    st.dataframe(release_df)
    st.download_button(
        label="📥 Download Matched Data from Hospitality Ticket Releases",
        data=release_df.to_csv(index=False),
        file_name="matched_data_hosp_releases.csv",
        mime="text/csv",
    )

    # Chart for Hospitality Ticket Releases
    st.markdown("### Tickets Found on TX by Game")
    if matched_on_tx.empty:
        st.write("Sorry, no matching data found on Ticket Exchange from Hospitality Released Tickets.")
    else:
        fig, ax = plt.subplots()
        matched_on_tx.groupby("game_name")["ticket_sold_price"].sum().plot(kind="bar", ax=ax)
        ax.set_title("Tickets Found on TX by Game")
        ax.set_xlabel("Game")
        ax.set_ylabel("Total Tickets Sold Price")
        st.pyplot(fig)

if __name__ == "__main__":
    run_app()

