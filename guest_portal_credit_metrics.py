import pandas as pd
import re

def preprocess_guests_account_report(file_path, skiprows=4):
    """
    Reads the 'Guests account report' Excel file, cleans it up, and returns a pandas DataFrame.
    Adjust skiprows if the header row is not in the expected position.
    """
    # 1. Read the raw Excel file while skipping the first few rows.
    df_raw = pd.read_excel(file_path, header=None, skiprows=skiprows)
    
    # Debug: Check the first row (which should be the header row)
    print("DEBUG - First row of data (should be headers):", df_raw.iloc[0].tolist())
    
    # 2. Set the first row of the remaining data as the header, and then drop that row from the data.
    df_raw.columns = df_raw.iloc[0]
    df_raw = df_raw.iloc[1:, :]
    
    # 3. Clean and normalize header names:
    #    - Convert to string.
    #    - Replace newline characters with a space.
    #    - Strip leading/trailing whitespace.
    df_raw.columns = df_raw.columns.astype(str).str.replace("\n", " ").str.strip().str.lower()
    
    # 4. Drop columns whose header is literally "nan".
    df_raw = df_raw.loc[:, df_raw.columns != "nan"]
    
    # Debug: Print the actual column names.
    print("DEBUG - Actual columns after cleaning:", df_raw.columns.tolist())
    
    # 5. Rename columns – adjust keys according to the cleaned (lowercase) header.
    df_raw.rename(columns={
        "guest name": "GuestName",
        "box names": "BoxNames",
        "current credit (£)": "CurrentCredit",
        "last activity  (invoice/deposit)": "LastActivity"
    }, inplace=True)

    # 6. Drop rows that are fully empty.
    df_raw.dropna(how='all', inplace=True)
    
    # 7. Remove duplicate rows.
    df_raw.drop_duplicates(inplace=True)
    
    # 8. Remove any 'Total' rows.
    df_raw = df_raw[~df_raw["GuestName"].str.contains("Total", na=False)]
    
    # 9. Remove rows with '#VALUE!' in GuestName.
    df_raw = df_raw[~df_raw["GuestName"].str.contains("#VALUE!", na=False)]
    
    # 10. Convert "CurrentCredit": Remove the currency symbol and convert to numeric.
    df_raw["CurrentCredit"] = df_raw["CurrentCredit"].replace(r"£", "", regex=True)
    df_raw["CurrentCredit"] = pd.to_numeric(df_raw["CurrentCredit"], errors='coerce')
    
    # Format the numeric value to a string with a £ symbol and two decimals.
    df_raw["CurrentCredit"] = df_raw["CurrentCredit"].apply(lambda x: f"£{x:,.2f}" if pd.notnull(x) else "")
    
    # 11. Convert "LastActivity" to datetime.
    df_raw["LastActivity"] = pd.to_datetime(df_raw["LastActivity"], errors='coerce')
    
    # 12. Optionally, if GuestName contains both a name and email in parentheses, split them.
    pattern = re.compile(r"^[\-\.\s]*(?P<name>[^(]+)\((?P<email>[^)]+)\)$")
    def parse_name_email(value):
        if not isinstance(value, str):
            return value, None
        value = value.strip()
        m = pattern.match(value)
        if m:
            return m.group("name").strip(), m.group("email").strip()
        else:
            return value, None
    df_raw["GuestName"], df_raw["GuestEmail"] = zip(*df_raw["GuestName"].apply(parse_name_email))
    
    # 13. *** New Code: Extract date range from BoxNames ***
    #    For example: "Executive Box 148 (12/08/2024 - 31/05/2025)"
    #    We want to extract "Executive Box 148" into BoxNames,
    #    "12/08/2024" into ValidFrom, and "31/05/2025" into ValidTo.
    pattern_box = re.compile(r"^(?P<box>.*?)\s*\(\s*(?P<from>\d{2}/\d{2}/\d{4})\s*-\s*(?P<to>\d{2}/\d{2}/\d{4})\s*\)$")
    
    def parse_box(value):
        if not isinstance(value, str):
            return value, None, None
        value = value.strip()
        m = pattern_box.match(value)
        if m:
            box_name = m.group("box").strip()
            valid_from = m.group("from").strip()
            valid_to = m.group("to").strip()
            return box_name, valid_from, valid_to
        else:
            return value, None, None
    
    df_raw["BoxNames"], df_raw["ValidFrom"], df_raw["ValidTo"] = zip(*df_raw["BoxNames"].apply(parse_box))
    
    # 14. Reorder columns to the desired order.
    desired_columns = ["GuestName", "GuestEmail", "BoxNames", "ValidFrom", "ValidTo", "CurrentCredit", "LastActivity"]
    df_raw = df_raw[[col for col in desired_columns if col in df_raw.columns]]
    
    return df_raw

if __name__ == "__main__":
    cleaned_df = preprocess_guests_account_report("/Users/cmunthali/Documents/PYTHON/APPS/GuestsAccountBalance-2.xls", skiprows=4)
    print(cleaned_df.head(20))
    # Save the DataFrame locally as an Excel file
    cleaned_df.to_excel("Cleaned_GuestsAccountBalance.xlsx", index=False)
