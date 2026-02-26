from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from decimal import Decimal
from .models import (
    Client, Produit, Lot, Vente, Entrepot, ZoneEntrepot,
    Producteur, MouvementStock, HistoriqueTracabilite,
    Commande, LigneCommande, AffectationLot,
    AlerteStock, DemandeAchat, VenteImmediate,
)
from .forms import (
    ClientForm, ProduitForm, LotForm, VenteForm, EntrepotForm,
    ZoneEntrepotForm, ProducteurForm, MouvementStockForm,
    CommandeForm, VenteImmediateForm, DemandeAchatForm,
)
from .services import (
    generate_lot_code, generate_vente_numero,
    generate_commande_numero, generate_vente_immediate_numero,
    generate_demande_achat_numero,
    get_stock_info, reserver_stock_commande,
    traiter_vente_immediate_service, verifier_et_creer_alertes,
    generer_demande_achat_depuis_alerte, confirmer_commande,
    livrer_commande, receptionner_demande_achat,
)


def _log_historique(user, type_action, description, lot=None, commande=None,
                    ancienne_valeur=None, nouvelle_valeur=None):
    """Helper pour enregistrer une entrée dans l'historique de traçabilité."""
    HistoriqueTracabilite.objects.create(
        date_action=timezone.now(),
        type_action=type_action,
        description=description,
        lot=lot,
        commande=commande,
        user=user,
        ancienne_valeur=ancienne_valeur,
        nouvelle_valeur=nouvelle_valeur,
    )


def _model_to_dict(instance, fields=None):
    """Convertit un objet model en dict lisible pour l'historique."""
    from django.forms.models import model_to_dict as django_m2d
    data = {}
    if fields:
        field_list = fields
    else:
        field_list = [f.name for f in instance._meta.fields
                      if f.name not in ('id', 'user', 'date_creation')]
    for field_name in field_list:
        try:
            val = getattr(instance, field_name, None)
            if hasattr(val, '__str__') and not isinstance(val, (str, int, float, bool, type(None))):
                val = str(val)
            data[field_name] = val
        except Exception:
            pass
    return data


@login_required
def dashboard(request):
    """Tableau de bord principal du gestionnaire"""
    context = {
        'total_clients': Client.objects.count(),
        'total_produits': Produit.objects.count(),
        'total_lots': Lot.objects.count(),
        'total_ventes': Vente.objects.count(),
        'total_entrepots': Entrepot.objects.count(),
        'total_producteurs': Producteur.objects.count(),
        'total_commandes': Commande.objects.exclude(statut__in=['LIVREE', 'ANNULEE']).count(),
        'total_alertes': AlerteStock.objects.filter(statut='ACTIVE').count(),

        # Statistiques détaillées
        'lots_expiration_proche': Lot.objects.filter(
            date_expiration__lte=timezone.now() + timedelta(days=30),
            date_expiration__gte=timezone.now()
        ).count(),
        'lots_expires': Lot.objects.filter(
            date_expiration__lt=timezone.now()
        ).count(),
        'entrepots_alerte': Entrepot.objects.filter(
            quantite_disponible__lte=F('seuil_critique')
        ).count(),

        # Derniers mouvements
        'derniers_mouvements': MouvementStock.objects.select_related(
            'lot', 'user'
        ).order_by('-date_mouvement')[:5],

        # Dernières ventes
        'dernieres_ventes': Vente.objects.select_related(
            'client', 'lot', 'user'
        ).order_by('-date_vente')[:5],

        # Stock par zone
        'stock_par_zone': ZoneEntrepot.objects.filter(
            quantite__gt=0
        ).select_related('entrepot').order_by('-quantite')[:10],
    }
    return render(request, 'gestion/dashboard.html', context)


# ==================== VUES CLIENTS ====================

@login_required
def clients_list(request):
    """Liste des clients avec recherche et filtrage"""
    queryset = Client.objects.all()
    search_query = request.GET.get('search', '')

    if search_query:
        queryset = queryset.filter(
            Q(nom__icontains=search_query) |
            Q(prenom__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(entreprise__icontains=search_query)
        )

    context = {
        'clients': queryset.order_by('-date_inscription'),
        'search_query': search_query,
    }
    return render(request, 'gestion/clients/list.html', context)


@login_required
def clients_create(request):
    """Créer un nouveau client"""
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            _log_historique(
                request.user, 'creation',
                f'Création du client {client.nom} {client.prenom or ""}',
                nouvelle_valeur=_model_to_dict(client, ['nom', 'prenom', 'entreprise', 'telephone', 'email', 'type_client']),
            )
            messages.success(request, 'Client créé avec succès')
            return redirect('clients_list')
    else:
        form = ClientForm()

    return render(request, 'gestion/clients/form.html', {
        'form': form, 'title': 'Nouveau Client',
    })


@login_required
def clients_detail(request, pk):
    """Détail d'un client"""
    client = get_object_or_404(Client, pk=pk)
    ventes_client = Vente.objects.filter(
        client=client
    ).select_related('lot', 'user')

    context = {
        'client': client,
        'ventes': ventes_client.order_by('-date_vente'),
        'total_achats': ventes_client.aggregate(
            Sum('montant_total')
        )['montant_total__sum'] or 0,
    }
    return render(request, 'gestion/clients/detail.html', context)


@login_required
def clients_update(request, pk):
    """Modifier un client"""
    client = get_object_or_404(Client, pk=pk)
    old_data = _model_to_dict(client, ['nom', 'prenom', 'entreprise', 'telephone', 'email', 'type_client'])
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            client = form.save()
            _log_historique(
                request.user, 'modification',
                f'Modification du client {client.nom}',
                ancienne_valeur=old_data,
                nouvelle_valeur=_model_to_dict(client, ['nom', 'prenom', 'entreprise', 'telephone', 'email', 'type_client']),
            )
            messages.success(request, 'Client modifié avec succès')
            return redirect('clients_detail', pk=pk)
    else:
        form = ClientForm(instance=client)

    return render(request, 'gestion/clients/form.html', {
        'form': form, 'title': f'Modifier {client.nom}',
    })


@login_required
def clients_delete(request, pk):
    """Supprimer un client"""
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        old_data = _model_to_dict(client, ['nom', 'prenom', 'entreprise', 'telephone', 'email', 'type_client'])
        _log_historique(
            request.user, 'suppression',
            f'Suppression du client {client.nom}',
            ancienne_valeur=old_data,
        )
        client.delete()
        messages.success(request, 'Client supprimé avec succès')
        return redirect('clients_list')

    return render(request, 'gestion/confirm_delete.html', {'object': client})


# ==================== VUES PRODUITS ====================

@login_required
def produits_list(request):
    """Liste des produits avec infos de stock"""
    queryset = Produit.objects.all()
    search_query = request.GET.get('search', '')
    categorie_filter = request.GET.get('categorie', '')

    if search_query:
        queryset = queryset.filter(
            Q(nom__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if categorie_filter:
        queryset = queryset.filter(categorie=categorie_filter)

    # Ajouter les infos de stock pour chaque produit
    produits_avec_stock = []
    for p in queryset.order_by('nom'):
        produits_avec_stock.append({
            'produit': p,
            'stock': get_stock_info(p),
        })

    context = {
        'produits_avec_stock': produits_avec_stock,
        'produits': queryset.order_by('nom'),
        'search_query': search_query,
        'categories': Produit.objects.values_list(
            'categorie', flat=True
        ).distinct(),
    }
    return render(request, 'gestion/produits/list.html', context)


@login_required
def produits_create(request):
    """Créer un nouveau produit"""
    if request.method == 'POST':
        form = ProduitForm(request.POST)
        if form.is_valid():
            produit = form.save()
            _log_historique(
                request.user, 'creation',
                f'Création du produit {produit.nom}',
                nouvelle_valeur=_model_to_dict(produit, ['nom', 'categorie', 'unite', 'prix_unitaire', 'seuil_alerte']),
            )
            messages.success(request, 'Produit créé avec succès')
            return redirect('produits_list')
    else:
        form = ProduitForm()

    return render(request, 'gestion/produits/form.html', {
        'form': form, 'title': 'Nouveau Produit',
    })


@login_required
def produits_update(request, pk):
    """Modifier un produit"""
    produit = get_object_or_404(Produit, pk=pk)
    old_data = _model_to_dict(produit, ['nom', 'categorie', 'unite', 'prix_unitaire', 'seuil_alerte'])
    if request.method == 'POST':
        form = ProduitForm(request.POST, instance=produit)
        if form.is_valid():
            produit = form.save()
            _log_historique(
                request.user, 'modification',
                f'Modification du produit {produit.nom}',
                ancienne_valeur=old_data,
                nouvelle_valeur=_model_to_dict(produit, ['nom', 'categorie', 'unite', 'prix_unitaire', 'seuil_alerte']),
            )
            messages.success(request, 'Produit modifié avec succès')
            return redirect('produits_list')
    else:
        form = ProduitForm(instance=produit)

    return render(request, 'gestion/produits/form.html', {
        'form': form, 'title': f'Modifier {produit.nom}',
    })


@login_required
def produits_delete(request, pk):
    """Supprimer un produit et toutes ses données liées"""
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        old_data = _model_to_dict(produit, ['nom', 'categorie', 'unite', 'prix_unitaire'])
        _log_historique(
            request.user, 'suppression',
            f'Suppression du produit {produit.nom}',
            ancienne_valeur=old_data,
        )

        from django.db import connection
        with connection.cursor() as cur:
            # Désactiver temporairement les triggers de protection
            cur.execute('ALTER TABLE stock_cajou.mouvement_stock DISABLE TRIGGER ALL')
            cur.execute('ALTER TABLE stock_cajou.lot DISABLE TRIGGER ALL')
            cur.execute('ALTER TABLE stock_cajou.vente DISABLE TRIGGER ALL')
            cur.execute('ALTER TABLE stock_cajou.produit DISABLE TRIGGER ALL')

            try:
                # Supprimer les affectations de lots liés à ce produit
                cur.execute(
                    'DELETE FROM stock_cajou.affectation_lot WHERE lot_id IN '
                    '(SELECT id FROM stock_cajou.lot WHERE produit_id = %s)', [pk])
                # Supprimer les mouvements de stock des lots liés
                cur.execute(
                    'DELETE FROM stock_cajou.mouvement_stock WHERE lot_id IN '
                    '(SELECT id FROM stock_cajou.lot WHERE produit_id = %s)', [pk])
                # Détacher l'historique des lots liés
                cur.execute(
                    'UPDATE stock_cajou.historique_tracabilite SET lot_id = NULL WHERE lot_id IN '
                    '(SELECT id FROM stock_cajou.lot WHERE produit_id = %s)', [pk])
                # Supprimer les ventes liées aux lots
                cur.execute(
                    'DELETE FROM stock_cajou.vente WHERE lot_id IN '
                    '(SELECT id FROM stock_cajou.lot WHERE produit_id = %s)', [pk])
                # Supprimer les lots
                cur.execute(
                    'DELETE FROM stock_cajou.lot WHERE produit_id = %s', [pk])
                # Supprimer les lignes de commande liées
                cur.execute(
                    'DELETE FROM stock_cajou.ligne_commande WHERE produit_id = %s', [pk])
                # Supprimer les ventes immédiates
                cur.execute(
                    'DELETE FROM stock_cajou.vente_immediate WHERE produit_id = %s', [pk])
                # Supprimer les demandes d'achat
                cur.execute(
                    'DELETE FROM stock_cajou.demande_achat WHERE produit_id = %s', [pk])
                # Supprimer les alertes de stock
                cur.execute(
                    'DELETE FROM stock_cajou.alerte_stock WHERE produit_id = %s', [pk])
                # Supprimer le produit
                cur.execute(
                    'DELETE FROM stock_cajou.produit WHERE id = %s', [pk])
            finally:
                # Réactiver les triggers dans tous les cas
                cur.execute('ALTER TABLE stock_cajou.mouvement_stock ENABLE TRIGGER ALL')
                cur.execute('ALTER TABLE stock_cajou.lot ENABLE TRIGGER ALL')
                cur.execute('ALTER TABLE stock_cajou.vente ENABLE TRIGGER ALL')
                cur.execute('ALTER TABLE stock_cajou.produit ENABLE TRIGGER ALL')

        messages.success(request, f'Produit « {old_data["nom"]} » et toutes ses données associées supprimés avec succès')
        return redirect('produits_list')

    return render(request, 'gestion/confirm_delete.html', {'object': produit})


# ==================== VUES PRODUCTEURS ====================

@login_required
def producteurs_list(request):
    """Liste des producteurs"""
    queryset = Producteur.objects.all()
    search_query = request.GET.get('search', '')
    statut_filter = request.GET.get('statut', '')

    if search_query:
        queryset = queryset.filter(
            Q(nom__icontains=search_query) |
            Q(prenom__icontains=search_query) |
            Q(numero_identification__icontains=search_query)
        )

    if statut_filter:
        queryset = queryset.filter(statut=statut_filter)

    context = {
        'producteurs': queryset.order_by('-date_inscription'),
        'search_query': search_query,
        'statuts': Producteur.objects.values_list(
            'statut', flat=True
        ).distinct(),
    }
    return render(request, 'gestion/producteurs/list.html', context)


@login_required
def producteurs_create(request):
    """Créer un nouveau producteur"""
    if request.method == 'POST':
        form = ProducteurForm(request.POST)
        if form.is_valid():
            producteur = form.save()
            _log_historique(
                request.user, 'creation',
                f'Création du producteur {producteur.nom} {producteur.prenom or ""}',
                nouvelle_valeur=_model_to_dict(producteur, ['nom', 'prenom', 'telephone', 'localisation', 'type_producteur', 'statut']),
            )
            messages.success(request, 'Producteur créé avec succès')
            return redirect('producteurs_list')
    else:
        form = ProducteurForm()

    return render(request, 'gestion/producteurs/form.html', {
        'form': form, 'title': 'Nouveau Producteur',
    })


@login_required
def producteurs_detail(request, pk):
    """Détail d'un producteur"""
    producteur = get_object_or_404(Producteur, pk=pk)
    lots_producteur = Lot.objects.filter(
        producteur=producteur
    ).select_related('produit', 'zone')

    context = {
        'producteur': producteur,
        'lots': lots_producteur.order_by('-date_creation'),
        'total_lots': lots_producteur.count(),
    }
    return render(request, 'gestion/producteurs/detail.html', context)


@login_required
def producteurs_update(request, pk):
    """Modifier un producteur"""
    producteur = get_object_or_404(Producteur, pk=pk)
    old_data = _model_to_dict(producteur, ['nom', 'prenom', 'telephone', 'localisation', 'type_producteur', 'statut'])
    if request.method == 'POST':
        form = ProducteurForm(request.POST, instance=producteur)
        if form.is_valid():
            producteur = form.save()
            _log_historique(
                request.user, 'modification',
                f'Modification du producteur {producteur.nom}',
                ancienne_valeur=old_data,
                nouvelle_valeur=_model_to_dict(producteur, ['nom', 'prenom', 'telephone', 'localisation', 'type_producteur', 'statut']),
            )
            messages.success(request, 'Producteur modifié avec succès')
            return redirect('producteurs_detail', pk=pk)
    else:
        form = ProducteurForm(instance=producteur)

    return render(request, 'gestion/producteurs/form.html', {
        'form': form, 'title': f'Modifier {producteur.nom}',
    })


@login_required
def producteurs_delete(request, pk):
    """Supprimer un producteur"""
    producteur = get_object_or_404(Producteur, pk=pk)
    if request.method == 'POST':
        old_data = _model_to_dict(producteur, ['nom', 'prenom', 'telephone', 'localisation', 'type_producteur'])
        _log_historique(
            request.user, 'suppression',
            f'Suppression du producteur {producteur.nom}',
            ancienne_valeur=old_data,
        )
        producteur.delete()
        messages.success(request, 'Producteur supprimé avec succès')
        return redirect('producteurs_list')

    return render(request, 'gestion/confirm_delete.html', {'object': producteur})


# ==================== VUES ENTREPOTS ====================

@login_required
def entrepots_list(request):
    """Liste des entrepôts"""
    queryset = Entrepot.objects.select_related('responsable').all()
    search_query = request.GET.get('search', '')
    statut_filter = request.GET.get('statut', '')

    if search_query:
        queryset = queryset.filter(
            Q(nom__icontains=search_query) |
            Q(localisation__icontains=search_query)
        )

    if statut_filter:
        queryset = queryset.filter(statut=statut_filter)

    context = {
        'entrepots': queryset.order_by('nom'),
        'search_query': search_query,
        'statuts': Entrepot.objects.values_list(
            'statut', flat=True
        ).distinct(),
    }
    return render(request, 'gestion/entrepots/list.html', context)


@login_required
def entrepots_create(request):
    """Créer un nouvel entrepôt"""
    if request.method == 'POST':
        form = EntrepotForm(request.POST)
        if form.is_valid():
            entrepot = form.save()
            _log_historique(
                request.user, 'creation',
                f'Création de l\'entrepôt {entrepot.nom}',
                nouvelle_valeur=_model_to_dict(entrepot, ['nom', 'localisation', 'capacite_max', 'seuil_critique', 'statut']),
            )
            messages.success(request, 'Entrepôt créé avec succès')
            return redirect('entrepots_list')
    else:
        form = EntrepotForm()

    return render(request, 'gestion/entrepots/form.html', {
        'form': form, 'title': 'Nouvel Entrepôt',
    })


@login_required
def entrepots_detail(request, pk):
    """Détail d'un entrepôt"""
    entrepot = get_object_or_404(Entrepot, pk=pk)
    zones = ZoneEntrepot.objects.filter(entrepot=entrepot)

    context = {
        'entrepot': entrepot,
        'zones': zones,
        'total_stock': zones.aggregate(
            Sum('quantite')
        )['quantite__sum'] or 0,
    }
    return render(request, 'gestion/entrepots/detail.html', context)


@login_required
def entrepots_update(request, pk):
    """Modifier un entrepôt"""
    entrepot = get_object_or_404(Entrepot, pk=pk)
    old_data = _model_to_dict(entrepot, ['nom', 'localisation', 'capacite_max', 'seuil_critique', 'statut'])
    if request.method == 'POST':
        form = EntrepotForm(request.POST, instance=entrepot)
        if form.is_valid():
            entrepot = form.save()
            _log_historique(
                request.user, 'modification',
                f'Modification de l\'entrepôt {entrepot.nom}',
                ancienne_valeur=old_data,
                nouvelle_valeur=_model_to_dict(entrepot, ['nom', 'localisation', 'capacite_max', 'seuil_critique', 'statut']),
            )
            messages.success(request, 'Entrepôt modifié avec succès')
            return redirect('entrepots_detail', pk=pk)
    else:
        form = EntrepotForm(instance=entrepot)

    return render(request, 'gestion/entrepots/form.html', {
        'form': form, 'title': f'Modifier {entrepot.nom}',
    })


@login_required
def entrepots_delete(request, pk):
    """Supprimer un entrepôt"""
    entrepot = get_object_or_404(Entrepot, pk=pk)
    if request.method == 'POST':
        old_data = _model_to_dict(entrepot, ['nom', 'localisation', 'capacite_max', 'seuil_critique'])
        _log_historique(
            request.user, 'suppression',
            f'Suppression de l\'entrepôt {entrepot.nom}',
            ancienne_valeur=old_data,
        )
        entrepot.delete()
        messages.success(request, 'Entrepôt supprimé avec succès')
        return redirect('entrepots_list')

    return render(request, 'gestion/confirm_delete.html', {'object': entrepot})


# ==================== VUES ZONES ====================

@login_required
def zones_list(request):
    """Liste des zones"""
    queryset = ZoneEntrepot.objects.select_related(
        'entrepot', 'responsable'
    ).all()
    search_query = request.GET.get('search', '')
    entrepot_filter = request.GET.get('entrepot', '')

    if search_query:
        queryset = queryset.filter(nom__icontains=search_query)

    if entrepot_filter:
        queryset = queryset.filter(entrepot_id=entrepot_filter)

    context = {
        'zones': queryset.order_by('entrepot', 'nom'),
        'search_query': search_query,
        'entrepots': Entrepot.objects.all(),
    }
    return render(request, 'gestion/zones/list.html', context)


@login_required
def zones_create(request):
    """Créer une nouvelle zone"""
    if request.method == 'POST':
        form = ZoneEntrepotForm(request.POST)
        if form.is_valid():
            zone = form.save()
            _log_historique(
                request.user, 'creation',
                f'Création de la zone {zone.nom} ({zone.entrepot.nom})',
                nouvelle_valeur=_model_to_dict(zone, ['nom', 'capacite', 'statut']),
            )
            messages.success(request, 'Zone créée avec succès')
            return redirect('zones_list')
    else:
        form = ZoneEntrepotForm()

    return render(request, 'gestion/zones/form.html', {
        'form': form, 'title': 'Nouvelle Zone',
    })


@login_required
def zones_update(request, pk):
    """Modifier une zone"""
    zone = get_object_or_404(ZoneEntrepot, pk=pk)
    old_data = _model_to_dict(zone, ['nom', 'capacite', 'quantite', 'statut'])
    if request.method == 'POST':
        form = ZoneEntrepotForm(request.POST, instance=zone)
        if form.is_valid():
            zone = form.save()
            _log_historique(
                request.user, 'modification',
                f'Modification de la zone {zone.nom}',
                ancienne_valeur=old_data,
                nouvelle_valeur=_model_to_dict(zone, ['nom', 'capacite', 'quantite', 'statut']),
            )
            messages.success(request, 'Zone modifiée avec succès')
            return redirect('zones_list')
    else:
        form = ZoneEntrepotForm(instance=zone)

    return render(request, 'gestion/zones/form.html', {
        'form': form, 'title': f'Modifier {zone.nom}',
    })


@login_required
def zones_delete(request, pk):
    """Supprimer une zone"""
    zone = get_object_or_404(ZoneEntrepot, pk=pk)
    if request.method == 'POST':
        old_data = _model_to_dict(zone, ['nom', 'capacite', 'statut'])
        _log_historique(
            request.user, 'suppression',
            f'Suppression de la zone {zone.nom}',
            ancienne_valeur=old_data,
        )
        zone.delete()
        messages.success(request, 'Zone supprimée avec succès')
        return redirect('zones_list')

    return render(request, 'gestion/confirm_delete.html', {'object': zone})


# ==================== VUES LOTS ====================

@login_required
def lots_list(request):
    """Liste des lots"""
    queryset = Lot.objects.select_related(
        'produit', 'producteur', 'zone'
    ).all()
    search_query = request.GET.get('search', '')
    etat_filter = request.GET.get('etat', '')
    produit_filter = request.GET.get('produit', '')

    if search_query:
        queryset = queryset.filter(
            Q(code_lot__icontains=search_query) |
            Q(produit__nom__icontains=search_query)
        )

    if etat_filter:
        queryset = queryset.filter(etat=etat_filter)

    if produit_filter:
        queryset = queryset.filter(produit_id=produit_filter)

    context = {
        'lots': queryset.order_by('-date_creation'),
        'search_query': search_query,
        'etats': Lot.objects.values_list('etat', flat=True).distinct(),
        'produits': Produit.objects.all(),
    }
    return render(request, 'gestion/lots/list.html', context)


@login_required
def lots_create(request):
    """Créer un nouveau lot"""
    if request.method == 'POST':
        form = LotForm(request.POST)
        if form.is_valid():
            lot = form.save(commit=False)
            lot.code_lot = generate_lot_code()
            lot.quantite_restante = lot.quantite_restante if lot.quantite_restante is not None else lot.quantite_initiale
            lot.quantite_reservee = Decimal('0.00')
            lot.user = request.user
            lot.date_creation = timezone.now()
            lot.save()

            # ── Mettre à jour le stock physique du produit ──
            produit = lot.produit
            produit.stock_physique = (
                (produit.stock_physique or Decimal('0.00')) + lot.quantite_initiale
            )
            produit.date_dernier_reappro = timezone.now()
            produit.save(update_fields=['stock_physique', 'date_dernier_reappro'])

            # ── Créer un mouvement d'entrée ──
            MouvementStock.objects.create(
                lot=lot,
                type_mouvement='ENTREE',
                quantite=lot.quantite_initiale,
                motif=f'Réception lot {lot.code_lot}',
                zone_destination=lot.zone,
                user=request.user,
                date_mouvement=timezone.now(),
                valide=True,
            )

            # ── Vérifier les alertes (résoudre si stock remonté) ──
            verifier_et_creer_alertes(produit, request.user)

            _log_historique(
                request.user, 'creation',
                f'Création du lot {lot.code_lot} — {lot.quantite_initiale} {lot.produit.unite or "unités"} de {lot.produit.nom}',
                lot=lot,
                nouvelle_valeur=_model_to_dict(lot, ['code_lot', 'quantite_initiale', 'qualite', 'etat', 'date_reception', 'date_expiration']),
            )
            messages.success(request, f'Lot {lot.code_lot} créé avec succès')
            return redirect('lots_list')
    else:
        form = LotForm()

    return render(request, 'gestion/lots/form.html', {
        'form': form, 'title': 'Nouveau Lot',
    })


@login_required
def lots_detail(request, pk):
    """Détail d'un lot"""
    lot = get_object_or_404(Lot, pk=pk)
    mouvements = MouvementStock.objects.filter(
        lot=lot
    ).select_related('user', 'zone_origine', 'zone_destination')
    ventes = Vente.objects.filter(
        lot=lot
    ).select_related('client', 'user')
    historique = HistoriqueTracabilite.objects.filter(
        lot=lot
    ).select_related('user')

    context = {
        'lot': lot,
        'mouvements': mouvements.order_by('-date_mouvement'),
        'ventes': ventes.order_by('-date_vente'),
        'historique': historique.order_by('-date_action'),
    }
    return render(request, 'gestion/lots/detail.html', context)


@login_required
def lots_update(request, pk):
    """Modifier un lot"""
    lot = get_object_or_404(Lot, pk=pk)
    old_data = _model_to_dict(lot, ['code_lot', 'quantite_initiale', 'quantite_restante', 'qualite', 'etat', 'date_expiration', 'observations'])
    if request.method == 'POST':
        form = LotForm(request.POST, instance=lot)
        if form.is_valid():
            lot = form.save()
            _log_historique(
                request.user, 'modification',
                f'Modification du lot {lot.code_lot}',
                lot=lot,
                ancienne_valeur=old_data,
                nouvelle_valeur=_model_to_dict(lot, ['code_lot', 'quantite_initiale', 'quantite_restante', 'qualite', 'etat', 'date_expiration', 'observations']),
            )
            messages.success(request, 'Lot modifié avec succès')
            return redirect('lots_detail', pk=pk)
    else:
        form = LotForm(instance=lot)

    return render(request, 'gestion/lots/form.html', {
        'form': form, 'title': f'Modifier {lot.code_lot}',
    })


@login_required
def lots_delete(request, pk):
    """Supprimer un lot et ses données liées (mouvements, affectations)."""
    lot = get_object_or_404(Lot, pk=pk)
    if request.method == 'POST':
        old_data = _model_to_dict(lot, ['code_lot', 'quantite_initiale', 'quantite_restante', 'qualite', 'etat'])
        _log_historique(
            request.user, 'suppression',
            f'Suppression du lot {lot.code_lot}',
            ancienne_valeur=old_data,
        )
        # Supprimer les enregistrements liés (contraintes RESTRICT en base)
        # Désactiver le trigger qui interdit la suppression des mouvements
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE mouvement_stock DISABLE TRIGGER ALL;")
            MouvementStock.objects.filter(lot=lot).delete()
            cursor.execute("ALTER TABLE mouvement_stock ENABLE TRIGGER ALL;")
        AffectationLot.objects.filter(lot=lot).delete()
        Vente.objects.filter(lot=lot).delete()
        lot.delete()
        messages.success(request, 'Lot supprimé avec succès')
        return redirect('lots_list')

    return render(request, 'gestion/confirm_delete.html', {'object': lot})


# ==================== VUES VENTES ====================

@login_required
def ventes_list(request):
    """Liste des ventes"""
    queryset = Vente.objects.select_related(
        'client', 'lot', 'user'
    ).all()
    search_query = request.GET.get('search', '')
    date_filter = request.GET.get('date', '')

    if search_query:
        queryset = queryset.filter(
            Q(numero_vente__icontains=search_query) |
            Q(client__nom__icontains=search_query) |
            Q(lot__code_lot__icontains=search_query)
        )

    if date_filter:
        queryset = queryset.filter(date_vente__date=date_filter)

    context = {
        'ventes': queryset.order_by('-date_vente'),
        'search_query': search_query,
        'total_ventes': queryset.aggregate(
            Sum('montant_total')
        )['montant_total__sum'] or 0,
    }
    return render(request, 'gestion/ventes/list.html', context)


@login_required
def ventes_create(request):
    """Créer une nouvelle vente"""
    if request.method == 'POST':
        form = VenteForm(request.POST)
        if form.is_valid():
            vente = form.save(commit=False)
            vente.numero_vente = generate_vente_numero()
            vente.montant_total = vente.quantite_vendue * vente.prix_unitaire
            vente.user = request.user
            vente.date_vente = timezone.now()
            vente.save()

            # ── Déduire le stock du lot et du produit ──
            lot = vente.lot
            lot.quantite_restante = max(
                Decimal('0.00'),
                (lot.quantite_restante or Decimal('0.00')) - vente.quantite_vendue
            )
            if lot.quantite_restante <= 0:
                lot.etat = 'EPUISE'
            elif lot.quantite_restante < lot.quantite_initiale:
                lot.etat = 'PARTIELLEMENT_SORTI'
            lot.save(update_fields=['quantite_restante', 'etat'])

            produit = lot.produit
            produit.stock_physique = max(
                Decimal('0.00'),
                (produit.stock_physique or Decimal('0.00')) - vente.quantite_vendue
            )
            produit.save(update_fields=['stock_physique'])

            # ── Créer un mouvement de sortie ──
            MouvementStock.objects.create(
                lot=lot,
                type_mouvement='SORTIE',
                quantite=vente.quantite_vendue,
                motif=f'Vente {vente.numero_vente}',
                user=request.user,
                date_mouvement=timezone.now(),
                valide=True,
            )

            # ── Vérifier et créer les alertes automatiquement ──
            verifier_et_creer_alertes(produit, request.user)

            _log_historique(
                request.user, 'vente',
                f'Vente {vente.numero_vente} — {vente.quantite_vendue} unités à {vente.montant_total} XOF',
                lot=vente.lot,
                nouvelle_valeur={
                    'numero_vente': vente.numero_vente,
                    'client': str(vente.client) if vente.client else '—',
                    'lot': str(vente.lot),
                    'quantite_vendue': str(vente.quantite_vendue),
                    'montant_total': str(vente.montant_total),
                    'mode_paiement': vente.mode_paiement,
                },
            )
            messages.success(request, f'Vente {vente.numero_vente} enregistrée avec succès')
            return redirect('ventes_list')
    else:
        form = VenteForm()

    return render(request, 'gestion/ventes/form.html', {
        'form': form, 'title': 'Nouvelle Vente',
    })


@login_required
def ventes_update(request, pk):
    """Modifier une vente — bloqué car les ventes confirmées sont immuables"""
    vente = get_object_or_404(Vente, pk=pk)
    # Les ventes sont immuables une fois créées (confirmées)
    messages.error(request, f'La vente {vente.numero_vente} ne peut pas être modifiée car elle est déjà confirmée.')
    return redirect('ventes_detail', pk=pk)


@login_required
def ventes_delete(request, pk):
    """Supprimer une vente — bloqué car les ventes confirmées sont immuables"""
    vente = get_object_or_404(Vente, pk=pk)
    # Les ventes sont immuables une fois créées (confirmées)
    messages.error(request, f'La vente {vente.numero_vente} ne peut pas être supprimée car elle est déjà confirmée.')
    return redirect('ventes_detail', pk=pk)


# ==================== VUES MOUVEMENTS ====================

@login_required
def mouvements_list(request):
    """Liste des mouvements de stock"""
    queryset = MouvementStock.objects.select_related(
        'lot', 'user', 'zone_origine', 'zone_destination'
    ).all()

    context = {
        'mouvements': queryset.order_by('-date_mouvement'),
    }
    return render(request, 'gestion/mouvements/list.html', context)


@login_required
def mouvements_create(request):
    """Créer un nouveau mouvement"""
    if request.method == 'POST':
        form = MouvementStockForm(request.POST)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.user = request.user
            mouvement.date_mouvement = timezone.now()
            mouvement.save()

            # ── Vérifier les alertes après mouvement de stock ──
            produit = mouvement.lot.produit
            verifier_et_creer_alertes(produit, request.user)

            # Enregistrer dans l'historique
            _log_historique(
                request.user, 'mouvement_stock',
                f'Mouvement {mouvement.get_type_mouvement_display()} de {mouvement.quantite} '
                f'{mouvement.lot.produit.unite or "unités"} — {mouvement.motif or ""}',
                lot=mouvement.lot,
                ancienne_valeur={"zone": str(mouvement.zone_origine) if mouvement.zone_origine else '—'},
                nouvelle_valeur={
                    "zone": str(mouvement.zone_destination) if mouvement.zone_destination else '—',
                    "type_mouvement": mouvement.get_type_mouvement_display(),
                    "quantite": str(mouvement.quantite),
                    "motif": mouvement.motif or '—',
                },
            )

            messages.success(request, 'Mouvement créé avec succès')
            return redirect('mouvements_list')
    else:
        form = MouvementStockForm()

    return render(request, 'gestion/mouvements/form.html', {
        'form': form, 'title': 'Nouveau Mouvement',
    })


@login_required
def mouvements_delete(request, pk):
    """Supprimer un mouvement"""
    mouvement = get_object_or_404(MouvementStock, pk=pk)
    if request.method == 'POST':
        _log_historique(
            request.user, 'suppression',
            f'Suppression du mouvement {mouvement.get_type_mouvement_display()} — {mouvement.quantite} unités du lot {mouvement.lot.code_lot}',
            lot=mouvement.lot,
            ancienne_valeur={
                'type_mouvement': mouvement.get_type_mouvement_display(),
                'quantite': str(mouvement.quantite),
                'motif': mouvement.motif or '—',
            },
        )
        mouvement.delete()
        messages.success(request, 'Mouvement supprimé avec succès')
        return redirect('mouvements_list')

    return render(request, 'gestion/confirm_delete.html', {'object': mouvement})


# ==================== VUES HISTORIQUE ====================

@login_required
def historique_list(request):
    """Liste de l'historique de traçabilité"""
    queryset = HistoriqueTracabilite.objects.select_related(
        'lot', 'commande', 'user'
    ).all()
    search_query = request.GET.get('search', '')
    type_action_filter = request.GET.get('type_action', '')

    if search_query:
        queryset = queryset.filter(
            Q(lot__code_lot__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(commande__numero_commande__icontains=search_query)
        )

    if type_action_filter:
        queryset = queryset.filter(type_action=type_action_filter)

    # Statistiques pour les cartes
    all_qs = HistoriqueTracabilite.objects.all()
    types_action = list(
        HistoriqueTracabilite.objects.values_list('type_action', flat=True).distinct()
    )

    context = {
        'historiques': queryset.order_by('-date_action'),
        'search_query': search_query,
        'type_action_filter': type_action_filter,
        'types_action': types_action,
        'count_creations': all_qs.filter(type_action='creation').count(),
        'count_modifications': all_qs.filter(type_action='modification').count(),
        'count_suppressions': all_qs.filter(type_action='suppression').count(),
    }
    return render(request, 'gestion/historique/list.html', context)


@login_required
def historique_detail(request, pk):
    """Détail d'une entrée de l'historique"""
    historique = get_object_or_404(HistoriqueTracabilite, pk=pk)
    context = {'historique': historique}
    return render(request, 'gestion/historique/detail.html', context)


from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy


class CustomLoginView(LoginView):
    """Vue de connexion personnalisée"""
    template_name = 'auth/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')


class CustomLogoutView(LogoutView):
    """Vue de déconnexion personnalisée"""
    next_page = reverse_lazy('login')


# ==================== VUES PRÉDICTION DE STOCK ====================

def stock_forecast_view(request):
    """Prévisions de stock IA - Ferme Mokpokpo (via StockAnalyticsService)"""
    from .services import StockAnalyticsService
    context = StockAnalyticsService.analyze_complete()
    return render(request, 'gestion/stock-forecast/stock_forecast.html', context)


# ==================== VUE DÉTAIL PRODUIT ====================

@login_required
def produits_detail(request, pk):
    """Détail d'un produit avec séparation du stock"""
    produit = get_object_or_404(Produit, pk=pk)
    lots_produit = Lot.objects.filter(
        produit=produit
    ).select_related('producteur', 'zone')
    alertes = AlerteStock.objects.filter(produit=produit).order_by('-date_alerte')[:5]
    stock_info = get_stock_info(produit)

    # Commandes actives pour ce produit
    commandes_actives = Commande.objects.filter(
        lignecommande__produit=produit
    ).exclude(statut__in=['LIVREE', 'ANNULEE']).distinct().select_related('client')

    # Ventes immédiates récentes
    ventes_recentes = VenteImmediate.objects.filter(
        produit=produit
    ).order_by('-date_vente')[:5]

    # Demandes d'achat en cours
    demandes_actives = DemandeAchat.objects.filter(
        produit=produit
    ).exclude(statut__in=['RECEPTIONNEE', 'ANNULEE']).order_by('-date_creation')

    context = {
        'produit': produit,
        'lots': lots_produit.order_by('-date_creation'),
        'total_lots': lots_produit.count(),
        'alertes': alertes,
        'stock_info': stock_info,
        'commandes_actives': commandes_actives,
        'ventes_recentes': ventes_recentes,
        'demandes_actives': demandes_actives,
    }
    return render(request, 'gestion/produits/detail.html', context)


# ==================== VUE DÉTAIL VENTE ====================

@login_required
def ventes_detail(request, pk):
    """Détail d'une vente"""
    vente = get_object_or_404(Vente, pk=pk)
    context = {'vente': vente}
    return render(request, 'gestion/ventes/detail.html', context)


# ==================== VUES COMMANDES ====================

@login_required
def commandes_list(request):
    """Liste des commandes"""
    queryset = Commande.objects.select_related('client', 'user').all()
    search_query = request.GET.get('search', '')
    statut_filter = request.GET.get('statut', '')

    if search_query:
        queryset = queryset.filter(
            Q(numero_commande__icontains=search_query) |
            Q(client__nom__icontains=search_query)
        )

    if statut_filter:
        queryset = queryset.filter(statut=statut_filter)

    context = {
        'commandes': queryset.order_by('-date_commande'),
        'search_query': search_query,
        'statut_filter': statut_filter,
    }
    return render(request, 'gestion/commandes/list.html', context)


@login_required
def commandes_create(request):
    """Créer une nouvelle commande planifiée avec réservation automatique"""
    if request.method == 'POST':
        form = CommandeForm(request.POST)
        if form.is_valid():
            commande = form.save(commit=False)
            commande.numero_commande = generate_commande_numero()
            commande.quantite_reservee = form.cleaned_data.get('quantite_reservee') or Decimal('0.00')
            commande.quantite_servie = form.cleaned_data.get('quantite_servie') or Decimal('0.00')
            commande.statut = 'EN_ATTENTE'
            commande.user = request.user
            commande.date_commande = timezone.now()
            commande.save()

            # Créer la ligne de commande avec le produit sélectionné
            produit = form.cleaned_data['produit']
            from .models import LigneCommande
            LigneCommande.objects.create(
                commande=commande,
                produit=produit,
                quantite_demandee=commande.quantite_demandee,
                quantite_reservee=commande.quantite_reservee,
                quantite_servie=commande.quantite_servie,
                prix_unitaire=produit.prix_unitaire,
                statut_ligne='EN_ATTENTE',
            )

            _log_historique(
                request.user, 'creation',
                f'Création de la commande {commande.numero_commande} — {commande.quantite_demandee} unités pour {commande.client}',
                commande=commande,
                nouvelle_valeur={
                    'numero_commande': commande.numero_commande,
                    'client': str(commande.client),
                    'produit': str(produit),
                    'quantite_demandee': str(commande.quantite_demandee),
                    'priorite': commande.priorite,
                    'statut': 'EN_ATTENTE',
                },
            )

            messages.success(request,
                f'Commande {commande.numero_commande} créée — en attente d\'acceptation.')

            return redirect('commandes_detail', pk=commande.pk)
    else:
        form = CommandeForm()

    # Passer les infos de stock pour le JS dynamique
    produits_stock = {}
    for p in Produit.objects.all():
        produits_stock[p.pk] = get_stock_info(p)
        produits_stock[p.pk] = {
            k: str(v) for k, v in produits_stock[p.pk].items()
        }

    return render(request, 'gestion/commandes/form.html', {
        'form': form, 'title': 'Nouvelle Commande Planifiée',
        'produits_stock_json': produits_stock,
    })


@login_required
def commandes_detail(request, pk):
    """Détail d'une commande avec infos de stock"""
    commande = get_object_or_404(Commande, pk=pk)
    lignes = LigneCommande.objects.filter(
        commande=commande
    ).select_related('produit')
    affectations = AffectationLot.objects.filter(
        commande=commande
    ).select_related('lot')
    mouvements = MouvementStock.objects.filter(
        commande=commande
    ).select_related('lot', 'user')

    # Info stock pour chaque ligne
    lignes_avec_stock = []
    for ligne in lignes:
        stock_info = get_stock_info(ligne.produit)
        lignes_avec_stock.append({
            'ligne': ligne,
            'stock': stock_info,
        })

    context = {
        'commande': commande,
        'lignes': lignes,
        'lignes_avec_stock': lignes_avec_stock,
        'affectations': affectations,
        'mouvements': mouvements.order_by('-date_mouvement'),
    }
    return render(request, 'gestion/commandes/detail.html', context)


@login_required
def commandes_update(request, pk):
    """Modifier une commande — autorisé si EN_ATTENTE, CONFIRMEE ou EN_ATTENTE_REAPPRO"""
    commande = get_object_or_404(Commande, pk=pk)
    # Bloquer la modification si la commande est dans un état avancé
    statuts_bloques = ('RESERVEE', 'LIVREE', 'ANNULEE')
    if commande.statut in statuts_bloques:
        messages.error(request,
            f'La commande {commande.numero_commande} ne peut pas être modifiée '
            f'car elle est en statut « {commande.get_statut_display()} ».')
        return redirect('commandes_detail', pk=pk)

    old_data = {
        'client': str(commande.client),
        'quantite_demandee': str(commande.quantite_demandee),
        'priorite': commande.priorite,
        'date_livraison_souhaitee': str(commande.date_livraison_souhaitee or '—'),
        'observations': commande.observations or '—',
    }
    if request.method == 'POST':
        form = CommandeForm(request.POST, instance=commande)
        if form.is_valid():
            commande = form.save()

            # Mettre à jour la ligne de commande (produit / quantité)
            produit = form.cleaned_data['produit']
            ligne = LigneCommande.objects.filter(commande=commande).first()
            if ligne:
                ligne.produit = produit
                ligne.quantite_demandee = commande.quantite_demandee
                ligne.quantite_reservee = commande.quantite_reservee or Decimal('0.00')
                ligne.quantite_servie = commande.quantite_servie or Decimal('0.00')
                ligne.prix_unitaire = produit.prix_unitaire
                ligne.save(update_fields=[
                    'produit', 'quantite_demandee', 'quantite_reservee',
                    'quantite_servie', 'prix_unitaire'])

            _log_historique(
                request.user, 'modification',
                f'Modification de la commande {commande.numero_commande}',
                commande=commande,
                ancienne_valeur=old_data,
                nouvelle_valeur={
                    'client': str(commande.client),
                    'produit': str(produit),
                    'quantite_demandee': str(commande.quantite_demandee),
                    'priorite': commande.priorite,
                    'date_livraison_souhaitee': str(commande.date_livraison_souhaitee or '—'),
                    'observations': commande.observations or '—',
                },
            )
            messages.success(request, 'Commande modifiée avec succès.')
            return redirect('commandes_detail', pk=pk)
    else:
        form = CommandeForm(instance=commande)

    # Passer les infos de stock pour le JS dynamique
    produits_stock = {}
    for p in Produit.objects.all():
        produits_stock[p.pk] = get_stock_info(p)
        produits_stock[p.pk] = {
            k: str(v) for k, v in produits_stock[p.pk].items()
        }

    return render(request, 'gestion/commandes/form.html', {
        'form': form,
        'title': f'Modifier {commande.numero_commande}',
        'is_edit': True,
        'produits_stock_json': produits_stock,
    })


@login_required
def commandes_delete(request, pk):
    """Supprimer une commande — bloqué uniquement si livrée."""
    commande = get_object_or_404(Commande, pk=pk)
    if commande.statut == 'LIVREE':
        messages.error(request,
            f'La commande {commande.numero_commande} ne peut pas être supprimée '
            f'car elle est déjà livrée.')
        return redirect('commandes_detail', pk=pk)
    if request.method == 'POST':
        old_data = {
            'numero_commande': commande.numero_commande,
            'client': str(commande.client),
            'quantite_demandee': str(commande.quantite_demandee),
            'statut': commande.statut,
        }
        _log_historique(
            request.user, 'suppression',
            f'Suppression de la commande {commande.numero_commande}',
            ancienne_valeur=old_data,
        )

        # Libérer le stock réservé si nécessaire
        from .models import AffectationLot, MouvementStock
        affectations = AffectationLot.objects.filter(
            commande=commande, statut='RESERVE'
        ).select_related('lot', 'lot__produit')
        for aff in affectations:
            lot = aff.lot
            lot.quantite_reservee = max(
                Decimal('0.00'),
                (lot.quantite_reservee or Decimal('0.00')) - aff.quantite_affectee
            )
            if lot.etat == 'RESERVE':
                lot.etat = 'EN_STOCK'
            lot.save(update_fields=['quantite_reservee', 'etat'])

            produit = lot.produit
            produit.stock_reserve = max(
                Decimal('0.00'),
                (produit.stock_reserve or Decimal('0.00')) - aff.quantite_affectee
            )
            produit.save(update_fields=['stock_reserve'])

        # Supprimer les données liées via SQL brut (triggers protègent les DELETE ORM)
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute(
                'DELETE FROM stock_cajou.affectation_lot WHERE commande_id = %s',
                [commande.pk])
            cur.execute(
                'UPDATE stock_cajou.mouvement_stock SET commande_id = NULL WHERE commande_id = %s',
                [commande.pk])
            cur.execute(
                'DELETE FROM stock_cajou.ligne_commande WHERE commande_id = %s',
                [commande.pk])
            cur.execute(
                'DELETE FROM stock_cajou.commande WHERE id = %s',
                [commande.pk])

        messages.success(request, 'Commande supprimée avec succès.')
        return redirect('commandes_list')
    return render(request, 'gestion/confirm_delete.html', {'object': commande})


# ==================== VUES ALERTES STOCK ====================

@login_required
def alertes_list(request):
    """Tableau de bord des alertes de stock — vue dynamique et analytique."""
    queryset = AlerteStock.objects.select_related(
        'produit', 'user_traitement'
    ).all()
    statut_filter = request.GET.get('statut', '')
    search_query = request.GET.get('search', '')
    priorite_filter = request.GET.get('priorite', '')

    if statut_filter:
        queryset = queryset.filter(statut=statut_filter)
    if search_query:
        queryset = queryset.filter(
            Q(produit__nom__icontains=search_query) |
            Q(observations__icontains=search_query)
        )

    alertes = queryset.order_by('-date_alerte')

    # ── KPI statistiques ──
    total_alertes = AlerteStock.objects.count()
    alertes_actives = AlerteStock.objects.filter(statut='ACTIVE').count()
    alertes_traitees = AlerteStock.objects.filter(statut='TRAITEE').count()
    alertes_ignorees = AlerteStock.objects.filter(statut='IGNOREE').count()
    alertes_avec_da = AlerteStock.objects.filter(demande_achat_generee=True).count()

    # ── Produits en état critique (stock < seuil) ──
    produits_critiques = []
    for produit in Produit.objects.all():
        stock_dispo = produit.stock_disponible or Decimal('0.00')
        seuil = produit.seuil_alerte or Decimal('0.00')
        if seuil > 0:
            ratio = (stock_dispo / seuil * 100) if seuil else 0
            ratio = min(ratio, 100)
            if stock_dispo <= seuil:
                severity = 'CRITIQUE' if stock_dispo <= seuil * Decimal('0.25') else (
                    'URGENT' if stock_dispo <= seuil * Decimal('0.50') else 'ATTENTION'
                )
                produits_critiques.append({
                    'produit': produit,
                    'stock_dispo': stock_dispo,
                    'seuil': seuil,
                    'ratio': round(float(ratio), 1),
                    'severity': severity,
                    'deficit': seuil - stock_dispo,
                })

    # Trier par sévérité (les plus critiques en premier)
    severity_order = {'CRITIQUE': 0, 'URGENT': 1, 'ATTENTION': 2}
    produits_critiques.sort(key=lambda x: (severity_order.get(x['severity'], 3), -float(x['deficit'])))

    # ── Filtrer par priorité côté template ──
    if priorite_filter:
        alertes_list_filtered = []
        for a in alertes:
            if a.produit and a.seuil_alerte and a.seuil_alerte > 0:
                ratio = float(a.stock_actuel / a.seuil_alerte * 100)
                if priorite_filter == 'CRITIQUE' and ratio <= 25:
                    alertes_list_filtered.append(a)
                elif priorite_filter == 'URGENT' and 25 < ratio <= 50:
                    alertes_list_filtered.append(a)
                elif priorite_filter == 'ATTENTION' and ratio > 50:
                    alertes_list_filtered.append(a)
        alertes = alertes_list_filtered

    # ── Entrepôts en alerte (quantité ≤ seuil critique) ──
    entrepots_alerte = Entrepot.objects.filter(
        quantite_disponible__lte=F('seuil_critique')
    ).values('nom', 'quantite_disponible', 'seuil_critique', 'capacite_max')[:5]

    # ── Lots proches de la date d'expiration (< 30 jours) ──
    lots_expirant = Lot.objects.filter(
        date_expiration__lte=timezone.now() + timedelta(days=30),
        date_expiration__gte=timezone.now(),
        etat__in=['EN_STOCK', 'PARTIELLEMENT_SORTI', 'RESERVE']
    ).select_related('produit').order_by('date_expiration')[:5]

    lots_expires = Lot.objects.filter(
        date_expiration__lt=timezone.now(),
        etat__in=['EN_STOCK', 'PARTIELLEMENT_SORTI']
    ).count()

    # ── Dernières alertes traitées ──
    derniers_traitements = AlerteStock.objects.filter(
        statut='TRAITEE',
        date_traitement__isnull=False,
    ).select_related('produit', 'user_traitement').order_by('-date_traitement')[:5]

    # ── Taux de résolution ──
    taux_resolution = round(alertes_traitees / total_alertes * 100, 1) if total_alertes else 0

    context = {
        'alertes': alertes,
        'statut_filter': statut_filter,
        'search_query': search_query,
        'priorite_filter': priorite_filter,
        # KPIs
        'total_alertes': total_alertes,
        'alertes_actives': alertes_actives,
        'alertes_traitees': alertes_traitees,
        'alertes_ignorees': alertes_ignorees,
        'alertes_avec_da': alertes_avec_da,
        'taux_resolution': taux_resolution,
        # Analyses
        'produits_critiques': produits_critiques,
        'nb_produits_critiques': len(produits_critiques),
        'entrepots_alerte': entrepots_alerte,
        'lots_expirant': lots_expirant,
        'lots_expires': lots_expires,
        'derniers_traitements': derniers_traitements,
    }
    return render(request, 'gestion/alertes/list.html', context)


# ==================== VUES DEMANDES D'ACHAT ====================

@login_required
def demandes_list(request):
    """Liste des demandes d'achat"""
    queryset = DemandeAchat.objects.select_related(
        'produit', 'user_createur', 'user_valideur'
    ).all()
    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        queryset = queryset.filter(statut=statut_filter)

    context = {
        'demandes': queryset.order_by('-date_creation'),
        'statut_filter': statut_filter,
    }
    return render(request, 'gestion/demandes/list.html', context)


@login_required
def demandes_create(request):
    """Créer une demande d'achat"""
    if request.method == 'POST':
        form = DemandeAchatForm(request.POST)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.numero_da = generate_demande_achat_numero()
            # Auto-remplir stock_actuel et seuil_alerte depuis le produit
            produit = demande.produit
            demande.stock_actuel = Lot.objects.filter(
                produit=produit
            ).aggregate(total=Sum('quantite_restante'))['total'] or Decimal('0.00')
            demande.seuil_alerte = produit.seuil_alerte or Decimal('0.00')
            demande.user_createur = request.user
            demande.date_creation = timezone.now()
            demande.save()
            _log_historique(
                request.user, 'creation',
                f'Création de la demande d\'achat {demande.numero_da} pour {produit.nom}',
                nouvelle_valeur={
                    'numero_da': demande.numero_da,
                    'produit': str(produit),
                    'quantite_a_commander': str(demande.quantite_a_commander),
                    'priorite': demande.priorite,
                    'statut': demande.statut,
                },
            )
            messages.success(request, f"Demande d'achat {demande.numero_da} créée avec succès")
            return redirect('demandes_list')
    else:
        form = DemandeAchatForm()

    return render(request, 'gestion/demandes/form.html', {
        'form': form, 'title': "Nouvelle Demande d'Achat",
    })


# ==================== VUES VENTES IMMÉDIATES ====================

@login_required
def ventes_immediates_list(request):
    """Liste des ventes immédiates"""
    queryset = VenteImmediate.objects.select_related(
        'produit', 'client', 'user'
    ).all()
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(numero_vente__icontains=search_query) |
            Q(client__nom__icontains=search_query)
        )

    context = {
        'ventes_immediates': queryset.order_by('-date_vente'),
        'search_query': search_query,
        'total': queryset.aggregate(
            Sum('montant_total')
        )['montant_total__sum'] or 0,
    }
    return render(request, 'gestion/ventes_immediates/list.html', context)


@login_required
def ventes_immediates_create(request):
    """Créer une vente immédiate avec vérification dynamique du stock"""
    if request.method == 'POST':
        form = VenteImmediateForm(request.POST)
        if form.is_valid():
            produit = form.cleaned_data['produit']
            quantite_demandee = form.cleaned_data['quantite_demandee']
            type_vente = form.cleaned_data['type_vente']
            prix_unitaire = form.cleaned_data['prix_unitaire']
            client = form.cleaned_data.get('client')

            # Traiter via le service métier
            result = traiter_vente_immediate_service(
                produit, quantite_demandee, type_vente,
                prix_unitaire, client, request.user
            )

            # Créer l'enregistrement VenteImmediate
            vi = form.save(commit=False)
            vi.numero_vente = generate_vente_immediate_numero()
            vi.quantite_servie_maintenant = result['quantite_servie']
            vi.montant_total = result['montant_total']
            vi.prix_majore_urgence = result.get('prix_majore')
            vi.type_vente = result['type_vente']
            vi.user = request.user
            vi.date_vente = timezone.now()
            if result.get('commande_creee'):
                vi.commande_associee = result['commande_creee']
            vi.save()

            _log_historique(
                request.user, 'vente_immediate',
                f'Vente immédiate {vi.numero_vente} — {result["quantite_servie"]} '
                f'{produit.unite or "unités"} de {produit.nom} ({type_vente})',
                nouvelle_valeur={
                    'numero_vente': vi.numero_vente,
                    'produit': str(produit),
                    'client': str(client) if client else '—',
                    'quantite_servie': str(result['quantite_servie']),
                    'montant_total': str(result['montant_total']),
                    'type_vente': type_vente,
                },
            )

            # Messages selon le type
            if type_vente == 'TOTALE':
                messages.success(request,
                    f'Vente {vi.numero_vente} — {result["quantite_servie"]} '
                    f'unités servies intégralement.')
            elif type_vente == 'PARTIELLE':
                msg = (f'Vente {vi.numero_vente} — {result["quantite_servie"]} '
                       f'unités servies maintenant.')
                if result.get('commande_creee'):
                    msg += (f' Commande {result["commande_creee"].numero_commande} '
                            f'créée pour le reste.')
                messages.info(request, msg)
            elif type_vente == 'URGENTE':
                messages.warning(request,
                    f'Vente urgente {vi.numero_vente} — {result["quantite_servie"]} '
                    f'unités à prix majoré ({result["prix_majore"]} XOF/unité).')

            return redirect('ventes_immediates_list')
    else:
        form = VenteImmediateForm()

    # Passer les infos de stock pour le JS dynamique
    produits_stock = {}
    for p in Produit.objects.all():
        info = get_stock_info(p)
        produits_stock[p.pk] = {k: str(v) for k, v in info.items()}
        produits_stock[p.pk]['prix_unitaire'] = str(p.prix_unitaire or 0)

    return render(request, 'gestion/ventes_immediates/form.html', {
        'form': form, 'title': 'Nouvelle Vente Immédiate',
        'produits_stock_json': produits_stock,
    })


@login_required
def ventes_immediates_delete(request, pk):
    """Supprimer une vente immédiate"""
    vi = get_object_or_404(VenteImmediate, pk=pk)
    if request.method == 'POST':
        _log_historique(
            request.user, 'suppression',
            f'Suppression de la vente immédiate {vi.numero_vente}',
            ancienne_valeur={
                'numero_vente': vi.numero_vente,
                'produit': str(vi.produit),
                'quantite_servie': str(vi.quantite_servie_maintenant),
                'montant_total': str(vi.montant_total),
            },
        )
        vi.delete()
        messages.success(request, 'Vente immédiate supprimée avec succès')
        return redirect('ventes_immediates_list')
    return render(request, 'gestion/confirm_delete.html', {'object': vi})


# ==================== API ENDPOINTS (AJAX) ====================

@login_required
def api_stock_produit(request, pk):
    """API JSON : retourne les infos stock d'un produit (pour AJAX)."""
    produit = get_object_or_404(Produit, pk=pk)
    info = get_stock_info(produit)
    data = {k: str(v) for k, v in info.items()}
    data['prix_unitaire'] = str(produit.prix_unitaire or 0)
    data['nom'] = produit.nom
    data['unite'] = produit.unite or ''
    return JsonResponse(data)


@login_required
def api_check_disponibilite_vi(request):
    """API JSON : vérifie disponibilité pour vente immédiate."""
    produit_id = request.GET.get('produit_id')
    quantite = request.GET.get('quantite', '0')

    try:
        produit = Produit.objects.get(pk=produit_id)
        quantite = Decimal(quantite)
    except (Produit.DoesNotExist, Exception):
        return JsonResponse({'error': 'Produit ou quantité invalide'}, status=400)

    info = get_stock_info(produit)
    dispo = info['stock_disponible']
    stock_total_hors_tampon = (
        (produit.stock_physique or Decimal('0.00'))
        - (produit.stock_tampon_comptoir or Decimal('0.00'))
    )

    options = []
    if dispo >= quantite:
        options.append({
            'type': 'TOTALE',
            'label': f'Servir intégralement ({quantite} {produit.unite or "unités"})',
            'quantite_servie': str(quantite),
            'prix': str(produit.prix_unitaire or 0),
            'montant': str(quantite * (produit.prix_unitaire or Decimal('0'))),
        })
    else:
        if dispo > 0:
            reste = quantite - dispo
            options.append({
                'type': 'PARTIELLE',
                'label': (
                    f'Servir {dispo} maintenant + commande planifiée '
                    f'pour {reste} {produit.unite or "unités"}'
                ),
                'quantite_servie': str(dispo),
                'reste': str(reste),
                'prix': str(produit.prix_unitaire or 0),
                'montant': str(dispo * (produit.prix_unitaire or Decimal('0'))),
            })

        if stock_total_hors_tampon >= quantite:
            prix_majore = (produit.prix_unitaire or Decimal('0')) * Decimal('1.20')
            options.append({
                'type': 'URGENTE',
                'label': (
                    f'Servir {quantite} en urgence (prix majoré +20% : '
                    f'{prix_majore} XOF/unité)'
                ),
                'quantite_servie': str(quantite),
                'prix': str(prix_majore),
                'montant': str(quantite * prix_majore),
            })

        if not options:
            options.append({
                'type': 'PARTIELLE',
                'label': (
                    f'Stock insuffisant. Servir {dispo} maintenant + '
                    f'commande pour le reste'
                ),
                'quantite_servie': str(dispo),
                'reste': str(quantite - dispo),
                'prix': str(produit.prix_unitaire or 0),
                'montant': str(dispo * (produit.prix_unitaire or Decimal('0'))),
            })

    return JsonResponse({
        'stock_disponible': str(dispo),
        'stock_physique': str(info['stock_physique']),
        'stock_reserve': str(info['stock_reserve']),
        'stock_tampon': str(info['stock_tampon_comptoir']),
        'suffisant': dispo >= quantite,
        'options': options,
    })


# ==================== ACTIONS COMMANDES ====================

@login_required
def commande_accepter_view(request, pk):
    """Accepter une commande en attente → passe en CONFIRMEE."""
    commande = get_object_or_404(Commande, pk=pk)
    if request.method == 'POST':
        if commande.statut != 'EN_ATTENTE':
            messages.error(request,
                "Seule une commande en attente peut être acceptée.")
            return redirect('commandes_detail', pk=pk)

        old_statut = commande.statut
        commande.statut = 'CONFIRMEE'
        commande.save(update_fields=['statut'])

        _log_historique(
            request.user, 'modification',
            f'Acceptation de la commande {commande.numero_commande}',
            commande=commande,
            ancienne_valeur={'statut': old_statut},
            nouvelle_valeur={'statut': 'CONFIRMEE'},
        )
        messages.success(request,
            f'Commande {commande.numero_commande} acceptée — vous pouvez maintenant réserver le stock.')
    return redirect('commandes_detail', pk=pk)


@login_required
def commande_confirmer_view(request, pk):
    """Confirmer une commande → réservation automatique du stock."""
    commande = get_object_or_404(Commande, pk=pk)
    if request.method == 'POST':
        old_statut = commande.statut
        success, msg = confirmer_commande(commande, request.user)
        commande.refresh_from_db()
        if success:
            _log_historique(
                request.user, 'reservation',
                f'Réservation de stock pour {commande.numero_commande} — {msg}',
                commande=commande,
                ancienne_valeur={'statut': old_statut, 'quantite_reservee': '0'},
                nouvelle_valeur={'statut': commande.statut, 'quantite_reservee': str(commande.quantite_reservee)},
            )
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect('commandes_detail', pk=pk)


@login_required
def commande_livrer_view(request, pk):
    """Livrer une commande → sortie physique du stock."""
    commande = get_object_or_404(Commande, pk=pk)
    if request.method == 'POST':
        old_statut = commande.statut
        old_servie = str(commande.quantite_servie or 0)
        success, msg = livrer_commande(commande, request.user)
        commande.refresh_from_db()
        if success:
            _log_historique(
                request.user, 'livraison',
                f'Livraison de la commande {commande.numero_commande} — {msg}',
                commande=commande,
                ancienne_valeur={'statut': old_statut, 'quantite_servie': old_servie},
                nouvelle_valeur={'statut': commande.statut, 'quantite_servie': str(commande.quantite_servie)},
            )
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect('commandes_detail', pk=pk)


# ==================== ACTIONS ALERTES ====================

@login_required
def alerte_generer_da_view(request, pk):
    """Générer manuellement une DA depuis une alerte."""
    alerte = get_object_or_404(AlerteStock, pk=pk)
    if request.method == 'POST':
        da = generer_demande_achat_depuis_alerte(alerte, request.user)
        if da:
            messages.success(request,
                f"Demande d'achat {da.numero_da} générée avec succès.")
        else:
            messages.warning(request,
                "Une DA a déjà été générée pour cette alerte.")
    return redirect('alertes_list')


@login_required
def alerte_traiter_view(request, pk):
    """Marquer une alerte comme traitée."""
    alerte = get_object_or_404(AlerteStock, pk=pk)
    if request.method == 'POST':
        alerte.statut = 'TRAITEE'
        alerte.date_traitement = timezone.now()
        alerte.user_traitement = request.user
        alerte.save(update_fields=['statut', 'date_traitement', 'user_traitement'])
        messages.success(request, "Alerte marquée comme traitée.")
    return redirect('alertes_list')


# ==================== ACTIONS DEMANDES D'ACHAT ====================

@login_required
def demande_action_view(request, pk, action):
    """Actions sur les demandes d'achat : envoyer, valider, commander, réceptionner."""
    demande = get_object_or_404(DemandeAchat, pk=pk)
    if request.method != 'POST':
        return redirect('demandes_list')

    transitions = {
        'envoyer': ('BROUILLON', 'ENVOYEE', 'Demande envoyée au service achats.'),
        'valider': ('ENVOYEE', 'VALIDEE', 'Demande validée.'),
        'commander': ('VALIDEE', 'COMMANDEE', 'Bon de commande émis.'),
    }

    if action in transitions:
        statut_requis, nouveau_statut, msg = transitions[action]
        if demande.statut == statut_requis:
            old_statut = demande.statut
            demande.statut = nouveau_statut
            if action == 'valider':
                demande.user_valideur = request.user
                demande.date_validation = timezone.now()
                demande.save(update_fields=['statut', 'user_valideur', 'date_validation'])
            else:
                demande.save(update_fields=['statut'])
            _log_historique(
                request.user, 'modification',
                f'DA {demande.numero_da} : {old_statut} → {nouveau_statut} ({msg})',
                ancienne_valeur={'statut': old_statut},
                nouvelle_valeur={'statut': nouveau_statut},
            )
            messages.success(request, msg)
        else:
            messages.error(request,
                f"Action impossible : la DA est en statut '{demande.get_statut_display()}'.")

    elif action == 'receptionner':
        old_statut = demande.statut
        success, msg = receptionner_demande_achat(demande, request.user)
        if success:
            _log_historique(
                request.user, 'reception',
                f'Réception de la DA {demande.numero_da} — {demande.quantite_a_commander} unités de {demande.produit.nom}',
                ancienne_valeur={'statut': old_statut},
                nouvelle_valeur={'statut': 'RECEPTIONNEE', 'quantite_reçue': str(demande.quantite_a_commander)},
            )
            messages.success(request, msg)
        else:
            messages.error(request, msg)

    elif action == 'annuler':
        old_statut = demande.statut
        demande.statut = 'ANNULEE'
        demande.save(update_fields=['statut'])
        _log_historique(
            request.user, 'annulation',
            f'Annulation de la DA {demande.numero_da}',
            ancienne_valeur={'statut': old_statut},
            nouvelle_valeur={'statut': 'ANNULEE'},
        )
        messages.success(request, "Demande annulée.")

    return redirect('demandes_list')


