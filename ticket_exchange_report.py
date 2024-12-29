import streamlit as st
import pandas as pd
import logging
from io import StringIO

# Configure logging
log_stream = StringIO()
logging.basicConfig(stream=log_stream, level=logging.INFO, format="%(asctime)s - %(message)s")

# Helper function to adjust block names
def adjust_block(block):
    if isinstance(block, str) and block.startswith("C") and block[1:].isdigit():
        block_number = int(block[1:])
        return f"{block_number} Club Level"
    elif isinstance(block, str) and block.isdigit():
        block_number = int(block)
        return f"{block_number} Club Level"
    return block

# Preprocess data
def preprocess_data(df):
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    df.drop_duplicates(inplace=True)
    return df

# Load and preprocess Seat List and Game Category
@st.cache_data
def load_seat_list_and_game_category(path):
    try:
        seat_list = pd.read_excel(path, sheet_name="Seat List")
        seat_list.columns = seat_list.columns.str.strip().str.lower()
        seat_list["block"] = seat_list["block"].apply(adjust_block)
        seat_list = preprocess_data(seat_list)

        game_category = pd.read_excel(path, sheet_name="Game Category")
        game_category.columns = game_category.columns.str.strip().str.lower()
        game_category = preprocess_data(game_category)

        return seat_list, game_category
    except Exception as e:
        st.error(f"Error loading Seat List and Game Category: {e}")
        return None, None

# Process From Hosp data
@st.cache_data
def process_from_hosp(from_hosp_file):
    try:
        from_hosp = pd.read_excel(from_hosp_file, sheet_name=None)
        from_hosp_combined = pd.concat(from_hosp.values(), ignore_index=True)
        from_hosp_combined.columns = from_hosp_combined.columns.str.strip().str.lower()
        from_hosp_combined = preprocess_data(from_hosp_combined)
        from_hosp_combined["row"] = pd.to_numeric(from_hosp_combined["row"], errors="coerce")
        from_hosp_combined["seat"] = pd.to_numeric(from_hosp_combined["seat"], errors="coerce")
        return from_hosp_combined
    except Exception as e:
        st.error(f"Error processing From Hosp data: {e}")
        return None

# Process TX Sales data
@st.cache_data
def process_tx_sales(tx_sales_file):
    try:
        tx_sales_data = pd.read_excel(tx_sales_file, sheet_name=1)
        tx_sales_data.columns = tx_sales_data.columns.str.strip().str.lower()
        tx_sales_data = preprocess_data(tx_sales_data)
        tx_sales_data["block_lower"] = tx_sales_data["block"].str.lower()
        tx_sales_data["is_club_level"] = tx_sales_data["block_lower"].str.contains("club level", na=False)
        return tx_sales_data
    except Exception as e:
        st.error(f"Error processing TX Sales data: {e}")
        return None

# Combine and classify matches
def classify_matches(tx_sales_data, seat_list, from_hosp_combined):
    # Match TX Sales with predefined seats
    tx_sales_with_seat_list = tx_sales_data.merge(seat_list, how="left", on=["block", "row", "seat"], indicator=True)
    tx_sales_with_seat_list["matched_predefined_seats"] = tx_sales_with_seat_list["_merge"] == "both"
    tx_sales_with_seat_list.drop(columns=["_merge"], inplace=True)

    # Match TX Sales with From Hosp
    tx_sales_with_hosp = tx_sales_data.merge(from_hosp_combined, how="left", on=["game_name", "block", "row", "seat"], indicator=True)
    tx_sales_with_hosp["matched_from_hosp"] = tx_sales_with_hosp["_merge"] == "both"
    tx_sales_with_hosp.drop(columns=["_merge"], inplace=True)

    # Combine matches
    combined_matches = tx_sales_with_seat_list.merge(tx_sales_with_hosp, how="outer", on=["game_name", "block", "row", "seat"], suffixes=("_seat_list", "_from_hosp"))

    # Add club level only flag
    combined_matches = combined_matches.merge(
        tx_sales_data[["game_name", "block", "row", "seat", "is_club_level"]],
        how="left",
        on=["game_name", "block", "row", "seat"]
    )

    # Classify rows based on match source
    def classify_source(row):
        if row["matched_predefined_seats"] and row["matched_from_hosp"]:
            return "Both"
        elif row["matched_predefined_seats"]:
            return "Predefined Only"
        elif row["matched_from_hosp"]:
            return "From Hosp Only"
        elif row["is_club_level"]:
            return "Club Level Only"
        else:
            return "Neither"

    combined_matches["match_source"] = combined_matches.apply(classify_source, axis=1)
    return combined_matches

# Main Streamlit app
def run_app():
    st.title("🏟️ Hospitality Seat Matching App")

    st.sidebar.title("File Uploads")
    seat_list_game_cat_path = "seat_list_game_cat.xlsx"
    tx_sales_file = st.sidebar.file_uploader("Upload TX Sales File", type=["xlsx"])
    from_hosp_file = st.sidebar.file_uploader("Upload From Hosp File", type=["xlsx"])

    with st.spinner("Loading Seat List and Game Category..."):
        seat_list, game_category = load_seat_list_and_game_category(seat_list_game_cat_path)
        if seat_list is None or game_category is None:
            return

    if not tx_sales_file or not from_hosp_file:
        st.sidebar.info("Please upload all required files to proceed.")
        return

    with st.spinner("Processing files..."):
        tx_sales_data = process_tx_sales(tx_sales_file)
        from_hosp_combined = process_from_hosp(from_hosp_file)
        if tx_sales_data is None or from_hosp_combined is None:
            return

        combined_matches = classify_matches(tx_sales_data, seat_list, from_hosp_combined)

    # Separate outputs
    predefined_only = combined_matches[combined_matches["match_source"] == "Predefined Only"]
    from_hosp_only = combined_matches[combined_matches["match_source"] == "From Hosp Only"]
    both_matches = combined_matches[combined_matches["match_source"] == "Both"]
    club_level_only = combined_matches[combined_matches["match_source"] == "Club Level Only"]
    neither_matches = combined_matches[combined_matches["match_source"] == "Neither"]

    # Display results
    st.markdown("### Predefined Club Level Seats Only")
    st.dataframe(predefined_only.head(100))
    st.download_button("Download Predefined Only", predefined_only.to_csv(index=False), "predefined_only.csv")

    st.markdown("### From Hosp Seats Only")
    st.dataframe(from_hosp_only.head(100))
    st.download_button("Download From Hosp Only", from_hosp_only.to_csv(index=False), "from_hosp_only.csv")

    st.markdown("### Both (Predefined + From Hosp)")
    st.dataframe(both_matches.head(100))
    st.download_button("Download Both Matches", both_matches.to_csv(index=False), "both_matches.csv")

    st.markdown("### Club Level Seats Only (Not Predefined)")
    st.dataframe(club_level_only.head(100))
    st.download_button("Download Club Level Only", club_level_only.to_csv(index=False), "club_level_only.csv")

    st.markdown("### Neither Matches")
    st.dataframe(neither_matches.head(100))
    st.download_button("Download Neither Matches", neither_matches.to_csv(index=False), "neither_matches.csv")

if __name__ == "__main__":
    run_app()
