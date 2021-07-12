# -*- coding: utf-8 -*-
"""tricks.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1UZQuMCifg3ICKehby41SKMZQGpgKf-lO
"""

import pandas as pd
import numpy as np
import math

!pip install sklearn-ts==0.0.5

"""#Load data"""

covid = pd.read_csv("https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv")
#covid.head(2)

target = 'new_cases'
h = 14

dataset = covid[(covid['location']=='World')].copy()[[target, 'date']]
dataset[[target]].plot()

# prepare features
features = ['year', 'month', f'{h}_lag', f'{h}_lag_rolling', 'dayofweek', 'intercept', 'trend', 'log']
categorical_features = ['year', 'month', 'dayofweek']
numerical_features = ['intercept', 'trend', 'log', f'{h}_lag_rolling']
lag_features= []

dataset['date'] = pd.to_datetime(dataset['date'])
dataset.index = dataset['date']
dataset['month'] = dataset['date'].dt.month
dataset['year'] = dataset['date'].dt.year
dataset['dayofweek'] = dataset['date'].dt.dayofweek

for lag in [h + i for i in range(14)]:
    dataset[f'{lag}_lag'] = dataset[target].shift(lag)
    lag_features.append(f'{lag}_lag')

dataset[f'rolling_{target}'] = dataset[target].rolling(window=h).mean()
dataset[f'{h}_lag_rolling'] = dataset[f'rolling_{target}'].shift(h)
dataset['intercept'] = 1
dataset['trend'] = range(dataset.shape[0])
dataset['log'] = dataset['trend'].apply(lambda x: math.log(x+1))
dataset = dataset[['date', target] + numerical_features + categorical_features + lag_features]
dataset = dataset.dropna()

"""# Outliers"""

from sklearn.ensemble import IsolationForest

iso = IsolationForest(random_state=0)
iso.fit(dataset[features])

scores = pd.DataFrame({
    'index': dataset.index,
    'is_inlier': iso.predict(dataset[features]), 
    'score': iso.score_samples(dataset[features]) + 0.5
})

pd.pivot_table(scores, index='index', columns='is_inlier', values='score').plot.kde()

"""# Fourier"""

from sklearn_ts.features.seasonality import add_fourier_to_X

X_with_fourier = add_fourier_to_X(dataset, periods=[7], N=[1], with_intercept=False)
X_with_fourier.head()

features = [ f'{h}_lag', f'{h}_lag_rolling', 'intercept', 'trend', 'log'] + ['fourier_sin_7_1', 'fourier_cos_7_1']

from sklearn_ts.validator import check_model

from sklearn.linear_model import LinearRegression

params = {'fit_intercept': [False]}
regressor = LinearRegression(fit_intercept=False)

results = check_model(
    regressor, params, X_with_fourier,
    target='new_cases', features=features, categorical_features=[], user_transformers=[],
    h=30, n_splits=5, gap=30,
    plotting=True
)

from sklearn_ts.features.explainer import plot_features

plot_features(results['model'], results['features'], figsize=(10, 5));

"""# Hierarchical"""

covid.head(2)

continents = covid['continent'].dropna().unique()

dataset = covid[(covid['location']=='World') | (covid['location'].isin(continents))].copy()[['location', target, 'date']]
dataset['date'] = pd.to_datetime(dataset['date'])
#dataset.index = dataset['date']

dataset.head()

from matplotlib import pyplot as plt

fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(10, 6))
pivoted = pd.pivot_table(dataset, values='new_cases', index='date', columns='location', aggfunc='sum')[['World'] + sorted(list(continents))]
pivoted.plot(title='Hierarchical example', ax=axes)
fig.savefig(f'continents.png')

!pip install scikit-hts

import hts

pivoted.head()

# necessary
hierarchy = {'total': list(continents)}
pivoted = pivoted.rename(columns={'World': 'total'})

model_bu_arima = hts.HTSRegressor(model='prophet', revision_method='OLS', n_jobs=0)
model_bu_arima = model_bu_arima.fit(pivoted, hierarchy)

pred_bu_arima = model_bu_arima.predict(steps_ahead=14)

fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(10, 6))
pred_bu_arima.plot(title='Hierarchical example', ax=axes)
fig.savefig(f'continents_predicted.png')

"""# Power transform

## Box-Cox
"""

from sklearn.preprocessing import PowerTransformer
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import LinearRegression

dataset = covid[(covid['location']=='World')].copy()[[target, 'date']]
dataset[[target]].plot()

# prepare features
features = ['year', 'month', f'{h}_lag', f'{h}_lag_rolling', 'dayofweek', 'intercept', 'trend', 'log']
categorical_features = ['year', 'month', 'dayofweek']
numerical_features = ['intercept', 'trend', 'log', f'{h}_lag_rolling']
lag_features= []

dataset['date'] = pd.to_datetime(dataset['date'])
dataset.index = dataset['date']
dataset['month'] = dataset['date'].dt.month
dataset['year'] = dataset['date'].dt.year
dataset['dayofweek'] = dataset['date'].dt.dayofweek

for lag in [h + i for i in range(14)]:
    dataset[f'{lag}_lag'] = dataset[target].shift(lag)
    lag_features.append(f'{lag}_lag')

dataset[f'rolling_{target}'] = dataset[target].rolling(window=h).mean()
dataset[f'{h}_lag_rolling'] = dataset[f'rolling_{target}'].shift(h)
dataset['intercept'] = 1
dataset['trend'] = range(dataset.shape[0])
dataset['log'] = dataset['trend'].apply(lambda x: math.log(x+1))
dataset = dataset[['date', target] + numerical_features + categorical_features + lag_features]
dataset = dataset.dropna()

pt = PowerTransformer(method='box-cox')
dataset['box-cox'] = np.squeeze(pt.fit_transform(dataset[['new_cases']]+1))
pt.lambdas_

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import FunctionTransformer
from sklearn.pipeline import Pipeline

preprocessor = ColumnTransformer(
    transformers=[('num', FunctionTransformer(), numerical_features)]
)

pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('regressor', LinearRegression())])

tt = TransformedTargetRegressor(regressor=pipeline, transformer=PowerTransformer(method='box-cox'))
tt.fit(dataset[numerical_features], dataset[target])

dataset['pred'] = tt.predict(dataset[numerical_features])

dataset[['pred', 'new_cases', 'box-cox']].plot()

dataset['box-cox'].hist()

dataset['new_cases'].hist()

tt.regressor.named_steps['regressor']

tt.transformer.lambdas_

