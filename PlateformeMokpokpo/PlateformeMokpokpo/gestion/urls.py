from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Clients
    path('clients/', views.clients_list, name='clients_list'),
    path('clients/create/', views.clients_create, name='clients_create'),
    path('clients/<int:pk>/', views.clients_detail, name='clients_detail'),
    path('clients/<int:pk>/update/', views.clients_update, name='clients_update'),
    path('clients/<int:pk>/delete/', views.clients_delete, name='clients_delete'),
    
    # Produits
    path('produits/', views.produits_list, name='produits_list'),
    path('produits/create/', views.produits_create, name='produits_create'),
    path('produits/<int:pk>/update/', views.produits_update, name='produits_update'),
    path('produits/<int:pk>/delete/', views.produits_delete, name='produits_delete'),
    
    # Producteurs
    path('producteurs/', views.producteurs_list, name='producteurs_list'),
    path('producteurs/create/', views.producteurs_create, name='producteurs_create'),
    path('producteurs/<int:pk>/', views.producteurs_detail, name='producteurs_detail'),
    path('producteurs/<int:pk>/update/', views.producteurs_update, name='producteurs_update'),
    path('producteurs/<int:pk>/delete/', views.producteurs_delete, name='producteurs_delete'),
    
    # Entrepots
    path('entrepots/', views.entrepots_list, name='entrepots_list'),
    path('entrepots/create/', views.entrepots_create, name='entrepots_create'),
    path('entrepots/<int:pk>/', views.entrepots_detail, name='entrepots_detail'),
    path('entrepots/<int:pk>/update/', views.entrepots_update, name='entrepots_update'),
    path('entrepots/<int:pk>/delete/', views.entrepots_delete, name='entrepots_delete'),
    
    # Zones
    path('zones/', views.zones_list, name='zones_list'),
    path('zones/create/', views.zones_create, name='zones_create'),
    path('zones/<int:pk>/update/', views.zones_update, name='zones_update'),
    path('zones/<int:pk>/delete/', views.zones_delete, name='zones_delete'),
    
    # Lots
    path('lots/', views.lots_list, name='lots_list'),
    path('lots/create/', views.lots_create, name='lots_create'),
    path('lots/<int:pk>/', views.lots_detail, name='lots_detail'),
    path('lots/<int:pk>/update/', views.lots_update, name='lots_update'),
    path('lots/<int:pk>/delete/', views.lots_delete, name='lots_delete'),
    
    # Ventes
    path('ventes/', views.ventes_list, name='ventes_list'),
    path('ventes/create/', views.ventes_create, name='ventes_create'),
    path('ventes/<int:pk>/update/', views.ventes_update, name='ventes_update'),
    path('ventes/<int:pk>/delete/', views.ventes_delete, name='ventes_delete'),
    
    # Mouvements
    path('mouvements/', views.mouvements_list, name='mouvements_list'),
    path('mouvements/create/', views.mouvements_create, name='mouvements_create'),
    path('mouvements/<int:pk>/delete/', views.mouvements_delete, name='mouvements_delete'),
    
    # Historique
    path('historique/', views.historique_list, name='historique_list'),

    # Prévisions de stock
    path('stock-forecast/', views.stock_forecast_view, name='stock_prediction'),
]
