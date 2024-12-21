import requests
import json
import pandas as pd
from datetime import datetime, timedelta

# OAuth2 endpoint and credentials
TOKEN_URL = 'https://www.tjhub3.com/export_arsenal/token'
USERNAME = 'hospitality'
PASSWORD = 'OkMessageSectionType000!'
GRANT_TYPE = 'password'

# Global variables for token management
token_expiry_time = None
access_token = None


def get_access_token():
    """Retrieve a new access token using OAuth2 credentials."""
    global token_expiry_time, access_token
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'Username': USERNAME,
        'Password': PASSWORD,
        'grant_type': GRANT_TYPE
    }
    response = requests.post(TOKEN_URL, headers=headers, data=data, verify=True)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 3600)  # Default to 1 hour
        token_expiry_time = datetime.now() + timedelta(seconds=expires_in)
        return access_token
    else:
        raise Exception(f"Failed to retrieve access token: {response.status_code} - {response.text}")


def refresh_token_if_needed():
    """Refresh the access token if it has expired."""
    global token_expiry_time, access_token
    if token_expiry_time is None or datetime.now() >= token_expiry_time:
        access_token = get_access_token()


def parse_datetime(date_str):
    """Parse datetime string into a uniform format."""
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
    return date_str


def fetch_hospitality_data():
    """Fetch and process hospitality data."""
    global access_token

    refresh_token_if_needed()
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

    # Step 3: Process transactions and merge data
    final_data = []
    for event in event_list:
        event_id = event['Id']
        fixture_name = event['Name']

        transaction_url = f"https://www.tjhub3.com/export_arsenal/HospitalitySaleTransactions/List?EventId={event_id}"
        response = requests.get(transaction_url, headers=headers)
        if response.status_code == 200:
            transactions_data = response.json().get('Data', {}).get('HospitalitySaleTransactions', [])
            for transaction in transactions_data:
                record = {"Fixture Name": fixture_name, **event, **transaction}

                # Merge with account data
                guest_info = accounts_df[accounts_df['GuestId'] == transaction.get('GuestId')].to_dict(orient='records')
                if guest_info:
                    record.update({
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

                # Process TMSessionId for seating data
                if record.get('TMSessionId'):
                    tm_session_data = json.loads(record['TMSessionId'])
                    seats = tm_session_data.get('Seats', [])
                    for seat in seats:
                        seat_record = record.copy()
                        seat_record.update({
                            "Seats": record.get("Seats", seat.get("Seats")),
                            "PriceBandName": seat.get("PriceBandName"),
                            "Row": seat.get("Row"),
                            "Seat Number": seat.get("Number"),
                            "AreaName": seat.get("AreaName"),
                            "BlockId": seat.get("BlockId"),
                        })
                        final_data.append(seat_record)
                else:
                    final_data.append(record)
        else:
            print(f"Failed to retrieve transactions for EventId {event_id}: {response.status_code} - {response.text}")

    # Step 4: Convert to DataFrame
    final_df = pd.DataFrame(final_data)

    # Step 5: Filter columns
    filtered_columns_without_seats = [
        "Order Id", "KickOffEventStart", "EventCategory", "EventCompetition", "Fixture Name", "Type", "Package Name",
        "LocationName", "PackageId", "EventId", "GuestId", "Seats", "CRCCode", "Price", "Discount", "DiscountValue",
        "IsPaid", "PaymentTime", "CreatedOn", "CreatedBy", "TotalPrice", "GLCode", "SaleLocation", "CompanyName", "DOB",
        "GuestId", "Status", "IsSeasonal", "First Name", "Surname", "Email", "Country Code", "PostCode", "City"
    ]
    filtered_columns = [col for col in final_df.columns if col in filtered_columns_without_seats]
    filtered_df = final_df[filtered_columns].drop_duplicates()

    # Step 6: Save to Excel
    with pd.ExcelWriter('filtered_hosp_data2.xlsx') as writer:
        filtered_df.to_excel(writer, sheet_name='Without seating information', index=False)
        print("Filtered data saved to 'filtered_hosp_data2.xlsx'")

    return filtered_df


# Trigger data fetching
if __name__ == "__main__":
    try:
        hospitality_data = fetch_hospitality_data()
        print("Data successfully fetched and saved.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
