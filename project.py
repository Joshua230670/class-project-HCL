import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from datetime import datetime
import requests
from dotenv import load_dotenv
import os
import matplotlib

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")

@st.cache_data
def observed_US_cached():
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

# Fetch recent notable observations in a region
def fetch_notable_observations(region_code, back=14, detail="simple", hotspot=False, max_results=100):
    url = f"https://api.ebird.org/v2/data/obs/{region_code}/recent/notable"
    params = {
        "back": back,
        "detail": detail,
        "hotspot": hotspot,
        "maxResults": max_results,
        "sppLocale": "en"  # Default language for species names
    }
    response = requests.get(url, headers={'X-eBirdApiToken': API_KEY}, params=params)

    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            st.error("Error decoding API response.")
            return []
    else:
        st.error(f"Error: Received status code {response.status_code}")
        return []

def display_map(species_selected, pin_color="red"):
    species_dict = observed_US_cached()
    species_data = [obs for obs in species_dict if obs["comName"] in species_selected]

    if not species_data:
        st.error(f"No data available for species: {', '.join(species_selected)}")
        return

    # Create a list of locations with species names, latitudes, longitudes, and cities
    locations = [{"latitude": obs["lat"], "longitude": obs["lng"], "city": obs["locName"], "species": obs["comName"], "population": obs.get("howMany", "N/A")}
                 for obs in species_data if "lat" in obs and "lng" in obs]

    if locations:
        df = pd.DataFrame(locations)

        # Check if the map center is saved in session state, otherwise calculate the average center
        if "map_center" not in st.session_state:
            center_lat = df["latitude"].mean()
            center_lon = df["longitude"].mean()
            st.session_state.map_center = (center_lat, center_lon)
        else:
            center_lat, center_lon = st.session_state.map_center

        # Check if the zoom level is saved in session state, otherwise set it to 3
        if "zoom_level" not in st.session_state:
            st.session_state.zoom_level = 3

        # Sidebar slider for pin size (default size set to 10)
        pin_size = st.slider(
            "Select map pin size",
            min_value=5,  # Minimum pin size
            max_value=30,  # Maximum pin size
            value=10,  # Default pin size
            step=1
        )

        # Sidebar slider for zoom level (default zoom level set to 3)
        zoom_level = st.slider(
            "Select zoom level",
            min_value=3,  # Minimum zoom level
            max_value=10,  # Maximum zoom level
            value=st.session_state.zoom_level,  # Use stored zoom level
            step=1
        )

        # Save the zoom level in session state
        st.session_state.zoom_level = zoom_level

        # Save the map center position
        st.session_state.map_center = (center_lat, center_lon)

        # Create the map with individual pins for each species
        fig = px.scatter_mapbox(df, lat='latitude', lon='longitude', zoom=zoom_level,
                                mapbox_style="open-street-map", opacity=0.7)

        # Update the hovertemplate and marker color for the same color for all pins
        fig.update_traces(
            marker=dict(
                size=pin_size,  # Use the pin_size argument here
                color=pin_color,  # Use the pin_color argument here
                opacity=0.6
            ),
            hovertemplate='<b>Species: %{text}</b><br>Location: %{hovertext}<br>Latitude: %{lat}<br>Longitude: %{lon}<extra></extra>',
            text=df['species'],  # Species name for the hover text
            hovertext=df['city']  # Location (city) for the hovertext
        )

        # Update map layout to make the map interactive
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            mapbox_center={"lat": center_lat, "lon": center_lon},
            mapbox=dict(
                style="open-street-map",
                zoom=zoom_level,
                bearing=0,
                pitch=0
            ),
            dragmode="zoom",  # Enable dragging and zooming
            hovermode="closest",  # Highlight the closest point when hovering
        )

        # Display the map
        st.plotly_chart(fig)

        # Persistent Information Box for the selected species
        st.subheader("Information about selected observations:")

        for species in species_selected:
            st.markdown(f"### {species}")
            species_obs = [obs for obs in species_data if obs["comName"] == species]

            for selected_obs in species_obs:
                # Accessing 'howMany' safely using .get() to avoid KeyError
                population = selected_obs.get("howMany", "Data not available")

                # Display information about the observation
                st.markdown(f"**Species Name:** {selected_obs['comName']}")
                st.markdown(f"**Location:** {selected_obs['locName']}")
                st.markdown(f"**Latitude:** {selected_obs['lat']}")
                st.markdown(f"**Longitude:** {selected_obs['lng']}")
                st.markdown(f"**Observation Date:** {selected_obs['obsDt']}")
                st.markdown(f"**Population:** {population} birds observed")

    else:
        st.error("No location data available for selected species.")

# Function to display recent notable observations in a region
def display_notable_observations():
    region_code = st.text_input("Enter Region Code (e.g., US for United States)", "")
    if region_code:
        notable_data = fetch_notable_observations(region_code)
        if notable_data:
            notable_df = pd.DataFrame(notable_data)
            if not notable_df.empty:
                st.dataframe(notable_df[['comName', 'locName', 'obsDt', 'howMany', 'lat', 'lng']])
            else:
                st.info("No notable observations found for the selected region.")
        else:
            st.error("No data available for the selected region.")
    else:
        st.warning("Please enter a valid region code.")

# Function to display line plot for multiple species
def display_line_plot(species_selected):
    species_dict = observed_US_cached()
    species_data = [obs for obs in species_dict if obs["comName"] in species_selected]

    if not species_data:
        st.error(f"No data available for species: {', '.join(species_selected)}")
        return

    combined_data = []
    for species in species_selected:
        species_data_filtered = [obs for obs in species_data if obs["comName"] == species]
        for obs in species_data_filtered:
            combined_data.append({
                "species": species,
                "date": pd.to_datetime(obs["obsDt"]),
                "population": obs.get("howMany", 0)
            })

    df = pd.DataFrame(combined_data)
    df.sort_values(by="date", inplace=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    for species in species_selected:
        species_data_filtered = df[df["species"] == species]
        ax.plot(species_data_filtered["date"], species_data_filtered["population"], marker='o', label=species)

    ax.set_title(f"Population over observation date")
    ax.set_xlabel('Date')
    ax.set_ylabel('Population')
    ax.legend()

    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig)

# Function to display bar graph for multiple species grouped by date
def display_bar_graph(species_selected):
    species_dict = observed_US_cached()
    species_data = [obs for obs in species_dict if obs["comName"] in species_selected]

    if not species_data:
        st.error(f"No data available for species: {', '.join(species_selected)}")
        return

    all_dates = []
    all_populations = []
    all_species = []

    for species in species_selected:
        species_data_filtered = [obs for obs in species_data if obs["comName"] == species]
        for obs in species_data_filtered:
            all_dates.append(obs["obsDt"])
            all_populations.append(obs.get("howMany", 0))
            all_species.append(species)

    all_dates = pd.to_datetime(all_dates)

    df = pd.DataFrame({
        "date": all_dates,
        "population": all_populations,
        "species": all_species
    })

    grouped_df = df.groupby(["date", "species"]).sum().reset_index()

    unique_species = species_selected
    color_map = matplotlib.cm.get_cmap("tab20", len(unique_species))

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, species in enumerate(unique_species):
        species_data = grouped_df[grouped_df["species"] == species]
        for idx, row in species_data.iterrows():
            label = species if idx == species_data.index[0] else ""
            ax.bar(row["date"], row["population"], label=label, color=color_map(i / len(unique_species)))

    ax.set_title("Population Observed for Selected Species Grouped by Date")
    ax.set_xlabel("Observation Date")
    ax.set_ylabel("Total Population Observed")

    plt.xticks(rotation=45, ha="right")

    ax.legend(title="Species")
    st.pyplot(fig)

# Function to display interactive table for multiple species
def display_table(species_selected):
    species_dict = observed_US_cached()
    species_data = [obs for obs in species_dict if obs["comName"] in species_selected]

    if not species_data:
        st.error(f"No data available for species: {', '.join(species_selected)}")
        return

    df = pd.DataFrame(species_data)

    if df.empty:
        st.error("No data available to display.")
        return

    # Let the user select data view mode
    selection_choice = st.radio(
        "Select a choice",
        ["Specific Data", "Raw Data"]
    )

    if selection_choice == "Specific Data":
        # User filtering options
        species_filter = st.multiselect(
            "Filter by species:", options=df["comName"].unique()
        )
        simplify_data = st.checkbox("Simplify data?")

        # Filter DataFrame by selected species
        filtered_df = df[df["comName"].isin(species_filter)] if species_filter else df

        # Define column mappings
        column_mapping = {
            "speciesCode": "Species Code",
            "comName": "Common Name",
            "sciName": "Scientific Name",
            "locID": "Location ID",
            "locName": "Location Observed",
            "obsDt": "Date Observed",
            "howMany": "Population",
            "lat": "Latitude",
            "lng": "Longitude",
            "valid": "Valid Observation",
            "reviewed": "Reviewed Observation",
            "private": "Location Private",
            "subID": "Sub ID",
        }

        # Check for missing columns
        existing_columns = [col for col in column_mapping.keys() if col in filtered_df.columns]
        if not existing_columns:
            st.error("No relevant data available to display.")
            return

        # Apply renaming
        filtered_df = filtered_df.rename(columns={k: v for k, v in column_mapping.items() if k in existing_columns})

        # Simplify or display full data
        if simplify_data:
            display_columns = ["Common Name", "Scientific Name", "Location Observed", "Population", "Latitude", "Longitude"]
        else:
            display_columns = [column_mapping[col] for col in existing_columns]

        # Display DataFrame
        st.dataframe(filtered_df[display_columns])
    elif selection_choice == "Raw Data":
        # Display raw data without filtering
        st.dataframe(df)
        
##################TO DO######################

# filtered_df = df[df["comName"].isin(species_filter)]

# Allow filtering by observation date
# min_date = pd.to_datetime(df["obsDt"].min())
# max_date = pd.to_datetime(df["obsDt"].max())
# date_range = st.date_input(
#     "Filter by date range:",
#     [min_date, max_date],
#     min_value=min_date,
#     max_value=max_date,
# )

# if len(date_range) == 2:
#     start_date, end_date = date_range
# filtered_df = filtered_df[
# (pd.to_datetime(filtered_df["obsDt"]) >= start_date) &
# (pd.to_datetime(filtered_df["obsDt"]) <= end_date)
# ]

# Display the filtered data
# st.dataframe(filtered_df)


# Allow user to download the table
# @st.cache_data
# def convert_to_csv(dataframe):
#     return dataframe.to_csv(index=False).encode('utf-8')


# csv = convert_to_csv(filtered_df)
# st.download_button(
#     label="Download Table as CSV",
#     data=csv,
#     file_name='bird_observations.csv',
#     mime='text/csv',
# )

# Show summary statistics
# if "howMany" in filtered_df.columns:
# st.write("### Summary Statistics:")
# st.write(filtered_df["howMany"].describe())
#######################################################

# Streamlit UI Setup
st.title("Bird Observation Dashboard")
st.sidebar.header("Species Selection")

# Display today's date
today = datetime.now().strftime("%A, %B %d, %Y")
st.markdown(f"<p style='color: green; font-size: 18px;'>Today is {today}</p>", unsafe_allow_html=True)

# Inform the user about the selection limit
st.sidebar.info("You can select up to 11 species.")
st.sidebar.warning("Unselecting all species will close displayed data.")

# Set up species data
species_dict = observed_US_cached()
species_list = list({i["comName"] for i in species_dict})  # Remove duplicates
species_list.sort()  # Optional: Sort for better UI experience

# Sidebar species selection with a max selection limit
species_selected = st.sidebar.multiselect(
    "Select species of birds", species_list
)

# Inform the user about the selected species
if species_selected:
    if len(species_selected) <= 11:
        st.info(f"Displaying data for: {', '.join(species_selected)}")
    else:
        st.warning("Reduce your selection to 11 species or fewer to view data.")
else:
    st.info("Please select at least one species from the sidebar to view data.")

# Tabs for different visualizations
tabs = st.tabs(["Map", "Line Plot", "Bar Graph", "Interactive Table", "Notable Observations"])

# Check the number of selected species
if len(species_selected) > 11:
    for i, tab_name in enumerate(["Map", "Line Plot", "Bar Graph", "Interactive Table"]):
        with tabs[i]:
            st.error("You can only select up to 11 species. Please reduce your selection.")
else:
    for i, tab_name in enumerate(["Map", "Line Plot", "Bar Graph", "Interactive Table"]):
        with tabs[i]:
            if species_selected:
                # Call the respective function based on the tab
                if tab_name == "Map":
                    # Use session state to manage the pin color
                    if "pin_color" not in st.session_state:
                        st.session_state.pin_color = "#FF0000"

                    pin_color = st.color_picker("Pick a color for map pins", st.session_state.pin_color)

                    # Update the map only if the color changes
                    if pin_color != st.session_state.pin_color:
                        st.session_state.pin_color = pin_color

                    display_map(species_selected, st.session_state.pin_color)
                elif tab_name == "Line Plot":
                    display_line_plot(species_selected)
                elif tab_name == "Bar Graph":
                    display_bar_graph(species_selected)
                elif tab_name == "Interactive Table":
                    display_table(species_selected)

# Notable Observations Tab (Always available)
with tabs[4]:
    display_notable_observations()
