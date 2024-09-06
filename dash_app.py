import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from app_pages import *
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import vectorbt as vbt


# Initialize Dash app
fonts = 'https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap'
# external_stylesheets = [fonts, dbc.themes.FLATLY, dbc.icons.FONT_AWESOME]
external_stylesheets = [fonts, dbc.themes.FLATLY, dbc.icons.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.css.config.serve_locally = True
server = app.server

# Load CSV files
def load_csv_files(folder, flist):
    dataframes = {}
    for file in os.listdir(folder):
        if file.endswith(".csv"):
            for ftype in flist:
                fname = "_" + ftype
                if fname in file:
                    df = pd.read_csv(os.path.join(folder, file))
                    dataframes[ftype] = df
                    break
    
    dataframes = modify_dataframes(dataframes)
    return dataframes

def load_data_from_data_folder():
    pass

# Convert a DataFrame dictionary to JSON for storing in dcc.Store
def dataframe_dict_to_json(dataframes):
    return {key: df.to_json(date_format='iso', orient='split') for key, df in dataframes.items()}

# Convert a JSON back to DataFrame dictionary
def json_to_dataframe_dict(json_data):
    return {key: pd.read_json(df_json, orient='split') for key, df_json in json_data.items()}

def dataframe_to_json(df):
    return df.to_json()

def json_to_dataframe(df_json):
    return pd.read_json(df_json)

def modify_dataframes(dataframes):
    # Manipulate data as appropriate
    dataframes["unrealized_pnl"] = dataframes["unrealized_pnl"].set_index("Unnamed: 0")
    dataframes["realized_pnl"] = dataframes["realized_pnl"].set_index("Unnamed: 0")
    dataframes["position"] = dataframes["position"].set_index("Unnamed: 0")
    dataframes["entry_info"] = dataframes["entry_info"].rename(columns={"Unnamed: 0": "symbols"})

    dataframes["unrealized_pnl"].index = pd.to_datetime(dataframes["unrealized_pnl"].index).tz_localize(None)
    dataframes["realized_pnl"].index = pd.to_datetime(dataframes["realized_pnl"].index).tz_localize(None)
    dataframes["position"].index = pd.to_datetime(dataframes["position"].index).tz_localize(None)

    return dataframes

def load_ohlcv_data(available_symbols):
    start_date = (pd.Timestamp.now() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    start_date = "2010-01-01"

    ohlcv_dataloader = load_data_files(available_symbols, OHLCV_DIR, start_date=start_date)
    ohlcv_multidf = pd.concat(ohlcv_dataloader).unstack(0)
    ohlcv_multidf.index = ohlcv_multidf.index.tz_localize(None)
    
    return ohlcv_multidf

def get_total_pnl_data(dataframes):
    u_pnl = dataframes["unrealized_pnl"].sum(axis=1)
    r_pnl = dataframes["realized_pnl"].cumsum().sum(axis=1)
    t_pnl = u_pnl + r_pnl

    df = pd.concat([t_pnl, u_pnl, r_pnl], axis=1)
    df.columns = ["Total PnL", "Unrealized PnL", "Realized PnL"]

    return df

def create_pnl_figure(dataframes):
    fig = go.Figure()
    fig = get_total_pnl_data(dataframes).vbt.plot(fig=fig)

    return fig

def calculate_pos_val(dataframes, ohlcv_multidf):
    close_df = ohlcv_multidf["close"]
    pos_val = dataframes["position"] * close_df.loc[dataframes["position"].index]

    return pos_val

def create_pos_val_figure(pos_val):
    pos = pos_val.iloc[-1]
    date = pos.name

    fig = go.Figure(data=[
        go.Bar(name=pos_val.index[-4].strftime("%Y-%m-%d"), x=pos_val.columns, y=pos_val.iloc[-4]),
        go.Bar(name=pos_val.index[-3].strftime("%Y-%m-%d"), x=pos_val.columns, y=pos_val.iloc[-3]),
        go.Bar(name=pos_val.index[-2].strftime("%Y-%m-%d"), x=pos_val.columns, y=pos_val.iloc[-2]),
        go.Bar(name=pos_val.index[-1].strftime("%Y-%m-%d"), x=pos_val.columns, y=pos_val.iloc[-1]),
    ])
    
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
    )
    fig.update_traces(
        opacity=0.8,
    )

    return fig

def create_pos_val_sunburst_figure(pos_val):
    pos = pos_val.iloc[-1]
    df = pd.DataFrame()
    df["Value"] = pos
    df["PositionSide"] = "Long"
    df.loc[df["Value"] < 0, "PositionSide"] = "Short"
    df.loc[df["Value"] == 0, "PositionSide"] = "None"
    df["Symbol"] = df.index
    df["Value"] = abs(df["Value"])
    df["Center"] = "Position"
    
    # Custom colors for the chart: green for long, red for short, gray for none
    custom_colors = {
        'Long': '#69EBA6',  # Teal for Long
        'Short': '#E0305B',  # Coral Pink for Short
        'None': '#778899',  # Slate Gray for None
        "(?)": "rgba(0, 0, 0, 0)"
    }

    fig = px.sunburst(df,
                      path=["Center", 'PositionSide', 'Symbol'],
                      values='Value',
                      color='PositionSide',
                      color_discrete_map=custom_colors)
    
    labels = fig.data[0]['labels']
    labels[-1] = ""

    fig.update_traces(
        opacity=1,
        labels=labels,
        insidetextorientation='tangential'
        # marker=dict(line=dict(color='#161618', width=0.5))  # Dark border
    )

    # Hide the root label by setting its text to be blank
    # fig.data[0].text = [""] * len(fig.data[0].text)

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        sunburstcolorway=["#4CD4C8", "#FF6F61", "#778899"],  # Custom colorway
    )

    return fig

def create_sunburst_bar_figure(pos_val):
    pos = pos_val.iloc[-1]
    date = pos.name

    total_dollar = abs(pos).sum()
    long_dollar = abs(pos[pos > 0]).sum()
    short_dollar = abs(pos[pos < 0]).sum()
    cash = total_dollar - long_dollar - short_dollar

    custom_colors = {
        'Long': '#69EBA6', 
        'Short': '#E0305B', 
        'Total': '#944FBE', 
        'Cash': '#3C4749', 
    }

    fig = go.Figure(data=[
        go.Bar(name="Total", x=["Total"], y=[total_dollar], marker_color=custom_colors["Total"]),
        go.Bar(name="Long", x=["Long"], y=[long_dollar], marker_color=custom_colors["Long"]),
        go.Bar(name="Short", x=["Short"], y=[short_dollar], marker_color=custom_colors["Short"]),
        go.Bar(name="Cash", x=["Cash"], y=[cash], marker_color=custom_colors["Cash"]),
        ], layout = dict(barcornerradius=5,),
        )
    

    fig.update_layout(
        yaxis_title="Dollars ($)",
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        # color_discrete_map=custom_colors,
    )
    fig.update_traces(
        opacity=0.8,
    )

    return fig

def create_trades_log_table(dataframes):
    # table = dash_table.DataTable(data=dataframes["trades"].to_dict('records'),
    #     columns=[{'id': c, 'name': c} for c in dataframes["trades"].columns],
    #     page_size=11, style_table={'overflowX': 'auto'},
    #     style_cell={'fontSize':15, 'font-family':'helvetica'},
    #     id="trades_log_table")
    
    grid = dag.AgGrid(
        id="trades_log_table",
        rowData=dataframes["trades"].to_dict('records'),
        columnDefs=[{'field': c} for c in dataframes["trades"].columns],
    )
    
    return grid

def create_dropdown_item_strategies():
    strategy_list = os.listdir("/home/yong_woo/PycharmProjects/Trader_redesign_v2/logs/strategy/")
    items = [dbc.DropdownMenuItem(i, id=i) for i in strategy_list]

    return items



# Define the sidebar layout
sidebar = html.Div([
            html.Div([
                html.A([
                    html.Div([
                        html.Img(src=BRAND_ICON_DIR, height="100%"),
                        dbc.NavbarBrand(html.H1("MagicButton", className="brand"))
                    ], className="row-div-brand")
                ],
                href="/",
                style={"textDecoration": "none"}),
            ], style={"margin-bottom": "50px"}),

            # html.Hr(style={"border-color":"gray"}),
            html.Br(className="navbar-space"),

            dbc.Nav(
                [
                    dbc.NavLink([
                        html.Div([
                            html.I(className="bi bi-graph-up-arrow"),
                            # html.I(className="bi bi-clipboard-data"),
                            "Dashboard"
                        ], style={"display":"flex", "gap":"10px"})
                        ], href="/", active="exact"),
                    # dbc.NavLink([html.I(className="fa-regular fa-clipboard"), "  Dashboard"], href="/", active="exact"),
                    dbc.NavLink([
                        html.Div([
                            html.I(className="bi bi-activity"),
                            "Simulation"
                        ], style={"display":"flex", "gap":"10px"})
                    ], href="/page-1", active="exact"),
                    dbc.NavLink([
                        html.Div([
                            html.I(className="bi bi-box"),
                            "Analysis"
                        ], style={"display":"flex", "gap":"10px"})
                    ], href="/page-2", active="exact"),
                ],
                vertical=True,
                pills=True,
                className="sidebar-nav"
            ),

            ], style={
                'width': '23%',
                'margin-left': 15,
                'margin-right': 15,
                'margin-top': 35,
                'margin-bottom': 35,
                "padding-top": 20
                },
            className="sidebar")

# Content container where the page layouts will be rendered
content = html.Div(id="page-content",
                   style={"padding": "20px",
                          "background-color": "#161618",
                          "width":"100%",})


app.layout = dbc.Container([
    dcc.Location(id="url"),  # This component handles page routing
    sidebar,
    
    html.Div([], className="vertical-line"),
    
    content,

    # Store to save the loaded dataframes
    dcc.Store(id='data-store'),
    dcc.Store(id='ohlcv-store'),

], fluid=True, className="dashboard-container", style={"display":"flex"})


# Callback to handle page routing
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def display_page(pathname):
    if pathname == "/":
        return dashboard_layout()  # Return dashboard layout when on homepage
    elif pathname == "/page-1":
        return page_1_layout()  # Return Page 1 layout
    elif pathname == "/page-2":
        return page_2_layout()  # Return Page 2 layout
    else:
        return "404: Page Not Found"

# Update data when strategy selected
@app.callback(
    Output("data-store", "data"),
    Output("ohlcv-store", "data"),
    Input("strategies-dropdown", "value"),
)
def load_and_store_data(selected_folder):
    folder_path = os.path.join(STRATEGIES_FOLDER, selected_folder)
    dataframes = load_csv_files(folder_path, FILE_NAMES)

    # Extract available symbols (columns) from any dataframe
    available_symbols = dataframes["position"].columns.tolist()  # Symbols are columns

    # Load ohlcv data
    ohlcv_multidf = load_ohlcv_data(available_symbols)

    return dataframe_dict_to_json(dataframes), dataframe_to_json(ohlcv_multidf)

# Update trades table when strategy selected
@app.callback(
    Output("trades-table", "children"),
    Output("trading-fee-value", "children"),
    Output("trading-fee-value", "style"),
    Output("trading-fee-percent", "children"),
    Output("trading-fee-percent", "style"),
    Input("data-store", "data")
)
def update_trades_fee_info(data_json):
    dataframes = json_to_dataframe_dict(data_json)
    
    # Update trades table
    grid = dag.AgGrid(
        id="trades-log-grid",
        rowData=dataframes["trades"].to_dict('records'),
        columnDefs=[{'field': c} for c in dataframes["trades"].columns],
        className="ag-theme-balham-dark",
        columnSize="sizeToFit"
    )

    init_balance = dataframes["balance_cash"]["current_balance"].iloc[0]

    df = dataframes["trades"].copy()
    df = df.loc[df["status"] != "failed"]
    df = df[["quantity", "price", "order_type"]]
    df["fee_percent"] = config["trading_fee"]["binance"]["futures"]["market"]
    df.loc[df["order_type"] == "LIMIT"] = config["trading_fee"]["binance"]["futures"]["limit"]

    df["dollar_fee"] = df["quantity"] * df["price"] * df["fee_percent"] / 100

    total_dollar_fee = df["dollar_fee"].sum()
    total_percent_fee = total_dollar_fee / init_balance * 100

    if total_dollar_fee > 0:
        total_dollar_fee = f"-$ {abs(round(total_dollar_fee, 2)):,}"
        style = {"color": "#ff8fa2"}

        total_percent_fee = f"↘ {round(total_percent_fee, 2):,}%"
        style_percent = {"background-color": "#ff8fa2",}

    
    return grid, total_dollar_fee, style, total_percent_fee, style_percent

# Update trades table when strategy selected
@app.callback(
    Output("entry-info-table", "children"),
    Input("data-store", "data")
)
def update_entry_info_table(data_json):
    dataframes = json_to_dataframe_dict(data_json)
    
    grid = dag.AgGrid(
        id="entry-info-grid",
        rowData=dataframes["entry_info"].to_dict('records'),
        columnDefs=[{'field': c} for c in dataframes["entry_info"].columns],
        className="ag-theme-balham-dark",
        columnSize="sizeToFit"
    )
    
    return grid

# Update figures when strategy selected
@app.callback(
    # Output("position-value-figure", "figure"),
    Output("pos-val-graph-div", "children"),
    Input("data-store", "data"),
    Input("ohlcv-store", "data"),
    Input("pos-val-btn-group", "value"),
)
def update_pos_val_figure(data_json, ohlcv_json, btn_val):
    dataframes = json_to_dataframe_dict(data_json)

    ohlcv_multidf = json_to_dataframe(ohlcv_json)
    multi_index = pd.MultiIndex.from_tuples([eval(col) for col in ohlcv_multidf.columns])
    ohlcv_multidf.columns = multi_index

    pos_val = calculate_pos_val(dataframes, ohlcv_multidf)

    if btn_val == 1:
        children = []

        fig = create_pos_val_sunburst_figure(pos_val)

        # Common figure settings
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            margin=dict(l=20, r=20, t=20, b=20),
            modebar={"bgcolor":'rgba(0, 0, 0, 0)'},
        )

        fig2 = create_sunburst_bar_figure(pos_val)

        fig2.update_layout(
            template="plotly_dark",
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
        )

        children.append(dcc.Graph(id="position-value-sunburst-figure",
                                  animate=True,
                                  figure=fig,
                                  style={"width":"70%"}))
        children.append(dcc.Graph(id="position-value-sunburst-bar-figure",
                                  animate=True,
                                  figure=fig2,
                                  style={"width":"30%"},
                                  config={'displayModeBar': False}))

        return children
    
    elif btn_val == 2:
        fig = create_pos_val_figure(pos_val)
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            margin=dict(l=20, r=20, t=20, b=20),
            modebar={"bgcolor":'rgba(0, 0, 0, 0)'},
        )

        return dcc.Graph(id="position-value-figure",
                        animate=True,
                        figure=fig)
    
    # return fig

@app.callback(
    Output("pnl-figure", "figure"),
    Input("data-store", "data"),
    Input("pnl-btn-group", "value"),
)
def update_pnl_figure(data_json, button_value):
    dataframes = json_to_dataframe_dict(data_json)
    if button_value == 1:
        fig = create_pnl_figure(dataframes)
    # Total
    elif button_value == 2:
        fig = go.Figure()
        tmp = dataframes["unrealized_pnl"] + dataframes["realized_pnl"].cumsum()
        tmp["SUM"] = tmp.sum(axis=1)
        fig = tmp.vbt.plot(fig=fig)
    # Unrealized
    elif button_value == 3:
        fig = go.Figure()
        tmp = dataframes["unrealized_pnl"].copy()
        tmp["SUM"] = tmp.sum(axis=1)
        fig = tmp.vbt.plot(fig=fig)
    # Realized
    elif button_value == 4:
        fig = go.Figure()
        tmp = dataframes["realized_pnl"].copy().cumsum()
        tmp["SUM"] = tmp.sum(axis=1)
        fig = tmp.vbt.plot(fig=fig)
    
    # Common figure settings
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=20, r=20, t=20, b=20),
        modebar={"bgcolor":'rgba(0, 0, 0, 0)'},
    )
    
    return fig

@app.callback(
    Output("balance-value", "children"),
    Output("pnl-all-time-value", "children"),
    Output("pnl-all-time-value", "style"),
    Output("pnl-all-time-percent", "children"),
    Output("pnl-all-time-percent", "style"),
    Output("balance-daily-percent", "children"),
    Output("balance-daily-percent", "style"),
    Input("data-store", "data"),
)
def update_pnl_values(data_json):
    dataframes = json_to_dataframe_dict(data_json)
    df = get_total_pnl_data(dataframes)
    init_balance = dataframes["balance_cash"]["current_balance"].iloc[0]
    
    all_time_pnl = df["Total PnL"].iloc[-1]
    all_time_percent = all_time_pnl / init_balance * 100

    current_balance = f"$ {round(init_balance + all_time_pnl, 2):,}"

    # Calculate 1 day pnl
    daily_pnl = all_time_pnl - df["Total PnL"].iloc[-2]
    daily_percent = daily_pnl / init_balance * 100

    if all_time_pnl < 0:
        all_time_pnl = f"-$ {abs(round(all_time_pnl, 2)):,}"
        style = {"color": "#ff8fa2"}

        # all_time_percent = f"↘ {abs(round(all_time_percent, 2))}%"
        all_time_percent = [html.I(className="bi bi-graph-down-arrow"), f" {abs(round(all_time_percent, 2))}%"]
        style_percent = {"background-color": "#ff8fa2",}

    elif all_time_pnl > 0:
        all_time_pnl = f"+$ {abs(round(all_time_pnl, 2))}"
        style = {"color": "#69EBA6"}

        # all_time_percent = f"↗ {round(all_time_percent, 2)}%"
        all_time_percent = [html.I(className="bi bi-graph-up-arrow"), f" {round(all_time_percent, 2)}%"]
        style_percent = {"background-color": "#69EBA6",}
    


    if daily_pnl < 0:
        daily_pnl = f"-$ {abs(round(daily_pnl, 2)):,}"

        # daily_percent = f"↘ {abs(round(daily_percent, 2))}%"
        daily_percent = [html.I(className="bi bi-graph-down-arrow"), f" {abs(round(daily_percent, 2))}%"]
        style_daily_percent = {"background-color": "#ff8fa2",}

    elif daily_pnl > 0:
        daily_pnl = f"+$ {abs(round(daily_pnl, 2))}"

        # daily_percent = f"↗ {round(daily_percent, 2)}%"
        daily_percent = [html.I(className="bi bi-graph-up-arrow"), f" {abs(round(daily_percent, 2))}%"]
        style_daily_percent = {"background-color": "#69EBA6",}

    return current_balance, all_time_pnl, style, all_time_percent, style_percent, daily_percent, style_daily_percent


# To run the Dash app independently, uncomment below:
if __name__ == '__main__':
    app.run_server(debug=True)