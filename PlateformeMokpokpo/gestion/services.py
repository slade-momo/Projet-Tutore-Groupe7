import re
import pandas as pd
import numpy as np
from prophet import Prophet
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import base64
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
    """Service de prévision IA basé sur les données réelles en base."""

    @staticmethod
    def generate_stock_data():
        """Construit la série temporelle mensuelle à partir des données réelles."""
        from .models import (
            MouvementStock, Produit, Entrepot, Lot, Vente, VenteImmediate,
        )
        from django.db.models import Sum, Q
        from django.db.models.functions import TruncMonth

        # ── Paramètres réels depuis la BD ──
        agg = Entrepot.objects.aggregate(
            cap=Sum('capacite_max'), seuil=Sum('seuil_critique'))
        capacite_max = float(agg['cap'] or 50000)
        seuil_critique = float(agg['seuil'] or 10000)
        stock_actuel = float(
            Produit.objects.aggregate(t=Sum('stock_physique'))['t'] or 0)

        def _to_key(dt):
            """Convertit un date/datetime en clé 'YYYY-MM'."""
            return f"{dt.year:04d}-{dt.month:02d}" if dt else None

        entrees = {}
        sorties = {}

        # ── Source 1 : MouvementStock (source principale) ──
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

        # ── Source 2 : Lots reçus (complément entrées) ──
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

        # ── Source 3 : Ventes + Ventes Immédiates (complément sorties) ──
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

        # ── Fusionner en série temporelle continue ──
        all_keys = sorted(set(entrees.keys()) | set(sorties.keys()))
        if not all_keys:
            return None, None, capacite_max, seuil_critique, stock_actuel

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

        df_stock = pd.DataFrame(rows)

        # ── Stock glissant recalé sur le stock physique actuel ──
        flux_cumule = (df_stock['entrees'] - df_stock['sorties']).cumsum()
        stock_initial = stock_actuel - float(flux_cumule.iloc[-1])
        df_stock['stock'] = stock_initial + flux_cumule
        df_stock['stock'] = df_stock['stock'].clip(lower=0, upper=capacite_max)

        df_stock['alerte'] = df_stock['stock'].apply(
            lambda x: 'CRITIQUE' if x < seuil_critique else 'OK')
        df_stock['remplissage'] = (df_stock['stock'] / capacite_max) * 100

        df_prophet = df_stock[['ds', 'stock']].rename(columns={'stock': 'y'})
        return df_stock, df_prophet, capacite_max, seuil_critique, stock_actuel

    @staticmethod
    def analyze_complete():
        """Pipeline complet : données réelles → Prophet → prévisions."""
        result = StockAnalyticsService.generate_stock_data()
        df_stock, df_prophet, capacite_max, seuil_critique, stock_actuel = result

        if df_prophet is None or len(df_prophet) < 2:
            return {
                'current_stock': int(stock_actuel),
                'precision': 0,
                'capacite_max': int(capacite_max),
                'seuil_critique': int(seuil_critique),
                'historique_stock': [],
                'historique_prophet': [],
                'year_forecasts': [],
                'no_data': True,
            }

        # ── Entraîner Prophet ──
        has_yearly = len(df_prophet) >= 24
        model = Prophet(
            yearly_seasonality=has_yearly,
            weekly_seasonality=False,
            daily_seasonality=False,
        )
        model.fit(df_prophet)

        future = model.make_future_dataframe(periods=36, freq='MS')
        forecast = model.predict(future)

        forecast['alerte'] = forecast['yhat'].apply(
            lambda x: 'CRITIQUE' if x < seuil_critique else 'OK')
        forecast['remplissage'] = (forecast['yhat'] / capacite_max) * 100

        # ── Années de prévision dynamiques ──
        last_data_year = df_prophet['ds'].max().year
        forecast_years = [last_data_year + 1, last_data_year + 2, last_data_year + 3]
        colors = ['var(--clr-danger)', 'var(--clr-warning)', 'var(--clr-info)']
        icons = ['fas fa-calendar-alt', 'fas fa-calendar-alt', 'fas fa-calendar-alt']

        year_forecasts = []
        for i, year in enumerate(forecast_years):
            year_df = forecast[forecast['ds'].dt.year == year][
                ['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'alerte', 'remplissage']]
            year_data = year_df.round(0).to_dict('records')
            year_forecasts.append({
                'year': year,
                'data': year_data,
                'img': StockAnalyticsService.plot_year_bar(year_data, str(year)),
                'color': colors[i],
            })

        # ── Précision MAPE ──
        y_true = df_prophet['y'].values
        y_pred = forecast.head(len(df_prophet))['yhat'].values
        mask = y_true != 0
        if mask.sum() > 0:
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
            precision = round(max(0, 100 - mape), 2)
        else:
            precision = 0

        # ── Plage de dates pour le sous-titre ──
        first_year = df_prophet['ds'].min().year
        last_forecast_year = forecast['ds'].max().year
        date_range_str = f"{first_year}–{last_forecast_year}"

        return {
            'current_stock': int(stock_actuel),
            'precision': precision,
            'capacite_max': int(capacite_max),
            'seuil_critique': int(seuil_critique),
            'date_range': date_range_str,
            'nb_mois_historique': len(df_prophet),
            'historique_stock': df_stock.tail(12).round(0).to_dict('records'),
            'historique_prophet': df_prophet.tail(12).round(0).to_dict('records'),
            'year_forecasts': year_forecasts,
            'img_forecast': StockAnalyticsService.plot_forecast(model, forecast),
            'img_components': StockAnalyticsService.plot_components(model, forecast),
        }

    @staticmethod
    def plot_forecast(model, forecast):
        """Graphique principal de prévision Prophet."""
        fig, ax = plt.subplots(figsize=(14, 8))
        model.plot(forecast, ax=ax)
        ax.set_title('Prévision Stock — Ferme Mokpokpo (données réelles)',
                      fontsize=16, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Stock (kg)')
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def plot_components(model, forecast):
        """Composantes saisonnières Prophet."""
        fig = model.plot_components(forecast, figsize=(14, 10))
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def plot_year_bar(year_data, year):
        """Graphique barres mensuelles pour une année de prévision."""
        if not year_data:
            return ""

        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 6))

        months_present = [pd.to_datetime(d['ds']).month for d in year_data]
        yhat = [float(d['yhat']) for d in year_data]

        if not yhat:
            plt.close()
            return ""

        norm = plt.Normalize(min(yhat), max(yhat))
        colors = plt.cm.RdYlGn(norm(yhat))

        ax.bar(months_present, yhat, color=colors, alpha=0.8,
               edgecolor='black', linewidth=0.5)
        ax.set_title(f'Prévision Stock (kg) par Mois — {year}',
                      fontsize=14, fontweight='bold')
        ax.set_xlabel('Mois')
        ax.set_ylabel('Stock Prévu (kg)')
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                            'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'])
        ax.grid(True, linestyle='--', alpha=0.3)

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        return base64.b64encode(buffer.getvalue()).decode()
