from django import forms
from .models import (
    Clients, Produits, Lots, Ventes, Entrepots, ZoneEntrepots,
    Producteurs, MouvementStocks, HistoriqueTracabilites
)


class ClientsForm(forms.ModelForm):
    class Meta:
        model = Clients
        fields = ['nom', 'prenom', 'entreprise', 'telephone', 'email', 'adresse']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
            'entreprise': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Entreprise'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Téléphone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Adresse', 'rows': 3}),
        }


class ProduitsForm(forms.ModelForm):
    class Meta:
        model = Produits
        fields = ['nom', 'categorie', 'unite', 'prix_unitaire', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du produit'}),
            'categorie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Catégorie'}),
            'unite': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unité (ex: kg, L)'}),
            'prix_unitaire': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Prix unitaire', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description', 'rows': 4}),
        }


class ProducteursForm(forms.ModelForm):
    class Meta:
        model = Producteurs
        fields = ['nom', 'prenom', 'type_producteur', 'numero_identification', 'localisation', 'telephone', 'statut', 'observations']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
            'type_producteur': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type de producteur'}),
            'numero_identification': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro d\'identification'}),
            'localisation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Localisation'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Téléphone'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'observations': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Observations', 'rows': 3}),
        }


class EntrepotsForm(forms.ModelForm):
    class Meta:
        model = Entrepots
        fields = ['nom', 'localisation', 'capacite_max', 'seuil_critique', 'quantite_disponible', 'statut', 'responsable']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de l\'entrepôt'}),
            'localisation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Localisation'}),
            'capacite_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Capacité maximale', 'step': '0.01'}),
            'seuil_critique': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Seuil critique', 'step': '0.01'}),
            'quantite_disponible': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantité disponible', 'step': '0.01'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'responsable': forms.Select(attrs={'class': 'form-control'}),
        }


class ZoneEntrepotsForm(forms.ModelForm):
    class Meta:
        model = ZoneEntrepots
        fields = ['nom', 'entrepot', 'capacite', 'quantite', 'statut', 'responsable', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de la zone'}),
            'entrepot': forms.Select(attrs={'class': 'form-control'}),
            'capacite': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Capacité', 'step': '0.01'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantité', 'step': '0.01'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'responsable': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description', 'rows': 3}),
        }


class LotsForm(forms.ModelForm):
    class Meta:
        model = Lots
        fields = ['code_lot', 'produit', 'producteur', 'quantite_initiale', 'quantite_restante', 'qualite', 'etat', 'date_reception', 'date_expiration', 'zone', 'observations']
        widgets = {
            'code_lot': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Code du lot'}),
            'produit': forms.Select(attrs={'class': 'form-control'}),
            'producteur': forms.Select(attrs={'class': 'form-control'}),
            'quantite_initiale': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantité initiale', 'step': '0.01'}),
            'quantite_restante': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantité restante', 'step': '0.01'}),
            'qualite': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Qualité'}),
            'etat': forms.Select(attrs={'class': 'form-control'}),
            'date_reception': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_expiration': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'observations': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Observations', 'rows': 3}),
        }


class VentesForm(forms.ModelForm):
    class Meta:
        model = Ventes
        fields = ['numero_vente', 'client', 'lot', 'quantite_vendue', 'prix_unitaire', 'montant_total', 'mode_paiement', 'observations']
        widgets = {
            'numero_vente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro de vente'}),
            'client': forms.Select(attrs={'class': 'form-control'}),
            'lot': forms.Select(attrs={'class': 'form-control'}),
            'quantite_vendue': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantité vendue', 'step': '0.01'}),
            'prix_unitaire': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Prix unitaire', 'step': '0.01'}),
            'montant_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Montant total', 'step': '0.01'}),
            'mode_paiement': forms.Select(attrs={'class': 'form-control'}),
            'observations': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Observations', 'rows': 3}),
        }


class MouvementStocksForm(forms.ModelForm):
    class Meta:
        model = MouvementStocks
        fields = ['type_mouvement', 'lot', 'quantite', 'zone_origine', 'zone_destination', 'valide', 'motif']
        widgets = {
            'type_mouvement': forms.Select(attrs={'class': 'form-control'}),
            'lot': forms.Select(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantité', 'step': '0.01'}),
            'zone_origine': forms.Select(attrs={'class': 'form-control'}),
            'zone_destination': forms.Select(attrs={'class': 'form-control'}),
            'valide': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'motif': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Motif', 'rows': 3}),
        }


class HistoriqueTracabilitesForm(forms.ModelForm):
    class Meta:
        model = HistoriqueTracabilites
        fields = ['lot', 'type_action', 'ancienne_valeur', 'nouvelle_valeur', 'description']
        widgets = {
            'lot': forms.Select(attrs={'class': 'form-control'}),
            'type_action': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type d\'action'}),
            'ancienne_valeur': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Ancienne valeur', 'rows': 2}),
            'nouvelle_valeur': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Nouvelle valeur', 'rows': 2}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description', 'rows': 3}),
        }
