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
access_token = None
token_expiry_time = None

def get_access_token():
    global token_expiry_time, access_token
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
        raise Exception(f"Failed to retrieve access token: {response.status_code} - {response.text}")

def refresh_token_if_needed():
    global token_expiry_time, access_token
    if token_expiry_time is None or datetime.now() >= token_expiry_time:
        access_token = get_access_token()

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
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d-%m-%Y %H:%M")
        except ValueError:
            continue
    return date_str  # Return the original string if no format matched

def fetch_hospitality_data():
    """Fetch and process hospitality data."""
    global token_expiry_time, access_token

    # Refresh token if needed
    refresh_token_if_needed()

    # Set headers
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Step 1: Retrieve accounts (Guests)
    accounts_url = "https://www.tjhub3.com/export_arsenal/Accounts/List"
    response = requests.get(accounts_url, headers=headers)
    if response.status_code == 200:
        accounts_data = response.json().get('Data', {}).get('Guests', [])
        accounts_df = pd.DataFrame(accounts_data)
    else:
        raise Exception(f"Failed to retrieve accounts list: {response.status_code} - {response.text}")

    # Step 2: Retrieve events
    event_list_url = "https://www.tjhub3.com/export_arsenal/Events/List"
    response = requests.get(event_list_url, headers=headers)
    if response.status_code == 200:
        events_data = response.json()
        event_list = events_data.get('Data', {}).get('Events', [])
    else:
        raise Exception(f"Failed to retrieve event list: {response.status_code} - {response.text}")

    # Step 3: Initialize merged data
    merged_data = []

    # Step 4: Retrieve transaction data for each event and merge with event details
    for event in event_list:
        event_id = event['Id']
        fixture_name = event['Name']

        transaction_url = f"https://www.tjhub3.com/export_arsenal/HospitalitySaleTransactions/List?EventId={event_id}"
        response = requests.get(transaction_url, headers=headers)
        if response.status_code == 200:
            transactions_data = response.json().get('Data', {}).get('HospitalitySaleTransactions', [])
            for transaction in transactions_data:
                # Merge event and transaction data
                merged_record = {"Fixture Name": fixture_name, **event, **transaction}

                # Merge with account data
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

                if transaction.get('TMSessionId'):
                    tm_session_data = json.loads(transaction['TMSessionId'])
                    seats = tm_session_data.get('Seats', [])

                    for seat in seats:
                        seat_record = {
                            "Order Id": transaction["Id"],
                            "EventId": event_id,
                            "First Name": guest_info[0].get("FirstName", "") if guest_info else "",
                            "Surname": guest_info[0].get("Surname", "") if guest_info else "",
                            "CompanyName": guest_info[0].get("CompanyName", "") if guest_info else "",
                            "DOB": guest_info[0].get("DOB", "") if guest_info else "",
                            "Email": guest_info[0].get("Email", "") if guest_info else "",
                            "IsSeasonal": guest_info[0].get("IsSeasonal", "") if guest_info else "",
                            "Country Code": guest_info[0].get("CountryCode", "") if guest_info else "",
                            "PostCode": guest_info[0].get("PostCode", "") if guest_info else "",
                            "City": guest_info[0].get("City", "") if guest_info else "",
                            "Status": guest_info[0].get("Status", "") if guest_info else "",
                            "GLCode": transaction.get("GLCode"),
                            "PackageId": transaction.get("PackageId"),
                            "GuestId": transaction.get("GuestId"),
                            "CRCCode": transaction.get("CRCCode"),
                            "Fixture Name": fixture_name,
                            "EventCategory": event.get("EventCategory"),
                            "EventCompetition": event.get("EventCompetition"),
                            "Type": event.get("Type"),
                            "KickOffEventStart": parse_datetime(event.get("KickOffEventStart")),
                            "Package Name": transaction.get("Name"),
                            "LocationName": transaction.get("LocationName"),
                            "Price": transaction.get("Price"),
                            "Seats": seat.get("Seats"),
                            "PriceBandName": seat.get("PriceBandName"),
                            "Row": seat.get("Row"),
                            "Seat Number": seat.get("Number"),
                            "AreaName": seat.get("AreaName"),
                            "BlockId": seat.get("BlockId"),
                            "Discount": transaction.get("Discount"),
                            "DiscountValue": transaction.get("DiscountValue"),
                            "IsPaid": transaction.get("IsPaid"),
                            "TotalPrice": transaction.get("TotalPrice"),
                            "CreatedOn": parse_datetime(transaction.get("CreatedOn")),
                            "PaymentTime": parse_datetime(transaction.get("PaymentTime")),
                            "CreatedBy": transaction.get("CreatedBy"),
                            "SaleLocation": transaction.get("SaleLocation"),
                        }
                        merged_data.append(seat_record)
                else:
                    merged_data.append(merged_record)
        else:
            print(f"Failed to retrieve transactions for EventId {event_id}: {response.status_code} - {response.text}")

    # Convert merged data to DataFrame
    df = pd.DataFrame(merged_data)

    # Save the merged DataFrame
    df.to_excel('merged_events_transactions1.xlsx', index=False)
    print("Initial merged events transactions saved.")

    return df

# Main script continues with filtering and exporting data
try:
    df = fetch_hospitality_data()
    print("Data fetched successfully.")
except Exception as e:
    print(f"Error fetching data: {e}")

# Example of filtering and saving final DataFrame
filtered_columns_without_seat_data = [
    "Order Id", "KickOffEventStart", "EventCategory", "EventCompetition", "Fixture Name", "Type", "Package Name",
    "LocationName", "PackageId", "EventId", "GuestId", "Seats", "CRCCode", "Price", "Discount", "DiscountValue",
    "IsPaid", "PaymentTime", "CreatedOn", "CreatedBy", "TotalPrice", "GLCode", "SaleLocation", "CompanyName", "DOB",
    "GuestId", "Status", "IsSeasonal", "First Name", "Surname", "Email", "Country Code", "PostCode", "City"
]

filtered_columns_with_seat_data = [
    "Order Id", "KickOffEventStart", "EventCategory", "EventCompetition", "Fixture Name", "Type", "Package Name",
    "LocationName", "PackageId", "EventId", "GuestId", "Seats", "AreaName", "PriceBandName", "Seat Number", "Row",
    "BlockId", "CRCCode", "Price", "Discount", "DiscountValue", "IsPaid", "PaymentTime", "CreatedOn", "CreatedBy",
    "TotalPrice", "GLCode", "SaleLocation", "First Name", "Surname", "Email", "Country Code", "PostCode"
]

filtered_df_without_seats = df[[col for col in filtered_columns_without_seat_data if col in df.columns]].drop_duplicates()

# Save filtered DataFrame to Excel
with pd.ExcelWriter('filtered_hosp_data2.xlsx') as writer:
    filtered_df_without_seats.to_excel(writer, sheet_name='Without seating information', index=False)
    print("Filtered data saved successfully.")
