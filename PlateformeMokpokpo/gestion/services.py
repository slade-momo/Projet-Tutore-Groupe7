import re
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error
import json
import warnings
warnings.filterwarnings('ignore')


def _next_numero(model_class, field_name, prefix):
    """
    Génère le prochain numéro séquentiel pour un modèle donné.
    Ex : prefix='LOT' → LOT-0001, LOT-0002, …
    """
    last = (
        model_class.objects
        .filter(**{f'{field_name}__startswith': f'{prefix}-'})
        .order_by(f'-{field_name}')
        .values_list(field_name, flat=True)
        .first()
    )
    if last:
        match = re.search(r'(\d+)$', last)
        next_num = int(match.group(1)) + 1 if match else 1
    else:
        next_num = 1
    return f'{prefix}-{next_num:04d}'


def generate_lot_code():
    from .models import Lot
    return _next_numero(Lot, 'code_lot', 'LOT')


def generate_vente_numero():
    from .models import Vente
    return _next_numero(Vente, 'numero_vente', 'VNT')


def generate_commande_numero():
    from .models import Commande
    return _next_numero(Commande, 'numero_commande', 'CMD')


def generate_vente_immediate_numero():
    from .models import VenteImmediate
    return _next_numero(VenteImmediate, 'numero_vente', 'VI')


def generate_demande_achat_numero():
    from .models import DemandeAchat
    return _next_numero(DemandeAchat, 'numero_da', 'DA')


# ==================== BUSINESS LOGIC ====================

def get_stock_info(produit):
    """Retourne les informations de stock détaillées pour un produit."""
    from decimal import Decimal
    sp = produit.stock_physique or Decimal('0.00')
    sr = produit.stock_reserve or Decimal('0.00')
    st = produit.stock_tampon_comptoir or Decimal('0.00')
    sd = max(Decimal('0.00'), sp - sr - st)
    seuil = produit.seuil_alerte or Decimal('0.00')
    return {
        'stock_physique': sp,
        'stock_reserve': sr,
        'stock_tampon_comptoir': st,
        'stock_disponible': sd,
        'seuil_alerte': seuil,
        'en_alerte': sd <= seuil and seuil > 0,
    }


def reserver_stock_commande(commande, produit, quantite, user):
    """
    Réserve du stock pour une commande planifiée.
    Retourne (quantite_reservee, statut).
    """
    from .models import Lot, AffectationLot, MouvementStock, LigneCommande
    from django.utils import timezone
    from decimal import Decimal

    info = get_stock_info(produit)
    dispo = info['stock_disponible']

    if dispo >= quantite:
        qty_res = quantite
        statut = 'RESERVEE'
    elif dispo > 0:
        qty_res = dispo
        statut = 'EN_ATTENTE_REAPPRO'
    else:
        qty_res = Decimal('0.00')
        statut = 'EN_ATTENTE_REAPPRO'

    if qty_res > 0:
        # Mettre à jour le stock réservé du produit
        produit.stock_reserve = (produit.stock_reserve or Decimal('0.00')) + qty_res
        produit.save(update_fields=['stock_reserve'])

        # Affecter depuis les lots disponibles (FIFO)
        lots = Lot.objects.filter(
            produit=produit,
            etat__in=['EN_STOCK', 'PARTIELLEMENT_SORTI'],
            quantite_restante__gt=0,
        ).order_by('date_reception')

        reste = qty_res
        for lot in lots:
            if reste <= 0:
                break
            lot_dispo = lot.quantite_restante - (lot.quantite_reservee or Decimal('0.00'))
            if lot_dispo <= 0:
                continue
            affecte = min(reste, lot_dispo)

            AffectationLot.objects.create(
                commande=commande, lot=lot,
                quantite_affectee=affecte,
                date_affectation=timezone.now(),
                user=user, statut='RESERVE',
            )
            lot.quantite_reservee = (lot.quantite_reservee or Decimal('0.00')) + affecte
            if lot.quantite_reservee >= lot.quantite_restante:
                lot.etat = 'RESERVE'
            lot.save(update_fields=['quantite_reservee', 'etat'])

            MouvementStock.objects.create(
                lot=lot, type_mouvement='RESERVATION',
                quantite=affecte,
                motif=f'Réservation pour {commande.numero_commande}',
                commande=commande, user=user,
                date_mouvement=timezone.now(), valide=True,
            )
            reste -= affecte

    # Mettre à jour la commande
    commande.quantite_reservee = (commande.quantite_reservee or Decimal('0.00')) + qty_res
    commande.statut = statut
    commande.save(update_fields=['quantite_reservee', 'statut'])

    # Mettre à jour la ligne commande associée
    ligne = LigneCommande.objects.filter(commande=commande, produit=produit).first()
    if ligne:
        ligne.quantite_reservee = (ligne.quantite_reservee or Decimal('0.00')) + qty_res
        ligne.statut_ligne = 'RESERVEE' if statut == 'RESERVEE' else 'EN_ATTENTE_REAPPRO'
        ligne.save(update_fields=['quantite_reservee', 'statut_ligne'])

    # Vérifier les alertes
    verifier_et_creer_alertes(produit, user)
    return qty_res, statut


def traiter_vente_immediate_service(produit, quantite_demandee, type_vente,
                                    prix_unitaire, client, user):
    """
    Traite la logique métier d'une vente immédiate.
    Retourne un dict avec le résultat.
    """
    from .models import Commande, LigneCommande, Lot, MouvementStock
    from django.utils import timezone
    from decimal import Decimal

    info = get_stock_info(produit)
    dispo = info['stock_disponible']
    result = {'commande_creee': None}

    if type_vente == 'TOTALE':
        quantite_servie = quantite_demandee
        montant = quantite_servie * prix_unitaire
        prix_majore = None

    elif type_vente == 'PARTIELLE':
        quantite_servie = min(dispo, quantite_demandee)
        montant = quantite_servie * prix_unitaire
        reste = quantite_demandee - quantite_servie
        prix_majore = None
        if reste > 0:
            cmd = Commande.objects.create(
                numero_commande=generate_commande_numero(),
                client=client, date_commande=timezone.now(),
                quantite_demandee=reste,
                quantite_reservee=Decimal('0.00'),
                quantite_servie=Decimal('0.00'),
                statut='EN_ATTENTE_REAPPRO', priorite='NORMALE',
                user=user,
                observations='Commande auto (reste vente immédiate)',
            )
            LigneCommande.objects.create(
                commande=cmd, produit=produit,
                quantite_demandee=reste,
                quantite_reservee=Decimal('0.00'),
                quantite_servie=Decimal('0.00'),
                prix_unitaire=prix_unitaire,
                statut_ligne='EN_ATTENTE_REAPPRO',
            )
            result['commande_creee'] = cmd

    elif type_vente == 'URGENTE':
        stock_total = (produit.stock_physique or Decimal('0.00')) - \
                      (produit.stock_tampon_comptoir or Decimal('0.00'))
        quantite_servie = min(max(Decimal('0.00'), stock_total), quantite_demandee)
        prix_majore = prix_unitaire * Decimal('1.20')  # +20% urgence
        montant = quantite_servie * prix_majore

    else:
        quantite_servie = min(dispo, quantite_demandee)
        montant = quantite_servie * prix_unitaire
        prix_majore = None

    # Déduire du stock physique
    if quantite_servie > 0:
        produit.stock_physique = max(Decimal('0.00'),
            (produit.stock_physique or Decimal('0.00')) - quantite_servie)
        if type_vente == 'URGENTE':
            prise_reserve = max(Decimal('0.00'), quantite_servie - dispo)
            if prise_reserve > 0:
                produit.stock_reserve = max(Decimal('0.00'),
                    (produit.stock_reserve or Decimal('0.00')) - prise_reserve)
        produit.save(update_fields=['stock_physique', 'stock_reserve'])

        # Sortie FIFO des lots
        lots = Lot.objects.filter(
            produit=produit,
            etat__in=['EN_STOCK', 'PARTIELLEMENT_SORTI', 'RESERVE'],
            quantite_restante__gt=0,
        ).order_by('date_reception')
        reste = quantite_servie
        for lot in lots:
            if reste <= 0:
                break
            lot_dispo = lot.quantite_restante
            if type_vente != 'URGENTE':
                lot_dispo -= (lot.quantite_reservee or Decimal('0.00'))
            if lot_dispo <= 0:
                continue
            prendre = min(reste, lot_dispo)
            lot.quantite_restante -= prendre
            if lot.quantite_restante <= 0:
                lot.etat = 'EPUISE'
            else:
                lot.etat = 'PARTIELLEMENT_SORTI'
            lot.save(update_fields=['quantite_restante', 'etat'])

            MouvementStock.objects.create(
                lot=lot, type_mouvement='SORTIE',
                quantite=prendre,
                motif=f'Vente immédiate ({type_vente})',
                user=user, date_mouvement=timezone.now(), valide=True,
            )
            reste -= prendre

    # Vérifier les alertes
    verifier_et_creer_alertes(produit, user)

    result.update({
        'quantite_servie': quantite_servie,
        'montant_total': montant,
        'type_vente': type_vente,
        'prix_majore': prix_majore,
    })
    return result


def verifier_et_creer_alertes(produit, user=None):
    """Vérifie si stock ≤ seuil et crée alerte + DA automatiquement.
    Si le stock est repassé au-dessus du seuil, résout les alertes actives."""
    from .models import AlerteStock
    from django.utils import timezone

    # Rafraîchir le produit depuis la BD (les triggers DB ont pu modifier le stock)
    produit.refresh_from_db()
    info = get_stock_info(produit)

    if not info['en_alerte']:
        # Stock OK → résoudre les alertes actives existantes
        alertes_actives = AlerteStock.objects.filter(produit=produit, statut='ACTIVE')
        for alerte in alertes_actives:
            alerte.statut = 'TRAITEE'
            alerte.date_traitement = timezone.now()
            alerte.user_traitement = user
            alerte.observations = (
                (alerte.observations or '') +
                f'\nRésolue auto : stock remonté à {info["stock_disponible"]}'
            )
            alerte.save(update_fields=['statut', 'date_traitement',
                                       'user_traitement', 'observations'])
        return None

    existe = AlerteStock.objects.filter(produit=produit, statut='ACTIVE').exists()
    if existe:
        # Mettre à jour le stock_actuel de l'alerte existante
        AlerteStock.objects.filter(produit=produit, statut='ACTIVE').update(
            stock_actuel=info['stock_disponible']
        )
        return None

    alerte = AlerteStock.objects.create(
        produit=produit, date_alerte=timezone.now(),
        stock_actuel=info['stock_disponible'],
        seuil_alerte=info['seuil_alerte'],
        statut='ACTIVE', demande_achat_generee=False,
        observations=(
            f'Alerte auto : stock dispo ({info["stock_disponible"]}) '
            f'≤ seuil ({info["seuil_alerte"]})'
        ),
    )
    if user:
        generer_demande_achat_depuis_alerte(alerte, user)
    return alerte


def generer_demande_achat_depuis_alerte(alerte, user):
    """Génère une DA automatiquement depuis une alerte."""
    from .models import DemandeAchat
    from django.utils import timezone
    from decimal import Decimal

    if alerte.demande_achat_generee:
        return None

    produit = alerte.produit
    qty_opt = produit.quantite_optimale_commande or Decimal('100.00')
    qty_cmd = max(qty_opt, (alerte.seuil_alerte * 2) - alerte.stock_actuel)

    da = DemandeAchat.objects.create(
        numero_da=generate_demande_achat_numero(),
        date_creation=timezone.now(),
        produit=produit,
        stock_actuel=alerte.stock_actuel,
        seuil_alerte=alerte.seuil_alerte,
        quantite_a_commander=qty_cmd,
        priorite='URGENT' if alerte.stock_actuel <= 0 else 'NORMAL',
        statut='BROUILLON',
        alerte=alerte,
        user_createur=user,
    )
    alerte.demande_achat_generee = True
    alerte.save(update_fields=['demande_achat_generee'])
    return da


def confirmer_commande(commande, user):
    """Confirme une commande → lance la réservation automatique du stock."""
    from .models import LigneCommande

    lignes = LigneCommande.objects.filter(commande=commande).select_related('produit')
    if not lignes.exists():
        return False, "Aucune ligne de commande à réserver."

    tout_reserve = True
    for ligne in lignes:
        qty, statut = reserver_stock_commande(
            commande, ligne.produit, ligne.quantite_demandee, user)
        if statut != 'RESERVEE':
            tout_reserve = False

    msg = ("Stock entièrement réservé." if tout_reserve
           else "Réservation partielle — en attente de réapprovisionnement.")
    return True, msg


def livrer_commande(commande, user):
    """Livre une commande → sort physiquement le stock réservé."""
    from .models import AffectationLot, MouvementStock
    from django.utils import timezone
    from decimal import Decimal

    if commande.statut not in ('RESERVEE', 'PARTIELLEMENT_SERVIE',
                                'EN_ATTENTE_REAPPRO', 'CONFIRMEE'):
        return False, "La commande ne peut pas être livrée dans son état actuel."

    affectations = AffectationLot.objects.filter(
        commande=commande, statut='RESERVE'
    ).select_related('lot', 'lot__produit')

    if not affectations.exists():
        return False, "Aucune affectation de lot à livrer."

    total_servi = Decimal('0.00')
    for aff in affectations:
        lot = aff.lot
        qty = aff.quantite_affectee
        lot.quantite_restante = max(Decimal('0.00'), lot.quantite_restante - qty)
        lot.quantite_reservee = max(Decimal('0.00'),
            (lot.quantite_reservee or Decimal('0.00')) - qty)
        lot.etat = 'EPUISE' if lot.quantite_restante <= 0 else 'PARTIELLEMENT_SORTI'
        lot.save(update_fields=['quantite_restante', 'quantite_reservee', 'etat'])

        produit = lot.produit
        produit.stock_physique = max(Decimal('0.00'),
            (produit.stock_physique or Decimal('0.00')) - qty)
        produit.stock_reserve = max(Decimal('0.00'),
            (produit.stock_reserve or Decimal('0.00')) - qty)
        produit.save(update_fields=['stock_physique', 'stock_reserve'])

        MouvementStock.objects.create(
            lot=lot, type_mouvement='SORTIE', quantite=qty,
            motif=f'Livraison {commande.numero_commande}',
            commande=commande, user=user,
            date_mouvement=timezone.now(), valide=True,
        )
        aff.statut = 'SERVI'
        aff.save(update_fields=['statut'])
        total_servi += qty
        verifier_et_creer_alertes(produit, user)

    commande.quantite_servie = (commande.quantite_servie or Decimal('0.00')) + total_servi
    commande.statut = 'LIVREE'
    commande.date_livraison_effective = timezone.now().date()
    commande.save(update_fields=['quantite_servie', 'statut', 'date_livraison_effective'])

    return True, f"Commande livrée — {total_servi} unités servies."


def receptionner_demande_achat(demande, user):
    """Réceptionne une DA → met à jour le stock physique du produit."""
    from django.utils import timezone
    from decimal import Decimal

    if demande.statut not in ('COMMANDEE', 'VALIDEE'):
        return False, "La DA doit être commandée ou validée pour être réceptionnée."

    produit = demande.produit
    produit.stock_physique = (
        (produit.stock_physique or Decimal('0.00')) + demande.quantite_a_commander
    )
    produit.date_dernier_reappro = timezone.now()
    produit.save(update_fields=['stock_physique', 'date_dernier_reappro'])

    demande.statut = 'RECEPTIONNEE'
    demande.save(update_fields=['statut'])

    if demande.alerte:
        demande.alerte.statut = 'TRAITEE'
        demande.alerte.date_traitement = timezone.now()
        demande.alerte.user_traitement = user
        demande.alerte.save(update_fields=['statut', 'date_traitement', 'user_traitement'])

    return True, (
        f"DA réceptionnée — {demande.quantite_a_commander} "
        f"ajoutées au stock de {produit.nom}."
    )


class StockAnalyticsService:
    """Service de prévision basé sur LinearRegression + saisonnalité cajou Togo."""

    # ── Seuils par défaut ──
    SEUIL_MIN = 100
    SEUIL_ALERTE = 300
    SEUIL_OPTIMAL = 500

    MOIS_LABELS = [
        'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
        'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc',
    ]

    # ── Saisonnalité cajou au Togo ──
    # Récolte : Fév-Mai (pic Mars-Avr) → fortes entrées
    # Saison sèche (Nov-Jan) et saison des pluies (Jun-Sep) → entrées faibles
    # Ventes/export : pics en Avr-Jun (après récolte) et Nov-Déc (fêtes)
    SAISON_ENTREES_TOGO = {
        1: 0.30,   # Jan : hors récolte, très peu
        2: 0.85,   # Fév : début campagne cajou
        3: 1.50,   # Mar : pic récolte
        4: 1.60,   # Avr : pic récolte
        5: 1.10,   # Mai : fin récolte
        6: 0.40,   # Jun : saison pluies, peu
        7: 0.20,   # Jul : saison pluies
        8: 0.15,   # Aoû : saison pluies
        9: 0.20,   # Sep : fin pluies
        10: 0.30,  # Oct : transition
        11: 0.25,  # Nov : saison sèche
        12: 0.25,  # Déc : saison sèche
    }
    SAISON_SORTIES_TOGO = {
        1: 0.60,   # Jan : demande modérée
        2: 0.70,   # Fév : demande croissante
        3: 0.90,   # Mar : export début
        4: 1.30,   # Avr : export fort
        5: 1.40,   # Mai : export/ventes fort
        6: 1.20,   # Jun : export continue
        7: 0.80,   # Jul : baisse
        8: 0.70,   # Aoû : baisse
        9: 0.75,   # Sep : reprise lente
        10: 0.85,  # Oct : reprise
        11: 1.10,  # Nov : fêtes, demande forte
        12: 1.20,  # Déc : fêtes, demande forte
    }

    @staticmethod
    def generate_stock_data():
        """Construit la série temporelle mensuelle à partir des données réelles."""
        from .models import (
            MouvementStock, Produit, Entrepot, Lot, Vente, VenteImmediate,
        )
        from django.db.models import Sum, Q, Avg
        from django.db.models.functions import TruncMonth

        # ── Paramètres réels depuis la BD ──
        agg = Entrepot.objects.aggregate(
            cap=Sum('capacite_max'), seuil=Sum('seuil_critique'))
        capacite_max = float(agg['cap'] or 50000)
        seuil_critique = float(agg['seuil'] or StockAnalyticsService.SEUIL_ALERTE)
        stock_actuel = float(
            Produit.objects.aggregate(t=Sum('stock_physique'))['t'] or 0)

        # Seuils dynamiques basés sur les données réelles
        seuil_min = float(
            Produit.objects.aggregate(t=Avg('seuil_alerte'))['t']
            or StockAnalyticsService.SEUIL_MIN)
        seuil_alerte = max(seuil_critique, StockAnalyticsService.SEUIL_ALERTE)
        seuil_optimal = float(
            Produit.objects.aggregate(t=Avg('quantite_optimale_commande'))['t']
            or StockAnalyticsService.SEUIL_OPTIMAL)

        def _to_key(dt):
            return f"{dt.year:04d}-{dt.month:02d}" if dt else None

        entrees = {}
        sorties = {}

        # ── Source 1 : MouvementStock ──
        mvt_qs = (
            MouvementStock.objects
            .filter(date_mouvement__isnull=False)
            .annotate(mois=TruncMonth('date_mouvement'))
            .values('mois')
            .annotate(
                ent=Sum('quantite', filter=Q(
                    type_mouvement__in=['ENTREE', 'AJUSTEMENT', 'LIBERATION'])),
                sor=Sum('quantite', filter=Q(
                    type_mouvement__in=['SORTIE', 'RESERVATION'])),
            )
            .order_by('mois')
        )
        for r in mvt_qs:
            k = _to_key(r['mois'])
            if k:
                entrees[k] = entrees.get(k, 0) + float(r['ent'] or 0)
                sorties[k] = sorties.get(k, 0) + float(r['sor'] or 0)

        # ── Source 2 : Lots reçus ──
        lots_agg = (
            Lot.objects
            .filter(date_reception__isnull=False)
            .annotate(mois=TruncMonth('date_reception'))
            .values('mois')
            .annotate(total=Sum('quantite_initiale'))
            .order_by('mois')
        )
        for r in lots_agg:
            k = _to_key(r['mois'])
            if k and k not in entrees:
                entrees[k] = float(r['total'] or 0)

        # ── Source 3 : Ventes + Ventes Immédiates ──
        ventes_agg = (
            Vente.objects
            .filter(date_vente__isnull=False)
            .annotate(mois=TruncMonth('date_vente'))
            .values('mois')
            .annotate(total=Sum('quantite_vendue'))
            .order_by('mois')
        )
        for r in ventes_agg:
            k = _to_key(r['mois'])
            if k and k not in sorties:
                sorties[k] = float(r['total'] or 0)

        vi_agg = (
            VenteImmediate.objects
            .filter(date_vente__isnull=False)
            .annotate(mois=TruncMonth('date_vente'))
            .values('mois')
            .annotate(total=Sum('quantite_servie_maintenant'))
            .order_by('mois')
        )
        for r in vi_agg:
            k = _to_key(r['mois'])
            if k:
                sorties[k] = sorties.get(k, 0) + float(r['total'] or 0)

        # ── Fusion en série temporelle continue ──
        all_keys = sorted(set(entrees.keys()) | set(sorties.keys()))
        if not all_keys:
            return None, capacite_max, seuil_min, seuil_alerte, seuil_optimal, stock_actuel

        first = pd.Timestamp(all_keys[0] + '-01')
        last = pd.Timestamp(all_keys[-1] + '-01')
        date_range = pd.date_range(start=first, end=last, freq='MS')

        rows = []
        for dt in date_range:
            k = f"{dt.year:04d}-{dt.month:02d}"
            rows.append({
                'ds': dt,
                'entrees': entrees.get(k, 0),
                'sorties': sorties.get(k, 0),
            })

        df = pd.DataFrame(rows)

        # ── Stock glissant recalé sur le stock physique actuel ──
        flux_cumule = (df['entrees'] - df['sorties']).cumsum()
        stock_initial = stock_actuel - float(flux_cumule.iloc[-1])
        df['stock'] = stock_initial + flux_cumule
        df['stock'] = df['stock'].clip(lower=0, upper=capacite_max)

        # ── Features pour la régression ──
        df['mois_num'] = df['ds'].dt.month
        df['tendance'] = np.arange(len(df))
        df['stock_prev'] = df['stock'].shift(1).fillna(df['stock'].iloc[0])

        return df, capacite_max, seuil_min, seuil_alerte, seuil_optimal, stock_actuel

    @staticmethod
    def _train_models(df):
        """Entraîne les 3 modèles de régression linéaire."""
        if len(df) < 3:
            return None, None, None, {}

        # ── Features communes ──
        X_entrees = df[['mois_num', 'tendance', 'stock_prev']].values
        y_entrees = df['entrees'].values

        X_sorties = df[['mois_num', 'tendance', 'stock_prev']].values
        y_sorties = df['sorties'].values

        X_stock = df[['stock_prev', 'entrees', 'sorties', 'mois_num', 'tendance']].values
        y_stock = df['stock'].values

        model_entrees = LinearRegression()
        model_entrees.fit(X_entrees, y_entrees)
        pred_entrees = model_entrees.predict(X_entrees)

        model_sorties = LinearRegression()
        model_sorties.fit(X_sorties, y_sorties)
        pred_sorties = model_sorties.predict(X_sorties)

        model_stock = LinearRegression()
        model_stock.fit(X_stock, y_stock)
        pred_stock = model_stock.predict(X_stock)

        # ── Métriques RÉALISTES ──
        # R² brut sur données d'entraînement (pas de test set)
        def _safe_r2(y_true, y_pred):
            if len(y_true) < 2 or np.std(y_true) == 0:
                return 0
            return max(0, r2_score(y_true, y_pred))

        r2_e = _safe_r2(y_entrees, pred_entrees)
        r2_s = _safe_r2(y_sorties, pred_sorties)
        r2_st = _safe_r2(y_stock, pred_stock)

        # Pénalité pour petit jeu de données (R² sur-estimé)
        # Moins de 12 mois → forte pénalité, plus de 24 → faible pénalité
        n = len(df)
        penalite_data = min(1.0, 0.4 + 0.6 * (n / 24))  # 0.4 à 3 mois, 1.0 à 24+
        # On plafonne à 92% max (jamais 100% - c'est irréaliste)
        plafond = 0.92

        r2_e_adj = min(r2_e * penalite_data, plafond)
        r2_s_adj = min(r2_s * penalite_data, plafond)
        r2_st_adj = min(r2_st * penalite_data, plafond)
        precision_globale = (r2_e_adj + r2_s_adj + r2_st_adj) / 3

        metrics = {
            'r2_entrees': round(r2_e_adj * 100, 1),
            'r2_sorties': round(r2_s_adj * 100, 1),
            'r2_stock': round(r2_st_adj * 100, 1),
            'mae_entrees': round(mean_absolute_error(y_entrees, pred_entrees), 1),
            'mae_sorties': round(mean_absolute_error(y_sorties, pred_sorties), 1),
            'mae_stock': round(mean_absolute_error(y_stock, pred_stock), 1),
            'precision_globale': round(precision_globale * 100, 1),
            'nb_points': n,
            'fiabilite': (
                'Faible' if n < 6 else
                'Moyenne' if n < 12 else
                'Bonne' if n < 24 else 'Elevee'
            ),
        }

        return model_entrees, model_sorties, model_stock, metrics

    @staticmethod
    def _generate_predictions(df, model_entrees, model_sorties, model_stock,
                              n_months=36, capacite_max=50000):
        """Génère n_months de prédictions avec saisonnalité cajou togolaise."""
        last_date = df['ds'].iloc[-1]
        last_stock = float(df['stock'].iloc[-1])
        last_tendance = int(df['tendance'].iloc[-1])

        # Variabilité historique pour ajouter du réalisme
        hist_entrees_std = max(float(df['entrees'].std()), 1)
        hist_sorties_std = max(float(df['sorties'].std()), 1)
        hist_entrees_mean = max(float(df['entrees'].mean()), 1)
        hist_sorties_mean = max(float(df['sorties'].mean()), 1)

        # Calcul de la saisonnalité observée vs saisonnalité Togo
        # Si assez de données, on pondère historique réel + modèle Togo
        n = len(df)
        poids_modele_togo = max(0.3, 1.0 - (n / 36))  # 30% min, 100% à 0 données

        predictions = []
        current_stock = last_stock
        np.random.seed(42)  # Reproductibilité

        for i in range(1, n_months + 1):
            future_date = last_date + pd.DateOffset(months=i)
            mois_num = future_date.month
            tendance = last_tendance + i

            # Prédiction brute du modèle
            X_e = np.array([[mois_num, tendance, current_stock]])
            pred_entree_brut = max(0, float(model_entrees.predict(X_e)[0]))

            X_s = np.array([[mois_num, tendance, current_stock]])
            pred_sortie_brut = max(0, float(model_sorties.predict(X_s)[0]))

            # Appliquer la saisonnalité cajou togolaise
            coeff_entree_togo = StockAnalyticsService.SAISON_ENTREES_TOGO[mois_num]
            coeff_sortie_togo = StockAnalyticsService.SAISON_SORTIES_TOGO[mois_num]

            # Prédiction pondérée : modèle LR + saisonnalité Togo
            pred_entree_saison = hist_entrees_mean * coeff_entree_togo
            pred_sortie_saison = hist_sorties_mean * coeff_sortie_togo

            pred_entree = (
                (1 - poids_modele_togo) * pred_entree_brut +
                poids_modele_togo * pred_entree_saison
            )
            pred_sortie = (
                (1 - poids_modele_togo) * pred_sortie_brut +
                poids_modele_togo * pred_sortie_saison
            )

            # Ajouter variabilité réaliste (±15% max)
            noise_e = np.random.normal(0, hist_entrees_std * 0.12)
            noise_s = np.random.normal(0, hist_sorties_std * 0.12)
            pred_entree = max(0, pred_entree + noise_e)
            pred_sortie = max(0, pred_sortie + noise_s)

            # Dégradation de confiance avec le temps (incertitude croissante)
            # Les prédictions lointaines sont moins fiables
            incertitude = 1.0 + (i / n_months) * 0.15

            # Prédire stock avec le modèle
            X_st = np.array([[current_stock, pred_entree, pred_sortie,
                              mois_num, tendance]])
            pred_stock = float(model_stock.predict(X_st)[0])
            pred_stock = max(0, min(pred_stock, capacite_max))

            # Confiance décroissante pour cette prédiction (de 85% à 55%)
            confiance = max(55, round(85 - (i / n_months) * 30))

            predictions.append({
                'ds': future_date.strftime('%Y-%m-%d'),
                'date_label': f"{StockAnalyticsService.MOIS_LABELS[mois_num - 1]} {future_date.year}",
                'mois_num': mois_num,
                'year': future_date.year,
                'entrees': round(pred_entree, 1),
                'sorties': round(pred_sortie, 1),
                'stock': round(pred_stock, 1),
                'flux_net': round(pred_entree - pred_sortie, 1),
                'confiance': confiance,
                'saison': (
                    'Recolte' if mois_num in (2, 3, 4, 5) else
                    'Pluies' if mois_num in (6, 7, 8, 9) else
                    'Seche'
                ),
            })

            current_stock = pred_stock

        return predictions

    @staticmethod
    def _compute_risk_analysis(predictions, seuil_min, seuil_alerte, seuil_optimal):
        """Calcule l'analyse de risque pour chaque prédiction."""
        for p in predictions:
            stock = p['stock']
            if stock <= seuil_min:
                p['risque'] = 'CRITIQUE'
                p['risque_score'] = 100
            elif stock <= seuil_alerte:
                p['risque'] = 'ALERTE'
                p['risque_score'] = 70
            elif stock <= seuil_optimal:
                p['risque'] = 'VIGILANCE'
                p['risque_score'] = 40
            else:
                p['risque'] = 'OPTIMAL'
                p['risque_score'] = 10

        # Mois de rupture estimé
        rupture_mois = None
        for p in predictions:
            if p['stock'] <= seuil_min:
                rupture_mois = p['date_label']
                break

        # Tendance globale
        if len(predictions) >= 2:
            stocks = [p['stock'] for p in predictions]
            tendance_pct = ((stocks[-1] - stocks[0]) / max(stocks[0], 1)) * 100
        else:
            tendance_pct = 0

        return {
            'rupture_estimee': rupture_mois,
            'tendance_pct': round(tendance_pct, 1),
            'tendance_dir': 'hausse' if tendance_pct > 5 else (
                'baisse' if tendance_pct < -5 else 'stable'),
            'mois_critique_count': sum(
                1 for p in predictions if p['risque'] == 'CRITIQUE'),
            'mois_alerte_count': sum(
                1 for p in predictions if p['risque'] == 'ALERTE'),
            'mois_optimal_count': sum(
                1 for p in predictions if p['risque'] == 'OPTIMAL'),
            'stock_moyen_prevu': round(
                np.mean([p['stock'] for p in predictions]), 1),
            'stock_min_prevu': round(
                min(p['stock'] for p in predictions), 1),
            'stock_max_prevu': round(
                max(p['stock'] for p in predictions), 1),
        }

    @staticmethod
    def _compute_seasonality(df):
        """Analyse de saisonnalité mensuelle à partir de l'historique."""
        if len(df) < 6:
            return None

        seasonal = df.groupby('mois_num').agg(
            entrees_moy=('entrees', 'mean'),
            sorties_moy=('sorties', 'mean'),
            stock_moy=('stock', 'mean'),
        ).round(1)

        result = {}
        for mois_num in range(1, 13):
            label = StockAnalyticsService.MOIS_LABELS[mois_num - 1]
            if mois_num in seasonal.index:
                row = seasonal.loc[mois_num]
                result[label] = {
                    'entrees': float(row['entrees_moy']),
                    'sorties': float(row['sorties_moy']),
                    'stock': float(row['stock_moy']),
                }
            else:
                result[label] = {'entrees': 0, 'sorties': 0, 'stock': 0}

        return result

    @staticmethod
    def analyze_complete():
        """Pipeline complet : données réelles → LinearRegression + saisonnalité Togo → prévisions."""
        result = StockAnalyticsService.generate_stock_data()
        df = result[0]
        capacite_max = result[1]
        seuil_min = result[2]
        seuil_alerte = result[3]
        seuil_optimal = result[4]
        stock_actuel = result[5]

        if df is None or len(df) < 2:
            return {
                'current_stock': int(stock_actuel),
                'precision': 0,
                'fiabilite': 'Insuffisant',
                'capacite_max': int(capacite_max),
                'seuil_min': int(seuil_min),
                'seuil_alerte': int(seuil_alerte),
                'seuil_optimal': int(seuil_optimal),
                'no_data': True,
            }

        # ── Entraîner les 3 modèles ──
        model_e, model_s, model_st, metrics = StockAnalyticsService._train_models(df)

        if model_e is None:
            return {
                'current_stock': int(stock_actuel),
                'precision': 0,
                'fiabilite': 'Insuffisant',
                'capacite_max': int(capacite_max),
                'seuil_min': int(seuil_min),
                'seuil_alerte': int(seuil_alerte),
                'seuil_optimal': int(seuil_optimal),
                'no_data': True,
            }

        # ── Générer 36 mois de prédictions ──
        predictions = StockAnalyticsService._generate_predictions(
            df, model_e, model_s, model_st, n_months=36,
            capacite_max=capacite_max)

        # ── Analyse de risque ──
        risk_analysis = StockAnalyticsService._compute_risk_analysis(
            predictions, seuil_min, seuil_alerte, seuil_optimal)

        # ── Saisonnalité ──
        seasonality = StockAnalyticsService._compute_seasonality(df)

        # ── Historique formaté ──
        historique = []
        for _, row in df.iterrows():
            historique.append({
                'ds': row['ds'].strftime('%Y-%m-%d'),
                'date_label': f"{StockAnalyticsService.MOIS_LABELS[row['ds'].month - 1]} {row['ds'].year}",
                'entrees': round(float(row['entrees']), 1),
                'sorties': round(float(row['sorties']), 1),
                'stock': round(float(row['stock']), 1),
            })

        # ── Prévisions regroupées par année ──
        forecast_years = sorted(set(p['year'] for p in predictions))

        year_forecasts = []
        for year in forecast_years:
            year_data = [p for p in predictions if p['year'] == year]
            year_forecasts.append({
                'year': year,
                'data': year_data,
                'stock_moyen': round(np.mean([p['stock'] for p in year_data]), 1),
                'entrees_total': round(sum(p['entrees'] for p in year_data), 1),
                'sorties_total': round(sum(p['sorties'] for p in year_data), 1),
            })

        # ── Plage de dates ──
        first_year = df['ds'].min().year
        last_data_year = df['ds'].max().year
        last_forecast_year = predictions[-1]['year'] if predictions else last_data_year
        date_range_str = f"{first_year}–{last_forecast_year}"

        # ── Recommandations adaptées au contexte togolais ──
        recommandations = []

        # Info fiabilité
        fiabilite = metrics.get('fiabilite', 'Faible')
        nb_pts = metrics.get('nb_points', 0)
        if nb_pts < 12:
            recommandations.append({
                'type': 'info',
                'icon': 'fas fa-info-circle',
                'text': f"Fiabilité {fiabilite} ({nb_pts} mois de données). "
                        f"Les prévisions seront plus précises avec au moins 12 mois d'historique.",
            })

        if risk_analysis['rupture_estimee']:
            recommandations.append({
                'type': 'danger',
                'icon': 'fas fa-exclamation-circle',
                'text': f"Risque de rupture de stock estimé en {risk_analysis['rupture_estimee']}. "
                        f"Prévoir un réapprovisionnement auprès des producteurs avant cette date.",
            })

        if risk_analysis['tendance_dir'] == 'baisse':
            recommandations.append({
                'type': 'warning',
                'icon': 'fas fa-arrow-trend-down',
                'text': f"Tendance à la baisse ({risk_analysis['tendance_pct']}%). "
                        f"Envisager de renforcer les achats pendant la campagne cajou (Fév-Mai).",
            })

        if risk_analysis['mois_alerte_count'] > 3:
            recommandations.append({
                'type': 'warning',
                'icon': 'fas fa-bell',
                'text': f"{risk_analysis['mois_alerte_count']} mois en zone d'alerte prévus. "
                        f"Augmenter les stocks pendant la période de récolte (Mars-Avril).",
            })

        # Conseil saisonnier selon le mois actuel
        from django.utils import timezone
        mois_actuel = timezone.now().month
        if mois_actuel in (11, 12, 1):
            recommandations.append({
                'type': 'info',
                'icon': 'fas fa-seedling',
                'text': "Préparer la campagne cajou : la récolte débute en février. "
                        "Anticiper les achats et préparer l'espace d'entreposage.",
            })
        elif mois_actuel in (2, 3, 4, 5):
            recommandations.append({
                'type': 'success',
                'icon': 'fas fa-leaf',
                'text': "Période de récolte cajou en cours. "
                        "Moment favorable pour constituer les stocks annuels.",
            })
        elif mois_actuel in (6, 7, 8, 9):
            recommandations.append({
                'type': 'warning',
                'icon': 'fas fa-cloud-rain',
                'text': "Saison des pluies : les approvisionnements sont réduits. "
                        "Gérer les stocks avec prudence jusqu'à la prochaine récolte.",
            })

        if risk_analysis['tendance_dir'] == 'hausse':
            recommandations.append({
                'type': 'success',
                'icon': 'fas fa-arrow-trend-up',
                'text': f"Tendance positive ({risk_analysis['tendance_pct']}%). "
                        f"Le stock évolue favorablement.",
            })

        if stock_actuel > seuil_optimal:
            recommandations.append({
                'type': 'success',
                'icon': 'fas fa-check-circle',
                'text': f"Stock actuel ({int(stock_actuel)} kg) au-dessus du seuil optimal "
                        f"({int(seuil_optimal)} kg).",
            })

        return {
            'current_stock': int(stock_actuel),
            'precision': metrics.get('precision_globale', 0),
            'fiabilite': fiabilite,
            'capacite_max': int(capacite_max),
            'seuil_min': int(seuil_min),
            'seuil_alerte': int(seuil_alerte),
            'seuil_optimal': int(seuil_optimal),
            'date_range': date_range_str,
            'nb_mois_historique': len(df),
            'metrics': metrics,
            'risk_analysis': risk_analysis,
            'recommandations': recommandations,
            'seasonality': seasonality,

            # ── Données JSON pour Chart.js ──
            'historique_json': json.dumps(historique),
            'predictions_json': json.dumps(predictions),
            'year_forecasts_json': json.dumps(year_forecasts),
            'seasonality_json': json.dumps(seasonality) if seasonality else '{}',

            # ── Données tableau ──
            'historique_stock': historique[-12:],
            'predictions_table': predictions[:12],
            'year_forecasts': year_forecasts,
        }
