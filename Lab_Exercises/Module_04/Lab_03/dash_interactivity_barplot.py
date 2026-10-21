# 1/ Import all the required libraries and read the Airline Reporting Carrier On-Time Performance dataset.
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.express as px

# Read the airline data into the pandas dataframe
airline_data =  pd.read_csv('https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/IBMDeveloperSkillsNetwork-DV0101EN-SkillsNetwork/Data%20Files/airline_data.csv', 
                            encoding = "ISO-8859-1",
                            dtype={'Div1Airport': str, 'Div1TailNum': str, 
                                   'Div2Airport': str, 'Div2TailNum': str})
# 2/ Give the title to the dashboard as "Total number of flights to the destination state split by reporting airline" using HTML H1 component and font-size as 40.
app = dash.Dash(__name__)
                               
app.layout = html.Div(children=[ html.H1('Total number of flights to the destination state split by reporting airline',style={'textAlign': 'center', 'color': '#503D36', 'font-size': 40}),
                                html.Div([html.Span("Input Year: ", style={'marginRight': '15px', 'whiteSpace': 'nowrap'}),dcc.Input(id='input-year', value='2010', type='number', 
                                style={'height': '50px', 'width': '150px', 'fontSize': 35})], 
                                style={'fontSize': 35, 'display': 'flex', 'alignItems': 'center','width': 'fit-content' }),
                                html.Br(),
                                html.Br(),
                                html.Div(dcc.Graph(id='bar-plot')),
                                ])

# 3/ Add Callback decorator
@app.callback( Output(component_id='bar-plot', component_property='figure'),
               Input(component_id='input-year', component_property='value'))

# Add the code for running the app, save the above changes, and relaunch the dashboard application to see the new dashboard.aa
def get_graph(entered_year):
    # Select 2019 data
    df =  airline_data[airline_data['Year']==int(entered_year)]
    
    # Group by destination state and reporting airline, summing total flights
    bar_data = df.groupby(['DestState', 'Reporting_Airline'])['Flights'].sum().reset_index()
    fig = px.bar(bar_data, x="DestState", y="Flights", color="Reporting_Airline", title="Total number of flights to the destination state split by reporting airline")
    
    # Update axis labels
    fig.update_layout(xaxis_title="Destination State", yaxis_title="Number of Flights")
    return fig

# Run the app
if __name__ == '__main__':
    app.run()