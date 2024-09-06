import os
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import yaml
import pandas as pd

# Config loader
def load_config(config_file='strategy_modules/trade_configs.yaml'):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

# Data loader
def load_data_files(symbol_list, data_folder, start_date, end_date=None, columns="simple"):

    dataloader = {}
    remove_sym = []
    for symbol in symbol_list:
        fname = os.path.join(data_folder, f"{symbol}_ohlcv_data.csv")
        df_orig = pd.read_csv(fname)
        if columns == "simple":
            df_orig = df_orig[["open_time", "open", "high", "low", "close", "volume"]]
        df_orig = df_orig.rename(columns={"open_time": "date"})

        if start_date is not None:
            df_orig = df_orig[df_orig["date"] >= start_date].reset_index(drop=True)

        if end_date is not None:
            df_orig = df_orig[df_orig["date"] <= end_date].reset_index(drop=True)

        if len(df_orig) == 0:
            remove_sym.append(symbol)
            continue
        df_orig["date"] = pd.to_datetime(df_orig["date"], utc=True)
        df_orig = df_orig.set_index("date").sort_index()
        dataloader[symbol] = df_orig

    for symbol in remove_sym:
        symbol_list.remove(symbol)
    
    return dataloader

# Load config
config = load_config("strategy_modules/trade_configs.yaml")

# Path to the folder containing CSV files
STRATEGIES_FOLDER = config["web"]["strategy"]["dir"]
FILE_NAMES = config["web"]["strategy"]["ftypes"]
OHLCV_DIR = config["ohlcv_data"]["1d"]["dir"]
BRAND_ICON_DIR = "assets/icons/gems.png"


def get_strategy_list(STRATEGIES_FOLDER):
    strategy_list = os.listdir(STRATEGIES_FOLDER)
    for exclude_folder in config["web"]["strategy"]["exclude_folders"]:
        if exclude_folder in strategy_list:
            strategy_list.remove(exclude_folder)
    
    return strategy_list

# Create strategy list
strategy_list = get_strategy_list(STRATEGIES_FOLDER)

def dashboard_layout():
    dashboard_layout = html.Div([
        html.Div([
            html.H1("Dashboard"),
            html.Div([
                html.H4("Select Strategy"),
                dcc.Dropdown(
                    id="strategies-dropdown",
                    options=strategy_list,
                    value=strategy_list[0],
                    clearable=False,
                    className="customDropdown"
                    ),
            ], style={"width": "20%"}),
        ], className="row-div"),
        html.Br(),
        html.Div([
            dbc.Card([
                html.Div([
                    html.H6("Strategy Balance", className="header1"),
                    html.Div([
                        html.H3(id="balance-value", className="balance-display"),
                        html.H5(id="balance-daily-percent", className="pill-text"),
                    ], className="row-div2"),
                ])

            ], className="info-card", style={"width":"30%"}),

            dbc.Card([
                html.P("All time PnL", style={"margin-bottom":"0px"}),
                html.Div([
                    html.H3(id="pnl-all-time-value", className="pnl-display"),
                    html.H5(id="pnl-all-time-percent", className="pill-text"),
                ], className="row-div2"),
            ], className="blue-gray-card", style={"width":"20%"}),

            dbc.Card([
                html.P("Estimated trading fee", style={"margin-bottom":"0px"}),
                html.Div([
                    html.H3(id="trading-fee-value", className="fee-display"),
                    html.H5(id="trading-fee-percent", className="pill-text"),
                ], className="row-div2"),
            ], className="blue-gray-card", style={"width":"20%"}),

            dbc.Card([
                html.P("30d PnL", style={"margin-bottom":"0px"}),
                html.Div([
                    html.H3("10045.29", className="fee-display"),
                    html.H5("+1927%", className="pill-text"),
                ], className="row-div2"),

            ], className="blue-gray-card", style={"width":"20%"}),
        ], className="row-div", style={"width":"100%"}),
        html.Br(),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.H2("PnL Plot"),
                            dbc.RadioItems(
                                id="pnl-btn-group",
                                className="btn-group time-selector",
                                inputClassName="btn-check",
                                labelClassName="btn time-btn",
                                labelCheckedClassName="btn-selected",
                                options=[
                                    {"label": "Account", "value": 1},
                                    {"label": "Total", "value": 2},
                                    {"label": "Unrealized", "value": 3},
                                    {"label": "Realized", "value": 4},
                                ],
                                value=1,
                            ),
                        ], className="row-div"),  # Flexbox to align items horizontally
                                        
                        html.Br(),
                        dcc.Graph(id="pnl-figure", animate=True)
                    ]),
                ], id="pnl-container", className="graph-card"),
            ], width=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.H2("Open Position Value"),
                            dbc.RadioItems(
                                id="pos-val-btn-group",
                                className="btn-group time-selector",
                                inputClassName="btn-check",
                                labelClassName="btn time-btn",
                                labelCheckedClassName="btn-selected",
                                options=[
                                    {"label": "Status", "value": 1},
                                    {"label": "History", "value": 2},
                                ],
                                value=1,
                            ),
                        ], className="row-div"),

                        html.Br(),

                        # dcc.Graph(id="position-value-sunburst-figure", animate=True),
                        html.Div(id="pos-val-graph-div", children=[], className="row-div"),
                        # dcc.Graph(id="position-value-figure", animate=True),
                    ])
                ], id="pos-val-container", className="graph-card")
            ], width=6),
        ]),

        html.Br(),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.H2("Entry Info"),
                            html.Br(),
                            html.Div(id="entry-info-table", children=[], className="pop-out"),
                        ]),
                    ])
                ], className="graph-card"),
            ], width=4),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.H2("Trades Log"),
                            html.Br(),
                            html.Div(id="trades-table", children=[], className="pop-out"),
                        ]),
                    ])
                ], className="graph-card"),
            ], width=8)
        ]),
                        
        ], style={
                'width': '100%',
                'margin-left': 15,
                'margin-top': 35,
                'margin-bottom': 35
                })
    return dashboard_layout

def page_1_layout():
    page_1_layout = html.Div([
        html.H2("Page 1"),
        html.P("This is Page 1 content.")
    ], style={'width': '100%',
            'margin-left': 15,
            'margin-top': 35,
            'margin-bottom': 35})
    return page_1_layout

def page_2_layout():
    page_2_layout = html.Div([
        html.H2("Page 2"),
        html.P("This is Page 2 content.")
    ], style={'width': '100%',
        'margin-left': 15,
        'margin-top': 35,
        'margin-bottom': 35})
    return page_2_layout