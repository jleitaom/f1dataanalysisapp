# TESTE
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
    driver_colors = {}
    used_colors = set()

    for _, row in session.results.iterrows():
        abbreviation = row['Abbreviation']

        # fetch driver color
        color = get_driver_color(abbreviation, session).lstrip('#')

        # check for duplicates
        if color in used_colors:
            color = '808080'

        driver_colors[abbreviation] = color
        used_colors.add(color)

    return driver_colors

def main():
    st.title("🏎️ Formula 1 Data Analysis")
    st.sidebar.header("🏁 Session")

    # get current year
    current_year = datetime.now().year

    # select session
    year = st.sidebar.selectbox("Select year", range(current_year-1, 2015, -1))

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

    st.sidebar.write("Note: data could take a few seconds to connect with API and load.")

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

        with tab1:
            try:
                if selected_session == 'R' or selected_session == 'S':
                    session.results["WL_positions"] = session.results["GridPosition"] - session.results["Position"]
                    session.results["WL_positions"] = session.results["WL_positions"].fillna(0).astype(float).astype(int).astype(str)
                    not_finished = session.results["Status"] != "Finished"
                    session.results.loc[not_finished, "WL_positions"] = (session.results["WL_positions"].astype(str) + " (" + session.results["Status"] + ")")
                    results_data = {
                        'Position': session.results['Position'].fillna(0).astype(float).astype(int).astype(str),
                        'Name': session.results['FullName'],
                        'Team': session.results['TeamName'],
                        'Grid Position': session.results["GridPosition"].fillna(0).astype(float).astype(int).astype(str),
                        'Positions Gained/Lost': session.results["WL_positions"],
                        'Status & Occurrences': session.results['Status']
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

                # add Points column only for Race sessions
                if selected_session in ['R', 'S']:  # Race or Sprint
                    results_data['Points'] = session.results['Points'].fillna(0).astype(int)
                
                results_df = pd.DataFrame(results_data)
                st.table(results_df)

            except Exception as e:
                st.error(f'No session data {str(e)}')
                return None

        with tab2:
            try:
                # driver selection for lap times
                drivers = session.results['Abbreviation'].tolist()
                selected_drivers = st.multiselect(
                    "Select Drivers to Compare",
                    drivers,
                    key="tab2_multiselect",
                    max_selections=2
                )

                if selected_drivers:
                    # get driver colors
                    driver_colors = get_driver_colors(session)

                    def format_time(time_obj):
                        if pd.isna(time_obj):
                            return "N/A"
                        try:
                            minutes, seconds = divmod(float(time_obj.total_seconds()), 60)
                            return f"{int(minutes):02}:{seconds:05.3f}"
                        except AttributeError:
                            return time_obj

                    # Display best lap time for each driver
                    st.write("**Best Lap Times**")
                    for driver in selected_drivers:
                        laps = session.laps.pick_drivers(driver).pick_fastest()
                        best_lap_time = laps['LapTime']  # This is likely a single Timedelta object
                        formatted_time = format_time(best_lap_time)  # Call format_time directly
                        st.write(f"**{driver}**: {formatted_time}")

                    # create figure with subplots
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

                        # speed plot
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
                        
                        # throttle plot
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
                        
                        # brake plot
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
                    
                    # update layout
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
                    
                    # update axes labels
                    fig.update_xaxes(title_text="Distance", row=3, col=1)
                    fig.update_yaxes(title_text="Speed", row=1, col=1)
                    fig.update_yaxes(title_text="Throttle", row=2, col=1)
                    fig.update_yaxes(title_text="Brake", row=3, col=1)

                    st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                st.error(f'No session data {str(e)}')
                return None
        
        with tab3:
            try: 
                # driver selection for lap times
                driver = session.results['Abbreviation'].tolist()
                selected_driver = st.selectbox(
                    "Select Driver",
                    driver,
                    key="tab5_selectbox"
                )

                if selected_driver:
                    # retrieve and filter laps for the selected driver
                    driver_laps = session.laps.pick_drivers(selected_driver).pick_quicklaps().reset_index()
                    
                    # convert LapTime to minutes
                    driver_laps["LapTimeMinutes"] = driver_laps["LapTime"].dt.total_seconds() / 60

                    # color mapping for tire compounds
                    compound_colors = fastf1.plotting.get_compound_mapping(session=session)

                    # create the scatter plot with lapTime in minutes
                    fig = px.scatter(
                        driver_laps,
                        x="LapNumber",
                        y="LapTimeMinutes",
                        color="Compound",
                        color_discrete_map=compound_colors,
                        labels={"LapNumber": "Lap Number", "LapTimeMinutes": "Lap Time (minutes)"}
                    )


                    fig.update_yaxes()

                    # add grid lines, set the background color, and adjust the font color
                    fig.update_layout(
                        plot_bgcolor="rgb(15, 17, 22)",
                        paper_bgcolor="rgb(15, 17, 22)",
                        font=dict(color="white"),
                        xaxis=dict(gridcolor="gray"),
                        yaxis=dict(gridcolor="gray"),
                        legend=dict(title="Compound", font=dict(color="white"))
                    )

                    st.plotly_chart(fig)\
            
            except Exception as e:
                st.error(f'No session data {str(e)}')
                return None
        
        with tab4:
            st.write("Driver Stints by Compound")
            try:

                # sort drivers by finishing position
                finishing_order = session.results.sort_values(by="Position")["Abbreviation"].tolist()

                # calculate stint lengths by counting laps in each stint
                stints = session.laps[["Driver", "Stint", "Compound", "LapNumber"]]
                stints = stints.groupby(["Driver", "Stint", "Compound"]).size().reset_index(name="StintLength")

                # track compounds already added to the legend to avoid repetition
                compounds_in_legend = set()

                fig = go.Figure()

                # loop through each driver (in finishing order) and plot their stints
                for driver in finishing_order:
                    driver_stints = stints.loc[stints["Driver"] == driver]
                    previous_stint_end = 0

                    # plot each stint as a horizontal bar
                    for _, row in driver_stints.iterrows():
                        compound_color = fastf1.plotting.get_compound_color(row["Compound"], session=session)
                        
                        # only show the legend for the first occurrence of each compound
                        show_legend = row["Compound"] not in compounds_in_legend
                        compounds_in_legend.add(row["Compound"])
                        
                        fig.add_trace(go.Bar(
                            y=[driver],
                            x=[row["StintLength"]],
                            base=previous_stint_end,
                            orientation='h',
                            marker=dict(color=compound_color, line=dict(color="black", width=1)),
                            name=row["Compound"],
                            showlegend=show_legend,
                            legendgroup=row["Compound"]
                        ))
                        
                        # update previous stint end position
                        previous_stint_end += row["StintLength"]

                # sort drivers by position and create a list of driver abbreviations in that order
                sorted_drivers = session.results.sort_values("Position")["Abbreviation"].tolist()

                # reverse the list so that the 1st place driver is first
                sorted_drivers.reverse()

                # update y-axis to reverse the driver order based on position (with 1st place at the top)
                fig.update_yaxes(categoryorder="array", categoryarray=sorted_drivers)

                # update layout for improved readability and appearance
                fig.update_layout(
                    xaxis_title="Lap Number",
                    yaxis_title="Driver",
                    barmode='stack',
                    font=dict(color="white"),
                    legend_traceorder="normal",
                    height=800,
                    xaxis=dict(tickvals=list(range(0, int(max(session.laps["LapNumber"])) + 1, 5)))
                )

                st.plotly_chart(fig)

            except Exception as e:
                st.error(f'No session data {str(e)}')
                return None
                     
if __name__ == "__main__":
    st.set_page_config(
        page_title="F1 Data Analysis",
        page_icon="🏎️",
        layout="wide"
    )
    main()
