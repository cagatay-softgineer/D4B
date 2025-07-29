# forecasting_model.py

import sys
import logging

import pandas as pd
import numpy as np

import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import root_mean_squared_error, mean_absolute_error, r2_score

# Dash & Plotly
import dash
from dash import dcc, html, Input, Output
import plotly.express as px

# ----------------------------------------
# Logging setup
# ----------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ----------------------------------------
# Data generation (same as before)
# ----------------------------------------
def generate_mock_data(n: int) -> pd.DataFrame:
    rng = np.random.default_rng()
    priority_map  = {'Critical': 3, 'High': 2, 'Medium': 1, 'Low': 0}
    base_duration = {'Critical': 1.5, 'High': 3.0, 'Medium': 5.0, 'Low': 7.0}
    team_types    = ['electricity', 'plumbing', 'HVAC', 'network']

    df = pd.DataFrame({
        'priority':        rng.choice(list(priority_map), size=n, p=[0.15,0.3,0.4,0.15]),
        'team_efficiency': rng.uniform(0.6,1.0, size=n),
        'team_type':       rng.choice(team_types, size=n),
        'created_at':      pd.date_range('2024-01-01', periods=n, freq='h')
    })
    df['priority_encoded'] = df['priority'].map(priority_map)
    df['day_of_week']      = df['created_at'].dt.dayofweek
    df['hour']             = df['created_at'].dt.hour
    df['month']            = df['created_at'].dt.month
    df['is_weekend']       = df['day_of_week'].isin([5,6]).astype(int)
    df['season']           = (df['month'] % 12) // 3
    df['base_duration']    = df['priority'].map(base_duration)

    # baseline + noise
    df['duration'] = (
        df['base_duration'] * rng.uniform(0.8,1.2,size=n)
        + (1 - df['team_efficiency']) * rng.uniform(1.0,4.0,size=n)
        + rng.normal(0,0.3,size=n)
    )
    # temporal bumps
    sf = rng.uniform(0.5,1.5,4)
    df['duration'] += df['season'].map(dict(enumerate(sf))) * df['base_duration']
    wb = rng.uniform(0.5,1.5,size=n)
    df['duration'] += df['is_weekend'] * wb * df['base_duration']
    he = rng.uniform(0.0,0.5,24)
    df['duration'] += df['base_duration'] * df['hour'].map(lambda h: he[h])
    df['duration'] = df['duration'].clip(lower=0.1)

    return pd.get_dummies(df, columns=['team_type'], prefix='team_type')

# ----------------------------------------
# Globals: prepare once
# ----------------------------------------
SAMPLES_PER_RUN = 10000
FORECAST_WEEKS   = 104

# generate full dataset once
df_full = generate_mock_data(SAMPLES_PER_RUN * FORECAST_WEEKS)
df_full['week'] = df_full['created_at'].dt.isocalendar().week

# determine FEATURES
FEATURES = [
    'day_of_week','hour','month','priority_encoded',
    'team_efficiency','is_weekend','season'
] + [c for c in df_full.columns if c.startswith('team_type_')]

# hold out a test set
X_train, X_test, y_train, y_test = train_test_split(
    df_full[FEATURES], df_full['duration'],
    test_size=0.2, random_state=42
)

# precompute weekly template
weekly_template = df_full[['week'] + FEATURES + ['team_type_'+tt for tt in ['electricity','plumbing','HVAC','network']]]

# ----------------------------------------
# Dash App
# ----------------------------------------
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H2("🎛️ Hyperparam Tuning + Weekly Forecast"),
    html.Div([
        html.Label("n_estimators"),
        dcc.Slider(id='n-est',
                   min=10, max=200, step=10, value=50,
                   marks={i:str(i) for i in range(10,201,50)}),
        html.Label("max_depth"),
        dcc.Slider(id='max-depth',
                   min=1, max=10, step=1, value=2,
                   marks={i:str(i) for i in range(1,11)}),
        html.Label("learning_rate"),
        dcc.Slider(id='lr',
                   min=0.01, max=0.5, step=0.01, value=0.1,
                   marks={i/100:str(i/100) for i in range(1,51,10)}),
    ], style={'columnCount':3, 'marginBottom':'30px'}),
    html.Div(id='metrics-div', style={'marginBottom':'30px'}),
    html.Label("Select Week Range"),
    dcc.RangeSlider(
        id='week-slider',
        min=int(df_full.week.min()), max=int(df_full.week.max()),
        value=[1, FORECAST_WEEKS],
        marks={w:str(w) for w in range(1,FORECAST_WEEKS+1,4)},
        tooltip={'always_visible':False}
    ),
    dcc.Graph(id='forecast-graph')
])

@app.callback(
    Output('metrics-div','children'),
    Output('forecast-graph','figure'),
    Input('n-est','value'),
    Input('max-depth','value'),
    Input('lr','value'),
    Input('week-slider','value'),
)
def update_all(n_est, max_depth, lr, week_range):
    # 1) retrain
    params = {'n_estimators':n_est, 'max_depth':max_depth, 'learning_rate':lr}
    model = xgb.XGBRegressor(objective='reg:squarederror', **params, verbosity=0)
    model.fit(X_train, y_train)

    # 2) compute metrics
    preds_test = model.predict(X_test)
    rmse = root_mean_squared_error(y_test, preds_test)
    mae  = mean_absolute_error(y_test, preds_test)
    r2   = r2_score(y_test, preds_test)

    # 3) forecast weekly
    df = df_full.copy()
    df['predicted_duration'] = model.predict(df[FEATURES])
    df['team_type'] = df.filter(like='team_type_')\
                        .idxmax(axis=1).str.replace('team_type_','')

    low, high = week_range
    df = df[(df.week>=low)&(df.week<=high)]
    weekly = df.groupby(['week','team_type'])['predicted_duration']\
               .mean().reset_index()

    fig = px.line(weekly, x='week', y='predicted_duration',
                  color='team_type', markers=True,
                  title=f"Weeks {low}–{high}")
    fig.update_layout(xaxis_title='ISO Week',
                      yaxis_title='Avg Predicted Duration (hrs)')

    # 4) metrics display
    metrics_txt = html.Div([
        html.Span(f"✅ RMSE: {rmse:.3f}  "),
        html.Span(f"✅ MAE: {mae:.3f}  "),
        html.Span(f"✅ R²: {r2:.3f}")
    ], style={'fontSize':'18px'})
    return metrics_txt, fig

if __name__=='__main__':
    app.run_server(debug=True)
