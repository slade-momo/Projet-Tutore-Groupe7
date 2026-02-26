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
    path('produits/<int:pk>/', views.produits_detail, name='produits_detail'),
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
    path('ventes/<int:pk>/', views.ventes_detail, name='ventes_detail'),
    path('ventes/<int:pk>/update/', views.ventes_update, name='ventes_update'),
    path('ventes/<int:pk>/delete/', views.ventes_delete, name='ventes_delete'),
    
    # Mouvements
    path('mouvements/', views.mouvements_list, name='mouvements_list'),
    path('mouvements/create/', views.mouvements_create, name='mouvements_create'),
    path('mouvements/<int:pk>/delete/', views.mouvements_delete, name='mouvements_delete'),
    
    # Historique
    path('historique/', views.historique_list, name='historique_list'),
    path('historique/<int:pk>/', views.historique_detail, name='historique_detail'),

    # Prévisions de stock
    path('stock-forecast/', views.stock_forecast_view, name='stock_prediction'),

    # Commandes
    path('commandes/', views.commandes_list, name='commandes_list'),
    path('commandes/create/', views.commandes_create, name='commandes_create'),
    path('commandes/<int:pk>/', views.commandes_detail, name='commandes_detail'),
    path('commandes/<int:pk>/update/', views.commandes_update, name='commandes_update'),
    path('commandes/<int:pk>/delete/', views.commandes_delete, name='commandes_delete'),
    path('commandes/<int:pk>/accepter/', views.commande_accepter_view, name='commande_accepter'),
    path('commandes/<int:pk>/confirmer/', views.commande_confirmer_view, name='commande_confirmer'),
    path('commandes/<int:pk>/livrer/', views.commande_livrer_view, name='commande_livrer'),

    # Alertes de stock
    path('alertes/', views.alertes_list, name='alertes_list'),
    path('alertes/<int:pk>/generer-da/', views.alerte_generer_da_view, name='alerte_generer_da'),
    path('alertes/<int:pk>/traiter/', views.alerte_traiter_view, name='alerte_traiter'),

    # Demandes d'achat
    path('demandes/', views.demandes_list, name='demandes_list'),
    path('demandes/create/', views.demandes_create, name='demandes_create'),
    path('demandes/<int:pk>/<str:action>/', views.demande_action_view, name='demande_action'),

    # Ventes immédiates
    path('ventes-immediates/', views.ventes_immediates_list, name='ventes_immediates_list'),
    path('ventes-immediates/create/', views.ventes_immediates_create, name='ventes_immediates_create'),
    path('ventes-immediates/<int:pk>/delete/', views.ventes_immediates_delete, name='ventes_immediates_delete'),

    # API endpoints (AJAX)
    path('api/stock/<int:pk>/', views.api_stock_produit, name='api_stock_produit'),
    path('api/check-disponibilite-vi/', views.api_check_disponibilite_vi, name='api_check_disponibilite_vi'),
]
