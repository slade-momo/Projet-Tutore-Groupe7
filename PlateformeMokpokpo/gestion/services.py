import pandas as pd
import numpy as np
from prophet import Prophet
import io
import base64

class StockAnalyticsService:
    @staticmethod
    def process_forecast(historique_donnees=None):
        # 1. Configuration des constantes (comme dans ton Colab)
        capacite_max = 50000
        seuil_critique = 10000
        
        # 2. Préparation des données (Utilise les données réelles ou simule si vide)
        if not historique_donnees:
            # Simulation identique à ton Colab pour test
            mois_list = pd.date_range(start="2025-01-01", periods=12, freq="MS")
            df = pd.DataFrame({
                'ds': mois_list,
                'y': [41000, 42000, 44000, 46000, 47000, 45000, 43000, 40000, 37000, 34000, 31000, 29000]
            })
        else:
            df = pd.DataFrame(historique_donnees)
            df['ds'] = pd.to_datetime(df['ds'])
            df['y'] = df['y']

        # 3. Modèle Prophet
        model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        model.fit(df)

        # 4. Prédiction sur 6 mois
        future = model.make_future_dataframe(periods=6, freq='MS')
        forecast = model.predict(future)

        # 5. Calcul des KPIs additionnels du Colab
        forecast['alerte'] = forecast['yhat'].apply(lambda x: "CRITIQUE" if x < seuil_critique else "OK")
        forecast['remplissage'] = (forecast['yhat'] / capacite_max) * 100
        
        # Calcul de l'erreur MAPE (Précision)
        y_true = df['y'].values
        y_pred = forecast.iloc[:len(df)]['yhat'].values
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        precision = round(100 - mape, 2)

        return {
            'full_data': forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'alerte', 'remplissage']].tail(12).to_dict(orient='records'),
            'precision': precision,
            'current_stock': round(df['y'].iloc[-1], 0),
            'capacite_max': capacite_max,
            'seuil_critique': seuil_critique
        }