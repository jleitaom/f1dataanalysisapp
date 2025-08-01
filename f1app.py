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
    """
    Load the session data for the given year, Grand Prix name, and session type.
    """
    try:
        session = ff1.get_session(year, gp_name, session_type)
        session.load()
        return session
    except Exception as e:
        st.error(f'Error loading session {str(e)}')
        return None

# main function to run the app
def main():
    """
    Main function to run the app    
    """
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
        st.warning("To continue, please make sure you have selected a year, Grand Prix, and session type.")
        return

    def get_event_first_session_date(event_schedule):
        """
        For each event in the schedule, find the date of the first available session:
        Sprint Qualifying > Sprint > Qualifying > Race
        """
        session_priority = ['Sprint Qualifying', 'Sprint', 'Qualifying', 'Race']
        first_session_dates = []

        for _, row in event_schedule.iterrows():
            # default to None, update if session exists
            session_date = None
            for session_type in session_priority:
                try:
                    session_info = ff1.get_session(row['EventDate'].year, row['EventName'], session_type)
                    # check if the session has a date assigned
                    if session_info.date is not None:
                        session_date = session_info.date
                        break
                except Exception:
                    continue

            first_session_dates.append(session_date)

        return first_session_dates

    # load schedule for the selected year and get available gp for the selected year
    schedule = ff1.get_event_schedule(selected_year)
    schedule = schedule.iloc[1:]
    schedule = schedule.sort_values('RoundNumber', ascending=False)
    schedule['FirstSessionDate'] = get_event_first_session_date(schedule)
    today = datetime.now()
    available_schedule = schedule[schedule['FirstSessionDate'] <= today]
    gp_names = available_schedule['EventName'].tolist()

    # select gp
    selected_gp = st.sidebar.selectbox(
        "Select Grand Prix", 
        gp_names,
        index=None,
        placeholder="Select a Grand Prix"
    )

    if selected_gp is None:
        st.sidebar.warning("Please select a Grand Prix to continue.")
        st.warning("To continue, please make sure you have selected a year, Grand Prix, and session type.")
        return
    
    gp_to_official = dict(zip(available_schedule['EventName'], available_schedule['OfficialEventName']))
    official_name = gp_to_official.get(selected_gp, "Unknown Event")

    st.markdown(f"{official_name}")

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
        st.warning("To continue, please make sure you have selected a year, Grand Prix, and session type.")
        return

    st.sidebar.markdown(" ")
    st.sidebar.markdown("**Please note:** Loading data may take a few seconds depending on your internet connection and API response time.")

    # load session data
    if selected_year and selected_gp and selected_session:
        session = load_session(selected_year, selected_gp, selected_session)


        DASH_MAP = {
        'solid': 'solid',
        'dashed': 'dash',
        'dotted': 'dot',
        'dashdot': 'dashdot',
        'longdash': 'longdash',
        'longdashdot': 'longdashdot'
    }

    if session:
        
        if selected_session == 'R' or selected_session == 'S':
            
            # tabs for Race and Sprint sessions
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                                            "Grand Prix Overview",
                                            "Session Results",
                                            "Position Changes",
                                            "Fastest Lap Telemetry",
                                            "Tyre Performance & Weather",
                                            "Tyre Strategy"
                                            ])
        else:

            # tabs for Qualifying and Sprint Qualifying sessions
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                                            "Grand Prix Overview",
                                            "Session Results",
                                            "Qualifying Results",
                                            "Fastest Lap Telemetry",
                                            "Tyre Performance & Weather",
                                            "Tyre Strategy"
                                            ])
        
        with tab1: # gp overview
            try:
                # pre-fetch session/gp information
                gp_details = schedule.loc[schedule['EventName'] == selected_gp, ['RoundNumber', 'Country', 'Location']]
                round_number = gp_details.RoundNumber.iloc[0]
                total_rounds = schedule['RoundNumber'].max()
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
                        """ 
                        Rotate coordinates by a given angle in radians.
                        """
                        rot_mat = np.array([[np.cos(angle), np.sin(angle)],
                                            [-np.sin(angle), np.cos(angle)]])
                        return np.matmul(xy, rot_mat)

                    # prepare and rotate track
                    track = pos.loc[:, ('X', 'Y')].to_numpy()
                    track_angle = circuit_info.rotation / 180 * np.pi
                    rotated_track = rotate(track, angle=track_angle)

                    # track trace
                    track_trace = go.Scatter(
                        x=rotated_track[:, 0],
                        y=rotated_track[:, 1],
                        mode='lines',
                        line=dict(color='white', width=4),
                        name='Track'
                    )

                    # corner markers and labels
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

                    st.plotly_chart(
                        fig, 
                        use_container_width=True,
                        config={
                        "modeBarButtonsToRemove": ["toImage"],
                        "displaylogo": False
                        }
                    )
            
            except Exception as e:
                st.error(f'No session data: {str(e)}')
                return None

        with tab2: # session results
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
                        """
                        Format time string to MM:SS.sss format
                        """
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
                st.error(f'No session data: {str(e)}')
                return None

        # tab3:
        if selected_session == 'R' or selected_session == 'S':
            with tab3:
                try:
                    laps = session.laps
                    driver_styles = {
                        drv: get_driver_style(drv, session=session, style=['color', 'linestyle'])
                        for drv in laps['Driver'].unique()
                    }

                    # sort drivers by finishing position
                    finish_order = (
                        session.results[["Abbreviation", "Position"]]
                        .sort_values("Position")
                        .dropna()
                    )
                    sorted_drivers = finish_order["Abbreviation"].tolist()

                    # include any drivers missing from results (e.g., DNF)
                    all_drivers = sorted(laps['Driver'].unique())
                    sorted_drivers += [drv for drv in all_drivers if drv not in sorted_drivers]

                    fig = go.Figure()

                    for drv in sorted_drivers:
                        drv_laps = laps.pick_drivers(drv).sort_values(by="LapNumber")
                        dash_style = DASH_MAP.get(driver_styles[drv].get('linestyle', 'solid'), 'solid')

                        fig.add_trace(go.Scatter(
                            x=drv_laps["LapNumber"],
                            y=drv_laps["Position"],
                            mode='lines',
                            name=drv,
                            line=dict(
                                color=driver_styles[drv]['color'],
                                dash=dash_style,
                                width=1.2
                            ),
                            hovertemplate="Pos %{y}<extra>%{fullData.name}</extra>"
                        ))

                    fig.update_yaxes(
                        autorange="reversed",
                        title="Race Position",
                        tickmode='array',
                        tickvals=[1, 5, 10, 15, 20],
                        ticktext=['P1', 'P5', 'P10', 'P15', 'P20']
                    )
                    
                    fig.update_xaxes(title="Lap Number")
                    
                    fig.update_layout(
                        title="Position Changes During Session",
                        template="plotly_white",
                        height=600,
                        legend_title="Driver",
                        hovermode="x unified"
                    )

                    st.plotly_chart(
                        fig, 
                        use_container_width=True,
                        config={
                        "modeBarButtonsToRemove": ["toImage"],
                        "displaylogo": False
                        }
                    )

                except Exception as e:
                    st.error(f'No session data: {str(e)}')
        
        else: # qualifying and sprint qualifying sessions
            with tab3:
                try:
                    # convert to seconds
                    def to_seconds(t):
                        if pd.isnull(t):
                            return None
                        return t.total_seconds()

                    # define quali parts
                    quali_parts = ['Q1', 'Q2', 'Q3']
                    fig = make_subplots(
                        rows=1, cols=3,
                        shared_xaxes=False,
                        subplot_titles=[f"{q}" for q in quali_parts]
                    )

                    for i, quali in enumerate(quali_parts, start=1):
                        # extract lap times
                        lap_times = session.results[['Abbreviation', 'TeamName', quali]].dropna(subset=[quali]).copy()
                        lap_times['LapTimeSec'] = lap_times[quali].apply(to_seconds)

                        if lap_times.empty:
                            continue

                        # fastest lap time in seconds
                        best_time = lap_times['LapTimeSec'].min()

                        # compute gap % relative to best
                        lap_times['Delta'] = lap_times['LapTimeSec'] - best_time
                        lap_times['DeltaPct'] = 100 * lap_times['Delta'] / best_time

                        # sort fastest first
                        lap_times = lap_times.sort_values(by='DeltaPct').reset_index(drop=True)

                        # get driver-specific styles (color, linestyle, etc.)
                        driver_styles = {
                            drv: fastf1.plotting.get_driver_style(drv, session=session, style=['color'])
                            for drv in lap_times['Abbreviation']
                        }
                        driver_colors = [driver_styles[drv]['color'] for drv in lap_times['Abbreviation']]

                        # bar
                        fig.add_trace(go.Bar(
                            y=lap_times['Abbreviation'],
                            x=lap_times['DeltaPct'],
                            orientation='h',
                            marker=dict(
                                color=driver_colors,
                                line=dict(color='gray', width=0.5)
                            ),
                            text=[
                                f"{int(lap // 60)}:{lap % 60:06.3f}" if delta == 0 else f"+{delta:.3f}s"
                                for lap, delta in zip(lap_times['LapTimeSec'], lap_times['Delta'])
                            ],
                            textposition='outside',
                            insidetextanchor='start',
                            cliponaxis=False,  # Ensures text isn't cut off when it's outside the chart
                            hovertemplate="Driver: %{y}<br>Gap: %{x:.3f}%<extra></extra>"
                        ), row=1, col=i)

                        fig.update_yaxes(autorange="reversed", 
                            row=1, 
                            col=i
                        )

                        fig.update_xaxes(
                            title_text="Gap to Fastest (%)",
                            showgrid=True,
                            dtick=0.1,
                            row=1,
                            col=i
                        )

                    # Final layout
                    fig.update_layout(
                        height=650,
                        title="Qualifying Gap to Fastest",
                        showlegend=False,
                        template="plotly_white",
                        uniformtext_minsize=8,
                        uniformtext_mode='show',
                        margin=dict(t=80, r=80),  # Add right margin so labels fit
                    )

                    st.plotly_chart(
                        fig, 
                        use_container_width=True,
                        config={
                        "modeBarButtonsToRemove": ["toImage"],
                        "displaylogo": False
                        }
                    )
                
                except Exception as e:
                    st.error(f'No session data: {str(e)}')
                    return None


        with tab4: # fastest lap telemetry
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
                        """
                        Format time object to MM:SS.sss format
                        """
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
                            hovermode='x unified',
                            margin=dict(t=60)
                        )

                        # update axes labels
                        fig.update_yaxes(dtick=50, title_text="Speed", row=1, col=1)
                        fig.update_yaxes(title_text="Delta", row=2, col=1)
                        fig.update_yaxes(title_text="Throttle", row=3, col=1)
                        fig.update_yaxes(title_text="Brake", row=4, col=1)
                        fig.update_yaxes(title_text="Gear", row=5, col=1)
                        fig.update_xaxes(title_text="Distance", row=5, col=1)

                        st.plotly_chart(
                            fig, 
                            use_container_width=True,
                            config={
                            "modeBarButtonsToRemove": ["toImage"],
                            "displaylogo": False
                            }
                        )

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
                                hovermode='x unified',
                                margin=dict(t=60)
                            )

                        # update axes labels
                        fig.update_yaxes(dtick=50, title_text="Speed", row=1, col=1)
                        fig.update_yaxes(title_text="Throttle", row=2, col=1)
                        fig.update_yaxes(title_text="Brake", row=3, col=1)
                        fig.update_yaxes(title_text="Gear", row=4, col=1)
                        fig.update_xaxes(title_text="Distance", row=4, col=1)

                        st.plotly_chart(
                            fig, 
                            use_container_width=True,
                            config={
                            "modeBarButtonsToRemove": ["toImage"],
                            "displaylogo": False
                            }
                        )
            
            except Exception as e:
                st.error(f'No session data: {str(e)}')
                return None
        
        with tab5: # tyre performance & weather
            try: 
                # driver selection for lap times
                driver = session.results['Abbreviation'].tolist()
                selected_driver = st.selectbox(
                    "Select Driver",
                    driver,
                    key="tab5_selectbox"
                )

                if selected_driver:
                    # retrieve and filter laps for a threshold of 120% of the fastest lap
                    driver_laps = session.laps.pick_drivers(selected_driver).pick_quicklaps(threshold=1.2).reset_index()

                    # convert LapTime to float seconds for y-axis
                    driver_laps["LapTimeSeconds"] = driver_laps["LapTime"].dt.total_seconds()

                    # format LapTime into min:sec for hover display
                    def format_laptime(td):
                        total_seconds = int(td.total_seconds())
                        minutes = total_seconds // 60
                        seconds = total_seconds % 60
                        return f"{minutes}:{seconds:02}"

                    driver_laps["LapTimeStr"] = driver_laps["LapTime"].apply(format_laptime)

                    # compound mapping
                    compound_colors = fastf1.plotting.get_compound_mapping(session=session)

                    # scatter
                    fig = px.scatter(
                        driver_laps,
                        x="LapNumber",
                        y="LapTimeSeconds",
                        color="Compound",
                        color_discrete_map=compound_colors,
                        labels={"LapNumber": "Lap Number", "LapTimeSeconds": "Lap Time"}
                    )

                    # format hovering tool
                    fig.update_traces(
                        customdata=driver_laps[["LapTimeStr"]],
                        hovertemplate="Lap %{x}<br>Lap Time: %{customdata[0]}<br><extra></extra>"
                    )

                    # format y-axis ticks to min:sec (no milliseconds)
                    min_time = driver_laps["LapTimeSeconds"].min()
                    max_time = driver_laps["LapTimeSeconds"].max()
                    tick_vals = np.linspace(min_time, max_time, num=8)

                    def format_tick(v):
                        total_seconds = int(v)
                        minutes = total_seconds // 60
                        seconds = total_seconds % 60
                        return f"{minutes}:{seconds:02}"

                    tick_texts = [format_tick(v) for v in tick_vals]

                    fig.update_yaxes(
                        tickmode='array',
                        tickvals=tick_vals,
                        ticktext=tick_texts
                    )

                    # layout adjustments
                    fig.update_layout(
                        title="Tyre and Lap Time Performance",
                        template="plotly_white",
                        font=dict(color="white"),
                        xaxis=dict(title="Lap Number"),
                        yaxis=dict(title="Lap Time"),
                        legend=dict(
                            orientation="h",
                            x=1.0,
                            xanchor='right',
                            y=1.1,
                            yanchor='bottom',
                        ),
                        height=400,
                        margin=dict(t=110),
                    )

                    st.plotly_chart(
                        fig, 
                        use_container_width=True,
                        config={
                        "modeBarButtonsToRemove": ["toImage"],
                        "displaylogo": False
                        }
                    )

                    # extract weather data
                    weather_data = session.weather_data
                    weather_data['TimeHours'] = weather_data['Time'].dt.total_seconds() / 3600
                    air_temp = weather_data['AirTemp']
                    track_temp = weather_data['TrackTemp']
                    rainfall = weather_data['Rainfall'].astype(int)


                    fig = go.Figure()

                    # track temperature
                    fig.add_trace(go.Scatter(
                        x=weather_data['TimeHours'],
                        y=track_temp,
                        name='Track Temp [°C]',
                        mode='lines',
                        line=dict(width=2, color='crimson'),
                        hovertemplate='Track Temp: %{y:.1f}°C<extra></extra>'
                    ))

                    # air temperature
                    fig.add_trace(go.Scatter(
                        x=weather_data['TimeHours'],
                        y=air_temp,
                        name='Air Temp [°C]',
                        mode='lines',
                        line=dict(width=2, dash='dash', color='yellow'),
                        hovertemplate='Air Temp: %{y:.1f}°C<extra></extra>'
                    ))

                    # humidity
                    fig.add_trace(go.Scatter(
                        x=weather_data['TimeHours'],
                        y=weather_data['Humidity'],
                        name='Humidity [%]',
                        mode='lines',
                        line=dict(width=1, color='deepskyblue', dash='dot'),
                        yaxis='y2',
                        hovertemplate='Humidity: %{y:.0f}%<extra></extra>'
                    ))

                    # rainfall
                    fig.add_trace(go.Scatter(
                        x=weather_data['TimeHours'],
                        y=rainfall * track_temp.max(),
                        fill='tozeroy',
                        name='Rainfall',
                        mode='none',
                        fillcolor='rgba(0, 100, 255, 0.3)',
                        hoverinfo='skip'
                    ))


                    fig.update_layout(
                        title="Weather Conditions",
                        xaxis_title='Session Time (Hours)',
                        yaxis=dict(
                            title='Temperature [°C]'
                        ),
                        yaxis2=dict(
                            title='Humidity [%]',
                            overlaying='y',
                            side='right',
                            showgrid=False
                        ),
                        legend=dict(
                            orientation="h",
                            x=1.0,
                            xanchor='right',
                            y=1.1,
                            yanchor='bottom',
                        ),
                        template='plotly_white',
                        height=400,
                        hovermode="x unified"
                    )

                    st.plotly_chart(
                        fig, 
                        use_container_width=True,
                        config={
                        "modeBarButtonsToRemove": ["toImage"],
                        "displaylogo": False
                        }
                    )

            except Exception as e:
                st.error(f'No session data: {str(e)}')
                return None
        
        with tab6: # tyre strategy
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
                            legendgroup=row["Compound"],
                            hoverinfo="skip"
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
                    title="Tyre Strategy by Driver",
                    xaxis_title="Lap Number",
                    yaxis_title="Driver",
                    barmode='stack',
                    font=dict(color="white"),
                    legend_traceorder="normal",
                    height=600,
                    xaxis=dict(tickvals=list(range(0, int(max(session.laps["LapNumber"])) + 1, 5))),
                    margin=dict(t=40)
                )

                st.plotly_chart(
                    fig, 
                    use_container_width=True,
                    config={
                    "modeBarButtonsToRemove": ["toImage"],
                    "displaylogo": False
                    }
                )

            except Exception as e:
                st.error(f'No session data: {str(e)}')
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