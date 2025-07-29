# Re-import required packages due to environment reset
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb
from sklearn.model_selection import train_test_split

# Dynamic configuration
N_EXPERIMENTS = 3
N_JOBS = 2000
PREDICTION_STORAGE = []

sns.set(style="whitegrid")

# Define job priority and duration mappings
priority_map = {'Critical': 3, 'High': 2, 'Medium': 1, 'Low': 0}
base_duration = {'Critical': 1.5, 'High': 3.0, 'Medium': 5.0, 'Low': 7.0}
features = ['day_of_week', 'hour', 'month', 'priority_encoded', 'team_efficiency']

# Generate mock job data
def generate_mock_data(n):
    df = pd.DataFrame({
        'priority': np.random.choice(['Critical', 'High', 'Medium', 'Low'], size=n, p=[0.15, 0.3, 0.4, 0.15]),
        'team_efficiency': np.random.uniform(0.6, 1.0, size=n),
        'created_at': pd.date_range('2024-01-01', periods=n, freq='h')
    })
    df['priority_encoded'] = df['priority'].map(priority_map)
    df['day_of_week'] = df['created_at'].dt.dayofweek
    df['hour'] = df['created_at'].dt.hour
    df['month'] = df['created_at'].dt.month
    df['base_duration'] = df['priority'].map(base_duration)
    df['duration'] = (
        df['base_duration'] * np.random.uniform(0.8, 1.2, size=n) +
        (1 - df['team_efficiency']) * np.random.uniform(1.0, 4.0, size=n) +
        np.random.normal(0, 0.3, size=n)
    )
    return df

# Plot training run prediction densities
plt.figure(figsize=(14, 6))
for i in range(N_EXPERIMENTS):
    data = generate_mock_data(N_JOBS)
    X = data[features]
    y = data['duration']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=i)

    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=50,
        max_depth=2,
        learning_rate=0.1,
        verbosity=0
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    PREDICTION_STORAGE.append((f'Run {i+1}', y_pred))
    sns.kdeplot(y_pred, label=f'Run {i+1}', alpha=0.3)

# Combine predictions and show overall density
combined = np.concatenate([pred for _, pred in PREDICTION_STORAGE])
sns.kdeplot(combined, label='Combined Prediction', color='black', linewidth=2)

plt.title('Distribution of Predictions Across Training Runs')
plt.xlabel('Predicted Duration (Hours)')
plt.ylabel('Density')
plt.legend()
plt.tight_layout()
plt.show()

# Train final model and generate forecast
forecast_data = generate_mock_data(168*52)  # One week's worth of hourly jobs
forecast_data['week'] = forecast_data['created_at'].dt.isocalendar().week

# Train model on new full batch
X_final = forecast_data[features]
y_final = forecast_data['duration']
final_model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=50, max_depth=2, learning_rate=0.1)
final_model.fit(X_final, y_final)

# Weekly forecasting
forecast_data['predicted_duration'] = final_model.predict(X_final)
weekly_forecast = forecast_data.groupby('week')['predicted_duration'].mean().reset_index()

# Plot weekly forecast
plt.figure(figsize=(12, 5))
sns.lineplot(data=weekly_forecast, x='week', y='predicted_duration', marker='o', color='purple')
plt.title('Weekly Forecasted Average Job Duration')
plt.xlabel('Week Number')
plt.ylabel('Avg Predicted Duration (Hours)')
plt.tight_layout()
plt.show()

import ace_tools_open as tools  # noqa: E402

tools.display_dataframe_to_user(name="Weekly Forecasted Jobs", dataframe=forecast_data[features + ['predicted_duration']])