from django.contrib import admin
from .models import (
    Client, Produit, Producteur, Entrepot, ZoneEntrepot,
    Lot, Commande, MouvementStock, Vente, HistoriqueTracabilite,
    AffectationLot, AlerteStock, DemandeAchat, LigneCommande,
    PreparationCommande, VenteImmediate,
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'entreprise', 'telephone', 'email', 'type_client')
    search_fields = ('nom', 'prenom', 'email', 'entreprise')
    list_filter = ('type_client',)


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie', 'unite', 'prix_unitaire', 'stock_disponible')
    search_fields = ('nom', 'categorie')
    list_filter = ('categorie',)


@admin.register(Producteur)
class ProducteurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'type_producteur', 'statut', 'telephone')
    search_fields = ('nom', 'prenom', 'numero_identification')
    list_filter = ('type_producteur', 'statut')


@admin.register(Entrepot)
class EntrepotAdmin(admin.ModelAdmin):
    list_display = ('nom', 'localisation', 'capacite_max', 'quantite_disponible', 'statut')
    search_fields = ('nom', 'localisation')
    list_filter = ('statut',)


@admin.register(ZoneEntrepot)
class ZoneEntrepotAdmin(admin.ModelAdmin):
    list_display = ('nom', 'entrepot', 'capacite', 'quantite', 'statut')
    search_fields = ('nom',)
    list_filter = ('statut', 'entrepot')


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ('code_lot', 'produit', 'quantite_restante', 'qualite', 'etat', 'date_expiration')
    search_fields = ('code_lot',)
    list_filter = ('etat', 'qualite')


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('numero_commande', 'client', 'statut', 'priorite', 'date_commande')
    search_fields = ('numero_commande',)
    list_filter = ('statut', 'priorite')


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ('lot', 'type_mouvement', 'quantite', 'date_mouvement', 'valide')
    list_filter = ('type_mouvement', 'valide')


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ('numero_vente', 'client', 'lot', 'quantite_vendue', 'montant_total', 'mode_paiement', 'type_vente')
    search_fields = ('numero_vente',)
    list_filter = ('mode_paiement', 'type_vente')


@admin.register(HistoriqueTracabilite)
class HistoriqueTracabiliteAdmin(admin.ModelAdmin):
    list_display = ('type_action', 'lot', 'date_action', 'user')
    search_fields = ('type_action', 'description')
    list_filter = ('type_action',)


@admin.register(AffectationLot)
class AffectationLotAdmin(admin.ModelAdmin):
    list_display = ('commande', 'lot', 'quantite_affectee', 'statut')
    list_filter = ('statut',)


@admin.register(AlerteStock)
class AlerteStockAdmin(admin.ModelAdmin):
    list_display = ('produit', 'stock_actuel', 'seuil_alerte', 'statut', 'date_alerte')
    list_filter = ('statut',)


@admin.register(DemandeAchat)
class DemandeAchatAdmin(admin.ModelAdmin):
    list_display = ('numero_da', 'produit', 'quantite_a_commander', 'statut', 'priorite')
    search_fields = ('numero_da',)
    list_filter = ('statut', 'priorite')


@admin.register(LigneCommande)
class LigneCommandeAdmin(admin.ModelAdmin):
    list_display = ('commande', 'produit', 'quantite_demandee', 'statut_ligne')
    list_filter = ('statut_ligne',)


@admin.register(PreparationCommande)
class PreparationCommandeAdmin(admin.ModelAdmin):
    list_display = ('commande', 'zone', 'statut', 'date_debut', 'date_fin')
    list_filter = ('statut',)


@admin.register(VenteImmediate)
class VenteImmediateAdmin(admin.ModelAdmin):
    list_display = ('numero_vente', 'produit', 'quantite_demandee', 'type_vente', 'montant_total')
    search_fields = ('numero_vente',)
    list_filter = ('type_vente',)
