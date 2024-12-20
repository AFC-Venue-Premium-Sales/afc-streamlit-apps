import requests
import json
import pandas as pd
from datetime import datetime, timedelta

# OAuth2 endpoint and credentials
token_url = 'https://www.tjhub3.com/export_arsenal/token'
Username = 'hospitality'
Password = 'OkMessageSectionType000!'
grant_type = 'password'

# Global variable for storing token expiry time
token_expiry_time = None

def get_access_token():
    global token_expiry_time
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'Username': Username,
        'Password': Password,
        'grant_type': grant_type
    }
    response = requests.post(token_url, headers=headers, data=data, verify=True)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 3600)  # Assuming 1 hour default if not provided
        token_expiry_time = datetime.now() + timedelta(seconds=expires_in)
        return access_token
    else:
        print(f"Failed to retrieve access token: {response.status_code} - {response.text}")
        return None

def refresh_token_if_needed():
    global token_expiry_time, access_token
    if token_expiry_time is None or datetime.now() >= token_expiry_time:
        access_token = get_access_token()

# Initial token retrieval
access_token = get_access_token()

# Set up the headers with the access token
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

# Step 1: Retrieve the list of accounts (Guests)
refresh_token_if_needed()
accounts_url = "https://www.tjhub3.com/export_arsenal/Accounts/List"
response = requests.get(accounts_url, headers=headers)

if response.status_code == 200:
    accounts_data = response.json().get('Data', {}).get('Guests', [])
    # Create a DataFrame for accounts to merge later
    accounts_df = pd.DataFrame(accounts_data)
else:
    print(f"Failed to retrieve accounts list: {response.status_code} - {response.text}")
    accounts_df = pd.DataFrame()

# Step 2: Retrieve the list of events
refresh_token_if_needed()
event_list_url = "https://www.tjhub3.com/export_arsenal/Events/List"
response = requests.get(event_list_url, headers=headers)

if response.status_code == 200:
    events_data = response.json()
    event_list = events_data.get('Data', {}).get('Events', [])
else:
    print(f"Failed to retrieve event list: {response.status_code} - {response.text}")
    event_list = []

# Step 3: Initialize an empty list to hold the merged data
merged_data = []

# Helper function to parse datetime with varying precision
def parse_datetime(date_str):
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",  # With microseconds
        "%Y-%m-%dT%H:%M:%S",      # Without microseconds
        "%Y-%m-%dT%H:%M:%S.%f%z", # With timezone and microseconds
        "%Y-%m-%dT%H:%M:%S%z",    # With timezone without microseconds
    ]
    
    for fmt in formats:
        try:
            # Parse the date string
            dt = datetime.strptime(date_str, fmt)
            # Format it as DD-MM-YYYY
            return dt.strftime("%d-%m-%Y %H:%M")
        except ValueError:
            continue
    return date_str  # Return the original string if no format matched

# Step 4: Retrieve transaction data for each event and merge with event details
for event in event_list:
    event_id = event['Id']
    fixture_name = event['Name']  # Renamed as Fixture Name

    refresh_token_if_needed()
    transaction_url = f"https://www.tjhub3.com/export_arsenal/HospitalitySaleTransactions/List?EventId={event_id}"
    response = requests.get(transaction_url, headers=headers)

    if response.status_code == 200:
        transactions_data = response.json().get('Data', {}).get('HospitalitySaleTransactions', [])

        for transaction in transactions_data:
            # Merge event details with transaction data
            merged_record = {"Fixture Name": fixture_name, **event, **transaction}

            # Merge with Accounts data based on GuestId
            guest_info = accounts_df[accounts_df['GuestId'] == transaction.get('GuestId')].to_dict(orient='records')
            if guest_info:
                merged_record.update({
                    "First Name": guest_info[0].get("FirstName", ""),
                    "Surname": guest_info[0].get("Surname", ""),
                    "Email": guest_info[0].get("Email", ""),
                    "Country Code": guest_info[0].get("CountryCode", ""),
                    "PostCode": guest_info[0].get("PostCode", ""),
                    "City": guest_info[0].get("City", ""),
                    "CompanyName": guest_info[0].get("CompanyName", ""),
                    "DOB": guest_info[0].get("DOB", ""),
                    "GuestId": guest_info[0].get("GuestId", ""),
                    "Status": guest_info[0].get("Status", ""),
                    "IsSeasonal": guest_info[0].get("IsSeasonal", ""),
                })
            
            merged_data.append(merged_record)
    else:
        print(f"Failed to retrieve transactions for EventId {event_id}: {response.status_code} - {response.text}")

# Step 5: Convert the merged data into a DataFrame
df = pd.DataFrame(merged_data)

# Step 6: Process data with seat details
final_data = []

for _, row in df.iterrows():
    if row['TMSessionId']:
        tm_session_data = json.loads(row['TMSessionId'])
        seats = tm_session_data.get('Seats', [])

        # Extract LocationName from Locations if it's a list of dictionaries
        if isinstance(row.get('Locations'), list) and row['Locations']:
            location_info = row['Locations'][0]
            location_name = location_info.get('LocationName', '')
        else:
            location_name = ''

        # Handle the extraction of the Package Name, especially for 'Platinum' under 'Seasonal Membership'
        package_name = row.get('Name')
        if row.get('Type') == 'Seasonal Membership' and 'Platinum' in row.get('Name', ''):
            package_name = 'Platinum'

        for seat in seats:
            seat_record = {
                "Order Id": row["Id"],
                "EventId": row.get("EventId"),
                "First Name": row.get("First Name"),
                "Surname": row.get("Surname"),
                "CompanyName": row.get("CompanyName"),
                "DOB": row.get("DOB"),
                "Email": row.get("Email"),
                "IsSeasonal": row.get("IsSeasonal"),
                "Country Code": row.get("Country Code"),
                "PostCode": row.get("PostCode"),
                "City": row.get("City"),
                "Status": row.get("Status"),
                "GLCode": row.get("GLCode"),
                "PackageId": row.get("PackageId"),
                "GuestId": row.get("GuestId"),
                "CRCCode": row.get("CRCCode"),
                "Fixture Name": row["Fixture Name"],
                "EventCategory": row.get("EventCategory"),
                "EventCompetition": row.get("EventCompetition"),
                "Type": row.get("Type"),
                "KickOffEventStart": parse_datetime(row.get("KickOffEventStart")),
                "Package Name": package_name,
                "LocationName": location_name,
                "Price": row.get("Price"),
                "Seats": seat.get("Seats"),
                "PriceBandName": seat.get("PriceBandName"),
                "Row": seat.get("Row"),
                "Seat Number": seat.get("Number"),
                "AreaName": seat.get("AreaName"),
                "BlockId": seat.get("BlockId"),
                "Discount": row.get("Discount"),
                "DiscountValue": row.get("DiscountValue"),
                "IsPaid": row.get("IsPaid"),
                "TotalPrice": row.get("TotalPrice"),
                "CreatedOn": parse_datetime(row.get("CreatedOn")),
                "PaymentTime": parse_datetime(row.get("PaymentTime")),
                "CreatedBy": row.get("CreatedBy"),
                "SaleLocation": row.get("SaleLocation"),
            }

            final_data.append(seat_record)
    else:
        # Handle rows without TMSessionId
        row['CreatedOn'] = parse_datetime(row.get("CreatedOn"))
        row['KickOffEventStart'] = parse_datetime(row.get("KickOffEventStart"))
        row['PaymentTime'] = parse_datetime(row.get("PaymentTime"))
        final_data.append(row)

# Convert final_data to a DataFrame
final_df = pd.DataFrame(final_data)

# Filter columns
filtered_columns_without_seat_data = [
    "Order Id", "KickOffEventStart", "EventCategory", "EventCompetition", "Fixture Name","Type", "Package Name", "LocationName", "PackageId", "EventId", "GuestId",
    "Seats", "CRCCode", "Price", "Discount","DiscountValue", "IsPaid", "PaymentTime", "CreatedOn", "CreatedBy", "TotalPrice", "GLCode", "SaleLocation","DiscountValue",
    "IsPaid", "PaymentTime", "CreatedOn", "CreatedBy", "TotalPrice", "GLCode", "SaleLocation", "CompanyName", "DOB",
    "GuestId", "Status", "IsSeasonal","First Name", "Surname", "Email", "Country Code", "PostCode", "City"
]

filtered_columns_without_seats = [col for col in final_df.columns if col in filtered_columns_without_seat_data]

# Filter the DataFrame
filtered_df_without_seats = final_df[filtered_columns_without_seats].drop_duplicates()


def fetch_hospitality_data():
    # Existing logic...

    if final_df.empty:
        print("🚨 Error: final_df is empty. Check your API integration.")
        return None

    # Check if filtered columns match
    filtered_columns_without_seats = [col for col in final_df.columns if col in filtered_columns_without_seat_data]
    if not filtered_columns_without_seats:
        print("🚨 Error: No matching columns in filtered_columns_without_seat_data.")
        print("Available Columns in final_df:", final_df.columns)
        return None

    # Generate the filtered DataFrame
    filtered_df_without_seats = final_df[filtered_columns_without_seats].drop_duplicates()

    # Return the filtered DataFrame
    print("✅ Filtered DataFrame created successfully.")
    return filtered_df_without_seats



# # Save the DataFrame
# with pd.ExcelWriter('filtered_hosp_data2.xlsx') as writer:
#     filtered_df_without_seats.to_excel(writer, sheet_name='Without seating information', index=False)
#     print(f'filtered_hosp_data2 saved')





# # Only select columns that exist in the DataFrame
# filtered_columns_without_seats = [col for col in final_df.columns if col in filtered_columns_without_seat_data]
# filtered_df_without_seats = final_df[filtered_columns_without_seats].drop_duplicates()

# # Convert filtered_columns_without_seat_data to a DataFrame if it's a list
# if isinstance(filtered_columns_without_seat_data, list):
#     filtered_columns_without_seat_data = pd.DataFrame(filtered_columns_without_seat_data)

# # Only select columns that exist in the DataFrame
# filtered_columns_without_seats = [col for col in final_df.columns if col in filtered_columns_without_seat_data.columns]
# filtered_df_without_seats = final_df[filtered_columns_without_seats].drop_duplicates()


# # Only select columns that exist in the DataFrame
# filtered_columns_with_seats = [col for col in final_df.columns if col in filtered_columns_with_seat_data]
# filtered_df_with_seats = final_df[filtered_columns_with_seats]

# # Save the filtered DataFrames into separate tabs of an Excel file
# with pd.ExcelWriter('filtered_hosp_data.xlsx') as writer:
#     filtered_df_without_seats.to_excel(writer, sheet_name='Without seat data', index=False)
#     filtered_df_with_seats.to_excel(writer, sheet_name='With seat data', index=False)
