import streamlit as st
import pandas as pd
import altair as alt

def preprocess_file(uploaded_file):
    # Read the Excel file without header.
    df_raw = pd.read_excel(uploaded_file, header=None)
    
    # Remove the first 3 rows containing extraneous information.
    df_raw = df_raw.iloc[3:, :]
    
    # Set the next row as header and remove it from the data.
    df_raw.columns = df_raw.iloc[0]
    df_raw = df_raw.iloc[1:, :]
    
    # Drop 'Unnamed: 1' if it's completely empty.
    if 'Unnamed: 1' in df_raw.columns and df_raw['Unnamed: 1'].isna().all():
        df_raw.drop(columns=['Unnamed: 1'], inplace=True)
    
    # Combine "Event name" and "Unnamed: 3" (if applicable), then drop 'Unnamed: 3'.
    if 'Unnamed: 3' in df_raw.columns and 'Event name' in df_raw.columns:
        df_raw['Event name'] = df_raw['Event name'].combine_first(df_raw['Unnamed: 3'])
        df_raw.drop(columns=['Unnamed: 3'], inplace=True)
    
    # Drop 'Unnamed: 10' if it's completely empty.
    if 'Unnamed: 10' in df_raw.columns and df_raw['Unnamed: 10'].isna().all():
        df_raw.drop(columns=['Unnamed: 10'], inplace=True)
    
    # Drop rows that are entirely empty.
    df_raw.dropna(how='all', inplace=True)
    
    # Forward-fill the 'Guest name' column.
    if 'Guest name' in df_raw.columns:
        df_raw['Guest name'] = df_raw['Guest name'].ffill()
    
    # Remove duplicate rows.
    df_raw.drop_duplicates(inplace=True)
    
    # Drop rows where all key columns (except 'Guest name') are empty.
    required_cols = [
        'Event name', 'Location', 'Invitation Name', 'Email', 
        'Date of sending', 'Status'
    ]
    df_raw = df_raw.dropna(subset=required_cols, how='all')
    
    # Rename columns for clarity.
    df_raw.rename(columns={"Guest name": "GuestName"}, inplace=True)
    
    # Drop columns that are entirely empty.
    df_raw = df_raw.dropna(axis=1, how='all')
    
    return df_raw

def run():
    # Set page configuration to wide mode.
    # st.set_page_config(page_title="Guest Invitations Dashboard", layout="wide")
    
    # Sidebar: File uploader.
    st.sidebar.header("Upload Data")
    uploaded_file = st.sidebar.file_uploader("Upload Guest Invitation Excel File", type=["xls", "xlsx"])
    
    if uploaded_file is not None:
        # Preprocess the file.
        df = preprocess_file(uploaded_file)
    
        # Reorder columns so that "Location" is the first column.
        if "Location" in df.columns:
            col_order = ["Location"] + [col for col in df.columns if col != "Location"]
            df = df[col_order]
    
        with st.expander("View Processed Data"):
            st.dataframe(df)
    
        # ---------------------------
        # Sidebar: Filters for Location, Event name, and Status.
        st.sidebar.header("Filters")
        available_locations = sorted(df["Location"].dropna().unique())
        selected_locations = st.sidebar.multiselect("Select Location(s)", options=available_locations, default=available_locations)
    
        available_events = sorted(df["Event name"].dropna().unique())
        selected_events = st.sidebar.multiselect("Select Event Name(s)", options=available_events, default=available_events)
    
        available_statuses = sorted(df["Status"].dropna().unique())
        selected_statuses = st.sidebar.multiselect("Select Status(es)", options=available_statuses, default=available_statuses)
    
        # Filter the dataframe based on selected filters.
        filtered_df = df[
            (df["Location"].isin(selected_locations)) &
            (df["Event name"].isin(selected_events)) &
            (df["Status"].isin(selected_statuses))
        ]
    
        with st.expander("View Filtered Data"):
            st.dataframe(filtered_df)
    
        # ---------------------------
        # Key Metrics Cards.
        total_invitations = len(filtered_df)
        status_counts = filtered_df['Status'].value_counts().to_dict()
        confirmed = status_counts.get('Confirmed', 0)
        not_coming = status_counts.get('Not Coming', 0)
        pending = total_invitations - confirmed - not_coming
    
        event_counts = filtered_df['Event name'].value_counts()
        most_popular_event = event_counts.idxmax() if not event_counts.empty else "N/A"
        most_event_invites = event_counts.max() if not event_counts.empty else 0
    
        location_counts = filtered_df['Location'].value_counts()
        most_popular_location = location_counts.idxmax() if not location_counts.empty else "N/A"
        most_location_invites = location_counts.max() if not location_counts.empty else 0
    
        # Calculate the count for the most popular location for the top event.
        top_event_location_count = len(
            filtered_df[
                (filtered_df["Event name"] == most_popular_event) &
                (filtered_df["Location"] == most_popular_location)
            ]
        )
    
        st.subheader("High Level Metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Invitations", total_invitations)
        col2.metric("Confirmed", confirmed)
        col3.metric("Not Coming", not_coming)
        col4.metric("Pending", pending)
    
        st.write(f"**Event with most invites:** {most_popular_event} ({most_event_invites})")
        st.write(f"**Executive Box with most invites (for top event):** {most_popular_location} ({top_event_location_count})")
        st.write(f"**Total invites for that Box:** {most_location_invites}")
    
        # ---------------------------
        # Bar Charts: Invitations by Event.
        st.write("### Invitations by Event")
        st.write("This chart shows the total number of invitations sent for each event. Each bar represents an event and its height indicates the number of invitations sent for that event.")
        st.bar_chart(event_counts)
    
        # ---------------------------
        # Bar Charts: Invitations by Location.
        st.write("### Invitations by Location")
        st.write("This chart displays the total number of invitations sent from each executive box (location). Each bar represents an executive box and its height shows the number of invitations sent from that box.")
        st.bar_chart(location_counts)
    
        # ---------------------------
        # Time Series Analysis
        if 'Date of sending' in filtered_df.columns:
            # Convert "Date of sending" to datetime.
            filtered_df['Date of sending'] = pd.to_datetime(filtered_df['Date of sending'], errors='coerce')
    
            frequency_option = st.sidebar.selectbox("Select Time Frequency", ["Daily", "Weekly", "Monthly"], index=1)
            freq_str = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[frequency_option]
    
            breakdown_option = st.sidebar.selectbox("Time Series Breakdown", ["Overall", "By Location", "By Event"], index=0)
    
            st.write("### Time Series Analysis")
            st.write("This chart shows how invitations were sent over time. You can change the time frequency (daily, weekly, monthly) and break down the data overall, by location, or by event to see patterns and trends in invitation activity.")
            if breakdown_option == "Overall":
                # Overall: plot total invitations sent over time.
                ts_inv = filtered_df.groupby(pd.Grouper(key='Date of sending', freq=freq_str)).size()
                ts_overall = pd.DataFrame({"Invitations Sent": ts_inv})
                st.line_chart(ts_overall)
            elif breakdown_option == "By Location":
                ts_inv = filtered_df.groupby([pd.Grouper(key='Date of sending', freq=freq_str), 'Location']).size().unstack(fill_value=0)
                st.write("#### Invitations Sent by Location")
                st.line_chart(ts_inv)
            else:  # By Event
                ts_inv = filtered_df.groupby([pd.Grouper(key='Date of sending', freq=freq_str), 'Event name']).size().unstack(fill_value=0)
                st.write("#### Invitations Sent by Event")
                st.line_chart(ts_inv)
    else:
        st.write("Please upload a guest invitation Excel file from the sidebar.")

if __name__ == "__main__":
    run()
