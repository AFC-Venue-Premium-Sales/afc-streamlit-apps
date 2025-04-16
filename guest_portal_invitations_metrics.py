import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

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

def to_excel(df):
    """
    Convert a DataFrame to an Excel file in memory.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Unused Boxes')
    processed_data = output.getvalue()
    return processed_data

def run():
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
        # Sidebar filters in separate expanders
        with st.sidebar.expander("Select Location(s)", expanded=True):
            available_locations = sorted(df["Location"].dropna().unique())
            selected_locations = st.multiselect("Select Location(s)", options=available_locations, default=available_locations)
    
        with st.sidebar.expander("Select Event Name(s)", expanded=True):
            available_events = sorted(df["Event name"].dropna().unique())
            selected_events = st.multiselect("Select Event Name(s)", options=available_events, default=available_events)
    
        with st.sidebar.expander("Select Status(es)", expanded=True):
            available_statuses = sorted(df["Status"].dropna().unique())
            selected_statuses = st.multiselect("Select Status(es)", options=available_statuses, default=available_statuses)
    
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
        pending = total_invitations - confirmed - not_coming  # Alternatively, pending might come from the data
        
        # Calculate additional percentage metrics.
        confirmed_pct = (confirmed / total_invitations * 100) if total_invitations > 0 else 0
    
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
    
        # -------------
        # Load the preset executive boxes from the box_numbers file.
        try:
            box_df = pd.read_excel("box_numbers.xlsx")
            # Drop duplicate boxes to ensure unique preset boxes.
            box_df = box_df.drop_duplicates(subset=["Box Number"])
            preset_boxes = box_df["Box Number"].unique()
        except Exception as e:
            st.error(f"Error loading box numbers: {e}")
            box_df = pd.DataFrame(columns=["Box Number", "Box Owner"])
            preset_boxes = []
    
        # Identify boxes (from the preset) that haven't sent any invites.
        used_boxes = filtered_df["Location"].dropna().unique()
        not_used_df = box_df[~box_df["Box Number"].isin(used_boxes)]
        not_used_count = len(not_used_df)
    
        # Calculate Boxes Utilized from the preset.
        total_boxes = len(box_df)
        boxes_utilized = total_boxes - not_used_count
        boxes_utilized_pct = (boxes_utilized / total_boxes * 100) if total_boxes > 0 else 0
    
        st.subheader("High Level Metrics")
        # Create a grid of 8 columns for metrics.
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
        col1.metric("Total Invitations", total_invitations)
        col2.metric("Confirmed", confirmed)
        col3.metric("Not Coming", not_coming)
        col4.metric("Pending", pending)
        col5.metric("Boxes Not Utilized", not_used_count)
        col6.metric("Boxes Utilized", boxes_utilized)
        col7.metric("Confirmed %", f"{confirmed_pct:.1f}%")
        col8.metric("Boxes Utilized %", f"{boxes_utilized_pct:.1f}%")
    
        st.write(f"**Event with most invites:** {most_popular_event} ({most_event_invites})")
        st.write(f"**Executive Box with most invites (for top event):** {most_popular_location} ({top_event_location_count})")
        st.write(f"**Total invites for that Box:** {most_location_invites}")
    
        # Provide a download button for the unused boxes that includes Box Owner.
        if not_used_count > 0:
            excel_data = to_excel(not_used_df)
            st.download_button(label="Download Boxes Not Utilized",
                               data=excel_data,
                               file_name='not_utilized_boxes.xlsx',
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        else:
            st.info("All boxes have been utilized.")
    
        # ---------------------------
        # Bar Charts: Invitations by Event.
        st.write("### Invitations by Event")
        st.write("This chart shows the total number of invitations sent for each event.")
        st.bar_chart(event_counts)
    
        # ---------------------------
        # Bar Charts: Invitations by Location.
        st.write("### Invitations by Location")
        st.write("This chart displays the total number of invitations sent from each executive box (location).")
        st.bar_chart(location_counts)
    
        # ---------------------------
        # Time Series Analysis.
        if 'Date of sending' in filtered_df.columns:
            filtered_df['Date of sending'] = pd.to_datetime(filtered_df['Date of sending'], errors='coerce')
    
            frequency_option = st.sidebar.selectbox("Select Time Frequency", ["Daily", "Weekly", "Monthly"], index=1)
            freq_str = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[frequency_option]
    
            breakdown_option = st.sidebar.selectbox("Time Series Breakdown", ["Overall", "By Location", "By Event"], index=0)
    
            st.write("### Time Series Analysis")
            st.write("This chart shows how the invitations were sent over time. Adjust the time frequency and breakdown to view trends overall, by location, or by event.")
            if breakdown_option == "Overall":
                ts_inv = filtered_df.groupby(pd.Grouper(key='Date of sending', freq=freq_str)).size()
                ts_overall = pd.DataFrame({"Invitations Sent": ts_inv})
                st.line_chart(ts_overall)
            elif breakdown_option == "By Location":
                ts_inv = filtered_df.groupby([pd.Grouper(key='Date of sending', freq=freq_str), 'Location']).size().unstack(fill_value=0)
                st.write("#### Invitations Sent by Location")
                st.line_chart(ts_inv)
            else:
                ts_inv = filtered_df.groupby([pd.Grouper(key='Date of sending', freq=freq_str), 'Event name']).size().unstack(fill_value=0)
                st.write("#### Invitations Sent by Event")
                st.line_chart(ts_inv)
    else:
        st.write("Please upload a guest invitation Excel file from the sidebar.")

if __name__ == "__main__":
    run()
