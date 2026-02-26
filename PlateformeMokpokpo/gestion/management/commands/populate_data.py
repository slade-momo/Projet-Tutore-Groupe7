"""
Commande de gestion pour peupler la base de données avec des données
réalistes du secteur cajou au Togo, en passant par les formulaires/vues
pour valider toutes les opérations CRUD.
"""
import os
import time
import django
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
from datetime import date, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Peuple la BD avec des données cajou réalistes du Togo via les formulaires'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Supprimer les données existantes avant insertion',
        )

    def handle(self, *args, **options):
        from decimal import Decimal
        from django.test import Client as TestClient
        from gestion.models import (
            Client, Produit, Producteur, Entrepot, ZoneEntrepot,
            Lot, Vente, MouvementStock, Commande, VenteImmediate,
            DemandeAchat, AlerteStock, HistoriqueTracabilite,
        )

        if options['clear']:
            self.stdout.write('Suppression des données existantes...')
            from django.db import connection
            with connection.cursor() as cursor:
                # Désactiver les triggers pour pouvoir supprimer
                cursor.execute("SET session_replication_role = 'replica'")
                tables = [
                    'demande_achat', 'alerte_stock', 'vente_immediate',
                    'mouvement_stock', 'historique_tracabilite',
                    'vente', 'affectation_lot', 'ligne_commande',
                    'preparation_commande', 'commande',
                    'lot', 'zone_entrepot', 'entrepot',
                    'producteur', 'produit', 'client',
                ]
                for t in tables:
                    cursor.execute(f'DELETE FROM stock_cajou.{t}')
                cursor.execute("SET session_replication_role = 'origin'")
            self.stdout.write(self.style.SUCCESS('  Données supprimées.'))

        # Récupérer ou créer le superuser
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.create_superuser('admin', 'admin@mokpokpo.tg', 'admin123')
            self.stdout.write(self.style.SUCCESS('Superuser admin créé'))

        # Préparer le client HTTP de test
        client = TestClient()
        client.force_login(admin)
        ok = 0
        fail = 0

        def post(url, data, label):
            nonlocal ok, fail
            try:
                resp = client.post(url, data)
            except Exception as exc:
                fail += 1
                self.stdout.write(self.style.ERROR(
                    f'  ✗ {label} → {exc.__class__.__name__}'))
                # Réinitialiser la connexion DB après erreur PostgreSQL
                from django.db import connection
                connection.close()
                return
            if resp.status_code in (301, 302):
                ok += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ {label}'))
            else:
                fail += 1
                # Afficher les erreurs du formulaire si disponibles
                if hasattr(resp, 'context') and resp.context and 'form' in resp.context:
                    errors = resp.context['form'].errors
                    self.stdout.write(self.style.ERROR(f'  ✗ {label} → {errors}'))
                else:
                    self.stdout.write(self.style.ERROR(
                        f'  ✗ {label} → HTTP {resp.status_code}'))

        # ==============================================================
        self.stdout.write('\n═══ 1. CLIENTS (acheteurs cajou au Togo) ═══')
        # ==============================================================
        clients_data = [
            {'nom': 'AGBODJAN', 'prenom': 'Kofi', 'entreprise': 'Cajou Export Togo SARL',
             'telephone': '+228 90 12 34 56', 'email': 'kagbodjan@cajouexport.tg',
             'adresse': 'Quartier Bè, Lomé', 'type_client': 'VIP'},
            {'nom': 'MENSAH', 'prenom': 'Ama', 'entreprise': 'Ets Mensah & Fils',
             'telephone': '+228 91 23 45 67', 'email': 'ama.mensah@etsmensah.tg',
             'adresse': 'Tokoin Gbadago, Lomé', 'type_client': 'REGULIER'},
            {'nom': 'KOUDJO', 'prenom': 'Yao', 'entreprise': 'Noix du Plateau',
             'telephone': '+228 92 34 56 78', 'email': 'ykoudjo@noixplateau.tg',
             'adresse': 'Quartier Administratif, Atakpamé', 'type_client': 'REGULIER'},
            {'nom': 'AMEGEE', 'prenom': 'Akua', 'entreprise': '',
             'telephone': '+228 93 45 67 89', 'email': '',
             'adresse': 'Marché Central, Kpalimé', 'type_client': 'OCCASIONNEL'},
            {'nom': 'LAWSON', 'prenom': 'Edem', 'entreprise': 'TG Cashew International',
             'telephone': '+228 70 56 78 90', 'email': 'elawson@tgcashew.com',
             'adresse': 'Zone Portuaire, Lomé', 'type_client': 'VIP'},
            {'nom': 'DZIDULA', 'prenom': 'Kafui', 'entreprise': 'Coopérative Cajou Centre',
             'telephone': '+228 96 67 89 01', 'email': 'kdzidula@coopcajou.tg',
             'adresse': 'Sokodé Centre', 'type_client': 'REGULIER'},
            {'nom': 'AKAKPO', 'prenom': 'Komlan', 'entreprise': '',
             'telephone': '+228 97 78 90 12', 'email': '',
             'adresse': 'Quartier Zongo, Bassar', 'type_client': 'OCCASIONNEL'},
            {'nom': 'ATCHOU', 'prenom': 'Essi', 'entreprise': 'Afrique Cajou Trading',
             'telephone': '+228 98 89 01 23', 'email': 'eatchou@africacajou.com',
             'adresse': 'Hédzranawoé, Lomé', 'type_client': 'VIP'},
        ]
        for d in clients_data:
            post('/gestion/clients/create/', d, f'Client {d["nom"]} {d["prenom"]}')

        # ==============================================================
        self.stdout.write('\n═══ 2. PRODUITS (gamme cajou togolaise) ═══')
        # ==============================================================
        produits_data = [
            {'nom': 'Noix de cajou brutes', 'categorie': 'Brut',
             'unite': 'kg', 'prix_unitaire': '350.00',
             'seuil_alerte': '100.00', 'stock_tampon_comptoir': '25.00',
             'quantite_optimale_commande': '500.00',
             'description': 'Noix de cajou brutes non décortiquées, collectées auprès des producteurs togolais'},
            {'nom': 'Amandes de cajou W320', 'categorie': 'Transformé',
             'unite': 'kg', 'prix_unitaire': '3500.00',
             'seuil_alerte': '40.00', 'stock_tampon_comptoir': '10.00',
             'quantite_optimale_commande': '100.00',
             'description': 'Amandes entières blanches calibre W320, qualité export'},
            {'nom': 'Amandes de cajou W240', 'categorie': 'Transformé',
             'unite': 'kg', 'prix_unitaire': '4500.00',
             'seuil_alerte': '30.00', 'stock_tampon_comptoir': '8.00',
             'quantite_optimale_commande': '80.00',
             'description': 'Amandes entières blanches calibre W240, qualité premium'},
            {'nom': 'Brisures de cajou', 'categorie': 'Sous-produit',
             'unite': 'kg', 'prix_unitaire': '1500.00',
             'seuil_alerte': '25.00', 'stock_tampon_comptoir': '5.00',
             'quantite_optimale_commande': '80.00',
             'description': 'Brisures et morceaux de cajou, idéal pour pâtisserie et industrie'},
            {'nom': 'Huile de cajou (CNSL)', 'categorie': 'Sous-produit',
             'unite': 'litre', 'prix_unitaire': '750.00',
             'seuil_alerte': '15.00', 'stock_tampon_comptoir': '3.00',
             'quantite_optimale_commande': '50.00',
             'description': 'Baume de cajou (CNSL) extrait des coques, usage industriel'},
            {'nom': 'Pomme de cajou séchée', 'categorie': 'Transformé',
             'unite': 'kg', 'prix_unitaire': '1000.00',
             'seuil_alerte': '20.00', 'stock_tampon_comptoir': '5.00',
             'quantite_optimale_commande': '60.00',
             'description': 'Pomme de cajou déshydratée, snack et jus'},
        ]
        for d in produits_data:
            post('/gestion/produits/create/', d, f'Produit {d["nom"]}')

        # ==============================================================
        self.stdout.write('\n═══ 3. PRODUCTEURS (zones cajou du Togo) ═══')
        # ==============================================================
        producteurs_data = [
            {'nom': 'TCHALA', 'prenom': 'Kossi', 'type_producteur': 'INDIVIDUEL',
             'statut': 'ACTIF', 'numero_identification': 'PROD-TG-001',
             'telephone': '+228 90 11 22 33', 'localisation': 'Sotouboua, Région Centrale',
             'observations': 'Producteur depuis 15 ans, plantation de 8 hectares'},
            {'nom': 'Coopérative MIFA Cajou', 'prenom': '', 'type_producteur': 'COOPERATIVE',
             'statut': 'ACTIF', 'numero_identification': 'COOP-TG-001',
             'telephone': '+228 91 22 33 44', 'localisation': 'Tchamba, Région Centrale',
             'observations': '120 membres, certification biologique en cours'},
            {'nom': 'BABA', 'prenom': 'Abdoulaye', 'type_producteur': 'INDIVIDUEL',
             'statut': 'ACTIF', 'numero_identification': 'PROD-TG-002',
             'telephone': '+228 92 33 44 55', 'localisation': 'Bassar, Région de la Kara',
             'observations': 'Plantation de 12 hectares, bonne qualité constante'},
            {'nom': 'GIE Anacarde Plateaux', 'prenom': '', 'type_producteur': 'COOPERATIVE',
             'statut': 'ACTIF', 'numero_identification': 'COOP-TG-002',
             'telephone': '+228 93 44 55 66', 'localisation': 'Badou, Région des Plateaux',
             'observations': '85 producteurs regroupés, volumes importants en saison'},
            {'nom': 'KOMBATE', 'prenom': 'Piyabalo', 'type_producteur': 'INDIVIDUEL',
             'statut': 'ACTIF', 'numero_identification': 'PROD-TG-003',
             'telephone': '+228 94 55 66 77', 'localisation': 'Guérin-Kouka, Région de la Kara',
             'observations': 'Jeune producteur dynamique, 5 hectares en expansion'},
            {'nom': 'AGRO-CAJOU Togo', 'prenom': '', 'type_producteur': 'ENTREPRISE',
             'statut': 'ACTIF', 'numero_identification': 'ENT-TG-001',
             'telephone': '+228 22 25 67 89', 'localisation': 'Sokodé, Région Centrale',
             'observations': 'Entreprise de collecte et transformation, 30 tonnes/an'},
        ]
        for d in producteurs_data:
            post('/gestion/producteurs/create/', d, f'Producteur {d["nom"]}')

        # ==============================================================
        self.stdout.write('\n═══ 4. ENTREPOTS ═══')
        # ==============================================================
        entrepots_data = [
            {'nom': 'Entrepôt Central Lomé', 'localisation': 'Zone Portuaire, Lomé',
             'statut': 'EN_ALERTE', 'responsable': admin.pk,
             'capacite_max': '10000.00', 'seuil_critique': '1000.00',
             'quantite_disponible': '0.00'},
            {'nom': 'Entrepôt Sokodé', 'localisation': 'Zone Industrielle, Sokodé',
             'statut': 'EN_ALERTE', 'responsable': admin.pk,
             'capacite_max': '6000.00', 'seuil_critique': '800.00',
             'quantite_disponible': '0.00'},
            {'nom': 'Magasin Kara', 'localisation': 'Quartier Commercial, Kara',
             'statut': 'OPERATIONNEL', 'responsable': admin.pk,
             'capacite_max': '3000.00', 'seuil_critique': '400.00',
             'quantite_disponible': '0.00'},
        ]
        for d in entrepots_data:
            post('/gestion/entrepots/create/', d, f'Entrepôt {d["nom"]}')

        # ==============================================================
        self.stdout.write('\n═══ 5. ZONES D\'ENTREPOT ═══')
        # ==============================================================
        entrepots = list(Entrepot.objects.all().order_by('pk'))
        if len(entrepots) >= 3:
            e_lome, e_sokode, e_kara = entrepots[0], entrepots[1], entrepots[2]
        else:
            self.stdout.write(self.style.ERROR('  Pas assez d\'entrepôts créés!'))
            return

        zones_data = [
            {'nom': 'Zone Brut A', 'description': 'Stockage noix brutes - section A',
             'entrepot': e_lome.pk, 'capacite': '3000.00', 'quantite': '0.00',
             'statut': 'DISPONIBLE', 'responsable': admin.pk},
            {'nom': 'Zone Brut B', 'description': 'Stockage noix brutes - section B',
             'entrepot': e_lome.pk, 'capacite': '3000.00', 'quantite': '0.00',
             'statut': 'DISPONIBLE', 'responsable': admin.pk},
            {'nom': 'Zone Transformé', 'description': 'Amandes et produits transformés',
             'entrepot': e_lome.pk, 'capacite': '2000.00', 'quantite': '0.00',
             'statut': 'DISPONIBLE', 'responsable': admin.pk},
            {'nom': 'Zone Sous-produits', 'description': 'Brisures, huile CNSL, pomme séchée',
             'entrepot': e_lome.pk, 'capacite': '2000.00', 'quantite': '0.00',
             'statut': 'DISPONIBLE', 'responsable': admin.pk},
            {'nom': 'Zone Collecte', 'description': 'Réception et tri des noix brutes de la zone Centre',
             'entrepot': e_sokode.pk, 'capacite': '4000.00', 'quantite': '0.00',
             'statut': 'DISPONIBLE', 'responsable': admin.pk},
            {'nom': 'Zone Stockage', 'description': 'Stockage intermédiaire avant transfert à Lomé',
             'entrepot': e_sokode.pk, 'capacite': '2000.00', 'quantite': '0.00',
             'statut': 'DISPONIBLE', 'responsable': admin.pk},
            {'nom': 'Zone Nord', 'description': 'Collecte producteurs Kara et Savanes',
             'entrepot': e_kara.pk, 'capacite': '2000.00', 'quantite': '0.00',
             'statut': 'DISPONIBLE', 'responsable': admin.pk},
            {'nom': 'Zone Transit', 'description': 'Transit avant expédition vers Sokodé',
             'entrepot': e_kara.pk, 'capacite': '1000.00', 'quantite': '0.00',
             'statut': 'DISPONIBLE', 'responsable': admin.pk},
        ]
        for d in zones_data:
            post('/gestion/zones/create/', d, f'Zone {d["nom"]} ({Entrepot.objects.get(pk=d["entrepot"]).nom})')

        # ==============================================================
        self.stdout.write('\n═══ 6. LOTS (récolte 2025-2026) ═══')
        # ==============================================================
        produits = list(Produit.objects.all().order_by('pk'))
        producteurs = list(Producteur.objects.all().order_by('pk'))
        zones = list(ZoneEntrepot.objects.all().order_by('pk'))

        if not produits or not producteurs or not zones:
            self.stdout.write(self.style.ERROR('  Prérequis manquants pour les lots!'))
            return

        today = date.today()
        lots_data = [
            # Noix brutes - gros volumes
            {'produit': produits[0].pk, 'producteur': producteurs[0].pk,
             'zone': zones[0].pk, 'quantite_initiale': '800.00',
             'qualite': 'PREMIUM', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=30)).isoformat(),
             'date_expiration': (today + timedelta(days=335)).isoformat(),
             'observations': 'Récolte Sotouboua février 2026, KOR 48'},
            {'produit': produits[0].pk, 'producteur': producteurs[1].pk,
             'zone': zones[4].pk, 'quantite_initiale': '1500.00',
             'qualite': 'STANDARD', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=15)).isoformat(),
             'date_expiration': (today + timedelta(days=350)).isoformat(),
             'observations': 'Collecte Coopérative MIFA, campagne 2026'},
            {'produit': produits[0].pk, 'producteur': producteurs[2].pk,
             'zone': zones[6].pk, 'quantite_initiale': '600.00',
             'qualite': 'STANDARD', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=7)).isoformat(),
             'date_expiration': (today + timedelta(days=358)).isoformat(),
             'observations': 'Lot Bassar, bon rendement au décorticage'},
            # Amandes W320
            {'produit': produits[1].pk, 'producteur': producteurs[5].pk,
             'zone': zones[2].pk, 'quantite_initiale': '250.00',
             'qualite': 'PREMIUM', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=20)).isoformat(),
             'date_expiration': (today + timedelta(days=345)).isoformat(),
             'observations': 'Transformé par AGRO-CAJOU, calibre vérifié'},
            # Amandes W240
            {'produit': produits[2].pk, 'producteur': producteurs[5].pk,
             'zone': zones[2].pk, 'quantite_initiale': '120.00',
             'qualite': 'PREMIUM', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=20)).isoformat(),
             'date_expiration': (today + timedelta(days=345)).isoformat(),
             'observations': 'Lot W240 premium, prêt pour export'},
            # Brisures
            {'produit': produits[3].pk, 'producteur': producteurs[5].pk,
             'zone': zones[3].pk, 'quantite_initiale': '150.00',
             'qualite': 'ECONOMIQUE', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=18)).isoformat(),
             'date_expiration': (today + timedelta(days=180)).isoformat(),
             'observations': 'Brisures issues du décorticage W320/W240'},
            # Huile CNSL
            {'produit': produits[4].pk, 'producteur': producteurs[5].pk,
             'zone': zones[3].pk, 'quantite_initiale': '70.00',
             'qualite': 'STANDARD', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=25)).isoformat(),
             'date_expiration': (today + timedelta(days=540)).isoformat(),
             'observations': 'CNSL extraction à froid, qualité industrielle'},
            # Pomme séchée
            {'produit': produits[5].pk, 'producteur': producteurs[3].pk,
             'zone': zones[3].pk, 'quantite_initiale': '50.00',
             'qualite': 'STANDARD', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=10)).isoformat(),
             'date_expiration': (today + timedelta(days=120)).isoformat(),
             'observations': 'Séchage solaire traditionnel, Région des Plateaux'},
            # Lot partiellement sorti
            {'produit': produits[0].pk, 'producteur': producteurs[4].pk,
             'zone': zones[1].pk, 'quantite_initiale': '700.00',
             'qualite': 'STANDARD', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=45)).isoformat(),
             'date_expiration': (today + timedelta(days=320)).isoformat(),
             'observations': 'Lot Guérin-Kouka, début de campagne 2025-2026'},
            # Lot ancien proche expiration
            {'produit': produits[1].pk, 'producteur': producteurs[1].pk,
             'zone': zones[2].pk, 'quantite_initiale': '80.00',
             'qualite': 'ECONOMIQUE', 'etat': 'EN_STOCK',
             'date_reception': (today - timedelta(days=300)).isoformat(),
             'date_expiration': (today + timedelta(days=25)).isoformat(),
             'observations': 'Lot ancien, à écouler rapidement'},
        ]
        for i, d in enumerate(lots_data):
            prod_nom = Produit.objects.get(pk=d['produit']).nom[:20]
            post('/gestion/lots/create/', d, f'Lot #{i+1} ({prod_nom})')

        # ==============================================================
        self.stdout.write('\n═══ 7. COMMANDES ═══')
        # ==============================================================
        clients_db = list(Client.objects.all().order_by('pk'))
        if len(clients_db) < 6:
            self.stdout.write(self.style.ERROR('  Pas assez de clients!'))
            return

        commandes_data = [
            {'client': clients_db[0].pk, 'produit': produits[0].pk,
             'quantite_demandee': '350.00',
             'date_livraison_souhaitee': (today + timedelta(days=14)).isoformat(),
             'priorite': 'URGENTE',
             'observations': 'Export vers Ghana, conteneur prévu semaine prochaine'},
            {'client': clients_db[4].pk, 'produit': produits[1].pk,
             'quantite_demandee': '800.00',
             'date_livraison_souhaitee': (today + timedelta(days=30)).isoformat(),
             'priorite': 'NORMALE',
             'observations': 'Commande export W320 pour marché européen'},
            {'client': clients_db[1].pk, 'produit': produits[1].pk,
             'quantite_demandee': '80.00',
             'date_livraison_souhaitee': (today + timedelta(days=7)).isoformat(),
             'priorite': 'URGENTE',
             'observations': 'Réapprovisionnement boutique Tokoin'},
            {'client': clients_db[5].pk, 'produit': produits[0].pk,
             'quantite_demandee': '250.00',
             'date_livraison_souhaitee': (today + timedelta(days=21)).isoformat(),
             'priorite': 'NORMALE',
             'observations': 'Distribution coopérative membres Sokodé'},
            {'client': clients_db[7].pk, 'produit': produits[2].pk,
             'quantite_demandee': '500.00',
             'date_livraison_souhaitee': (today + timedelta(days=45)).isoformat(),
             'priorite': 'NORMALE',
             'observations': 'Contrat annuel Afrique Cajou Trading, livraison mars'},
        ]
        for d in commandes_data:
            cl = Client.objects.get(pk=d['client'])
            post('/gestion/commandes/create/', d, f'Commande {cl.nom} ({d["quantite_demandee"]} kg)')
            time.sleep(1.1)  # Éviter collision timestamp trigger generer_da_auto

        # ==============================================================
        self.stdout.write('\n═══ 8. VENTES ═══')
        # ==============================================================
        lots_db = list(Lot.objects.all().order_by('pk'))
        if len(lots_db) < 8:
            self.stdout.write(self.style.ERROR('  Pas assez de lots!'))
            return

        ventes_data = [
            {'client': clients_db[0].pk, 'lot': lots_db[0].pk,
             'quantite_vendue': '150.00', 'prix_unitaire': '380.00',
             'mode_paiement': 'VIREMENT', 'type_vente': 'SUR_COMMANDE',
             'observations': 'Vente noix brutes à Cajou Export, prix négocié'},
            {'client': clients_db[4].pk, 'lot': lots_db[3].pk,
             'quantite_vendue': '80.00', 'prix_unitaire': '3500.00',
             'mode_paiement': 'VIREMENT', 'type_vente': 'SUR_COMMANDE',
             'observations': 'W320 pour TG Cashew International, export'},
            {'client': clients_db[1].pk, 'lot': lots_db[3].pk,
             'quantite_vendue': '25.00', 'prix_unitaire': '3800.00',
             'mode_paiement': 'MOBILE_MONEY', 'type_vente': 'IMMEDIATE',
             'observations': 'Vente comptoir Ets Mensah'},
            {'client': clients_db[3].pk, 'lot': lots_db[5].pk,
             'quantite_vendue': '10.00', 'prix_unitaire': '1500.00',
             'mode_paiement': 'ESPECES', 'type_vente': 'IMMEDIATE',
             'observations': 'Brisures pour pâtisserie locale Kpalimé'},
            {'client': clients_db[2].pk, 'lot': lots_db[7].pk,
             'quantite_vendue': '8.00', 'prix_unitaire': '1000.00',
             'mode_paiement': 'MOBILE_MONEY', 'type_vente': 'IMMEDIATE',
             'observations': 'Pomme séchée pour jus, client Atakpamé'},
            {'client': clients_db[7].pk, 'lot': lots_db[4].pk,
             'quantite_vendue': '40.00', 'prix_unitaire': '4800.00',
             'mode_paiement': 'VIREMENT', 'type_vente': 'SUR_COMMANDE',
             'observations': 'W240 premium, Afrique Cajou Trading'},
        ]
        for d in ventes_data:
            cl = Client.objects.get(pk=d['client'])
            post('/gestion/ventes/create/', d,
                 f'Vente à {cl.nom} ({d["quantite_vendue"]} kg × {d["prix_unitaire"]} XOF)')

        # ==============================================================
        self.stdout.write('\n═══ 9. MOUVEMENTS DE STOCK ═══')
        # ==============================================================
        mouvements_data = [
            {'type_mouvement': 'ENTREE', 'lot': lots_db[0].pk,
             'quantite': '800.00', 'zone_destination': zones[0].pk,
             'zone_origine': '', 'valide': 'on',
             'motif': 'Réception lot Sotouboua, campagne février 2026'},
            {'type_mouvement': 'ENTREE', 'lot': lots_db[1].pk,
             'quantite': '1500.00', 'zone_destination': zones[4].pk,
             'zone_origine': '', 'valide': 'on',
             'motif': 'Collecte MIFA Tchamba'},
            {'type_mouvement': 'TRANSFERT', 'lot': lots_db[1].pk,
             'quantite': '500.00', 'zone_origine': zones[4].pk,
             'zone_destination': zones[0].pk, 'valide': 'on',
             'motif': 'Transfert Sokodé → Lomé pour transformation'},
            {'type_mouvement': 'SORTIE', 'lot': lots_db[0].pk,
             'quantite': '150.00', 'zone_origine': zones[0].pk,
             'zone_destination': '', 'valide': 'on',
             'motif': 'Sortie vente Cajou Export Togo'},
            {'type_mouvement': 'SORTIE', 'lot': lots_db[3].pk,
             'quantite': '105.00', 'zone_origine': zones[2].pk,
             'zone_destination': '', 'valide': 'on',
             'motif': 'Sorties ventes W320 (TG Cashew + Mensah)'},
            {'type_mouvement': 'ENTREE', 'lot': lots_db[2].pk,
             'quantite': '600.00', 'zone_destination': zones[6].pk,
             'zone_origine': '', 'valide': 'on',
             'motif': 'Réception lot Bassar, zone Nord'},
        ]
        for d in mouvements_data:
            post('/gestion/mouvements/create/', d,
                 f'Mouvement {d["type_mouvement"]} ({d["quantite"]} kg)')

        # ==============================================================
        self.stdout.write('\n═══ 10. VENTES IMMÉDIATES ═══')
        # ==============================================================
        # Mettre à jour stock_physique des produits (le trigger VI vérifie ça)
        from django.db import connection
        from django.db.models import Sum
        for p in produits:
            total = Lot.objects.filter(produit=p).aggregate(
                t=Sum('quantite_restante'))['t'] or 0
            with connection.cursor() as cur:
                cur.execute(
                    'UPDATE stock_cajou.produit SET stock_physique=%s, stock_reserve=0 WHERE id=%s',
                    [total, p.pk],
                )
        self.stdout.write('  (stock_physique produits mis à jour)')

        vi_data = [
            {'produit': produits[0].pk, 'client': clients_db[6].pk,
             'quantite_demandee': '40.00', 'quantite_servie_maintenant': '40.00',
             'type_vente': 'TOTALE', 'prix_unitaire': '380.00'},
            {'produit': produits[3].pk, 'client': clients_db[3].pk,
             'quantite_demandee': '20.00', 'quantite_servie_maintenant': '20.00',
             'type_vente': 'TOTALE', 'prix_unitaire': '1600.00'},
            {'produit': produits[1].pk, 'client': clients_db[1].pk,
             'quantite_demandee': '12.00', 'quantite_servie_maintenant': '12.00',
             'type_vente': 'TOTALE', 'prix_unitaire': '3700.00'},
            {'produit': produits[5].pk, 'client': clients_db[2].pk,
             'quantite_demandee': '10.00', 'quantite_servie_maintenant': '10.00',
             'type_vente': 'TOTALE', 'prix_unitaire': '1100.00'},
        ]
        for d in vi_data:
            prod = Produit.objects.get(pk=d['produit'])
            post('/gestion/ventes-immediates/create/', d,
                 f'VI {prod.nom[:20]} ({d["quantite_servie_maintenant"]} kg)')

        # ==============================================================
        self.stdout.write('\n═══ 11. DEMANDES D\'ACHAT ═══')
        # ==============================================================
        da_data = [
            {'produit': produits[1].pk, 'quantite_a_commander': '200.00',
             'priorite': 'URGENT',
             'observations': 'Stock W320 bas, forte demande export prévue en mars'},
            {'produit': produits[4].pk, 'quantite_a_commander': '100.00',
             'priorite': 'NORMAL',
             'observations': 'Réappro huile CNSL, contrat industriel à honorer'},
            {'produit': produits[0].pk, 'quantite_a_commander': '800.00',
             'priorite': 'URGENT',
             'observations': 'Noix brutes pour campagne de transformation avril 2026'},
        ]
        for d in da_data:
            prod = Produit.objects.get(pk=d['produit'])
            post('/gestion/demandes/create/', d,
                 f'DA {prod.nom[:25]} ({d["quantite_a_commander"]} kg)')

        # ==============================================================
        self.stdout.write('\n═══ 12. ALERTES DE STOCK & DONNÉES LOGISTIQUES ═══')
        # ==============================================================
        from django.db import connection
        from django.db.models import Sum
        from datetime import datetime
        from decimal import Decimal

        now = timezone.now()
        produits = list(Produit.objects.all().order_by('pk'))
        lots_db = list(Lot.objects.all().order_by('pk'))
        zones = list(ZoneEntrepot.objects.all().order_by('pk'))
        entrepots = list(Entrepot.objects.all().order_by('pk'))

        # ─── 12a. Ajuster les niveaux de stock pour créer des situations d'alerte ───
        # Réduire drastiquement le stock de certains produits pour déclencher des alertes
        stock_adjustments = {
            # produits[1] = Amandes W320 : seuil=40, on met stock dispo à ~15 (CRITIQUE)
            1: {'stock_physique': '25.00', 'stock_reserve': '5.00'},
            # produits[2] = Amandes W240 : seuil=30, on met stock dispo à ~12 (CRITIQUE)
            2: {'stock_physique': '22.00', 'stock_reserve': '5.00'},
            # produits[4] = Huile CNSL : seuil=15, on met stock dispo à ~5 (CRITIQUE)
            4: {'stock_physique': '8.00', 'stock_reserve': '2.00'},
            # produits[5] = Pomme séchée : seuil=20, on met stock dispo à ~10 (URGENT)
            5: {'stock_physique': '15.00', 'stock_reserve': '3.00'},
            # produits[3] = Brisures : seuil=25, on met stock dispo à ~15 (ATTENTION)
            3: {'stock_physique': '22.00', 'stock_reserve': '4.00'},
        }

        # Désactiver les triggers sur produit pour éviter les conflits de numero_da
        with connection.cursor() as cur:
            cur.execute('ALTER TABLE stock_cajou.produit DISABLE TRIGGER ALL')

        for idx, adj in stock_adjustments.items():
            if idx < len(produits):
                p = produits[idx]
                with connection.cursor() as cur:
                    cur.execute(
                        'UPDATE stock_cajou.produit SET stock_physique=%s, stock_reserve=%s WHERE id=%s',
                        [adj['stock_physique'], adj['stock_reserve'], p.pk],
                    )
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Stock ajusté: {p.nom} → physique={adj["stock_physique"]}, réservé={adj["stock_reserve"]}'))

        # Le produit 0 (Noix brutes) garde un bon stock pour contraste
        if produits:
            with connection.cursor() as cur:
                cur.execute(
                    'UPDATE stock_cajou.produit SET stock_physique=%s, stock_reserve=%s WHERE id=%s',
                    ['2500.00', '300.00', produits[0].pk],
                )
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Stock ajusté: {produits[0].nom} → physique=2500, réservé=300 (OK)'))

        # Réactiver les triggers
        with connection.cursor() as cur:
            cur.execute('ALTER TABLE stock_cajou.produit ENABLE TRIGGER ALL')

        # ─── 12b. Créer des AlerteStock variées ───
        self.stdout.write('\n  ── Création des alertes de stock ──')

        alertes_data = []

        # Alertes ACTIVES — produits critiques (pas encore traitées)
        if len(produits) > 4:
            alertes_data.extend([
                # Amandes W320 — CRITIQUE (stock 15/40 = 38%)
                {
                    'produit': produits[1],
                    'date_alerte': now - timedelta(hours=6),
                    'stock_actuel': Decimal('15.00'),
                    'seuil_alerte': Decimal('40.00'),
                    'statut': 'ACTIVE',
                    'demande_achat_generee': False,
                    'observations': 'CRITIQUE — Stock W320 à 38% du seuil. Forte demande export prévue en mars. Risque de rupture sous 5 jours.',
                },
                # Amandes W240 — CRITIQUE (stock 12/30 = 40%)
                {
                    'produit': produits[2],
                    'date_alerte': now - timedelta(hours=3),
                    'stock_actuel': Decimal('12.00'),
                    'seuil_alerte': Decimal('30.00'),
                    'statut': 'ACTIVE',
                    'demande_achat_generee': False,
                    'observations': 'CRITIQUE — Stock W240 premium dangereusement bas. Commande Afrique Cajou Trading en attente.',
                },
                # Huile CNSL — CRITIQUE (stock 5/15 = 33%)
                {
                    'produit': produits[4],
                    'date_alerte': now - timedelta(hours=12),
                    'stock_actuel': Decimal('5.00'),
                    'seuil_alerte': Decimal('15.00'),
                    'statut': 'ACTIVE',
                    'demande_achat_generee': True,  # DA déjà générée
                    'observations': 'URGENT — Stock CNSL bas. DA-2026-004 générée automatiquement. En attente de réception fournisseur.',
                },
                # Pomme séchée — URGENT (stock 10/20 = 50%)
                {
                    'produit': produits[5],
                    'date_alerte': now - timedelta(days=1),
                    'stock_actuel': Decimal('10.00'),
                    'seuil_alerte': Decimal('20.00'),
                    'statut': 'ACTIVE',
                    'demande_achat_generee': False,
                    'observations': 'ATTENTION — Stock pomme séchée en diminution. Saison de collecte terminée, réappro limité.',
                },
                # Brisures — ATTENTION (stock 15/25 = 60%)
                {
                    'produit': produits[3],
                    'date_alerte': now - timedelta(days=2),
                    'stock_actuel': Decimal('15.00'),
                    'seuil_alerte': Decimal('25.00'),
                    'statut': 'ACTIVE',
                    'demande_achat_generee': False,
                    'observations': 'SURVEILLANCE — Brisures de cajou sous le seuil. Production dépendante du décorticage en cours.',
                },
            ])

        # Alertes TRAITÉES — historique de gestion réussie
        if len(produits) > 5:
            alertes_data.extend([
                {
                    'produit': produits[0],
                    'date_alerte': now - timedelta(days=15),
                    'stock_actuel': Decimal('70.00'),
                    'seuil_alerte': Decimal('100.00'),
                    'statut': 'TRAITEE',
                    'demande_achat_generee': True,
                    'date_traitement': now - timedelta(days=14),
                    'user_traitement': admin,
                    'observations': 'Résolu — Réception lot Sotouboua 800 kg. Stock brut rétabli à niveau optimal.',
                },
                {
                    'produit': produits[1],
                    'date_alerte': now - timedelta(days=30),
                    'stock_actuel': Decimal('25.00'),
                    'seuil_alerte': Decimal('40.00'),
                    'statut': 'TRAITEE',
                    'demande_achat_generee': True,
                    'date_traitement': now - timedelta(days=25),
                    'user_traitement': admin,
                    'observations': 'Résolu — Livraison AGRO-CAJOU de 250 kg W320. Stock reconstitué.',
                },
                {
                    'produit': produits[3],
                    'date_alerte': now - timedelta(days=45),
                    'stock_actuel': Decimal('8.00'),
                    'seuil_alerte': Decimal('25.00'),
                    'statut': 'TRAITEE',
                    'demande_achat_generee': True,
                    'date_traitement': now - timedelta(days=40),
                    'user_traitement': admin,
                    'observations': 'Résolu — Brisures récupérées du lot de décorticage de février.',
                },
                {
                    'produit': produits[5],
                    'date_alerte': now - timedelta(days=60),
                    'stock_actuel': Decimal('4.00'),
                    'seuil_alerte': Decimal('20.00'),
                    'statut': 'TRAITEE',
                    'demande_achat_generee': True,
                    'date_traitement': now - timedelta(days=55),
                    'user_traitement': admin,
                    'observations': 'Résolu — Réception séchage Plateaux 50 kg pomme séchée.',
                },
                {
                    'produit': produits[4],
                    'date_alerte': now - timedelta(days=20),
                    'stock_actuel': Decimal('2.00'),
                    'seuil_alerte': Decimal('15.00'),
                    'statut': 'TRAITEE',
                    'demande_achat_generee': True,
                    'date_traitement': now - timedelta(days=16),
                    'user_traitement': admin,
                    'observations': 'Résolu — Livraison extraction CNSL 70 litres. Circuit industriel sécurisé.',
                },
                {
                    'produit': produits[2],
                    'date_alerte': now - timedelta(days=50),
                    'stock_actuel': Decimal('18.00'),
                    'seuil_alerte': Decimal('30.00'),
                    'statut': 'TRAITEE',
                    'demande_achat_generee': True,
                    'date_traitement': now - timedelta(days=46),
                    'user_traitement': admin,
                    'observations': 'Résolu — Lot W240 premium réceptionné depuis AGRO-CAJOU.',
                },
            ])

        # Alertes IGNORÉES — pas de danger immédiat
        if len(produits) > 3:
            alertes_data.extend([
                {
                    'produit': produits[0],
                    'date_alerte': now - timedelta(days=90),
                    'stock_actuel': Decimal('95.00'),
                    'seuil_alerte': Decimal('100.00'),
                    'statut': 'IGNOREE',
                    'demande_achat_generee': False,
                    'observations': 'Ignorée — Pic saisonnier, collecte imminente. Stock sera naturellement reconstitué.',
                },
                {
                    'produit': produits[3],
                    'date_alerte': now - timedelta(days=75),
                    'stock_actuel': Decimal('22.00'),
                    'seuil_alerte': Decimal('25.00'),
                    'statut': 'IGNOREE',
                    'demande_achat_generee': False,
                    'observations': 'Ignorée — Brisures sous le seuil mais décorticage en cours, production attendue cette semaine.',
                },
            ])

        # Désactiver triggers sur alerte_stock pour éviter collisions DA auto-générées
        with connection.cursor() as cur:
            cur.execute('ALTER TABLE stock_cajou.alerte_stock DISABLE TRIGGER ALL')

        for a_data in alertes_data:
            try:
                AlerteStock.objects.create(**a_data)
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Alerte {a_data["statut"]} — {a_data["produit"].nom} (stock: {a_data["stock_actuel"]}/{a_data["seuil_alerte"]})'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Alerte {a_data["produit"].nom} → {e}'))

        # Réactiver triggers
        with connection.cursor() as cur:
            cur.execute('ALTER TABLE stock_cajou.alerte_stock ENABLE TRIGGER ALL')

        # ─── 12c. Lots supplémentaires pour logistique et prévision ───
        self.stdout.write('\n  ── Lots logistiques (expirations proches & volumes) ──')

        lots_logistiques = []
        if len(produits) >= 6 and len(producteurs) >= 5 and len(zones) >= 6:
            lots_logistiques = [
                # Lot W320 expiration dans 3 jours — TRÈS URGENT
                {
                    'produit': produits[1], 'producteur': producteurs[5],
                    'zone': zones[2], 'quantite_initiale': Decimal('30.00'),
                    'quantite_restante': Decimal('24.00'),
                    'quantite_reservee': Decimal('0.00'),
                    'qualite': 'ECONOMIQUE', 'etat': 'EN_STOCK',
                    'date_reception': today - timedelta(days=360),
                    'date_expiration': today + timedelta(days=3),
                    'user': admin, 'date_creation': now - timedelta(days=360),
                    'observations': 'LOT CRITIQUE — Expiration imminente dans 3 jours. Vente ou déstockage d\'urgence requis.',
                },
                # Lot brisures expiration dans 7 jours
                {
                    'produit': produits[3], 'producteur': producteurs[5],
                    'zone': zones[3], 'quantite_initiale': Decimal('40.00'),
                    'quantite_restante': Decimal('35.00'),
                    'quantite_reservee': Decimal('0.00'),
                    'qualite': 'ECONOMIQUE', 'etat': 'EN_STOCK',
                    'date_reception': today - timedelta(days=170),
                    'date_expiration': today + timedelta(days=7),
                    'user': admin, 'date_creation': now - timedelta(days=170),
                    'observations': 'Expiration sous 7 jours. Promotion en cours pour écoulement.',
                },
                # Lot pomme séchée expiration dans 12 jours
                {
                    'produit': produits[5], 'producteur': producteurs[3],
                    'zone': zones[3], 'quantite_initiale': Decimal('18.00'),
                    'quantite_restante': Decimal('12.00'),
                    'quantite_reservee': Decimal('0.00'),
                    'qualite': 'STANDARD', 'etat': 'PARTIELLEMENT_SORTI',
                    'date_reception': today - timedelta(days=105),
                    'date_expiration': today + timedelta(days=12),
                    'user': admin, 'date_creation': now - timedelta(days=105),
                    'observations': 'Lot pomme séchée à écouler. Commande possible pour jus artisanal.',
                },
                # Lot CNSL expiration dans 20 jours
                {
                    'produit': produits[4], 'producteur': producteurs[5],
                    'zone': zones[3], 'quantite_initiale': Decimal('25.00'),
                    'quantite_restante': Decimal('18.00'),
                    'quantite_reservee': Decimal('0.00'),
                    'qualite': 'STANDARD', 'etat': 'EN_STOCK',
                    'date_reception': today - timedelta(days=520),
                    'date_expiration': today + timedelta(days=20),
                    'user': admin, 'date_creation': now - timedelta(days=520),
                    'observations': 'CNSL approche fin de vie. Prévoir livraison client industriel.',
                },
                # Lot W240 expiration dans 25 jours
                {
                    'produit': produits[2], 'producteur': producteurs[5],
                    'zone': zones[2], 'quantite_initiale': Decimal('50.00'),
                    'quantite_restante': Decimal('18.00'),
                    'quantite_reservee': Decimal('10.00'),
                    'qualite': 'PREMIUM', 'etat': 'RESERVE',
                    'date_reception': today - timedelta(days=340),
                    'date_expiration': today + timedelta(days=25),
                    'user': admin, 'date_creation': now - timedelta(days=340),
                    'observations': 'Lot W240 réservé partiellement pour commande export. Fin de vie imminente.',
                },
                # Lot brut EXPIRÉ (pour statistiques)
                {
                    'produit': produits[0], 'producteur': producteurs[2],
                    'zone': zones[6], 'quantite_initiale': Decimal('100.00'),
                    'quantite_restante': Decimal('100.00'),
                    'quantite_reservee': Decimal('0.00'),
                    'qualite': 'ECONOMIQUE', 'etat': 'EN_STOCK',
                    'date_reception': today - timedelta(days=400),
                    'date_expiration': today - timedelta(days=5),
                    'user': admin, 'date_creation': now - timedelta(days=400),
                    'observations': 'LOT EXPIRÉ — Noix brutes dégradées. Évaluation pour destruction ou valorisation CNSL.',
                },
                # Lot brisures EXPIRÉ
                {
                    'produit': produits[3], 'producteur': producteurs[5],
                    'zone': zones[3], 'quantite_initiale': Decimal('60.00'),
                    'quantite_restante': Decimal('35.00'),
                    'quantite_reservee': Decimal('0.00'),
                    'qualite': 'ECONOMIQUE', 'etat': 'EN_STOCK',
                    'date_reception': today - timedelta(days=200),
                    'date_expiration': today - timedelta(days=12),
                    'user': admin, 'date_creation': now - timedelta(days=200),
                    'observations': 'LOT EXPIRÉ — Brisures périmées, mise en quarantaine.',
                },
                # Gros lot brut frais (bon stock pour prévision)
                {
                    'produit': produits[0], 'producteur': producteurs[1],
                    'zone': zones[4], 'quantite_initiale': Decimal('1800.00'),
                    'quantite_restante': Decimal('1500.00'),
                    'quantite_reservee': Decimal('200.00'),
                    'qualite': 'PREMIUM', 'etat': 'EN_STOCK',
                    'date_reception': today - timedelta(days=5),
                    'date_expiration': today + timedelta(days=360),
                    'user': admin, 'date_creation': now - timedelta(days=5),
                    'observations': 'Lot campagne 2026 — Collecte MIFA. Volume important, qualité premium vérifiée.',
                },
                # Lot W320 en transit (Sokodé → Lomé)
                {
                    'produit': produits[1], 'producteur': producteurs[5],
                    'zone': zones[5], 'quantite_initiale': Decimal('100.00'),
                    'quantite_restante': Decimal('100.00'),
                    'quantite_reservee': Decimal('0.00'),
                    'qualite': 'STANDARD', 'etat': 'EN_STOCK',
                    'date_reception': today - timedelta(days=2),
                    'date_expiration': today + timedelta(days=363),
                    'user': admin, 'date_creation': now - timedelta(days=2),
                    'observations': 'En stockage intermédiaire Sokodé. Transfert vers Lomé prévu cette semaine.',
                },
            ]

            from gestion.services import generate_lot_code
            for lot_data in lots_logistiques:
                try:
                    lot_data['code_lot'] = generate_lot_code()
                    Lot.objects.create(**lot_data)
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Lot {lot_data["code_lot"]} — {lot_data["produit"].nom} '
                        f'({lot_data["quantite_restante"]} restant, expire: {lot_data["date_expiration"]})'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'  ✗ Lot {lot_data["produit"].nom} → {e}'))

        # ─── 12d. Mettre à jour les quantités des entrepôts pour créer des alertes ───
        self.stdout.write('\n  ── Entrepôts : ajustement quantités ──')
        if len(entrepots) >= 3:
            # Entrepôt Central Lomé : seuil=1000, on met 850 → en alerte
            with connection.cursor() as cur:
                cur.execute(
                    'UPDATE stock_cajou.entrepot SET quantite_disponible=%s WHERE id=%s',
                    ['850.00', entrepots[0].pk])
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {entrepots[0].nom} → quantite=850 (seuil={entrepots[0].seuil_critique}) ⚠️'))

            # Entrepôt Sokodé : seuil=800, on met 600 → en alerte
            with connection.cursor() as cur:
                cur.execute(
                    'UPDATE stock_cajou.entrepot SET quantite_disponible=%s WHERE id=%s',
                    ['600.00', entrepots[1].pk])
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {entrepots[1].nom} → quantite=600 (seuil={entrepots[1].seuil_critique}) ⚠️'))

            # Magasin Kara : seuil=400, on met 1500 → OK (pas en alerte)
            with connection.cursor() as cur:
                cur.execute(
                    'UPDATE stock_cajou.entrepot SET quantite_disponible=%s WHERE id=%s',
                    ['1500.00', entrepots[2].pk])
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {entrepots[2].nom} → quantite=1500 (seuil={entrepots[2].seuil_critique}) ✅'))

        # ─── 12e. Mouvements supplémentaires pour historique logistique ───
        self.stdout.write('\n  ── Mouvements logistiques supplémentaires ──')
        mouv_extra = [
            {'type_mouvement': 'TRANSFERT', 'lot': lots_db[1] if len(lots_db) > 1 else lots_db[0],
             'quantite': '400.00', 'zone_origine': zones[4].pk if len(zones) > 4 else zones[0].pk,
             'zone_destination': zones[0].pk, 'valide': 'on',
             'motif': 'Transfert Sokodé → Lomé, lot MIFA campagne 2026'},
            {'type_mouvement': 'ENTREE', 'lot': lots_db[3] if len(lots_db) > 3 else lots_db[0],
             'quantite': '250.00', 'zone_destination': zones[2].pk if len(zones) > 2 else zones[0].pk,
             'zone_origine': '', 'valide': 'on',
             'motif': 'Réception W320 transformés AGRO-CAJOU'},
            {'type_mouvement': 'SORTIE', 'lot': lots_db[4] if len(lots_db) > 4 else lots_db[0],
             'quantite': '8.00', 'zone_origine': zones[2].pk if len(zones) > 2 else zones[0].pk,
             'zone_destination': '', 'valide': 'on',
             'motif': 'Sortie W240 export Afrique Cajou Trading'},
            {'type_mouvement': 'AJUSTEMENT', 'lot': lots_db[5] if len(lots_db) > 5 else lots_db[0],
             'quantite': '8.00', 'zone_origine': zones[3].pk if len(zones) > 3 else zones[0].pk,
             'zone_destination': '', 'valide': 'on',
             'motif': 'Ajustement inventaire brisures — casse lors manutention'},
        ]
        for d in mouv_extra:
            d_post = {k: (v.pk if hasattr(v, 'pk') else v) for k, v in d.items()}
            post('/gestion/mouvements/create/', d_post,
                 f'Mouvement {d["type_mouvement"]} ({d["quantite"]} kg)')

        # ─── 12e-bis. Mouvements HISTORIQUES pour prévision IA (4 ans) ───
        self.stdout.write('\n  ── Mouvements historiques (48 mois pour prévision IA) ──')
        import random
        random.seed(2026)

        # Créer un lot de référence historique pour y rattacher les mouvements
        from gestion.services import generate_lot_code
        hist_lot = None
        if produits and zones:
            # Désactiver TOUS les triggers pour insertion historique
            with connection.cursor() as cur:
                cur.execute('ALTER TABLE stock_cajou.lot DISABLE TRIGGER ALL')
                cur.execute('ALTER TABLE stock_cajou.mouvement_stock DISABLE TRIGGER ALL')
            try:
                hist_lot = Lot.objects.create(
                    code_lot=generate_lot_code(),
                    quantite_initiale=Decimal('1.00'),
                    quantite_restante=Decimal('0.00'),
                    qualite='STANDARD',
                    etat='EPUISE',
                    date_reception=today - timedelta(days=1460),
                    produit=produits[0],
                    zone=zones[0],
                    user=admin,
                    date_creation=now - timedelta(days=1460),
                    observations='Lot historique reconstitué — données prévision IA',
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Lot historique {hist_lot.code_lot} créé'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Lot historique → {e}'))

        if hist_lot and zones:
            nb_created = 0
            # Générer 48 mois de mouvements (ENTREE + SORTIE par mois)
            # Saisonnalité cajou Togo : collecte forte Fév-Mai, export fort Aoû-Déc
            for month_offset in range(48):
                dt = now - timedelta(days=30 * (48 - month_offset))
                month_num = dt.month

                # ── Entrées saisonnières ──
                if month_num in [2, 3, 4, 5]:       # Campagne cajou
                    entree_qty = random.randint(3000, 6000)
                elif month_num in [1, 6]:            # Transition
                    entree_qty = random.randint(1500, 3000)
                else:                                 # Saison sèche / export
                    entree_qty = random.randint(500, 1500)

                # ── Sorties saisonnières ──
                if month_num in [8, 9, 10, 11, 12]:  # Export + ventes locales
                    sortie_qty = random.randint(2500, 4500)
                elif month_num in [6, 7]:             # Début export
                    sortie_qty = random.randint(1800, 3000)
                else:                                  # Hors saison export
                    sortie_qty = random.randint(800, 2000)

                try:
                    MouvementStock.objects.create(
                        date_mouvement=dt,
                        type_mouvement='ENTREE',
                        quantite=Decimal(str(entree_qty)),
                        motif=f'Collecte cajou — historique {dt.strftime("%b %Y")}',
                        lot=hist_lot,
                        zone_destination=zones[0],
                        user=admin,
                        valide=True,
                    )
                    MouvementStock.objects.create(
                        date_mouvement=dt,
                        type_mouvement='SORTIE',
                        quantite=Decimal(str(sortie_qty)),
                        motif=f'Ventes/export — historique {dt.strftime("%b %Y")}',
                        lot=hist_lot,
                        zone_origine=zones[0],
                        user=admin,
                        valide=True,
                    )
                    nb_created += 2
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Mvt historique {dt.strftime("%Y-%m")} → {e}'))

            # Réactiver les triggers
            with connection.cursor() as cur:
                cur.execute('ALTER TABLE stock_cajou.mouvement_stock ENABLE TRIGGER ALL')
                cur.execute('ALTER TABLE stock_cajou.lot ENABLE TRIGGER ALL')

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {nb_created} mouvements historiques créés (48 mois × 2)'))

        # ─── 12f. Historique de traçabilité logistique ───
        self.stdout.write('\n  ── Entrées historique logistique ──')
        import json
        historique_entries = [
            {
                'date_action': now - timedelta(days=14),
                'type_action': 'reception',
                'description': 'Réception lot MIFA Tchamba — 1500 kg noix brutes, qualité standard vérifiée',
                'lot': lots_db[1] if len(lots_db) > 1 else None,
                'user': admin,
                'nouvelle_valeur': json.dumps({
                    'lot': 'MIFA Tchamba', 'quantite': '1500 kg',
                    'qualite': 'Standard', 'KOR': '47',
                }),
            },
            {
                'date_action': now - timedelta(days=10),
                'type_action': 'transfert',
                'description': 'Transfert inter-entrepôt Sokodé → Lomé — 500 kg noix brutes pour transformation',
                'lot': lots_db[1] if len(lots_db) > 1 else None,
                'user': admin,
                'ancienne_valeur': json.dumps({'entrepot': 'Sokodé', 'zone': 'Zone Collecte'}),
                'nouvelle_valeur': json.dumps({'entrepot': 'Lomé', 'zone': 'Zone Brut A'}),
            },
            {
                'date_action': now - timedelta(days=7),
                'type_action': 'controle_qualite',
                'description': 'Contrôle qualité lot W320 AGRO-CAJOU — Calibre vérifié, taux humidité 5.2%',
                'lot': lots_db[3] if len(lots_db) > 3 else None,
                'user': admin,
                'nouvelle_valeur': json.dumps({
                    'calibre': 'W320 conforme', 'humidite': '5.2%',
                    'defauts': '< 2%', 'resultat': 'VALIDÉ',
                }),
            },
            {
                'date_action': now - timedelta(days=5),
                'type_action': 'alerte_stock',
                'description': 'Détection automatique : stock W320 passé sous le seuil d\'alerte (15 < 40 kg)',
                'user': admin,
                'ancienne_valeur': json.dumps({'stock': '55 kg', 'seuil': '40 kg'}),
                'nouvelle_valeur': json.dumps({'stock': '15 kg', 'action': 'Alerte ACTIVE créée'}),
            },
            {
                'date_action': now - timedelta(days=3),
                'type_action': 'prevision',
                'description': 'Prévision consommation mars 2026 : +40% demande W320/W240 pour export Europe',
                'user': admin,
                'nouvelle_valeur': json.dumps({
                    'prevision_W320': '+150 kg', 'prevision_W240': '+80 kg',
                    'source': 'Tendance commandes Q1', 'fiabilite': '85%',
                }),
            },
            {
                'date_action': now - timedelta(days=2),
                'type_action': 'planification',
                'description': 'Planification réappro mars — commande AGRO-CAJOU 400 kg W320 + 100 kg W240',
                'user': admin,
                'nouvelle_valeur': json.dumps({
                    'fournisseur': 'AGRO-CAJOU Togo',
                    'W320': '400 kg', 'W240': '100 kg',
                    'delai': '10 jours', 'cout_estime': '1 850 000 XOF',
                }),
            },
            {
                'date_action': now - timedelta(days=1),
                'type_action': 'inventaire',
                'description': 'Inventaire physique Entrepôt Central Lomé — écart de 8 kg brisures (casse manutention)',
                'user': admin,
                'ancienne_valeur': json.dumps({'brisures_theorique': '165 kg'}),
                'nouvelle_valeur': json.dumps({
                    'brisures_reel': '157 kg', 'ecart': '-8 kg',
                    'cause': 'Casse manutention palette Z3',
                }),
            },
            {
                'date_action': now - timedelta(hours=8),
                'type_action': 'expedition',
                'description': 'Préparation expédition conteneur TG Cashew International — 80 kg W320 + 8 kg W240',
                'user': admin,
                'nouvelle_valeur': json.dumps({
                    'destination': 'Port de Lomé', 'client': 'TG Cashew International',
                    'W320': '80 kg', 'W240': '8 kg',
                    'conteneur': 'MSKU-2026-0312', 'depart_prevu': (today + timedelta(days=3)).isoformat(),
                }),
            },
        ]
        for h in historique_entries:
            try:
                HistoriqueTracabilite.objects.create(**h)
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Historique: {h["type_action"]} — {h["description"][:60]}...'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Historique → {e}'))

        # ─── 12g. (commandes supplémentaires omises — 5 commandes section 7 suffisent) ───

        # ─── 12h. DA supplémentaires liées aux alertes ───
        self.stdout.write('\n  ── Demandes d\'achat supplémentaires ──')
        extra_da = [
            {'produit': produits[2].pk, 'quantite_a_commander': '100.00',
             'priorite': 'URGENT',
             'observations': 'DA urgente W240 — Stock critique, commande Afrique Cajou en attente. Prévoir livraison AGRO-CAJOU sous 7 jours.'},
            {'produit': produits[5].pk, 'quantite_a_commander': '60.00',
             'priorite': 'NORMAL',
             'observations': 'Réappro pomme séchée — Fin de saison, négocier avec GIE Anacarde Plateaux pour séchage supplémentaire.'},
            {'produit': produits[3].pk, 'quantite_a_commander': '80.00',
             'priorite': 'NORMAL',
             'observations': 'Brisures — Dépend du prochain lot de décorticage W320. Prévu semaine prochaine.'},
        ]
        for d in extra_da:
            prod = Produit.objects.get(pk=d['produit'])
            post('/gestion/demandes/create/', d,
                 f'DA {prod.nom[:25]} ({d["quantite_a_commander"]} kg)')

        # ─── 12i. Créer des utilisateurs gestionnaires ───
        self.stdout.write('\n  ── Utilisateurs gestionnaires ──')
        gestionnaires = [
            ('gestionnaire', 'gest@mokpokpo.tg', 'Gest123!', 'Kofi', 'AGBODJAN'),
            ('logistique', 'log@mokpokpo.tg', 'Logi123!', 'Ama', 'MENSAH'),
            ('commercial', 'com@mokpokpo.tg', 'Comm123!', 'Yao', 'KOUDJO'),
        ]
        for uname, email, pwd, first, last in gestionnaires:
            if not User.objects.filter(username=uname).exists():
                u = User.objects.create_user(uname, email, pwd)
                u.first_name = first
                u.last_name = last
                u.is_staff = False
                u.save()
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Utilisateur créé: {uname} ({first} {last})'))
            else:
                self.stdout.write(f'  ⏭ Utilisateur {uname} existe déjà')

        # ==============================================================
        # RÉSUMÉ FINAL
        # ==============================================================
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS(
            f'RÉSULTAT: {ok} créations réussies, {fail} échecs'))
        self.stdout.write(f'{"="*60}')

        self.stdout.write(f'\n📊 DONNÉES EN BASE:')
        self.stdout.write(f'  Clients:         {Client.objects.count()}')
        self.stdout.write(f'  Produits:        {Produit.objects.count()}')
        self.stdout.write(f'  Producteurs:     {Producteur.objects.count()}')
        self.stdout.write(f'  Entrepôts:       {Entrepot.objects.count()}')
        self.stdout.write(f'  Zones:           {ZoneEntrepot.objects.count()}')
        self.stdout.write(f'  Lots:            {Lot.objects.count()}')
        self.stdout.write(f'  Commandes:       {Commande.objects.count()}')
        self.stdout.write(f'  Ventes:          {Vente.objects.count()}')
        self.stdout.write(f'  Mouvements:      {MouvementStock.objects.count()}')
        self.stdout.write(f'  Ventes Imm.:     {VenteImmediate.objects.count()}')
        self.stdout.write(f'  Demandes DA:     {DemandeAchat.objects.count()}')
        self.stdout.write(f'  Alertes Stock:   {AlerteStock.objects.count()}')
        self.stdout.write(f'  Historique:      {HistoriqueTracabilite.objects.count()}')

        self.stdout.write(f'\n🔔 ALERTES:')
        self.stdout.write(f'  Actives:         {AlerteStock.objects.filter(statut="ACTIVE").count()}')
        self.stdout.write(f'  Traitées:        {AlerteStock.objects.filter(statut="TRAITEE").count()}')
        self.stdout.write(f'  Ignorées:        {AlerteStock.objects.filter(statut="IGNOREE").count()}')

        self.stdout.write(f'\n📦 LOGISTIQUE:')
        lots_exp = Lot.objects.filter(
            date_expiration__lte=today + timedelta(days=30),
            date_expiration__gte=today,
        ).count()
        lots_expired = Lot.objects.filter(date_expiration__lt=today).count()
        self.stdout.write(f'  Lots ≤ 30 jours: {lots_exp}')
        self.stdout.write(f'  Lots expirés:    {lots_expired}')
        self.stdout.write(f'  Entrepôts alerte: {Entrepot.objects.filter(quantite_disponible__lte=models.F("seuil_critique")).count()}')

        self.stdout.write(f'\n👥 UTILISATEURS:')
        self.stdout.write(f'  Total:           {User.objects.count()}')
        self.stdout.write(f'  Admins:          {User.objects.filter(is_superuser=True).count()}')
        self.stdout.write(f'  Gestionnaires:   {User.objects.filter(is_superuser=False, is_active=True).count()}')

        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS('✅ POPULATION TERMINÉE — Données logistiques et prévision prêtes!'))
