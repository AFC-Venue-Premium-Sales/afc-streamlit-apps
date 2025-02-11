import requests
import json
import pandas as pd 
from datetime import datetime, timedelta

# OAuth2 endpoint and credentials
token_url = 'https://www.tjhub3.com/export_arsenal/token'
event_list_url = "https://www.tjhub3.com/export_arsenal/Events/List"
Username = 'hospitality'
Password = 'OkMessageSectionType000!'
grant_type = 'password'

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
        new_access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 3600)
        token_expiry_time = datetime.now() + timedelta(seconds=expires_in)
        return new_access_token
    else:
        print(f"Failed to retrieve access token: {response.status_code} - {response.text}")
        return None

def refresh_token_if_needed():
    global token_expiry_time, access_token
    if token_expiry_time is None or datetime.now() >= token_expiry_time:
        access_token = get_access_token()

def fetch_events():
    refresh_token_if_needed()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(event_list_url, headers=headers)
    
    if response.status_code == 200:
        events_data = response.json()
        return events_data.get('Data', {}).get('Events', [])
    else:
        print(f"Failed to retrieve event list: {response.status_code} - {response.text}")
        return []

def flatten_events(events):
    """
    Converts raw event JSON to a DataFrame with:
      - EventId, EventName, KickOffEventStart, EventCompetition, Gender, GoLiveDate
      - PackageId, PackageName, AvailableSeats, Price, Capacity
    """
    all_rows = []
    for event in events:
        event_id = event.get("Id")
        event_name = event.get("Name")
        kick_off = event.get("KickOffEventStart")
        competition = event.get("EventCompetition")
        gender = event.get("Gender")
        go_live_date = event.get("GoLiveDate")

        packages = event.get("HospitalityPackages", [])
        if not packages:
            continue

        for pkg in packages:
            package_id = pkg.get("PackageId")
            package_name = pkg.get("PackageName")
            price = pkg.get("Price")
            available_seats = pkg.get("AvailableSeats", None)

            locations = pkg.get("Locations", [])
            if not locations:
                all_rows.append({
                    "EventId": event_id,
                    "EventName": event_name,
                    "KickOffEventStart": kick_off,
                    "EventCompetition": competition,
                    "Gender": gender,
                    "GoLiveDate": go_live_date,
                    "PackageId": package_id,
                    "PackageName": package_name,
                    "AvailableSeats": available_seats,
                    "Price": price,
                    "Capacity": None
                })
            else:
                for loc in locations:
                    capacity = loc.get("Capacity")
                    all_rows.append({
                        "EventId": event_id,
                        "EventName": event_name,
                        "KickOffEventStart": kick_off,
                        "EventCompetition": competition,
                        "Gender": gender,
                        "GoLiveDate": go_live_date,
                        "PackageId": package_id,
                        "PackageName": package_name,
                        "AvailableSeats": available_seats,
                        "Price": price,
                        "Capacity": capacity
                    })

    df = pd.DataFrame(all_rows, columns=[
        "EventId",
        "EventName",
        "KickOffEventStart",
        "EventCompetition",
        "Gender",
        "GoLiveDate",
        "PackageId",
        "PackageName",
        "AvailableSeats",
        "Price",
        "Capacity"
    ])

    # Convert date/time columns to nicer string format
    if 'KickOffEventStart' in df.columns:
        df['KickOffEventStart'] = pd.to_datetime(df['KickOffEventStart'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    if 'GoLiveDate' in df.columns:
        df['GoLiveDate'] = pd.to_datetime(df['GoLiveDate'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    return df

def get_inventory_data(stock_file="/Users/cmunthali/Documents/PYTHON/APPS/stock_available.xlsx"):
    """
    1. Fetches event data from API
    2. Flattens into a DataFrame
    3. Reads 'stock_available.xlsx'
    4. Merges on columns ["EventName", "PackageName"] (you can add more if you want)
    5. Returns the merged DataFrame
    """
    global access_token
    # 1) Fetch
    access_token = get_access_token()
    raw_events = fetch_events()
    
    # 2) Flatten
    df_events = flatten_events(raw_events)

    # 3) Load stock file
    try:
        df_stock = pd.read_excel(stock_file)
    except FileNotFoundError:
        print(f"stock_available.xlsx not found at {stock_file}")
        return df_events  # Return at least the events if stock file not found

    # If the stock file has a "Package Name" column, rename to "PackageName"
    df_stock.rename(columns={"Package Name": "PackageName"}, inplace=True)

    # 4) Merge on ["EventName", "PackageName"]
    df_merged = pd.merge(
        df_events,
        df_stock,
        on=["EventName", "PackageName"],
        how="left",
        suffixes=("", "_y")
    )
    # Drop any duplicate columns from stock, if needed
    cols_to_drop = [col for col in df_merged.columns if col.endswith("_y")]
    df_merged.drop(cols_to_drop, axis=1, inplace=True)

    return df_merged
