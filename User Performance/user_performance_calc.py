import pandas as pd

FILE_PATH = '/Users/cmunthali/Documents/PYTHON/SALES_REPORTS/PaymentsReport-3.xlsx'

# Function to load data from Excel
def load_data(file_path):
    """
    This function loads an excel file and returns a DataFrame
    """
    df = pd.read_excel(file_path, engine='openpyxl', skiprows=1) 
    return df


# Columns to keep on sales summary report
# columns_to_keep = ['Package name', 'Available', 'Sold', 'Seats sold', 'Revenue Generated']

# Function to filter DataFrame to keep specified columns
def filter_columns(df, columns_to_keep):
    """
    Filter DataFrame df to keep only the columns listed in columns_to_keep.
    """
    return df[columns_to_keep]

# Function to clean and convert columns to numeric format
def clean_numeric_columns(df, columns_to_clean):
    """
    Clean specified columns in DataFrame df by removing pound signs and commas,
    then convert them to numeric format.
    """
    for col in columns_to_clean:
        df[col] = df[col].str.strip()
        # df[col] = pd.to_numeric(df[col].str.replace('£', '').str.replace(',', ''))
        df[col] = pd.to_numeric(df[col].str.replace('£', '').str.replace(',', ''), errors='coerce')

    return df


def clean_numeric_columns_on_guest_report(df, columns_to_clean):
    """
    This function cleans numeric columns by stripping whitespace from the values.

    Args:
        df (pd.DataFrame): The input dataframe.
        columns_to_clean (list): A list of column names to clean.

    Returns:
        pd.DataFrame: The cleaned dataframe with whitespace stripped from specified columns.
    """
    for col in columns_to_clean:
        # Convert column to string before stripping whitespace
        df[col] = df[col].astype(str).str.strip()
    return df

# Function to split created_by column
def split_created_by_column(df):
    """
    Split "Created by" column into "Created_by" (name) and "Created_on" (date).
    """
    # Extract Created_by (name)
    # Extract text before the first '(' and strip spaces
    df['Created_by'] = df['Created by'].str.extract(r'^([^\(]*)')[0].str.strip() 

    # Extract Created_on (date) and convert to datetime
    df['Created_on'] = pd.to_datetime(df['Created by'].str.extract(r'\((.*?)\)')[0], format='%d/%m/%Y %H:%M:%S')

    # Drop the original "Created by" column
    df.drop(columns=['Created by'], inplace=True)

    return df



