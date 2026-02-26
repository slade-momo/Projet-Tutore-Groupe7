"""Template filters pour l'affichage professionnel de l'historique."""
import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Labels lisibles pour les clés JSON courantes
FIELD_LABELS = {
    'nom': 'Nom',
    'prenom': 'Prénom',
    'entreprise': 'Entreprise',
    'telephone': 'Téléphone',
    'email': 'Email',
    'adresse': 'Adresse',
    'type_client': 'Type client',
    'categorie': 'Catégorie',
    'unite': 'Unité',
    'description': 'Description',
    'prix_unitaire': 'Prix unitaire',
    'stock_physique': 'Stock physique',
    'stock_reserve': 'Stock réservé',
    'stock_tampon_comptoir': 'Stock tampon',
    'seuil_alerte': 'Seuil alerte',
    'localisation': 'Localisation',
    'capacite_max': 'Capacité max',
    'capacite': 'Capacité',
    'seuil_critique': 'Seuil critique',
    'quantite_disponible': 'Quantité disponible',
    'statut': 'Statut',
    'quantite_initiale': 'Quantité initiale',
    'quantite_restante': 'Quantité restante',
    'qualite': 'Qualité',
    'etat': 'État',
    'date_reception': 'Date réception',
    'date_expiration': 'Date expiration',
    'quantite_reservee': 'Quantité réservée',
    'observations': 'Observations',
    'zone': 'Zone',
    'numero_vente': 'N° vente',
    'numero_commande': 'N° commande',
    'quantite_vendue': 'Quantité vendue',
    'montant_total': 'Montant total',
    'mode_paiement': 'Mode paiement',
    'type_vente': 'Type vente',
    'quantite_demandee': 'Quantité demandée',
    'quantite_servie': 'Quantité servie',
    'date_livraison_souhaitee': 'Livraison souhaitée',
    'priorite': 'Priorité',
    'type_mouvement': 'Type mouvement',
    'quantite': 'Quantité',
    'motif': 'Motif',
    'numero_identification': 'N° identification',
    'type_producteur': 'Type producteur',
    'responsable': 'Responsable',
    'produit': 'Produit',
    'producteur': 'Producteur',
    'client': 'Client',
    'lot': 'Lot',
    'entrepot': 'Entrepôt',
}


@register.filter(name='json_display')
def json_display(value, max_items=3):
    """
    Affiche un dict/JSON de manière lisible sous forme de badges HTML.
    Limite à max_items éléments pour la vue liste.
    """
    if not value:
        return mark_safe('<span class="text-muted">—</span>')

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return mark_safe(f'<span class="text-muted">{value}</span>')

    if not isinstance(value, dict):
        return mark_safe(f'<span class="text-muted">{value}</span>')

    items = list(value.items())
    html_parts = []
    for key, val in items[:int(max_items)]:
        label = FIELD_LABELS.get(key, key.replace('_', ' ').capitalize())
        display_val = val if val not in (None, '', 'None') else '—'
        html_parts.append(
            f'<span class="d-inline-block me-2 mb-1">'
            f'<span class="text-muted small">{label}:</span> '
            f'<strong>{display_val}</strong>'
            f'</span>'
        )

    if len(items) > int(max_items):
        html_parts.append(
            f'<span class="badge bg-secondary">+{len(items) - int(max_items)} champs</span>'
        )

    return mark_safe(' '.join(html_parts))


@register.filter(name='json_display_full')
def json_display_full(value):
    """
    Affiche un dict/JSON complet sous forme de tableau lisible.
    Utilisé pour la vue détail de l'historique.
    """
    if not value:
        return mark_safe('<span class="text-muted">Aucune donnée</span>')

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return mark_safe(f'<span>{value}</span>')

    if not isinstance(value, dict):
        return mark_safe(f'<span>{value}</span>')

    rows = []
    for key, val in value.items():
        label = FIELD_LABELS.get(key, key.replace('_', ' ').capitalize())
        display_val = val if val not in (None, '', 'None') else '—'
        rows.append(
            f'<tr><td class="text-muted" style="width:40%">{label}</td>'
            f'<td><strong>{display_val}</strong></td></tr>'
        )

    return mark_safe(
        f'<table class="table table-sm table-borderless mb-0">'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


@register.filter(name='action_icon')
def action_icon(type_action):
    """Retourne l'icône FontAwesome correspondant au type d'action."""
    icons = {
        'creation': 'fa-plus-circle',
        'modification': 'fa-pen',
        'suppression': 'fa-trash',
        'entree': 'fa-arrow-right-to-bracket',
        'sortie': 'fa-arrow-right-from-bracket',
        'mouvement_stock': 'fa-arrows-alt',
        'reservation': 'fa-lock',
        'livraison': 'fa-truck',
        'confirmation': 'fa-check-circle',
        'annulation': 'fa-ban',
        'vente': 'fa-shopping-cart',
        'vente_immediate': 'fa-bolt',
        'reception': 'fa-box-open',
    }
    return icons.get(str(type_action).lower(), 'fa-clock-rotate-left')


@register.filter(name='action_color')
def action_color(type_action):
    """Retourne la classe de couleur correspondant au type d'action."""
    colors = {
        'creation': 'success',
        'modification': 'info',
        'suppression': 'danger',
        'entree': 'success',
        'sortie': 'warning',
        'mouvement_stock': 'primary',
        'reservation': 'info',
        'livraison': 'success',
        'confirmation': 'primary',
        'annulation': 'danger',
        'vente': 'success',
        'vente_immediate': 'warning',
        'reception': 'success',
    }
    return colors.get(str(type_action).lower(), 'secondary')


@register.filter(name='action_label')
def action_label(type_action):
    """Retourne un label lisible pour le type d'action."""
    labels = {
        'creation': 'Création',
        'modification': 'Modification',
        'suppression': 'Suppression',
        'entree': 'Entrée stock',
        'sortie': 'Sortie stock',
        'mouvement_stock': 'Mouvement stock',
        'reservation': 'Réservation',
        'livraison': 'Livraison',
        'confirmation': 'Confirmation',
        'annulation': 'Annulation',
        'vente': 'Vente',
        'vente_immediate': 'Vente immédiate',
        'reception': 'Réception',
    }
    return labels.get(str(type_action).lower(), str(type_action).replace('_', ' ').capitalize())
