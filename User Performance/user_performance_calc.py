import pandas as pd

FILE_PATH = '/Users/cmunthali/Documents/PYTHON/SALES_REPORTS/PaymentsReport-3.xlsx'

# Function to load data from Excel
def load_data(file_path):
    """
    This function loads an excel file and returns a DataFrame
    """
    df = pd.read_excel(file_path, engine='openpyxl', skiprows=1) 
    return df

# Function to remove last row with grand total
def remove_grand_total_row(df):
    """
    Remove the last row if it contains the "Grand Total".
    """
    if 'Grand Total' in df.iloc[-1].values:
        df = df.iloc[:-1]
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



def flatten_competition_fixture(competition_fixture_df):
    """
    Flattens the competition_fixture_df by exploding the 'Fixture' column.
    """
    flattened_rows = []
    for index, row in competition_fixture_df.iterrows():
        fixtures = row['Fixture']
        for fixture in fixtures:
            new_row = row.copy()
            new_row['Fixture'] = fixture
            flattened_rows.append(new_row)
    return pd.DataFrame(flattened_rows)


def add_additional_info(df, total_packages_df, competition_fixture_df, total_budget_target_df):
    """
    Adds additional columns 'Budget Package Covers', 'Competition', and 'Budget Target' to the processed DataFrame 
    based on package name, fixture name, and event name.
    
    Parameters:
    df (DataFrame): The processed DataFrame containing fixture data.
    total_packages_df (DataFrame): The DataFrame containing package names and budget package covers.
    competition_fixture_df (DataFrame): The DataFrame containing competition and fixture lists.
    total_budget_target_df (DataFrame): The DataFrame containing fixture names and budget targets.
    
    Returns:
    DataFrame: The processed DataFrame with added columns for budget package covers, competition, and budget target.
    """
    # Flatten the competition fixture data
    flattened_competition_fixture_df = flatten_competition_fixture(competition_fixture_df)
    
    # Merge the dataframes on 'Package name'
    df = df.merge(total_packages_df, on='Package name', how='left')
    
    # Merge the dataframes on 'Event name' for competition
    df = df.merge(flattened_competition_fixture_df, left_on='Event name', right_on='Fixture', how='left')
    df.drop(columns=['Fixture'], inplace=True)
    
    # Merge the dataframes on 'Event name' for budget target
    df = df.merge(total_budget_target_df, left_on='Event name', right_on='Fixture name', how='left')
    df.drop(columns=['Fixture name'], inplace=True)
 # Move 'Budget Package Covers' to the position right after 'Package name'
    columns = df.columns.tolist()
    package_name_index = columns.index('Package name')
    columns.insert(package_name_index + 1, columns.pop(columns.index('Budget Package Covers')))
    df = df[columns]
    
    return df


# Function to split guest column
def split_guest_column(df):
    """
    Split "Guest" column into "Guest_name" and "Guest_email".
    """
    # Extract Guest_name
    df['Guest_name'] = df['Guest'].str.extract(r'^(.*?) \(')[0].str.strip()

    # Extract Guest_email
    df['Guest_email'] = df['Guest'].str.extract(r'\((.*?)\)')[0].str.strip()

    # Drop the original "Guest" column
    df.drop(columns=['Guest'], inplace=True)

    return df

def convert_date_format(df, column_name):
    """
    Ensure the datetime format of a specified column in a DataFrame.
    """
    if column_name in df.columns:
        df[column_name] = pd.to_datetime(df[column_name], errors='coerce')  # Convert and coerce errors
    return df


# Columns to keep
columns_to_keep = ['Order Id', 'Event name', 'Guest', 'Package name', 'Package GL code','Locations', 'Seats', 
                       'Price', 'Discount', 'Discount value', 'Total price', 'Paid', 'Payment time','Payment status', 
                       'Created by', 'Sale location']
    
   
    # Competition fixtures to add to DataFrame
competition_fixture = {
        'Season': ['Emirates Stadium Pre-Season 24-25', 'Emirates Stadium 24-25', 'Arsenal Women 24-25'],
        'Competition': ['Friendly & Emirates Cup', 'Premiere League', 'Womens Super League'],
        'Fixture': [
            ['Arsenal v Bayer 04 Leverkusen', 'Arsenal v Olympique Lyonnais'], 
            ['Arsenal v Wolves', 'Arsenal v Brighton', 'Arsenal v Leicester City', 'Arsenal v Southampton', 'Arsenal v Liverpool'],
            ['Arsenal Women v Everton Women', 'Arsenal Women v Manchester City Women']
        ]
    }
competition_fixture_df = pd.DataFrame(competition_fixture)
print("Competition Fixture DataFrame:")
print(competition_fixture_df.head(10))

    # Budget Package Covers column to add to DataFrame
total_budget_packages_data = {
        'Package name': ['Hero Experience', 'Inner Circle Package', 'The Heritage', 'N7 Executive Box', 'Foundry Legends', 'Woolwich Arsenal', 
                        'The Avenell', 'INTERNAL MBM BOX', 'N5 Executive Box', 'Club 1886', 'The Academy', 'Executive Box Package - Pre-Season', 'Diamond Package - Pre-Season',
                        'Foundry - Pre-Season', 'Club 1886 - Pre-Season', 'The Avenell - Pre-Season'],
        'Budget Package Covers': [4, 8, 8, 72, 78, 150, 10, 37, 36, 150, 232, 103, 168, 120, 150, 143]
    } 

total_budget_packages_df = pd.DataFrame(total_budget_packages_data)
print("\nTotal Budget Packages DataFrame:")
print(total_budget_packages_df.head(15))

    # Budget Target (based on 13M) column to add to DataFrame
total_budget_target_data = {
        'Fixture name': ['Arsenal v Bayer 04 Leverkusen', 'Arsenal v Olympique Lyonnais', 'Arsenal v Wolves', 'Arsenal v Brighton', 'Arsenal v Leicester City', 'Arsenal v Southampton', 'Arsenal v Liverpool',
                        'Arsenal Women v Everton Women', 'Arsenal Women v Manchester City Women'],
        'Budget Target': [113800, 113800, 469797, 319462, 469797, 390059, 558136, 0, 0]
    }

total_budget_target_df = pd.DataFrame(total_budget_target_data)
print("\nTotal Budget Target DataFrame:")
print(total_budget_target_df.head(10))
