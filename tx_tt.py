import pandas as pd

# Define the file paths
file_path = '/Users/cmunthali/Documents/PYTHON/APPS/sql_tx_tt.xlsx'
output_file = '/Users/cmunthali/Documents/PYTHON/APPS/updated_data2.xlsx'

# Load specific sheets
tx_sales_data = pd.read_excel(file_path, sheet_name="TX Sales Data")
seat_list = pd.read_excel(file_path, sheet_name="Seat List")

# Normalize column names to avoid case or whitespace issues
tx_sales_data.columns = tx_sales_data.columns.str.strip()
seat_list.columns = seat_list.columns.str.strip()

# Create a list to store matched rows
matched_data = []

# Update the CRC_Desc column in TX Sales Data based on matching Block, Row, and Seat
for index, row in tx_sales_data.iterrows():
    matching_row = seat_list[
        (seat_list["Block"] == row["Block"]) &
        (seat_list["Row"] == row["Row"]) &
        (seat_list["Seat"] == row["Seat"])
    ]
    if not matching_row.empty:
        # Update the CRC_Desc column with the matched value
        tx_sales_data.at[index, "CRC_Desc"] = matching_row["CRC_Desc"].values[0]
        matched_data.append(tx_sales_data.iloc[index])

# Convert matched data to a DataFrame
matched_df = pd.DataFrame(matched_data)

# Save the updated data to two sheets in the output file
with pd.ExcelWriter(output_file, mode="w", engine="openpyxl") as writer:
    # Write all data to the first sheet
    tx_sales_data.to_excel(writer, sheet_name="All Data", index=False)
    # Write matched data to the second sheet
    matched_df.to_excel(writer, sheet_name="Matched Data", index=False)

print(f"Updated data saved to {output_file}")
