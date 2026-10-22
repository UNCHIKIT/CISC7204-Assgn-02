#!/usr/bin/env python
# coding: utf-8
"""CISC7204 Assgn02 - Module 05 Practice Project, Lab 02: Creating Dashboards.

`Dash_wildfire.py`: regional wildfire dashboard built from the course skeleton
(`Practice_Assignment_Part2.md`), TASK 2.1 - 2.5.

    python "CISC7204 Assgn02 Module 05Practice - Lab02 MC664183 Kelden Jamtsho.py"
    # then open http://127.0.0.1:8050
"""
from pathlib import Path

import pandas as pd
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.express as px

DATA_URL = ('https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/'
            'IBMDeveloperSkillsNetwork-DV0101EN-SkillsNetwork/Data%20Files/Historical_Wildfires.csv')
LOCAL_DATA = Path(__file__).with_name('Historical_Wildfires.csv')

# Create app
app = dash.Dash(__name__)
app.title = 'Australia Wildfire Dashboard'

# Clear the layout and do not display exception till callback gets executed
app.config.suppress_callback_exceptions = True

# Read the wildfire data into a pandas dataframe
df = pd.read_csv(LOCAL_DATA if LOCAL_DATA.exists() else DATA_URL)

# Extract year and month from the date column
df['Month'] = pd.to_datetime(df['Date']).dt.month_name()  # names of the months
df['Year'] = pd.to_datetime(df['Date']).dt.year

# Layout Section of Dash

# TASK 2.1: Add the Title to the Dashboard
app.layout = html.Div(children=[
    html.H1('Australia Wildfire Dashboard',
            style={'textAlign': 'center', 'color': '#503D36', 'font-size': 26}),

    # TASK 2.2: Add the radio items and a dropdown right below the first inner division
    # outer division starts
    html.Div([
        # First inner division: the two inputs
        html.Div([
            html.H2('Select Region:', style={'margin-right': '2em'}),
            # Radio items to select the region
            dcc.RadioItems([{"label": "New South Wales", "value": "NSW"},
                            {"label": "Northern Territory", "value": "NT"},
                            {"label": "Queensland", "value": "QL"},
                            {"label": "South Australia", "value": "SA"},
                            {"label": "Tasmania", "value": "TA"},
                            {"label": "Victoria", "value": "VI"},
                            {"label": "Western Australia", "value": "WA"}],
                           value="NSW", id='region', inline=True)
        ]),

        # Dropdown to select year
        html.Div([
            html.H2('Select Year:', style={'margin-right': '2em'}),
            dcc.Dropdown(sorted(df['Year'].unique()), value=2005, id='year')
        ]),

        # TASK 2.3: Two empty divisions for the output, inside the next inner division
        html.Div([
            html.Div([], id='plot1'),
            html.Div([], id='plot2')
        ], style={'display': 'flex', 'flexDirection': 'row', 'gap': '2em'}),
    ])
    # outer division ends
])
# layout ends


# TASK 2.4: Add the output and input components inside the app.callback decorator
@app.callback([Output(component_id='plot1', component_property='children'),
               Output(component_id='plot2', component_property='children')],
              [Input(component_id='region', component_property='value'),
               Input(component_id='year', component_property='value')])
# TASK 2.5: The callback function
def reg_year_display(input_region, input_year):
    # data
    region_data = df[df['Region'] == input_region]
    y_r_data = region_data[region_data['Year'] == input_year]

    # Plot one - Monthly Average Estimated Fire Area
    est_data = y_r_data.groupby('Month')['Estimated_fire_area'].mean().reset_index()
    fig1 = px.pie(est_data, values='Estimated_fire_area', names='Month',
                  title="{} : Monthly Average Estimated Fire Area in year {}".format(
                      input_region, input_year))

    # Plot two - Monthly Average Count of Pixels for Presumed Vegetation Fires
    veg_data = y_r_data.groupby('Month')['Count'].mean().reset_index()
    fig2 = px.bar(veg_data, x='Month', y='Count',
                  title='{} : Average Count of Pixels for Presumed Vegetation Fires '
                        'in year {}'.format(input_region, input_year))

    return [dcc.Graph(figure=fig1),
            dcc.Graph(figure=fig2)]


if __name__ == '__main__':
    app.run(debug=True)
