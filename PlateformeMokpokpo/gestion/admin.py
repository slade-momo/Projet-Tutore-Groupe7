from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Clients, Produits, Lots, Ventes, Entrepots, ZoneEntrepots,
    Producteurs, MouvementStocks, HistoriqueTracabilites
)


@admin.register(Clients)
class ClientsAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'entreprise', 'email', 'telephone', 'date_inscription')
    list_filter = ('date_inscription', 'entreprise')
    search_fields = ('nom', 'prenom', 'email', 'telephone')
    ordering = ('-date_inscription',)
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('nom', 'prenom', 'entreprise')
        }),
        ('Coordonnées', {
            'fields': ('telephone', 'email', 'adresse')
        }),
        ('Dates', {
            'fields': ('date_inscription',)
        }),
    )


@admin.register(Produits)
class ProduitsAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie', 'unite', 'prix_unitaire')
    list_filter = ('categorie',)
    search_fields = ('nom', 'categorie')
    fieldsets = (
        ('Général', {
            'fields': ('nom', 'categorie', 'unite')
        }),
        ('Pricing', {
            'fields': ('prix_unitaire',)
        }),
        ('Description', {
            'fields': ('description',)
        }),
    )


@admin.register(Producteurs)
class ProducteursAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'type_producteur', 'statut', 'date_inscription')
    list_filter = ('type_producteur', 'statut', 'date_inscription')
    search_fields = ('nom', 'prenom', 'numero_identification')
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('nom', 'prenom')
        }),
        ('Professionnel', {
            'fields': ('type_producteur', 'numero_identification')
        }),
        ('Localisation', {
            'fields': ('localisation', 'telephone')
        }),
        ('Statut', {
            'fields': ('statut', 'date_inscription')
        }),
        ('Notes', {
            'fields': ('observations',)
        }),
    )


@admin.register(Entrepots)
class EntrepotsAdmin(admin.ModelAdmin):
    list_display = ('nom', 'localisation', 'statut_badge', 'capacite_max', 'responsable')
    list_filter = ('statut', 'date_creation')
    search_fields = ('nom', 'localisation')
    fieldsets = (
        ('Général', {
            'fields': ('nom', 'localisation', 'responsable')
        }),
        ('Capacité', {
            'fields': ('capacite_max', 'seuil_critique', 'quantite_disponible')
        }),
        ('Statut', {
            'fields': ('statut',)
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_maj')
        }),
    )

    def statut_badge(self, obj):
        color = 'green' if obj.statut == 'actif' else 'red'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.statut
        )
    statut_badge.short_description = 'Statut'


@admin.register(ZoneEntrepots)
class ZoneEntrepotsAdmin(admin.ModelAdmin):
    list_display = ('nom', 'entrepot', 'statut', 'capacite', 'responsable')
    list_filter = ('entrepot', 'statut')
    search_fields = ('nom', 'entrepot__nom')
    fieldsets = (
        ('Général', {
            'fields': ('nom', 'entrepot', 'responsable')
        }),
        ('Capacité', {
            'fields': ('capacite', 'quantite')
        }),
        ('Statut', {
            'fields': ('statut', 'description')
        }),
    )


@admin.register(Lots)
class LotsAdmin(admin.ModelAdmin):
    list_display = ('code_lot', 'produit', 'qualite', 'get_etat_badge', 'quantite_restante', 'date_expiration')
    list_filter = ('etat', 'qualite', 'date_reception', 'date_expiration')  # 'etat' maintenant filtrable
    search_fields = ('code_lot', 'produit__nom')
    
    # Champ pour afficher l'état avec badge coloré
    def get_etat_badge(self, obj):
        if not obj.etat:
            return format_html('<span style="background-color: gray; color: white; padding: 3px 8px; border-radius: 3px;">Non défini</span>')
        
        colors = {
            'en_stock': 'green',
            'reserve': 'orange', 
            'en_transit': 'blue',
            'expedie': 'purple',
            'perdu': 'red',
            'detruire': 'darkred',
        }
        color = colors.get(obj.etat, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, dict(obj.ETATS_CHOICES).get(obj.etat, obj.etat)
        )
    get_etat_badge.short_description = 'État'
    

@admin.register(MouvementStocks)
class MouvementStocksAdmin(admin.ModelAdmin):
    list_display = ('date_mouvement', 'type_mouvement', 'lot', 'quantite', 'user')
    list_filter = ('type_mouvement', 'date_mouvement', 'valide')
    search_fields = ('lot__code_lot', 'motif')
    fieldsets = (
        ('Mouvement', {
            'fields': ('type_mouvement', 'quantite', 'date_mouvement')
        }),
        ('Lot', {
            'fields': ('lot',)
        }),
        ('Zones', {
            'fields': ('zone_origine', 'zone_destination')
        }),
        ('Validation', {
            'fields': ('valide', 'user')
        }),
        ('Justification', {
            'fields': ('motif',)
        }),
    )
    readonly_fields = ('date_mouvement', 'user')


@admin.register(Ventes)
class VentesAdmin(admin.ModelAdmin):
    list_display = ('numero_vente', 'client', 'lot', 'quantite_vendue', 'montant_total', 'date_vente')
    list_filter = ('date_vente', 'mode_paiement')
    search_fields = ('numero_vente', 'client__nom', 'lot__code_lot')
    fieldsets = (
        ('Identification', {
            'fields': ('numero_vente', 'date_vente')
        }),
        ('Client', {
            'fields': ('client',)
        }),
        ('Lot', {
            'fields': ('lot',)
        }),
        ('Quantités et Prix', {
            'fields': ('quantite_vendue', 'prix_unitaire', 'montant_total')
        }),
        ('Paiement', {
            'fields': ('mode_paiement',)
        }),
        ('Responsable', {
            'fields': ('user',)
        }),
        ('Notes', {
            'fields': ('observations',)
        }),
    )


@admin.register(HistoriqueTracabilites)
class HistoriqueTracabilitesAdmin(admin.ModelAdmin):
    list_display = ('date_action', 'type_action', 'lot', 'user')
    list_filter = ('type_action', 'date_action')
    search_fields = ('lot__code_lot', 'type_action', 'description')
    readonly_fields = ('date_action', 'user', 'ancienne_valeur', 'nouvelle_valeur')
    fieldsets = (
        ('Action', {
            'fields': ('type_action', 'date_action', 'user')
        }),
        ('Lot concerné', {
            'fields': ('lot',)
        }),
        ('Changements', {
            'fields': ('ancienne_valeur', 'nouvelle_valeur')
        }),
        ('Description', {
            'fields': ('description',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Enregistrer l'utilisateur automatiquement"""
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)
