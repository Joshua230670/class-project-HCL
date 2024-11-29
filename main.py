import streamlit as st
from datetime import date
import pandas as pd
import matplotlib.pyplot as plt
import requests
from dotenv import load_dotenv
import os
import pydeck as pdk

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")

# Inject custom styles
st.markdown(
    """
    <style>
    /* Page background */
    .main {
        background-color: #001f3f;
        color: white;
    }
    /* Sidebar background */
    .css-1d391kg {
        background-color: #005f99;
    }
    /* Widget labels */
    .css-145kmo2, .css-16huue1 {
        color: white;
    }
    /* Table styling */
    .stDataFrame {
        color: black;
        background-color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html = True,
)


# Fetch data function
def observed_US():
    url = "https://api.ebird.org/v2/data/obs/US/recent"
    response = requests.get(url, headers={'X-eBirdApiToken': API_KEY})
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            st.error("Error decoding API response.")
            return []
    else:
        st.error(f"Error: Received status code {response.status_code}")
        return []


# Fetch bird observation data
species_dict = observed_US()
species_list = [i["comName"] for i in species_dict]
species_list.insert(0, "")

# App layout
st.title("Bird Observation Dashboard")
st.sidebar.header("Filters and Options")

# Sidebar elements
show_date = st.sidebar.checkbox("Show Current Date")
if show_date:
    st.sidebar.info(f"Today's Date: {date.today()}")

start_date = st.sidebar.date_input("Start Date")
end_date = st.sidebar.date_input("End Date", date.today())
if start_date > end_date:
    st.sidebar.error("Start date must be before end date.")

population_range = st.sidebar.slider(
    "Select a population range", 0, 100, (10, 50), step=1
)
st.sidebar.info(f"Population range: {population_range[0]} to {population_range[1]}")

selected_species_multi = st.sidebar.multiselect(
    "Choose species to focus on", options=species_list[1:]
)

if selected_species_multi:
    st.sidebar.success(f"Selected species: {', '.join(selected_species_multi)}")
else:
    st.sidebar.warning("No species selected.")

# Tabs for visualizations
maps, line_plot, bar_graph, table = st.tabs(["Map", "Line Plot", "Bar Graph", "Table"])

# Map Tab with Mapbox-style map
with maps:
    st.subheader("Bird Observations Map")

    species_selected = st.selectbox("Select the species of bird", options=species_list)

    if st.button("Show Locations"):
        if species_selected:
            st.info(f"Displaying map for {species_selected}")

            # Filter data for the selected species
            species_data = [obs for obs in species_dict if obs["comName"] == species_selected]
            locations = [{"lat": obs["lat"], "lon": obs["lng"]} for obs in species_data if
                         "lat" in obs and "lng" in obs]

            if locations:
                # Create a DataFrame for map points
                df_locations = pd.DataFrame(locations)

                # Define a pydeck layer
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_locations,
                    get_position="[lon, lat]",
                    get_radius=5000,
                    get_color=[200, 30, 0, 160],
                    pickable=True,
                )

                # Viewport settings
                view_state = pdk.ViewState(
                    latitude=df_locations["lat"].mean(),
                    longitude=df_locations["lon"].mean(),
                    zoom=6,
                    pitch=0,
                )

                # Render the map with open-street-map style
                deck = pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    map_style="open-street-map",
                )

                st.pydeck_chart(deck)
            else:
                st.error("No location data available for this species.")
        else:
            st.error("Please select a species.")

# Line Plot Tab
with line_plot:
    species_selected_for_plot = st.selectbox("Select species for line plot", options=species_list)
    if species_selected_for_plot:
        selected_species_for_plot = next(
            (species for species in species_dict if species["comName"] == species_selected_for_plot), None)
        if selected_species_for_plot:
            dates = [obs["obsDt"] for obs in species_dict if obs["comName"] == species_selected_for_plot]
            populations = [obs["howMany"] for obs in species_dict if obs["comName"] == species_selected_for_plot]

            if dates and populations:
                # Convert date to a more readable format
                dates = pd.to_datetime(dates).dt.strftime('%Y-%m-%d')

                fig, ax = plt.subplots()
                ax.plot(dates, populations, marker='o')
                ax.set_title(f"Population over observation date for {species_selected_for_plot}")
                ax.set_xlabel('Date')
                ax.set_ylabel('Population')
                st.pyplot(fig)
            else:
                st.error("No data available for plotting.")
        else:
            st.error("Species not found.")

# Bar Graph Tab
with bar_graph:
    species_selected_for_bar = st.selectbox("Select species for bar graph", options=species_list)
    if species_selected_for_bar:
        selected_species_for_bar = next(
            (species for species in species_dict if species["comName"] == species_selected_for_bar), None)
        if selected_species_for_bar:
            dates = [obs["obsDt"] for obs in species_dict if obs["comName"] == species_selected_for_bar]
            populations = [obs["howMany"] for obs in species_dict if obs["comName"] == species_selected_for_bar]

            if dates and populations:
                # Convert date to a more readable format
                dates = pd.to_datetime(dates).dt.strftime('%Y-%m-%d')

                fig, ax = plt.subplots()
                ax.bar(dates, populations)
                ax.set_title(f"Population distribution for {species_selected_for_bar}")
                ax.set_xlabel('Observation Date')
                ax.set_ylabel('Population')
                st.pyplot(fig)
            else:
                st.error("No data available for plotting.")
        else:
            st.error("Species not found.")

# Table Tab
with table:
    st.subheader("Interactive Bird Observations Table")

    # Convert the species dictionary into a DataFrame
    df = pd.DataFrame(species_dict)

    if not df.empty:
        # Allow filtering by species
        species_filter = st.multiselect(
            "Filter by species:", options=df["comName"].unique(), default=df["comName"].unique()
        )
        filtered_df = df[df["comName"].isin(species_filter)]

        # Allow filtering by observation date
        min_date = pd.to_datetime(df["obsDt"].min())
        max_date = pd.to_datetime(df["obsDt"].max())
        date_range = st.date_input(
            "Filter by date range:",
            [min_date, max_date],
            min_value=min_date,
            max_value=max_date,
        )

        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (pd.to_datetime(filtered_df["obsDt"]) >= start_date) &
                (pd.to_datetime(filtered_df["obsDt"]) <= end_date)
                ]

        # Display the filtered data
        st.dataframe(filtered_df)


        # Allow user to download the table
        @st.cache_data
        def convert_to_csv(dataframe):
            return dataframe.to_csv(index=False).encode('utf-8')


        csv = convert_to_csv(filtered_df)
        st.download_button(
            label="Download Table as CSV",
            data=csv,
            file_name='bird_observations.csv',
            mime='text/csv',
        )

        # Show summary statistics
        if "howMany" in filtered_df.columns:
            st.write("### Summary Statistics:")
            st.write(filtered_df["howMany"].describe())
    else:
        st.error("No data available to display in the table.")
