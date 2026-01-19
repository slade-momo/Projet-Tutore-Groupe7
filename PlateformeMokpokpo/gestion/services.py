import pandas as pd
import numpy as np
from prophet import Prophet
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import base64
import warnings
warnings.filterwarnings('ignore')

class StockAnalyticsService:
    @staticmethod
    def generate_stock_data():
        """Données EXACTEMENT comme votre Colab"""
        np.random.seed(42)
        capacite_max = 50000
        stock_initial = 41000
        seuil_critique = 10000
        
        dates = pd.date_range(start="2021-01-01", periods=60, freq="MS")
        entrees, sorties, stock = [], [], []
        stock_actuel = stock_initial
        
        for d in dates:
            month_num = d.month
            
            # Entrées saisonnières (Fév-Mai)
            entrees.append(np.random.randint(3000, 6000) if month_num in [2,3,4,5] else np.random.randint(500, 2000))
            
            # Sorties saisonnières (Aoû-Déc)
            sorties.append(np.random.randint(2500, 4000) if month_num in [8,9,10,11,12] else np.random.randint(1000, 2500))
            
            stock_actuel = max(0, min(capacite_max, stock_actuel + entrees[-1] - sorties[-1]))
            stock.append(stock_actuel)
        
        df_stock = pd.DataFrame({
            'ds': dates,
            'entrees': entrees,
            'sorties': sorties,
            'stock': stock
        })
        
        df_stock['alerte'] = df_stock['stock'].apply(lambda x: 'CRITIQUE' if x < seuil_critique else 'OK')
        df_stock['remplissage'] = (df_stock['stock'] / capacite_max) * 100
        
        df_prophet = df_stock[['ds', 'stock']].rename(columns={'stock': 'y'})
        
        return df_stock, df_prophet

    @staticmethod
    def analyze_complete():
        """Pipeline COMPLET = votre Colab"""
        df_stock, df_prophet = StockAnalyticsService.generate_stock_data()
        
        # Prophet (comme votre Colab)
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False
        )
        model.fit(df_prophet)
        
        future = model.make_future_dataframe(periods=36, freq='MS')
        forecast = model.predict(future)
        
        # Métriques
        capacite_max = 50000
        seuil_critique = 10000
        
        forecast['alerte'] = forecast['yhat'].apply(lambda x: 'CRITIQUE' if x < seuil_critique else 'OK')
        forecast['remplissage'] = (forecast['yhat'] / capacite_max) * 100
        
        # Données par année (EXACTEMENT comme Colab)
        years_data = {}
        for year in [2026, 2027, 2028]:
            year_df = forecast[forecast['ds'].dt.year == year][['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'alerte', 'remplissage']]
            years_data[f'forecast_{year}'] = year_df.round(0).to_dict('records')
        
        # Précision MAPE
        y_true = df_prophet['y'].values
        y_pred = forecast.head(len(df_prophet))['yhat'].values
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        precision = round(100 - mape, 2)
        
        return {
            # KPIs
            'current_stock': int(df_stock['stock'].iloc[-1]),
            'precision': precision,
            'capacite_max': capacite_max,
            'seuil_critique': seuil_critique,
            
            # Données historiques
            'historique_stock': df_stock.tail(12).round(0).to_dict('records'),
            'historique_prophet': df_prophet.tail(12).round(0).to_dict('records'),
            
            # Prévisions par année
            **years_data,
            
            # Graphiques (TOUS ceux de votre Colab)
            'img_forecast': StockAnalyticsService.plot_forecast(model, forecast),
            'img_components': StockAnalyticsService.plot_components(model, forecast),
            'img_2026': StockAnalyticsService.plot_year_bar(years_data['forecast_2026'], '2026'),
            'img_2027': StockAnalyticsService.plot_year_bar(years_data['forecast_2027'], '2027'),
            'img_2028': StockAnalyticsService.plot_year_bar(years_data['forecast_2028'], '2028'),
        }

    @staticmethod
    def plot_forecast(model, forecast):
        """fig1 de votre Colab"""
        fig, ax = plt.subplots(figsize=(14, 8))
        model.plot(forecast, ax=ax)
        ax.set_title('Prévision Complète Stock - Ferme Mokpokpo', fontsize=16, fontweight='bold')
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def plot_components(model, forecast):
        """fig2 de votre Colab"""
        fig = model.plot_components(forecast, figsize=(14, 10))
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def plot_year_bar(year_data, year):
        """Barcharts EXACTS de votre Colab"""
        if not year_data:
            return ""
        
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        months = [pd.to_datetime(d['ds']).month for d in year_data]
        yhat = [float(d['yhat']) for d in year_data]
        
        norm = plt.Normalize(min(yhat), max(yhat))
        colors = plt.cm.RdYlGn(norm(yhat))
        
        bars = ax.bar(range(1, 13), yhat, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        ax.set_title(f'Prévision Stock (kg) par Mois pour {year}', fontsize=14, fontweight='bold')
        ax.set_xlabel('Mois')
        ax.set_ylabel('Stock Prévu (kg)')
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 
                           'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'])
        ax.grid(True, linestyle='--', alpha=0.3)
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        return base64.b64encode(buffer.getvalue()).decode()
