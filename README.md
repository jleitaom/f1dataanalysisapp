# 🏎️ Interactive F1 Data APP

### App:
https://f1dataanalysisapp.streamlit.app/

### Description:

After analyzing a few specific moments in Formula 1, I noticed my friends kept asking for more charts and insights from other races. That’s when I realized I could turn this growing interest into an opportunity: to build a web app that allows anyone to explore F1 data throughout each race weekend.

The purpose of this tool is to analyze F1 session data with precision, through highly interactive visualizations built with Plotly. It offers an intuitive and interactive experience, making the data accessible to both enthusiasts and analysts looking to dive deeper into the sport.

![How to load session demo](https://github.com/jleitaom/f1dataanalysisapp/blob/main/assets/loadingsession_gif.gif)

### 1. Features

The app allows users to explore different Formula 1 events by selecting the **year**, **Grand Prix** and **session type** they wish to analyze.
To ensure a smooth and intuitive experience, users are guided through the process with helpful messages and instructions, making the app easy and efficient to use.

Available sessions range from **2018 to the current season**. For the ongoing season, only **Grand Prix events with available data** are shown — ensuring users don’t attempt to load sessions that haven’t yet occurred or been processed.
Depending on the event format, users can choose between the following session types:
**Race**, **Qualifying**, **Sprint**, or **Sprint Qualifying**.

Typically, data is made available by the API **shortly after the end of each session**, enabling users to analyze and explore the session almost in real time.

### 2. Featured Tabs

- Grand Prix Overview
- Session Results
- Race Position Changes & Detailed Qualifying Results
- Fastest Lap Telemetry
- Overall Pace
- Driver Performance
- Tyre Strategy

### 2. Acknowledgements

This project relies heavily on the data provided by the FastF1 Package ([fastf1_documentation](https://docs.fastf1.dev/))
