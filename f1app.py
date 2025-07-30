import streamlit as st
import fastf1 as ff1
import fastf1.plotting
from fastf1.plotting import get_driver_style
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# FastF1's delta and dark color scheme
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')

# load session data function
@st.cache_resource(show_spinner="Loading session data...")
def load_session(year, gp_name, session_type):
    try:
        session = ff1.get_session(year, gp_name, session_type)
        session.load()
        return session
    except Exception as e:
        st.error(f'Error loading session {str(e)}')
        return None

# main function to run the app
def main():
    st.title("🏎️ F1 Data App")
    st.sidebar.header("🏁 Session")
    st.sidebar.markdown("Use the sidebar to select the season year, Grand Prix, and session type you want to analyze!")
    st.sidebar.markdown(" ")

    # initialize session variables
    selected_year = None
    selected_gp = None
    selected_session = None
    session = None

    # get current year
    current_year = datetime.now().year

    # select session
    selected_year = st.sidebar.selectbox(
        "Select year", 
        range(current_year, 2015, -1),
        index=None,
        placeholder="Select a year"
    )

    if selected_year is None:
        st.sidebar.warning("Please select a year to continue.")
        return

    # load schedule for the selected year and get available gp for the selected year
    schedule = ff1.get_event_schedule(selected_year)
    schedule = schedule.sort_values('RoundNumber', ascending=False)
    schedule = schedule.iloc[1:]
    gp_names = schedule['EventName'].tolist()
    official_names = schedule['OfficialEventName'].tolist()

    # select gp
    selected_gp = st.sidebar.selectbox(
        "Select Grand Prix", 
        gp_names,
        index=None,
        placeholder="Select a Grand Prix"
    )

    if selected_gp is None:
        st.sidebar.warning("Please select a Grand Prix to continue.")
        return
    
    st.markdown(f"{official_names[gp_names.index(selected_gp)]}")

    # get available session types for the selected gp
    round_number = schedule[schedule['EventName'] == selected_gp]['RoundNumber'].values[0]
    event = ff1.get_event(selected_year, int(round_number))
    
    if event.EventFormat == "conventional":
        session_names = ['R', 'Q']
    else:
        session_names = ['R', 'Q', 'S', 'SQ']
    
    # select session type
    selected_session = st.sidebar.selectbox(
    "Select Session",
    session_names,
    index=None,
    placeholder="Select a session",
    format_func = lambda x: {
        'R': 'Race',
        'Q': 'Qualifying',
        'S': 'Sprint',
        'SQ': 'Sprint Qualifying'
    }[x]
    )
    
    if selected_session is None:
        st.sidebar.warning("Please select a session type to continue.")
        return

    st.sidebar.markdown(" ")
    st.sidebar.markdown("**Please note:** Loading data may take a few seconds depending on your internet connection and API response time.")

    # load session data
    if selected_year and selected_gp and selected_session:
        session = load_session(selected_year, selected_gp, selected_session)


    if session:

        # tabs
        tab1, tab2, tab3, tab4, tab5= st.tabs([
                                        "Grand Prix Overview",
                                        "Session Results",
                                        "Fastest Lap Telemetry",
                                        "Tyre & Laptime Performance",
                                        "Tyre Strategy"
                                        ])

        with tab1:
            try:
                # pre-fetch session/gp information
                gp_details = schedule.loc[schedule['EventName'] == selected_gp, ['RoundNumber', 'Country', 'Location']]
                round_number = gp_details.RoundNumber.iloc[0] + 1 # index starts at 0
                total_rounds = schedule['RoundNumber'].max() + 1 # index starts at 0
                circuit_country = gp_details.Country.iloc[0]
                circuit_location = gp_details.Location.iloc[0]

                fastest_lap = session.laps.pick_fastest()
                pos = fastest_lap.get_pos_data()

                circuit_info = session.get_circuit_info()
                num_corners = len(circuit_info.corners)
                
                telemetry = fastest_lap.get_telemetry()
                track_distance = telemetry['Distance'].max() / 1000
                

                # columns
                col1, col2, col3, col4, col5 = st.columns(5) 

                # round number
                with col1:
                    with st.container(border=True):
                        st.metric(label='Round Number', value=f"Round {round_number:.0f} of {total_rounds:.0f}")

                # country
                with col2:
                    with st.container(border=True):
                        st.metric(label='Country', value=f"{circuit_country}")

                # location
                with col3:
                    with st.container(border=True):
                        st.metric(label='Location', value=f"{circuit_location}")

                # total distance
                with col4:
                    with st.container(border=True):
                        st.metric(label='Total Distance', value=f"≈ {track_distance:.1f} km")
                
                # number of corners
                with col5:
                    with st.container(border=True):
                        st.metric(label='Number of Corners', value=f"{num_corners:.0f} corners")
                
                # circuit map
                with st.container(border=True): 
                    def rotate(xy, *, angle):
                        rot_mat = np.array([[np.cos(angle), np.sin(angle)],
                                            [-np.sin(angle), np.cos(angle)]])
                        return np.matmul(xy, rot_mat)

                    # Prepare and rotate track
                    track = pos.loc[:, ('X', 'Y')].to_numpy()
                    track_angle = circuit_info.rotation / 180 * np.pi
                    rotated_track = rotate(track, angle=track_angle)

                    # Track trace
                    track_trace = go.Scatter(
                        x=rotated_track[:, 0],
                        y=rotated_track[:, 1],
                        mode='lines',
                        line=dict(color='white', width=4),
                        name='Track'
                    )

                    # Corner markers and labels
                    offset_vector = [500, 0]
                    corner_labels = []
                    corner_lines = []

                    for _, corner in circuit_info.corners.iterrows():
                        txt = f"{corner['Number']}{corner['Letter']}"
                        offset_angle = corner['Angle'] / 180 * np.pi
                        offset_x, offset_y = rotate(offset_vector, angle=offset_angle)
                        text_x, text_y = rotate([corner['X'] + offset_x, corner['Y'] + offset_y], angle=track_angle)
                        track_x, track_y = rotate([corner['X'], corner['Y']], angle=track_angle)

                        corner_labels.append(go.Scatter(
                            x=[text_x], y=[text_y],
                            mode='markers+text',
                            marker=dict(size=12, color='yellow'),
                            text=[txt],
                            textposition='middle center',
                            textfont=dict(color='black', size=8),
                            hoverinfo='skip',
                            showlegend=False
                        ))

                        corner_lines.append(go.Scatter(
                            x=[track_x, text_x],
                            y=[track_y, text_y],
                            mode='lines',
                            line=dict(color='white', width=1),
                            showlegend=False
                        ))

                    fig = go.Figure(data=[track_trace] + corner_lines + corner_labels)
                    fig.update_layout(
                        height=450,
                        xaxis=dict(visible=False),
                        yaxis=dict(visible=False, scaleanchor='x', scaleratio=1),
                        showlegend=False,
                        margin=dict(t=80, b=20, l=20, r=20)
                    )

                    st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                st.error(f'No session data {str(e)}')
                return None

        with tab2:
            try:
                if selected_session == 'R' or selected_session == 'S':
                    session.results["WL_positions"] = (session.results["GridPosition"] - session.results["Position"]).fillna(0).astype(int)

                    results_data = {
                        'Position': session.results['Position'].fillna(0).astype(int).astype(str),
                        'Name': session.results['FullName'],
                        'Team': session.results['TeamName'],
                        'Grid Position': session.results["GridPosition"].fillna(0).astype(int).astype(str),
                        'Positions Gained/Lost': session.results["WL_positions"].astype(str),
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
                        'Position': session.results['Position'].astype(int).astype(str),
                        'Name': session.results['FullName'],
                        'Team': session.results['TeamName'],
                        'Q1': session.results['Q1'].apply(format_time),
                        'Q2': session.results['Q2'].apply(format_time),
                        'Q3': session.results['Q3'].apply(format_time)
                    }

                # add points column only for Race sessions
                if selected_session in ['R', 'S']:  # Race or Sprint
                    results_data['Points'] = session.results['Points'].fillna(0).astype(int)
                
                results_df = pd.DataFrame(results_data)
                st.table(results_df)

            except Exception as e:
                st.error(f'No session data {str(e)}')
                return None

        with tab3:
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
                    # get drivers colors
                    driver_styles = {
                        drv: get_driver_style(drv, session=session, style=['color', 'linestyle']) for drv in selected_drivers
                    }

                    # get drivers teams
                    driver_teams = {
                        drv: session.results.loc[session.results['Abbreviation'] == drv, 'TeamName'].values[0]
                        for drv in selected_drivers
                    }

                    # check if both drivers are from the same team
                    same_team = (
                        len(selected_drivers) == 2 and
                        driver_teams[selected_drivers[0]] == driver_teams[selected_drivers[1]]
                    )

                    def format_time(time_obj):
                        if pd.isna(time_obj):
                            return "N/A"
                        try:
                            minutes, seconds = divmod(float(time_obj.total_seconds()), 60)
                            return f"{int(minutes):02}:{seconds:05.3f}"
                        except AttributeError:
                            return time_obj

                    # display best lap time for each driver
                    st.write("**Best Lap Times**")
                    for driver in selected_drivers:
                        laps = session.laps.pick_drivers(driver).pick_fastest()
                        best_lap_time = laps['LapTime']
                        formatted_time = format_time(best_lap_time)
                        st.write(f"**{driver}**: {formatted_time}")


                    if len(selected_drivers) == 2:

                        # create figure with 5 subplots
                        fig = make_subplots(
                            rows=5, cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.03
                        )


                        driver1, driver2 = selected_drivers
                        laps1 = session.laps.pick_drivers(driver1).pick_fastest()
                        laps2 = session.laps.pick_drivers(driver2).pick_fastest()

                        tel1 = laps1.get_car_data().add_distance()
                        tel2 = laps2.get_car_data().add_distance()

                        # interpolate driver2's time to match driver1's distance
                        tel1_dist = tel1['Distance']
                        tel1_time = tel1['Time'].dt.total_seconds()
                        tel2_time_interp = np.interp(
                            x=tel1_dist,
                            xp=tel2['Distance'],
                            fp=tel2['Time'].dt.total_seconds()
                        )

                        delta_time = tel2_time_interp - tel1_time  # POSITIVE: driver2 is behind

                        # horizontal delta reference at 0
                        fig.add_trace(
                            go.Scatter(
                                x=tel1_dist,
                                y=[0] * len(tel1_dist),
                                mode='lines',
                                name='Zero Δt',
                                line=dict(color='gray', width=1),
                                hoverinfo='skip',
                                showlegend=False
                            ),
                            row=2, col=1
                        )

                        fig.add_trace(
                            go.Scatter(
                                x=tel1_dist,
                                y=delta_time,
                                mode='lines',
                                name=f"{driver2} vs {driver1}",
                                line=dict(color=driver_styles[driver2]['color'], dash='dot'),
                                showlegend=True,
                                legendgroup="delta",
                                legendgrouptitle_text="Delta Time",
                                hovertemplate=
                                "Distance: %{x:.0f}m<br>" +
                                "Delta: %{y:.3f}s<br>" +
                                "<extra></extra>"
                            ),
                            row=2, col=1
                        )


                        for i, driver in enumerate(selected_drivers):
                            laps = session.laps.pick_drivers(driver).pick_fastest()
                            telemetry = laps.get_car_data().add_distance()

                            color = driver_styles[driver]['color']
                            if same_team and i == 1:
                                color = '#FFFFFF'

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
                                    legendgrouptitle_text="Drivers",
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
                                    showlegend=False,
                                    legendgroup="throttle",
                                    legendgrouptitle_text="Throttle",
                                    hovertemplate=
                                    "<b>%{fullData.name}</b><br>" +
                                    "Distance: %{x:.0f}m<br>" +
                                    "Throttle: %{y:.0f}%<br>" +
                                    "<extra></extra>"
                                ),
                                row=3, col=1
                            )
                            
                            # brake plot
                            fig.add_trace(
                                go.Scatter(
                                    x=telemetry['Distance'],
                                    y=telemetry['Brake'],
                                    name=driver,
                                    mode='lines',
                                    line=dict(color=color),
                                    showlegend=False,
                                    legendgroup="brake",
                                    legendgrouptitle_text="Brake",
                                    hovertemplate=
                                    "<b>%{fullData.name}</b><br>" +
                                    "Distance: %{x:.0f}m<br>" +
                                    "Brake: %{y:.0f}%<br>" +
                                    "<extra></extra>"
                                ),
                                row=4, col=1
                            )

                            # gear plot
                            fig.add_trace(
                                go.Scatter(
                                    x=telemetry['Distance'],
                                    y=telemetry['nGear'],
                                    name=driver,
                                    mode='lines',
                                    line=dict(color=color),
                                    showlegend=False,
                                    legendgroup="gear",
                                    legendgrouptitle_text="Drivers",
                                    hovertemplate=
                                    "<b>%{fullData.name}</b><br>" +
                                    "Distance: %{x:.0f}m<br>" +
                                    "Gear: %{y:.0f}<br>" +
                                    "<extra></extra>"
                                ),
                                row=5, col=1
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
                        fig.update_yaxes(dtick=50, title_text="Speed", row=1, col=1)
                        fig.update_yaxes(title_text="Delta", row=2, col=1)
                        fig.update_yaxes(title_text="Throttle", row=3, col=1)
                        fig.update_yaxes(title_text="Brake", row=4, col=1)
                        fig.update_yaxes(title_text="Gear", row=5, col=1)
                        fig.update_xaxes(title_text="Distance", row=5, col=1)

                        st.plotly_chart(fig, use_container_width=True)

                    else:

                        # create figure with 4 subplots
                        fig = make_subplots(
                            rows=4, cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.03
                        )

                        for i, driver in enumerate(selected_drivers):
                            laps = session.laps.pick_drivers(driver).pick_fastest()
                            telemetry = laps.get_car_data().add_distance()

                            color = driver_styles[driver]['color']
                            if same_team and i == 1:
                                color = '#FFFFFF'

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
                                    legendgrouptitle_text="Drivers",
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
                                    showlegend=False,
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
                                    showlegend=False,
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

                            # gear plot
                            fig.add_trace(
                                go.Scatter(
                                    x=telemetry['Distance'],
                                    y=telemetry['nGear'],
                                    name=driver,
                                    mode='lines',
                                    line=dict(color=color),
                                    showlegend=False,
                                    legendgroup="gear",
                                    legendgrouptitle_text="Drivers",
                                    hovertemplate=
                                    "<b>%{fullData.name}</b><br>" +
                                    "Distance: %{x:.0f}m<br>" +
                                    "Gear: %{y:.0f}<br>" +
                                    "<extra></extra>"
                                ),
                                row=4, col=1
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
                        fig.update_yaxes(dtick=50, title_text="Speed", row=1, col=1)
                        fig.update_yaxes(title_text="Throttle", row=2, col=1)
                        fig.update_yaxes(title_text="Brake", row=3, col=1)
                        fig.update_yaxes(title_text="Gear", row=4, col=1)
                        fig.update_xaxes(title_text="Distance", row=4, col=1)

                        st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                st.error(f'No session data {str(e)}')
                return None
        
        with tab4:
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

                    # scatter plot
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
        
        with tab5:

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

    else:
        st.warning("To continue, please make sure you have selected a year, Grand Prix, and session type.")

if __name__ == "__main__":
    st.set_page_config(
        page_title="F1 Data App",
        page_icon="🏎️",
        layout="wide"
    )
    main()