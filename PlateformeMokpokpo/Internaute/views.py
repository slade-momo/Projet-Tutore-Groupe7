from django.shortcuts import render
from django.db.models import Sum, Count, Q
from gestion.models import Produit, Producteur, Entrepot, Vente


def home(request):
    """Page d'accueil vitrine — statistiques publiques dynamiques."""
    produits_count = Produit.objects.count()
    producteurs_count = Producteur.objects.filter(statut='ACTIF').count()
    entrepots_count = Entrepot.objects.count()

    # Quelques produits vedettes (ceux avec le plus de stock disponible)
    produits_vedettes = (
        Produit.objects
        .filter(stock_disponible__gt=0, prix_unitaire__isnull=False)
        .order_by('-stock_disponible')[:3]
    )

    context = {
        'produits_count': produits_count,
        'producteurs_count': producteurs_count,
        'entrepots_count': entrepots_count,
        'produits_vedettes': produits_vedettes,
    }
    return render(request, 'internaute/index.html', context)


def produits(request):
    """Catalogue dynamique — tous les produits disponibles en base."""
    categorie = request.GET.get('categorie', '')
    search = request.GET.get('q', '')

    qs = Produit.objects.filter(prix_unitaire__isnull=False).order_by('nom')

    if categorie:
        qs = qs.filter(categorie__iexact=categorie)
    if search:
        qs = qs.filter(Q(nom__icontains=search) | Q(description__icontains=search))

    categories = (
        Produit.objects
        .values_list('categorie', flat=True)
        .distinct()
        .order_by('categorie')
    )

    context = {
        'produits': qs,
        'categories': categories,
        'categorie_active': categorie,
        'search': search,
    }
    return render(request, 'internaute/produits.html', context)


def apropos(request):
    """Page À propos — quelques métriques dynamiques."""
    stats = {
        'produits': Produit.objects.count(),
        'producteurs': Producteur.objects.filter(statut='ACTIF').count(),
        'entrepots': Entrepot.objects.count(),
    }
    return render(request, 'internaute/apropos.html', {'stats': stats})
