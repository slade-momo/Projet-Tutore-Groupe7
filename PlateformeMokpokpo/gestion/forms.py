from django import forms
from .models import (
    Client, Produit, Producteur, Entrepot, ZoneEntrepot,
    Lot, MouvementStock, Vente, Commande, VenteImmediate, DemandeAchat,
)
from .services import (
    generate_lot_code, generate_vente_numero,
    generate_commande_numero, generate_vente_immediate_numero,
    generate_demande_achat_numero,
)


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'nom', 'prenom', 'entreprise', 'telephone',
            'email', 'adresse', 'type_client',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'entreprise': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'adresse': forms.TextInput(attrs={'class': 'form-control'}),
            'type_client': forms.Select(attrs={'class': 'form-select'}),
        }


class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = [
            'nom', 'categorie', 'unite', 'prix_unitaire',
            'stock_physique', 'stock_reserve', 'stock_tampon_comptoir',
            'seuil_alerte', 'quantite_optimale_commande', 'description',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'categorie': forms.TextInput(attrs={'class': 'form-control'}),
            'unite': forms.TextInput(attrs={'class': 'form-control'}),
            'prix_unitaire': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'stock_physique': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'placeholder': '0.00', 'min': '0',
            }),
            'stock_reserve': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'placeholder': '0.00', 'min': '0',
            }),
            'stock_tampon_comptoir': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'min': '0',
            }),
            'seuil_alerte': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'quantite_optimale_commande': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
            }),
        }
        labels = {
            'stock_physique': 'Stock Physique (= Disponible)',
            'stock_reserve': 'Stock Réservé',
            'stock_tampon_comptoir': 'Stock Tampon',
        }

    def clean_stock_physique(self):
        from decimal import Decimal
        val = self.cleaned_data.get('stock_physique')
        if val is not None and val < Decimal('0.00'):
            raise forms.ValidationError('Le stock physique ne peut pas être négatif.')
        return val

    def clean_stock_reserve(self):
        from decimal import Decimal
        val = self.cleaned_data.get('stock_reserve')
        if val is not None and val < Decimal('0.00'):
            raise forms.ValidationError('Le stock réservé ne peut pas être négatif.')
        return val

    def clean_stock_tampon_comptoir(self):
        from decimal import Decimal
        val = self.cleaned_data.get('stock_tampon_comptoir')
        if val is not None and val < Decimal('0.00'):
            raise forms.ValidationError('Le stock tampon ne peut pas être négatif.')
        return val

    def clean(self):
        cleaned = super().clean()
        from decimal import Decimal
        sp = cleaned.get('stock_physique') or Decimal('0.00')
        sr = cleaned.get('stock_reserve') or Decimal('0.00')
        st = cleaned.get('stock_tampon_comptoir') or Decimal('0.00')
        if sr + st > sp:
            raise forms.ValidationError(
                f'Stock réservé ({sr}) + tampon ({st}) = {sr + st} '
                f'ne peut pas dépasser le stock physique ({sp}).'
            )
        return cleaned


class ProducteurForm(forms.ModelForm):
    class Meta:
        model = Producteur
        fields = [
            'nom', 'prenom', 'type_producteur', 'statut',
            'numero_identification', 'telephone', 'localisation', 'observations',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'type_producteur': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'numero_identification': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'localisation': forms.TextInput(attrs={'class': 'form-control'}),
            'observations': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
            }),
        }


class EntrepotForm(forms.ModelForm):
    class Meta:
        model = Entrepot
        fields = [
            'nom', 'localisation', 'responsable', 'statut',
            'capacite_max', 'seuil_critique', 'quantite_disponible',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'localisation': forms.TextInput(attrs={'class': 'form-control'}),
            'responsable': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'capacite_max': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'seuil_critique': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'quantite_disponible': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
        }


class ZoneEntrepotForm(forms.ModelForm):
    class Meta:
        model = ZoneEntrepot
        fields = [
            'nom', 'description', 'capacite', 'quantite',
            'statut', 'responsable', 'entrepot',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
            }),
            'capacite': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'quantite': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'responsable': forms.Select(attrs={'class': 'form-select'}),
            'entrepot': forms.Select(attrs={'class': 'form-select'}),
        }


class LotForm(forms.ModelForm):
    code_lot = forms.CharField(
        label='Code Lot', required=False, disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    field_order = [
        'code_lot', 'produit', 'producteur', 'zone',
        'quantite_initiale', 'quantite_restante', 'qualite', 'etat',
        'date_reception', 'date_expiration', 'observations',
    ]

    class Meta:
        model = Lot
        fields = [
            'produit', 'producteur', 'zone',
            'quantite_initiale', 'quantite_restante',
            'qualite', 'etat', 'date_reception', 'date_expiration',
            'observations',
        ]
        labels = {
            'quantite_initiale': 'Quantité initiale',
            'quantite_restante': 'Quantité disponible',
        }
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'producteur': forms.Select(attrs={'class': 'form-select'}),
            'zone': forms.Select(attrs={'class': 'form-select'}),
            'quantite_initiale': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'quantite_restante': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'placeholder': 'Rempli auto si vide',
            }),
            'qualite': forms.Select(attrs={'class': 'form-select'}),
            'etat': forms.Select(attrs={'class': 'form-select'}),
            'date_reception': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'date_expiration': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'observations': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantite_restante'].required = False
        if self.instance and self.instance.pk:
            self.fields['code_lot'].initial = self.instance.code_lot
        else:
            self.fields['code_lot'].initial = generate_lot_code()


class VenteForm(forms.ModelForm):
    numero_vente = forms.CharField(
        label='Numéro Vente', required=False, disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    field_order = [
        'numero_vente', 'client', 'lot', 'quantite_vendue',
        'prix_unitaire', 'mode_paiement', 'type_vente', 'observations',
    ]

    class Meta:
        model = Vente
        fields = [
            'client', 'lot', 'quantite_vendue',
            'prix_unitaire', 'mode_paiement',
            'type_vente', 'observations',
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'lot': forms.Select(attrs={'class': 'form-select'}),
            'quantite_vendue': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'prix_unitaire': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'mode_paiement': forms.Select(attrs={'class': 'form-select'}),
            'type_vente': forms.Select(attrs={'class': 'form-select'}),
            'observations': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['numero_vente'].initial = self.instance.numero_vente
        else:
            self.fields['numero_vente'].initial = generate_vente_numero()


class MouvementStockForm(forms.ModelForm):
    class Meta:
        model = MouvementStock
        fields = [
            'type_mouvement', 'lot', 'quantite',
            'zone_origine', 'zone_destination', 'valide', 'motif',
        ]
        widgets = {
            'type_mouvement': forms.Select(attrs={'class': 'form-select'}),
            'lot': forms.Select(attrs={'class': 'form-select'}),
            'quantite': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'zone_origine': forms.Select(attrs={'class': 'form-select'}),
            'zone_destination': forms.Select(attrs={'class': 'form-select'}),
            'valide': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'motif': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
            }),
        }


class CommandeForm(forms.ModelForm):
    numero_commande = forms.CharField(
        label='Numéro Commande', required=False, disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    produit = forms.ModelChoiceField(
        queryset=Produit.objects.all(),
        label='Produit',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_produit_commande',
        }),
    )

    field_order = [
        'numero_commande', 'client', 'produit', 'quantite_demandee',
        'quantite_reservee', 'quantite_servie',
        'date_livraison_souhaitee', 'priorite', 'observations',
    ]

    class Meta:
        model = Commande
        fields = [
            'client', 'quantite_demandee', 'quantite_reservee', 'quantite_servie',
            'date_livraison_souhaitee', 'priorite', 'observations',
        ]
        labels = {
            'quantite_demandee': 'Qté demandée',
            'quantite_reservee': 'Qté réservée',
            'quantite_servie': 'Qté servie',
        }
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'quantite_demandee': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'id': 'id_quantite_commande',
            }),
            'quantite_reservee': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'quantite_servie': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'date_livraison_souhaitee': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'priorite': forms.Select(attrs={'class': 'form-select'}),
            'observations': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['numero_commande'].initial = self.instance.numero_commande
            # Pré-remplir le produit depuis la première ligne
            from .models import LigneCommande
            ligne = LigneCommande.objects.filter(commande=self.instance).first()
            if ligne:
                self.fields['produit'].initial = ligne.produit_id
        else:
            self.fields['numero_commande'].initial = generate_commande_numero()

    def clean(self):
        cleaned = super().clean()
        demandee = cleaned.get('quantite_demandee') or 0
        reservee = cleaned.get('quantite_reservee') or 0
        servie = cleaned.get('quantite_servie') or 0
        if reservee > demandee:
            self.add_error('quantite_reservee',
                f'La qté réservée ({reservee}) ne peut pas dépasser la qté demandée ({demandee}).')
        if servie > demandee:
            self.add_error('quantite_servie',
                f'La qté servie ({servie}) ne peut pas dépasser la qté demandée ({demandee}).')
        return cleaned


class VenteImmediateForm(forms.ModelForm):
    numero_vente = forms.CharField(
        label='Numéro Vente', required=False, disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    field_order = [
        'numero_vente', 'produit', 'client',
        'quantite_demandee', 'type_vente', 'prix_unitaire',
    ]

    class Meta:
        model = VenteImmediate
        fields = [
            'produit', 'client',
            'quantite_demandee',
            'type_vente', 'prix_unitaire',
        ]
        widgets = {
            'produit': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_produit_vi',
            }),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'quantite_demandee': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'id': 'id_quantite_vi',
            }),
            'type_vente': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_type_vente_vi',
            }),
            'prix_unitaire': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['numero_vente'].initial = self.instance.numero_vente
        else:
            self.fields['numero_vente'].initial = generate_vente_immediate_numero()


class DemandeAchatForm(forms.ModelForm):
    numero_da = forms.CharField(
        label='Numéro DA', required=False, disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    field_order = [
        'numero_da', 'produit', 'quantite_a_commander',
        'priorite', 'observations',
    ]

    class Meta:
        model = DemandeAchat
        fields = [
            'produit', 'quantite_a_commander',
            'priorite', 'observations',
        ]
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'quantite_a_commander': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
            }),
            'priorite': forms.Select(attrs={'class': 'form-select'}),
            'observations': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['numero_da'].initial = self.instance.numero_da
        else:
            self.fields['numero_da'].initial = generate_demande_achat_numero()
