from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from .models import (
    Clients, Produits, Lots, Ventes, Entrepots, ZoneEntrepots,
    Producteurs, MouvementStocks, HistoriqueTracabilites
)
from .forms import (
    ClientsForm, ProduitsForm, LotsForm, VentesForm, EntrepotsForm,
    ZoneEntrepotsForm, ProducteursForm, MouvementStocksForm
)


@login_required
def dashboard(request):
    """Tableau de bord principal du gestionnaire"""
    context = {
        'total_clients': Clients.objects.count(),
        'total_produits': Produits.objects.count(),
        'total_lots': Lots.objects.count(),
        'total_ventes': Ventes.objects.count(),
        'total_entrepots': Entrepots.objects.count(),
        'total_producteurs': Producteurs.objects.count(),
        
        # Statistiques détaillées
        'lots_expiration_proche': Lots.objects.filter(
            date_expiration__lte=timezone.now() + timedelta(days=30),
            date_expiration__gte=timezone.now()
        ).count(),
        'lots_expires': Lots.objects.filter(
            date_expiration__lt=timezone.now()
        ).count(),
        'entrepots_alerte': Entrepots.objects.filter(
            quantite_disponible__lte=F('seuil_critique')
        ).count(),
        
        # Dernier mouvements
        'derniers_mouvements': MouvementStocks.objects.select_related(
            'lot', 'user'
        ).order_by('-date_mouvement')[:5],
        
        # Dernieres ventes
        'dernieres_ventes': Ventes.objects.select_related(
            'client', 'lot', 'user'
        ).order_by('-date_vente')[:5],
        
        # Stock par zone
        'stock_par_zone': ZoneEntrepots.objects.filter(
            quantite__gt=0
        ).order_by('-quantite')[:10],
    }
    return render(request, 'gestion/dashboard.html', context)


# ==================== VUES CLIENTS ====================

@login_required
def clients_list(request):
    """Liste des clients avec recherche et filtrage"""
    queryset = Clients.objects.all()
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
@permission_required('app.add_clients', raise_exception=True)
def clients_create(request):
    """Créer un nouveau client"""
    if request.method == 'POST':
        form = ClientsForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client créé avec succès')
            return redirect('clients_list')
    else:
        form = ClientsForm()
    
    return render(request, 'gestion/clients/form.html', {'form': form, 'title': 'Nouveau Client'})


@login_required
def clients_detail(request, pk):
    """Détail d'un client"""
    client = get_object_or_404(Clients, pk=pk)
    ventes_client = Ventes.objects.filter(client=client).select_related('lot', 'user')
    
    context = {
        'client': client,
        'ventes': ventes_client.order_by('-date_vente'),
        'total_achats': ventes_client.aggregate(Sum('montant_total'))['montant_total__sum'] or 0,
    }
    return render(request, 'gestion/clients/detail.html', context)


@login_required
@permission_required('app.change_clients', raise_exception=True)
def clients_update(request, pk):
    """Modifier un client"""
    client = get_object_or_404(Clients, pk=pk)
    if request.method == 'POST':
        form = ClientsForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client modifié avec succès')
            return redirect('clients_detail', pk=pk)
    else:
        form = ClientsForm(instance=client)
    
    return render(request, 'gestion/clients/form.html', {'form': form, 'title': f'Modifier {client.nom}'})


@login_required
@permission_required('app.delete_clients', raise_exception=True)
def clients_delete(request, pk):
    """Supprimer un client"""
    client = get_object_or_404(Clients, pk=pk)
    if request.method == 'POST':
        client.delete()
        messages.success(request, 'Client supprimé avec succès')
        return redirect('clients_list')
    
    return render(request, 'gestion/confirm_delete.html', {'object': client})


# ==================== VUES PRODUITS ====================

@login_required
def produits_list(request):
    """Liste des produits"""
    queryset = Produits.objects.all()
    search_query = request.GET.get('search', '')
    categorie_filter = request.GET.get('categorie', '')
    
    if search_query:
        queryset = queryset.filter(
            Q(nom__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if categorie_filter:
        queryset = queryset.filter(categorie=categorie_filter)
    
    context = {
        'produits': queryset.order_by('nom'),
        'search_query': search_query,
        'categories': Produits.objects.values_list('categorie', flat=True).distinct(),
    }
    return render(request, 'gestion/produits/list.html', context)


@login_required
@permission_required('app.add_produits', raise_exception=True)
def produits_create(request):
    """Créer un nouveau produit"""
    if request.method == 'POST':
        form = ProduitsForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produit créé avec succès')
            return redirect('produits_list')
    else:
        form = ProduitsForm()
    
    return render(request, 'gestion/produits/form.html', {'form': form, 'title': 'Nouveau Produit'})


@login_required
@permission_required('app.change_produits', raise_exception=True)
def produits_update(request, pk):
    """Modifier un produit"""
    produit = get_object_or_404(Produits, pk=pk)
    if request.method == 'POST':
        form = ProduitsForm(request.POST, instance=produit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produit modifié avec succès')
            return redirect('produits_list')
    else:
        form = ProduitsForm(instance=produit)
    
    return render(request, 'gestion/produits/form.html', {'form': form, 'title': f'Modifier {produit.nom}'})


@login_required
@permission_required('app.delete_produits', raise_exception=True)
def produits_delete(request, pk):
    """Supprimer un produit"""
    produit = get_object_or_404(Produits, pk=pk)
    if request.method == 'POST':
        produit.delete()
        messages.success(request, 'Produit supprimé avec succès')
        return redirect('produits_list')
    
    return render(request, 'gestion/confirm_delete.html', {'object': produit})


# ==================== VUES PRODUCTEURS ====================

@login_required
def producteurs_list(request):
    """Liste des producteurs"""
    queryset = Producteurs.objects.all()
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
        'statuts': Producteurs.objects.values_list('statut', flat=True).distinct(),
    }
    return render(request, 'gestion/producteurs/list.html', context)


@login_required
@permission_required('app.add_producteurs', raise_exception=True)
def producteurs_create(request):
    """Créer un nouveau producteur"""
    if request.method == 'POST':
        form = ProducteursForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producteur créé avec succès')
            return redirect('producteurs_list')
    else:
        form = ProducteursForm()
    
    return render(request, 'gestion/producteurs/form.html', {'form': form, 'title': 'Nouveau Producteur'})


@login_required
def producteurs_detail(request, pk):
    """Détail d'un producteur"""
    producteur = get_object_or_404(Producteurs, pk=pk)
    lots_producteur = Lots.objects.filter(producteur=producteur).select_related('produit', 'zone')
    
    context = {
        'producteur': producteur,
        'lots': lots_producteur.order_by('-date_creation'),
        'total_lots': lots_producteur.count(),
    }
    return render(request, 'gestion/producteurs/detail.html', context)


@login_required
@permission_required('app.change_producteurs', raise_exception=True)
def producteurs_update(request, pk):
    """Modifier un producteur"""
    producteur = get_object_or_404(Producteurs, pk=pk)
    if request.method == 'POST':
        form = ProducteursForm(request.POST, instance=producteur)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producteur modifié avec succès')
            return redirect('producteurs_detail', pk=pk)
    else:
        form = ProducteursForm(instance=producteur)
    
    return render(request, 'gestion/producteurs/form.html', {'form': form, 'title': f'Modifier {producteur.nom}'})


@login_required
@permission_required('app.delete_producteurs', raise_exception=True)
def producteurs_delete(request, pk):
    """Supprimer un producteur"""
    producteur = get_object_or_404(Producteurs, pk=pk)
    if request.method == 'POST':
        producteur.delete()
        messages.success(request, 'Producteur supprimé avec succès')
        return redirect('producteurs_list')
    
    return render(request, 'gestion/confirm_delete.html', {'object': producteur})


# ==================== VUES ENTREPOTS ====================

@login_required
def entrepots_list(request):
    """Liste des entrepôts"""
    queryset = Entrepots.objects.select_related('responsable').all()
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
        'statuts': Entrepots.objects.values_list('statut', flat=True).distinct(),
    }
    return render(request, 'gestion/entrepots/list.html', context)


@login_required
@permission_required('app.add_entrepots', raise_exception=True)
def entrepots_create(request):
    """Créer un nouvel entrepôt"""
    if request.method == 'POST':
        form = EntrepotsForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entrepôt créé avec succès')
            return redirect('entrepots_list')
    else:
        form = EntrepotsForm()
    
    return render(request, 'gestion/entrepots/form.html', {'form': form, 'title': 'Nouvel Entrepôt'})


@login_required
def entrepots_detail(request, pk):
    """Détail d'un entrepôt"""
    entrepot = get_object_or_404(Entrepots, pk=pk)
    zones = ZoneEntrepots.objects.filter(entrepot=entrepot)
    
    context = {
        'entrepot': entrepot,
        'zones': zones,
        'total_stock': zones.aggregate(Sum('quantite'))['quantite__sum'] or 0,
    }
    return render(request, 'gestion/entrepots/detail.html', context)


@login_required
@permission_required('app.change_entrepots', raise_exception=True)
def entrepots_update(request, pk):
    """Modifier un entrepôt"""
    entrepot = get_object_or_404(Entrepots, pk=pk)
    if request.method == 'POST':
        form = EntrepotsForm(request.POST, instance=entrepot)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entrepôt modifié avec succès')
            return redirect('entrepots_detail', pk=pk)
    else:
        form = EntrepotsForm(instance=entrepot)
    
    return render(request, 'gestion/entrepots/form.html', {'form': form, 'title': f'Modifier {entrepot.nom}'})


@login_required
@permission_required('app.delete_entrepots', raise_exception=True)
def entrepots_delete(request, pk):
    """Supprimer un entrepôt"""
    entrepot = get_object_or_404(Entrepots, pk=pk)
    if request.method == 'POST':
        entrepot.delete()
        messages.success(request, 'Entrepôt supprimé avec succès')
        return redirect('entrepots_list')
    
    return render(request, 'gestion/confirm_delete.html', {'object': entrepot})


# ==================== VUES ZONES ====================

@login_required
def zones_list(request):
    """Liste des zones"""
    queryset = ZoneEntrepots.objects.select_related('entrepot', 'responsable').all()
    search_query = request.GET.get('search', '')
    entrepot_filter = request.GET.get('entrepot', '')
    
    if search_query:
        queryset = queryset.filter(nom__icontains=search_query)
    
    if entrepot_filter:
        queryset = queryset.filter(entrepot_id=entrepot_filter)
    
    context = {
        'zones': queryset.order_by('entrepot', 'nom'),
        'search_query': search_query,
        'entrepots': Entrepots.objects.all(),
    }
    return render(request, 'gestion/zones/list.html', context)


@login_required
@permission_required('app.add_zoneentrepots', raise_exception=True)
def zones_create(request):
    """Créer une nouvelle zone"""
    if request.method == 'POST':
        form = ZoneEntrepotsForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Zone créée avec succès')
            return redirect('zones_list')
    else:
        form = ZoneEntrepotsForm()
    
    return render(request, 'gestion/zones/form.html', {'form': form, 'title': 'Nouvelle Zone'})


@login_required
@permission_required('app.change_zoneentrepots', raise_exception=True)
def zones_update(request, pk):
    """Modifier une zone"""
    zone = get_object_or_404(ZoneEntrepots, pk=pk)
    if request.method == 'POST':
        form = ZoneEntrepotsForm(request.POST, instance=zone)
        if form.is_valid():
            form.save()
            messages.success(request, 'Zone modifiée avec succès')
            return redirect('zones_list')
    else:
        form = ZoneEntrepotsForm(instance=zone)
    
    return render(request, 'gestion/zones/form.html', {'form': form, 'title': f'Modifier {zone.nom}'})


@login_required
@permission_required('app.delete_zoneentrepots', raise_exception=True)
def zones_delete(request, pk):
    """Supprimer une zone"""
    zone = get_object_or_404(ZoneEntrepots, pk=pk)
    if request.method == 'POST':
        zone.delete()
        messages.success(request, 'Zone supprimée avec succès')
        return redirect('zones_list')
    
    return render(request, 'gestion/confirm_delete.html', {'object': zone})


# ==================== VUES LOTS ====================

@login_required
def lots_list(request):
    """Liste des lots"""
    queryset = Lots.objects.select_related('produit', 'producteur', 'zone').all()
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
        'etats': Lots.objects.values_list('etat', flat=True).distinct(),
        'produits': Produits.objects.all(),
    }
    return render(request, 'gestion/lots/list.html', context)


@login_required
@permission_required('app.add_lots', raise_exception=True)
def lots_create(request):
    """Créer un nouveau lot"""
    if request.method == 'POST':
        form = LotsForm(request.POST)
        if form.is_valid():
            lot = form.save(commit=False)
            lot.user = request.user
            lot.date_creation = timezone.now()
            lot.save()
            messages.success(request, 'Lot créé avec succès')
            return redirect('lots_list')
    else:
        form = LotsForm()
    
    return render(request, 'gestion/lots/form.html', {'form': form, 'title': 'Nouveau Lot'})


@login_required
def lots_detail(request, pk):
    """Détail d'un lot"""
    lot = get_object_or_404(Lots, pk=pk)
    mouvements = MouvementStocks.objects.filter(lot=lot).select_related('user', 'zone_origine', 'zone_destination')
    ventes = Ventes.objects.filter(lot=lot).select_related('client', 'user')
    historique = HistoriqueTracabilites.objects.filter(lot=lot).select_related('user')
    
    context = {
        'lot': lot,
        'mouvements': mouvements.order_by('-date_mouvement'),
        'ventes': ventes.order_by('-date_vente'),
        'historique': historique.order_by('-date_action'),
    }
    return render(request, 'gestion/lots/detail.html', context)


@login_required
@permission_required('app.change_lots', raise_exception=True)
def lots_update(request, pk):
    """Modifier un lot"""
    lot = get_object_or_404(Lots, pk=pk)
    if request.method == 'POST':
        form = LotsForm(request.POST, instance=lot)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lot modifié avec succès')
            return redirect('lots_detail', pk=pk)
    else:
        form = LotsForm(instance=lot)
    
    return render(request, 'gestion/lots/form.html', {'form': form, 'title': f'Modifier {lot.code_lot}'})


@login_required
@permission_required('app.delete_lots', raise_exception=True)
def lots_delete(request, pk):
    """Supprimer un lot"""
    lot = get_object_or_404(Lots, pk=pk)
    if request.method == 'POST':
        lot.delete()
        messages.success(request, 'Lot supprimé avec succès')
        return redirect('lots_list')
    
    return render(request, 'gestion/confirm_delete.html', {'object': lot})


# ==================== VUES VENTES ====================

@login_required
def ventes_list(request):
    """Liste des ventes"""
    queryset = Ventes.objects.select_related('client', 'lot', 'user').all()
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
        'total_ventes': queryset.aggregate(Sum('montant_total'))['montant_total__sum'] or 0,
    }
    return render(request, 'gestion/ventes/list.html', context)


@login_required
@permission_required('app.add_ventes', raise_exception=True)
def ventes_create(request):
    """Créer une nouvelle vente"""
    if request.method == 'POST':
        form = VentesForm(request.POST)
        if form.is_valid():
            vente = form.save(commit=False)
            vente.user = request.user
            vente.save()
            messages.success(request, 'Vente enregistrée avec succès')
            return redirect('ventes_list')
    else:
        form = VentesForm()
    
    return render(request, 'gestion/ventes/form.html', {'form': form, 'title': 'Nouvelle Vente'})


@login_required
@permission_required('app.change_ventes', raise_exception=True)
def ventes_update(request, pk):
    """Modifier une vente"""
    vente = get_object_or_404(Ventes, pk=pk)
    if request.method == 'POST':
        form = VentesForm(request.POST, instance=vente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vente modifiée avec succès')
            return redirect('ventes_list')
    else:
        form = VentesForm(instance=vente)
    
    return render(request, 'gestion/ventes/form.html', {'form': form, 'title': f'Modifier {vente.numero_vente}'})


@login_required
@permission_required('app.delete_ventes', raise_exception=True)
def ventes_delete(request, pk):
    """Supprimer une vente"""
    vente = get_object_or_404(Ventes, pk=pk)
    if request.method == 'POST':
        vente.delete()
        messages.success(request, 'Vente supprimée avec succès')
        return redirect('ventes_list')
    
    return render(request, 'gestion/confirm_delete.html', {'object': vente})


# ==================== VUES MOUVEMENTS ====================

@login_required
def mouvements_list(request):
    """Liste des mouvements de stock"""
    queryset = MouvementStocks.objects.select_related('lot', 'user', 'zone_origine', 'zone_destination').all()
    
    context = {
        'mouvements': queryset.order_by('-date_mouvement'),
    }
    return render(request, 'gestion/mouvements/list.html', context)


@login_required
@permission_required('app.add_mouvementstocks', raise_exception=True)
def mouvements_create(request):
    """Créer un nouveau mouvement"""
    if request.method == 'POST':
        form = MouvementStocksForm(request.POST)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.user = request.user
            mouvement.date_mouvement = timezone.now()
            mouvement.save()
            
            # Enregistrer dans l'historique
            HistoriqueTracabilites.objects.create(
                lot=mouvement.lot,
                type_action='mouvement_stock',
                user=request.user,
                ancienne_valeur=f"Zone: {mouvement.zone_origine}",
                nouvelle_valeur=f"Zone: {mouvement.zone_destination}",
                description=f"Mouvement de {mouvement.quantite} {mouvement.lot.produit.unite}"
            )
            
            messages.success(request, 'Mouvement créé avec succès')
            return redirect('mouvements_list')
    else:
        form = MouvementStocksForm()
    
    return render(request, 'gestion/mouvements/form.html', {'form': form, 'title': 'Nouveau Mouvement'})


@login_required
@permission_required('app.delete_mouvementstocks', raise_exception=True)
def mouvements_delete(request, pk):
    """Supprimer un mouvement"""
    mouvement = get_object_or_404(MouvementStocks, pk=pk)
    if request.method == 'POST':
        mouvement.delete()
        messages.success(request, 'Mouvement supprimé avec succès')
        return redirect('mouvements_list')
    
    return render(request, 'gestion/confirm_delete.html', {'object': mouvement})


# ==================== VUES HISTORIQUE ====================

@login_required
def historique_list(request):
    """Liste de l'historique de traçabilité"""
    queryset = HistoriqueTracabilites.objects.select_related('lot', 'user').all()
    search_query = request.GET.get('search', '')
    type_action_filter = request.GET.get('type_action', '')
    
    if search_query:
        queryset = queryset.filter(
            Q(lot__code_lot__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if type_action_filter:
        queryset = queryset.filter(type_action=type_action_filter)
    
    context = {
        'historiques': queryset.order_by('-date_action'),
        'search_query': search_query,
    }
    return render(request, 'gestion/historique/list.html', context)

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

#===================== VUES PRÉDICTION DE STOCK ====================
from .services import StockAnalyticsService

def stock_prediction_view(request):
    # Appel du service (ici on laisse le service simuler ou on passe des données)
    # Pour passer tes vraies données : data = [{'ds': '2025-01-01', 'y': 41000}, ...]
    results = StockAnalyticsService.process_forecast()
    
    context = {
        'forecast': results['full_data'],
        'precision': results['precision'],
        'current_stock': results['current_stock'],
        'capacite_max': results['capacite_max'],
        'seuil_critique': results['seuil_critique'],
    }
    return render(request, 'gestion/prediction/prediction.html', context)