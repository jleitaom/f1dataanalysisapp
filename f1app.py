# import libraries
import streamlit as st
import fastf1 as ff1
import fastf1.plotting
from fastf1.plotting import get_driver_color
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from matplotlib import pyplot as plt
from matplotlib.pyplot import figure
from matplotlib.collections import LineCollection
from matplotlib import cm
import seaborn as sns

# enable FastF1 cache
ff1.Cache.enable_cache('cache')

# Enable Matplotlib patches for plotting timedelta values and load
# FastF1's dark color scheme
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, misc_mpl_mods=False, color_scheme='fastf1')

# load session data function
def load_session(year, gp_name, session_type):
    try:
        session = ff1.get_session(year, gp_name, session_type)
        session.load()
        return session
    except Exception as e:
        st.error(f'Error loading session {str(e)}')
        return None

# get driver colors function
def get_driver_colors(session):
    """
    Get a dictionary mapping driver abbreviations to their colors,
    ensuring no two drivers have the same color.
    If duplicate colors are found, replace one with grey.
    """
    driver_colors = {}
    used_colors = set()  # Track already assigned colors

    for _, row in session.results.iterrows():
        abbreviation = row['Abbreviation']
        # Fetch driver color
        color = get_driver_color(abbreviation, session).lstrip('#')  # Remove '#' for consistency

        # Check for duplicates
        if color in used_colors:
            color = '808080'  # Set to grey if the color is already used

        driver_colors[abbreviation] = color
        used_colors.add(color)

    return driver_colors

def main():
    st.title("🏎️ Formula 1 Data Analysis")
    st.sidebar.header("🏁 Session")

    # get current year
    current_year = datetime.now().year

    # select session
    year = st.sidebar.selectbox("Select year", range(current_year, 2015, -1))

    # get available gp for the selected year
    schedule = ff1.get_event_schedule(year)
    schedule = schedule.sort_values('RoundNumber', ascending=False)
    gp_names = schedule['EventName'].tolist()
    selected_gp = st.sidebar.selectbox("Select Grand Prix", gp_names)

    session_types = ['R', 'Q', 'S']
    selected_session = st.sidebar.selectbox(
        "Select Session",
        session_types,
        format_func = lambda x: {
            'R': 'Race',
            'Q': 'Qualifying',
            'S': 'Sprint'
        }[x]
    )

    # load session data
    session = load_session(year, selected_gp, selected_session)

    if session:

        # tabs for visualizations
        tab1, tab2, tab3, tab4= st.tabs([
                                        "Session Results",
                                        "Fastest Lap Telemetry",
                                        "Tyre & Laptime Performance",
                                        "Tyre Strategy"
                                        ])
        
        # ---------Championship Results (Driver and Constructors)---------
            # ---------Driver championship points---------
            # ---------Constructors championship points---------

        # ---------Sector Performance ('Q')---------

        # ---------Tyre Strategy -> faltam os gráficos de weather(with weather and car data analysis) ('Q' 'R')---------        
        # ---------Max Speed vs Laptime ('Q' 'R')---------
        # ---------Driver positions by lap ('R')---------
        #---------Introduzir um LLM (RAG) que comunica com a API para responder a questões relativas a F1---------

        with tab1:

            if selected_session == 'R' or selected_session == 'S':
                session.results["WL_positions"] = session.results["GridPosition"] - session.results["Position"]
                session.results["WL_positions"] = session.results["WL_positions"].fillna(0).astype(float).astype(int).astype(str)
                not_finished = session.results["Status"] != "Finished"
                session.results.loc[not_finished, "WL_positions"] = (session.results["Status"] + " (" + session.results["WL_positions"].astype(str) + ")")
                results_data = {
                    'Position': session.results['Position'].fillna(0).astype(float).astype(int).astype(str),
                    'Name': session.results['FullName'],
                    'Team': session.results['TeamName'],
                    'GridPosition': session.results["GridPosition"].fillna(0).astype(float).astype(int).astype(str),
                    'WL_Positions': session.results["WL_positions"],
                    'Status': session.results['Status']
                }
            else:
                def format_time(time_str):
                    if pd.isna(time_str):
                        return "N/A"
                    try:
                        minutes, seconds = divmod(float(time_str.total_seconds()), 60)
                        return f"{int(minutes):02}:{seconds:05.3f}"
                    except AttributeError:
                        return time_str
                    
                results_data = {
                    'Position': session.results['Position'].astype(float).astype(int).astype(str),
                    'Name': session.results['FullName'],
                    'Team': session.results['TeamName'],
                    'Q1': session.results['Q1'].apply(format_time),
                    'Q2': session.results['Q2'].apply(format_time),
                    'Q3': session.results['Q3'].apply(format_time)
                }
            # ---------resolver problemas com treinos livres-----------

            # Add Points column only for Race sessions
            if selected_session in ['R', 'S']:  # Race or Sprint
                results_data['Points'] = session.results['Points'].fillna(0).astype(int)
            
            results_df = pd.DataFrame(results_data)
            st.table(results_df)

        with tab2:

            # Driver selection for lap times
            drivers = session.results['Abbreviation'].tolist()
            selected_drivers = st.multiselect(
                "Select Drivers to Compare",
                drivers,
                key="tab2_multiselect"
            )

            if selected_drivers:
                # Get driver colors
                driver_colors = get_driver_colors(session)
                
                # Create figure with subplots
                fig = make_subplots(
                    rows=3, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=('Speed', 'Throttle', 'Brake')
                )
                
                for driver in selected_drivers:
                    laps = session.laps.pick_drivers(driver).pick_fastest()
                    telemetry = laps.get_car_data().add_distance()
                    color = '#' + driver_colors[driver]
                    
                    # Speed plot
                    fig.add_trace(
                        go.Scatter(
                            x=telemetry['Distance'],
                            y=telemetry['Speed'],
                            name=driver,
                            mode='lines',
                            line=dict(color=color),
                            showlegend=True,
                            legendgroup="speed",
                            legendgrouptitle_text="Speed",
                            hovertemplate=
                            "<b>%{fullData.name}</b><br>" +
                            "Distance: %{x:.0f}m<br>" +
                            "Speed: %{y:.1f}km/h<br>" +
                            "<extra></extra>"
                        ),
                        row=1, col=1
                    )
                    
                    # Throttle plot
                    fig.add_trace(
                        go.Scatter(
                            x=telemetry['Distance'],
                            y=telemetry['Throttle'],
                            name=driver,
                            mode='lines',
                            line=dict(color=color),
                            showlegend=True,
                            legendgroup="throttle",
                            legendgrouptitle_text="Throttle",
                            hovertemplate=
                            "<b>%{fullData.name}</b><br>" +
                            "Distance: %{x:.0f}m<br>" +
                            "Throttle: %{y:.0f}%<br>" +
                            "<extra></extra>"
                        ),
                        row=2, col=1
                    )
                    
                    # Brake plot
                    fig.add_trace(
                        go.Scatter(
                            x=telemetry['Distance'],
                            y=telemetry['Brake'],
                            name=driver,
                            mode='lines',
                            line=dict(color=color),
                            showlegend=True,
                            legendgroup="brake",
                            legendgrouptitle_text="Brake",
                            hovertemplate=
                            "<b>%{fullData.name}</b><br>" +
                            "Distance: %{x:.0f}m<br>" +
                            "Brake: %{y:.0f}%<br>" +
                            "<extra></extra>"
                        ),
                        row=3, col=1
                    )
                
                # Update layout
                fig.update_layout(
                    height=800,
                    title="Fastest Lap Comparison",
                    template="plotly_white",
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=1.0
                    ),
                    hovermode='x unified'
                )
                
                # Update axes labels
                fig.update_xaxes(title_text="Distance", row=3, col=1)
                fig.update_yaxes(title_text="Speed", row=1, col=1)
                fig.update_yaxes(title_text="Throttle", row=2, col=1)
                fig.update_yaxes(title_text="Brake", row=3, col=1)
                
                st.plotly_chart(fig, use_container_width=True)

        with tab3:
            # Driver selection for lap times
            driver = session.results['Abbreviation'].tolist()
            selected_driver = st.selectbox(
                "Select Driver",
                driver,
                key="tab5_selectbox"  # Unique key for tab5
            )

            if selected_driver:
                # Retrieve and filter laps for the selected driver
                driver_laps = session.laps.pick_drivers(selected_driver).pick_quicklaps().reset_index()
                
                # Convert LapTime to minutes
                driver_laps["LapTimeMinutes"] = driver_laps["LapTime"].dt.total_seconds() / 60

                # Color mapping for tire compounds
                compound_colors = fastf1.plotting.get_compound_mapping(session=session)

                # Create the Plotly scatter plot with LapTime in minutes
                fig = px.scatter(
                    driver_laps,
                    x="LapNumber",
                    y="LapTimeMinutes",
                    color="Compound",
                    color_discrete_map=compound_colors,
                    labels={"LapNumber": "Lap Number", "LapTimeMinutes": "Lap Time (minutes)"}
                )


                fig.update_yaxes()

                # Add grid lines, set the background color, and adjust the font color
                fig.update_layout(
                    plot_bgcolor="rgb(15, 17, 22)",
                    paper_bgcolor="rgb(15, 17, 22)",
                    font=dict(color="white"),
                    xaxis=dict(gridcolor="gray"),
                    yaxis=dict(gridcolor="gray"),
                    legend=dict(title="Compound", font=dict(color="white"))
                )

                # Display the plot in Streamlit
                st.plotly_chart(fig)\
        
        with tab4:
            # Sort drivers by finishing position (assuming finishing order is available in `session.results`)
            finishing_order = session.results.sort_values(by="Position")["Abbreviation"].tolist()

            # Calculate stint lengths by counting laps in each stint
            stints = session.laps[["Driver", "Stint", "Compound", "LapNumber"]]
            stints = stints.groupby(["Driver", "Stint", "Compound"]).size().reset_index(name="StintLength")

            # Track compounds already added to the legend to avoid repetition
            compounds_in_legend = set()

            # Initialize figure
            fig = go.Figure()

            # Loop through each driver (in finishing order) and plot their stints
            for driver in finishing_order:
                driver_stints = stints.loc[stints["Driver"] == driver]
                previous_stint_end = 0

                # Plot each stint as a horizontal bar
                for _, row in driver_stints.iterrows():
                    compound_color = fastf1.plotting.get_compound_color(row["Compound"], session=session)
                    
                    # Only show the legend for the first occurrence of each compound
                    show_legend = row["Compound"] not in compounds_in_legend
                    compounds_in_legend.add(row["Compound"])  # Add compound to the legend set
                    
                    fig.add_trace(go.Bar(
                        y=[driver],                             # y-axis for driver name
                        x=[row["StintLength"]],                 # Stint length on x-axis
                        base=previous_stint_end,                # Offset to position each stint end-to-end
                        orientation='h',                        # Horizontal bar
                        marker=dict(color=compound_color, line=dict(color="black", width=1)),
                        name=row["Compound"],                   # Use compound name for legend
                        showlegend=show_legend,                 # Only show legend for first occurrence
                        legendgroup=row["Compound"]             # Group traces by compound
                    ))
                    
                    # Update previous stint end position
                    previous_stint_end += row["StintLength"]

            # Sort drivers by position and create a list of driver abbreviations in that order
            sorted_drivers = session.results.sort_values("Position")["Abbreviation"].tolist()

            # Reverse the list so that the 1st place driver is first
            sorted_drivers.reverse()

            # Update y-axis to reverse the driver order based on position (with 1st place at the top)
            fig.update_yaxes(categoryorder="array", categoryarray=sorted_drivers)

            # Update layout for improved readability and appearance
            fig.update_layout(
                title="Driver Stints by Compound",
                xaxis_title="Lap Number",
                yaxis_title="Driver",
                barmode='stack',
                plot_bgcolor="rgb(15, 17, 22)",
                paper_bgcolor="rgb(15, 17, 22)",
                font=dict(color="white"),
                legend_traceorder="normal",
                height=800,                    # Increase height for larger bars
                xaxis=dict(tickvals=list(range(0, int(max(session.laps["LapNumber"])) + 1, 5)))  # Adjust x-axis tick intervals
            )

            # Show in Streamlit
            st.plotly_chart(fig)

            # Get weather data and add lap numbers if not already present
            weather_data = session.laps.get_weather_data()

            # Create a line chart for humidity
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=session.laps['LapNumber'],  # x-axis as Lap Number
                    y=weather_data['Humidity'],   # y-axis as Humidity
                    mode='lines',                  # Line chart
                    name='Humidity',
                    line=dict(color='blue')
                )
            )

            # Update layout to add titles, labels, and background styling
            fig.update_layout(
                title="Humidity by Lap Number",
                xaxis_title="Lap Number",
                yaxis_title="Humidity (%)",
                plot_bgcolor="rgb(15, 17, 22)",
                paper_bgcolor="rgb(15, 17, 22)",
                font=dict(color="white")
            )

            # Customize grid color for better readability
            fig.update_xaxes(gridcolor="gray")
            fig.update_yaxes(gridcolor="gray")

            # Display the plot in Streamlit
            st.plotly_chart(fig)
                        
if __name__ == "__main__":
    st.set_page_config(
        page_title="F1 Data Analysis",
        page_icon="🏎️",
        layout="wide"
    )
    main()