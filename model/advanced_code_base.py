# forecasting_model.py

import argparse
import sys
import logging

import pandas as pd
import numpy as np

# Optional interactive plotting
try:
    import plotly.express as px
    INTERACTIVE = True
except ImportError:
    INTERACTIVE = False

import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    root_mean_squared_error,
    mean_absolute_error,
    r2_score
)

# Dash for web app
try:
    import dash
    from dash import dcc, html, Input, Output
    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False

# ----------------------------------------
# Logging setup
# ----------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ----------------------------------------
# Data generation
# ----------------------------------------
def generate_mock_data(n: int) -> pd.DataFrame:
    """
    Generate synthetic job data with:
      - categorical team_type (electricity, plumbing, HVAC, network)
      - engineered temporal and priority features with real randomness
    """
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

    # baseline duration + noise
    df['duration'] = (
        df['base_duration'] * rng.uniform(0.8,1.2,size=n)
        + (1 - df['team_efficiency']) * rng.uniform(1.0,4.0,size=n)
        + rng.normal(0,0.3,size=n)
    )

    # temporal bumps
    seasonal_factors = rng.uniform(0.5,1.5,4)
    df['duration'] += df['season'].map(dict(enumerate(seasonal_factors))) * df['base_duration']
    weekend_bumps = rng.uniform(0.5,1.5,size=n)
    df['duration'] += df['is_weekend'] * weekend_bumps * df['base_duration']
    hour_effects = rng.uniform(0.0,0.5,24)
    df['duration'] += df['base_duration'] * df['hour'].map(lambda h: hour_effects[h])

    df['duration'] = df['duration'].clip(lower=0.1)

    # one-hot encode team_type
    df = pd.get_dummies(df, columns=['team_type'], prefix='team_type')
    return df

# ----------------------------------------
# Model evaluation
# ----------------------------------------
def evaluate_model(X_tr, X_te, y_tr, y_te, params):
    model = xgb.XGBRegressor(objective='reg:squarederror',
                             **params, verbosity=0)
    model.fit(X_tr, y_tr)
    preds = model.predict(X_te)
    return model, preds, {
        'rmse': root_mean_squared_error(y_te, preds),
        'mae': mean_absolute_error(y_te, preds),
        'r2': r2_score(y_te, preds)
    }

# ----------------------------------------
# Plotting utilities (CLI mode)
# ----------------------------------------
def plot_prediction_distributions(all_preds):
    df_all = pd.concat([pd.DataFrame({'prediction': p, 'run': lbl})
                        for lbl,p in all_preds], ignore_index=True)
    if INTERACTIVE:
        fig = px.histogram(df_all, x='prediction', color='run',
                           marginal='rug', opacity=0.6, nbins=50,
                           barmode='overlay',
                           title='Prediction Distribution Across Runs')
        fig.update_layout(xaxis_title='Predicted Duration (hrs)',
                          yaxis_title='Count')
        fig.show()
    else:
        plt.figure(figsize=(12,5))
        sns.set(style="whitegrid")
        for lbl,p in all_preds:
            sns.kdeplot(p, label=lbl, alpha=0.3)
        combined = np.concatenate([p for _,p in all_preds])
        sns.kdeplot(combined, label='Combined', color='black', linewidth=2)
        plt.title('Prediction Distribution Across Runs')
        plt.xlabel('Predicted Duration (hrs)')
        plt.ylabel('Density')
        plt.legend()
        plt.tight_layout()
        plt.show()

def plot_team_distribution(df_fore):
    data = df_fore[['team_type','predicted_duration']].copy()
    if INTERACTIVE:
        fig = px.box(data, x='team_type', y='predicted_duration',
                     points='all', title='Predicted Duration by Team Type')
        fig.update_layout(xaxis_title='Team Type',
                          yaxis_title='Predicted Duration (hrs)')
        fig.show()
    else:
        plt.figure(figsize=(8,6))
        sns.boxplot(x='team_type', y='predicted_duration', data=data)
        plt.title('Predicted Duration by Team Type')
        plt.xlabel('Team Type')
        plt.ylabel('Predicted Duration (hrs)')
        plt.tight_layout()
        plt.show()

def plot_weekly_forecast_by_team(df_fore):
    weekly = df_fore.groupby(['week','team_type'])['predicted_duration']\
                    .mean().reset_index()
    if INTERACTIVE:
        fig = px.line(weekly, x='week', y='predicted_duration',
                      color='team_type', markers=True,
                      title='Weekly Forecasted Avg Duration by Team')
        fig.update_layout(xaxis_title='Week Number',
                          yaxis_title='Avg Predicted Duration (hrs)')
        fig.show()
    else:
        plt.figure(figsize=(12,6))
        sns.lineplot(data=weekly, x='week', y='predicted_duration',
                     hue='team_type', marker='o')
        plt.title('Weekly Forecasted Avg Duration by Team Type')
        plt.xlabel('Week Number')
        plt.ylabel('Avg Predicted Duration (hrs)')
        plt.legend(title='Team Type')
        plt.tight_layout()
        plt.show()

def shap_explain(model, X_sample):
    try:
        explainer = shap.TreeExplainer(model)
        vals = explainer.shap_values(X_sample)
        shap.summary_plot(vals, X_sample, plot_type='bar',
                          max_display=10, show=False)
        plt.tight_layout()
        plt.show()
    except Exception as e:
        logger.warning(f"Skipping SHAP: {e}")

# ----------------------------------------
# Dash app (web mode)
# ----------------------------------------
def run_dash(samples, weeks, params):
    if not DASH_AVAILABLE:
        logger.error("Dash is not installed. Install `dash` to use --dash mode.")
        sys.exit(1)

    # Prepare forecast data
    df_fore = generate_mock_data(168 * weeks)
    df_fore['week'] = df_fore['created_at'].dt.isocalendar().week

    # FEATURES list
    df0 = generate_mock_data(1)
    FEATURES = ['day_of_week','hour','month','priority_encoded',
                'team_efficiency','is_weekend','season'] + \
               [c for c in df0.columns if c.startswith('team_type_')]

    # Train model
    model = xgb.XGBRegressor(objective='reg:squarederror',
                             **params, verbosity=0)
    model.fit(df_fore[FEATURES], df_fore['duration'])
    df_fore['predicted_duration'] = model.predict(df_fore[FEATURES])

    # reconstruct team_type
    df_fore['team_type'] = df_fore.filter(like='team_type_')\
        .idxmax(axis=1).str.replace('team_type_','', regex=False)

    # precompute weekly averages
    weekly_df = df_fore.groupby(['week','team_type'])['predicted_duration']\
                       .mean().reset_index()

    # Build Dash layout
    app = dash.Dash(__name__)
    min_w, max_w = int(weekly_df.week.min()), int(weekly_df.week.max())

    app.layout = html.Div([
        html.H3("Weekly Forecasted Avg Job Duration by Team Type"),
        dcc.RangeSlider(
            id='week-slider', min=min_w, max=max_w,
            value=[min_w, max_w],
            marks={w: str(w) for w in range(min_w, max_w+1, 4)},
            tooltip={"always_visible": False}
        ),
        dcc.Graph(id='weekly-forecast-graph')
    ])

    @app.callback(
        Output('weekly-forecast-graph','figure'),
        Input('week-slider','value')
    )
    def update_chart(week_range):
        low, high = week_range
        df = weekly_df[(weekly_df.week>=low)&(weekly_df.week<=high)]
        fig = px.line(df, x='week', y='predicted_duration',
                      color='team_type', markers=True,
                      title=f"Weeks {low}–{high}")
        fig.update_layout(xaxis_title='ISO Week',
                          yaxis_title='Avg Predicted Duration (hrs)')
        return fig

    app.run_server(debug=True)

# ----------------------------------------
# Main entrypoint
# ----------------------------------------
def main(args):
    params = {
        'n_estimators': args.n_estimators,
        'max_depth':    args.max_depth,
        'learning_rate':args.learning_rate
    }

    if args.dash:
        run_dash(args.samples, args.weeks, params)
        return

    # CLI mode
    df0 = generate_mock_data(args.samples)
    FEATURES = ['day_of_week','hour','month','priority_encoded',
                'team_efficiency','is_weekend','season'] + \
               [c for c in df0.columns if c.startswith('team_type_')]

    # 1) Multi-run evaluation
    all_preds, metrics = [], {'rmse':[], 'mae':[], 'r2':[]}
    for i in range(args.runs):
        df = generate_mock_data(args.samples)
        X, y = df[FEATURES], df['duration']
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=args.test_size, random_state=i
        )
        _, preds, m = evaluate_model(X_tr, X_te, y_tr, y_te, params)
        all_preds.append((f'Run {i+1}', preds))
        for k in metrics:
            metrics[k].append(m[k])
        logger.info(
            f"Run {i+1} → RMSE={m['rmse']:.4f}, "
            f"MAE={m['mae']:.4f}, R²={m['r2']:.4f}"
        )

    logger.info(
        "Average metrics → RMSE={:.4f}, MAE={:.4f}, R²={:.4f}".format(
            np.mean(metrics['rmse']),
            np.mean(metrics['mae']),
            np.mean(metrics['r2'])
        )
    )
    plot_prediction_distributions(all_preds)

    # 2) Weekly forecasting & charts
    df_fore = generate_mock_data(168 * args.weeks)
    df_fore['week'] = df_fore['created_at'].dt.isocalendar().week
    model = xgb.XGBRegressor(objective='reg:squarederror',
                             **params, verbosity=0)
    model.fit(df_fore[FEATURES], df_fore['duration'])
    df_fore['predicted_duration'] = model.predict(df_fore[FEATURES])
    df_fore['team_type'] = df_fore.filter(like='team_type_')\
        .idxmax(axis=1).str.replace('team_type_','',regex=False)

    plot_team_distribution(df_fore)
    plot_weekly_forecast_by_team(df_fore)

    # 3) SHAP
    sample = df_fore[FEATURES].sample(
        min(len(df_fore), args.shap_sample_size),
        random_state=args.shap_random_state
    )
    shap_explain(model, sample)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs",          type=int,   default=3)
    parser.add_argument("--samples",       type=int,   default=2000)
    parser.add_argument("--test_size",     type=float, default=0.2)
    parser.add_argument("--weeks",         type=int,   default=52)
    parser.add_argument("--n_estimators",  type=int,   default=50)
    parser.add_argument("--max_depth",     type=int,   default=2)
    parser.add_argument("--learning_rate", type=float, default=0.1)
    parser.add_argument("--shap_sample_size", type=int, default=100)
    parser.add_argument("--shap_random_state",type=int, default=42)
    parser.add_argument("--dash",          action="store_true",
                        help="Launch Dash web app instead of CLI")
    args = parser.parse_args()

    main(args)
