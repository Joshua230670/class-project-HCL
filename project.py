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


# Fetch bird observation data
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


# Fetch recent notable observations in a region
def fetch_notable_observations(region_code, back=14, detail="simple", hotspot=False, max_results=100):
    url = f"https://api.ebird.org/v2/data/obs/{region_code}/recent/notable"

    # Set up query parameters
    params = {
        "back": back,
        "detail": detail,
        "hotspot": hotspot,
        "maxResults": max_results,
        "sppLocale": "en"  # Default language for species names
    }

    # Make the API request
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


# Function to display map for multiple species
def display_map(species_selected):
    species_dict = observed_US()
    species_data = [obs for obs in species_dict if obs["comName"] in species_selected]

    if not species_data:
        st.error(f"No data available for species: {', '.join(species_selected)}")
        return

    locations = [{"latitude": obs["lat"], "longitude": obs["lng"], "city": obs["locName"], "species": obs["comName"]}
                 for obs in species_data if "lat" in obs and "lng" in obs]

    if locations:
        df = pd.DataFrame(locations)

        # Calculate center of the map based on the average latitude and longitude
        center_lat = df["latitude"].mean()
        center_lon = df["longitude"].mean()

        # Set the zoom level based on the number of species selected
        zoom_level = 6 if len(species_selected) == 1 else 5  # Adjust zoom for one species vs. multiple species

        # Create the map with larger points and more prominent hover information
        fig = px.scatter_mapbox(df, lat='latitude', lon='longitude', zoom=zoom_level,
                                mapbox_style="open-street-map", hover_name='city', color='species',
                                opacity=0.7)

        # Update the hovertemplate to include latitude and longitude
        fig.update_traces(marker=dict(size=12, color='red', opacity=0.6),
                          hovertemplate="<b>Location:</b> %{hovertext}<br><b>Latitude:</b> %{lat}<br><b>Longitude:</b> %{lon}<extra></extra>")

        # Update map layout
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            mapbox_center={"lat": center_lat, "lon": center_lon},
        )

        # Display the map
        st.plotly_chart(fig)

        # Display today's date
        today = datetime.now().strftime("%A, %B %d, %Y")
        st.markdown(f"<p style='color: green; font-size: 18px;'>Today is {today}</p>", unsafe_allow_html=True)
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
    species_dict = observed_US()
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
    species_dict = observed_US()
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
    species_dict = observed_US()
    species_data = [obs for obs in species_dict if obs["comName"] in species_selected]

    if not species_data:
        st.error(f"No data available for species: {', '.join(species_selected)}")
        return

    df = pd.DataFrame(species_data)

    selection_choice = st.radio(
        "Select a choice",
        ["Specific Data", "Raw Data"]
    )

    if selection_choice == "Specific Data":
        if not df.empty:
            # Allow filtering by species
            species_filter = st.multiselect(
                "Filter by species:", options=df["comName"].unique()
            )
            simplify_data = st.checkbox("Simplify data?")
            filtered_df = df[df["comName"].isin(species_filter)]

            # Column names for simplified and raw data views
            col = ["Species Code", "Common Name", "Scientific Name", "Location ID",
                   "Location Observed", "Date Observed", "Population", "Latitude",
                   "Longitude", "Valid Observation", "Reviewed Observation",
                   "Location Private", "Sub ID"]

            if species_filter:
                if simplify_data:
                    filtered_df = filtered_df.rename(columns={
                        "comName": col[1],
                        "sciName": col[2],
                        "locName": col[4],
                        "howMany": col[6],
                        "lat": col[7],
                        "lng": col[8]
                    })
                    st.dataframe(filtered_df[[col[1], col[2], col[4], col[6], col[7], col[8]]])
                else:
                    filtered_df = filtered_df.rename(columns={
                        "speciesCode": col[0],
                        "comName": col[1],
                        "sciName": col[2],
                        "locId": col[3],
                        "locName": col[4],
                        "obsDt": col[5],
                        "howMany": col[6],
                        "lat": col[7],
                        "lng": col[8],
                        "obsValid": col[9],
                        "obsReviewed": col[10],
                        "locationPrivate": col[11],
                        "subId": col[12]
                    })
                    st.dataframe(filtered_df[[col[0], col[1], col[2], col[3], col[4], col[5], col[6],
                                               col[7], col[8], col[9], col[10], col[11], col[12]]])

    elif selection_choice == "Raw Data":
        st.info("All information on recently observed bird species is shown below.")
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
st.sidebar.header("Filters and Options")

species_dict = observed_US()
species_list = [i["comName"] for i in species_dict]
species_list = list(set(species_list))  # Remove duplicates
species_list.insert(0, "")  # Add empty option

# Sidebar species selection
species_selected = st.sidebar.multiselect("Select species of birds", species_list)

if species_selected:
    st.info(f"Displaying data for {', '.join(species_selected)}")

# Tabs for different visualizations
tabs = st.tabs(["Map", "Line Plot", "Bar Graph", "Interactive Table", "Notable Observations"])

# Map Tab
with tabs[0]:
    if species_selected:
        display_map(species_selected)

# Line Plot Tab
with tabs[1]:
    if species_selected:
        display_line_plot(species_selected)

# Bar Graph Tab
with tabs[2]:
    if species_selected:
        display_bar_graph(species_selected)

# Table Tab
with tabs[3]:
    if species_selected:
        display_table(species_selected)

# Notable Observations Tab (Always available)
with tabs[4]:
    display_notable_observations()
