from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client as HttpClient
from django.contrib.auth.models import User, Permission
from django.utils import timezone
from django.urls import reverse

from .models import (
    Clients, Produits, Lots, Ventes, Entrepots, ZoneEntrepots,
    Producteurs, MouvementStocks, HistoriqueTracabilites,
)
from .forms import (
    ClientsForm, ProduitsForm, LotsForm, VentesForm, EntrepotsForm,
    ZoneEntrepotsForm, ProducteursForm, MouvementStocksForm,
)


# ==============================================================================
# Helpers
# ==============================================================================

class BaseTestCase(TestCase):
    """Base test case with common setup: user, entrepot, zone, produit, lot."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        cls.superuser = User.objects.create_superuser(
            username='admin', password='adminpass123'
        )
        cls.entrepot = Entrepots.objects.create(
            nom='Entrepot Test',
            localisation='Lomé',
            capacite_max=Decimal('10000.00'),
            seuil_critique=Decimal('1000.00'),
            quantite_disponible=Decimal('5000.00'),
            statut='ACTIF',
            responsable=cls.user,
            date_creation=timezone.now(),
        )
        cls.zone = ZoneEntrepots.objects.create(
            nom='Zone A',
            entrepot=cls.entrepot,
            capacite=Decimal('5000.00'),
            quantite=Decimal('2000.00'),
            statut='ACTIF',
            responsable=cls.user,
        )
        cls.zone_b = ZoneEntrepots.objects.create(
            nom='Zone B',
            entrepot=cls.entrepot,
            capacite=Decimal('5000.00'),
            quantite=Decimal('0.00'),
            statut='ACTIF',
        )
        cls.produit = Produits.objects.create(
            nom='Noix de cajou brute',
            categorie='Brut',
            unite='kg',
            prix_unitaire=Decimal('500.00'),
        )
        cls.producteur = Producteurs.objects.create(
            nom='Koffi',
            prenom='Jean',
            telephone='22890001234',
            localisation='Sokodé',
            type_producteur='INDIVIDUEL',
            statut='ACTIF',
            date_inscription=timezone.now(),
        )
        cls.client_obj = Clients.objects.create(
            nom='Dupont',
            prenom='Marie',
            entreprise='Cajou SA',
            telephone='22891112222',
            email='marie@cajou.com',
            adresse='123 Rue de Lomé',
            date_inscription=timezone.now(),
        )
        cls.lot = Lots.objects.create(
            code_lot='LOT-001',
            quantite_initiale=Decimal('1000.00'),
            quantite_restante=Decimal('800.00'),
            qualite='PREMIUM',
            etat='EN_STOCK',
            date_reception=date.today(),
            date_expiration=date.today() + timedelta(days=90),
            produit=cls.produit,
            producteur=cls.producteur,
            zone=cls.zone,
            user=cls.user,
            date_creation=timezone.now(),
        )


# ==============================================================================
# MODEL TESTS
# ==============================================================================

class ClientsModelTest(BaseTestCase):
    def test_str(self):
        self.assertEqual(str(self.client_obj), 'Dupont Marie')

    def test_str_without_prenom(self):
        c = Clients.objects.create(nom='Solo')
        self.assertEqual(str(c), 'Solo')

    def test_email_field_type(self):
        field = Clients._meta.get_field('email')
        self.assertEqual(field.__class__.__name__, 'EmailField')


class EntrepotsModelTest(BaseTestCase):
    def test_str(self):
        self.assertEqual(str(self.entrepot), 'Entrepot Test')


class ProduitsModelTest(BaseTestCase):
    def test_str(self):
        self.assertEqual(str(self.produit), 'Noix de cajou brute (Brut)')


class ProducteursModelTest(BaseTestCase):
    def test_str(self):
        self.assertEqual(str(self.producteur), 'Koffi Jean')

    def test_str_without_prenom(self):
        p = Producteurs.objects.create(nom='Ama')
        self.assertEqual(str(p), 'Ama')


class ZoneEntrepotsModelTest(BaseTestCase):
    def test_str(self):
        self.assertEqual(str(self.zone), 'Zone A (Entrepot Test)')

    def test_unique_together(self):
        """Same name + same entrepot should raise IntegrityError."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ZoneEntrepots.objects.create(
                nom='Zone A',
                entrepot=self.entrepot,
                capacite=Decimal('1000.00'),
            )


class LotsModelTest(BaseTestCase):
    def test_str(self):
        self.assertEqual(str(self.lot), 'LOT-001 - Noix de cajou brute')

    def test_etat_choices(self):
        valid_etats = [c[0] for c in Lots.ETATS_CHOICES]
        self.assertIn('EN_STOCK', valid_etats)
        self.assertIn('PARTIELLEMENT_SORTI', valid_etats)
        self.assertIn('EPUISE', valid_etats)

    def test_unique_code_lot(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Lots.objects.create(
                code_lot='LOT-001',
                quantite_initiale=100,
                quantite_restante=100,
                date_reception=date.today(),
                produit=self.produit,
                zone=self.zone,
                user=self.user,
            )

    def test_no_duplicate_etat_field(self):
        """Verify etat field exists only once (regression test for the double-field bug)."""
        etat_fields = [f for f in Lots._meta.get_fields() if getattr(f, 'name', '') == 'etat']
        self.assertEqual(len(etat_fields), 1)

    def test_etat_has_choices(self):
        field = Lots._meta.get_field('etat')
        self.assertTrue(len(field.choices) > 0)


class VentesModelTest(BaseTestCase):
    def test_str(self):
        """Regression test: Ventes.__str__ should NOT crash (old bug: referenced self.nom)."""
        vente = Ventes.objects.create(
            numero_vente='V-001',
            quantite_vendue=Decimal('100.00'),
            prix_unitaire=Decimal('600.00'),
            montant_total=Decimal('60000.00'),
            lot=self.lot,
            user=self.user,
            client=self.client_obj,
        )
        result = str(vente)
        self.assertIn('V-001', result)
        # Should not raise AttributeError


class MouvementStocksModelTest(BaseTestCase):
    def test_str(self):
        m = MouvementStocks.objects.create(
            type_mouvement='TRANSFERT',
            quantite=Decimal('50.00'),
            lot=self.lot,
            user=self.user,
            date_mouvement=timezone.now(),
        )
        self.assertIn('TRANSFERT', str(m))
        self.assertIn('LOT-001', str(m))


class HistoriqueTracabilitesModelTest(BaseTestCase):
    def test_str(self):
        h = HistoriqueTracabilites.objects.create(
            type_action='creation',
            date_action=timezone.now(),
            lot=self.lot,
            user=self.user,
            description='Lot créé',
        )
        self.assertIn('creation', str(h))

    def test_json_fields(self):
        h = HistoriqueTracabilites.objects.create(
            type_action='modification',
            date_action=timezone.now(),
            lot=self.lot,
            user=self.user,
            ancienne_valeur={'zone': 'Zone A'},
            nouvelle_valeur={'zone': 'Zone B'},
        )
        h.refresh_from_db()
        self.assertEqual(h.ancienne_valeur['zone'], 'Zone A')
        self.assertEqual(h.nouvelle_valeur['zone'], 'Zone B')


# ==============================================================================
# ON_DELETE TESTS
# ==============================================================================

class OnDeleteTest(BaseTestCase):
    def test_delete_entrepot_cascades_zones(self):
        """Deleting an entrepot should cascade-delete its zones."""
        entrepot = Entrepots.objects.create(
            nom='Temp',
            capacite_max=1000,
            seuil_critique=100,
        )
        zone = ZoneEntrepots.objects.create(
            nom='TempZone',
            entrepot=entrepot,
            capacite=500,
        )
        zone_id = zone.id
        entrepot.delete()
        self.assertFalse(ZoneEntrepots.objects.filter(id=zone_id).exists())

    def test_delete_lot_cascades_mouvements(self):
        """Deleting a lot should cascade-delete its mouvements."""
        lot = Lots.objects.create(
            code_lot='LOT-DEL',
            quantite_initiale=100,
            quantite_restante=100,
            date_reception=date.today(),
            produit=self.produit,
            zone=self.zone,
            user=self.user,
        )
        mouv = MouvementStocks.objects.create(
            type_mouvement='ENTREE',
            quantite=100,
            lot=lot,
            user=self.user,
        )
        mouv_id = mouv.id
        lot.delete()
        self.assertFalse(MouvementStocks.objects.filter(id=mouv_id).exists())

    def test_delete_produit_protected_by_lot(self):
        """Cannot delete a produit that has lots (PROTECT)."""
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.produit.delete()


# ==============================================================================
# FORM TESTS
# ==============================================================================

class ClientsFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'nom': 'Test',
            'prenom': 'User',
            'entreprise': 'TestCo',
            'telephone': '12345',
            'email': 'test@example.com',
            'adresse': 'Addr',
        }
        form = ClientsForm(data=data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        form = ClientsForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('nom', form.errors)

    def test_invalid_email(self):
        data = {'nom': 'Test', 'email': 'not-an-email'}
        form = ClientsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class ProduitsFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'nom': 'Cajou torréfié',
            'categorie': 'Transformé',
            'unite': 'kg',
            'prix_unitaire': '800.00',
        }
        form = ProduitsForm(data=data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        form = ProduitsForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('nom', form.errors)
        self.assertIn('categorie', form.errors)


class LotsFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'code_lot': 'LOT-NEW',
            'produit': self.produit.pk,
            'producteur': self.producteur.pk,
            'quantite_initiale': '500.00',
            'quantite_restante': '500.00',
            'qualite': 'STANDARD',
            'etat': 'EN_STOCK',
            'date_reception': date.today().isoformat(),
            'date_expiration': (date.today() + timedelta(days=60)).isoformat(),
            'zone': self.zone.pk,
        }
        form = LotsForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_etat_choices_in_form(self):
        form = LotsForm()
        etat_field = form.fields['etat']
        choice_values = [c[0] for c in etat_field.choices if c[0]]
        self.assertIn('EN_STOCK', choice_values)
        self.assertIn('PARTIELLEMENT_SORTI', choice_values)


class VentesFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'numero_vente': 'V-NEW',
            'client': self.client_obj.pk,
            'lot': self.lot.pk,
            'quantite_vendue': '100.00',
            'prix_unitaire': '600.00',
            'montant_total': '60000.00',
        }
        form = VentesForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


class EntrepotsFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'nom': 'Entrepot Nouveau',
            'localisation': 'Kara',
            'capacite_max': '20000.00',
            'seuil_critique': '2000.00',
            'quantite_disponible': '0.00',
        }
        form = EntrepotsForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


class ZoneEntrepotsFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'nom': 'Zone C',
            'entrepot': self.entrepot.pk,
            'capacite': '3000.00',
            'quantite': '0.00',
        }
        form = ZoneEntrepotsForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


class ProducteursFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'nom': 'Akou',
            'prenom': 'Pierre',
            'type_producteur': 'COOPERATIVE',
            'telephone': '22800000000',
        }
        form = ProducteursForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


class MouvementStocksFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'type_mouvement': 'TRANSFERT',
            'lot': self.lot.pk,
            'quantite': '50.00',
            'zone_origine': self.zone.pk,
            'zone_destination': self.zone_b.pk,
            'motif': 'Réorganisation',
        }
        form = MouvementStocksForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


# ==============================================================================
# VIEW TESTS
# ==============================================================================

class LoginRequiredTest(BaseTestCase):
    """All gestion views should redirect to login when not authenticated."""

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_clients_list_requires_login(self):
        response = self.client.get(reverse('clients_list'))
        self.assertEqual(response.status_code, 302)

    def test_lots_list_requires_login(self):
        response = self.client.get(reverse('lots_list'))
        self.assertEqual(response.status_code, 302)


class DashboardViewTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='testuser', password='testpass123')

    def test_dashboard_status_200(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_context(self):
        response = self.client.get(reverse('dashboard'))
        self.assertIn('total_clients', response.context)
        self.assertIn('total_lots', response.context)
        self.assertIn('total_ventes', response.context)
        self.assertIn('lots_expires', response.context)

    def test_dashboard_template(self):
        response = self.client.get(reverse('dashboard'))
        self.assertTemplateUsed(response, 'gestion/dashboard.html')


class ClientsViewsTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='admin', password='adminpass123')

    def test_clients_list(self):
        response = self.client.get(reverse('clients_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dupont')

    def test_clients_list_search(self):
        response = self.client.get(reverse('clients_list') + '?search=Dupont')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dupont')

    def test_clients_create_get(self):
        response = self.client.get(reverse('clients_create'))
        self.assertEqual(response.status_code, 200)

    def test_clients_create_post(self):
        data = {
            'nom': 'Nouveau',
            'prenom': 'Client',
            'email': 'new@example.com',
        }
        response = self.client.post(reverse('clients_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Clients.objects.filter(nom='Nouveau').exists())

    def test_clients_detail(self):
        response = self.client.get(
            reverse('clients_detail', kwargs={'pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_clients_update(self):
        data = {
            'nom': 'Dupont-Modifié',
            'prenom': 'Marie',
            'email': 'marie@cajou.com',
        }
        response = self.client.post(
            reverse('clients_update', kwargs={'pk': self.client_obj.pk}), data
        )
        self.assertEqual(response.status_code, 302)

    def test_clients_delete(self):
        c = Clients.objects.create(nom='ToDelete')
        response = self.client.post(
            reverse('clients_delete', kwargs={'pk': c.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Clients.objects.filter(pk=c.pk).exists())


class ProduitsViewsTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='admin', password='adminpass123')

    def test_produits_list(self):
        response = self.client.get(reverse('produits_list'))
        self.assertEqual(response.status_code, 200)

    def test_produits_create(self):
        data = {
            'nom': 'Cajou grillé',
            'categorie': 'Transformé',
            'unite': 'kg',
            'prix_unitaire': '900.00',
        }
        response = self.client.post(reverse('produits_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Produits.objects.filter(nom='Cajou grillé').exists())

    def test_produits_update(self):
        data = {
            'nom': 'Noix modifié',
            'categorie': 'Brut',
            'unite': 'kg',
            'prix_unitaire': '550.00',
        }
        response = self.client.post(
            reverse('produits_update', kwargs={'pk': self.produit.pk}), data
        )
        self.assertEqual(response.status_code, 302)

    def test_produits_delete(self):
        # Create a produit without lots to allow deletion
        p = Produits.objects.create(nom='Temp', categorie='Temp')
        response = self.client.post(
            reverse('produits_delete', kwargs={'pk': p.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Produits.objects.filter(pk=p.pk).exists())


class ProducteursViewsTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='admin', password='adminpass123')

    def test_producteurs_list(self):
        response = self.client.get(reverse('producteurs_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Koffi')

    def test_producteurs_create(self):
        data = {
            'nom': 'Nouveau',
            'prenom': 'Prod',
            'type_producteur': 'COOPERATIVE',
        }
        response = self.client.post(reverse('producteurs_create'), data)
        self.assertEqual(response.status_code, 302)

    def test_producteurs_detail(self):
        response = self.client.get(
            reverse('producteurs_detail', kwargs={'pk': self.producteur.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_producteurs_update(self):
        data = {
            'nom': 'Koffi',
            'prenom': 'Jean-Modifié',
            'type_producteur': 'INDIVIDUEL',
        }
        response = self.client.post(
            reverse('producteurs_update', kwargs={'pk': self.producteur.pk}), data
        )
        self.assertEqual(response.status_code, 302)

    def test_producteurs_delete(self):
        p = Producteurs.objects.create(nom='Temp')
        response = self.client.post(
            reverse('producteurs_delete', kwargs={'pk': p.pk})
        )
        self.assertEqual(response.status_code, 302)


class EntrepotsViewsTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='admin', password='adminpass123')

    def test_entrepots_list(self):
        response = self.client.get(reverse('entrepots_list'))
        self.assertEqual(response.status_code, 200)

    def test_entrepots_create(self):
        data = {
            'nom': 'Entrepot Nouveau',
            'capacite_max': '20000.00',
            'seuil_critique': '2000.00',
        }
        response = self.client.post(reverse('entrepots_create'), data)
        self.assertEqual(response.status_code, 302)

    def test_entrepots_detail(self):
        response = self.client.get(
            reverse('entrepots_detail', kwargs={'pk': self.entrepot.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_entrepots_update(self):
        data = {
            'nom': 'Entrepot Modifié',
            'capacite_max': '10000.00',
            'seuil_critique': '1000.00',
        }
        response = self.client.post(
            reverse('entrepots_update', kwargs={'pk': self.entrepot.pk}), data
        )
        self.assertEqual(response.status_code, 302)


class ZonesViewsTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='admin', password='adminpass123')

    def test_zones_list(self):
        response = self.client.get(reverse('zones_list'))
        self.assertEqual(response.status_code, 200)

    def test_zones_create(self):
        data = {
            'nom': 'Zone Nouvelle',
            'entrepot': self.entrepot.pk,
            'capacite': '3000.00',
        }
        response = self.client.post(reverse('zones_create'), data)
        self.assertEqual(response.status_code, 302)

    def test_zones_update(self):
        data = {
            'nom': 'Zone A Modifiée',
            'entrepot': self.entrepot.pk,
            'capacite': '5000.00',
        }
        response = self.client.post(
            reverse('zones_update', kwargs={'pk': self.zone.pk}), data
        )
        self.assertEqual(response.status_code, 302)


class LotsViewsTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='admin', password='adminpass123')

    def test_lots_list(self):
        response = self.client.get(reverse('lots_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'LOT-001')

    def test_lots_list_search(self):
        response = self.client.get(reverse('lots_list') + '?search=LOT-001')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'LOT-001')

    def test_lots_list_filter_etat(self):
        response = self.client.get(reverse('lots_list') + '?etat=EN_STOCK')
        self.assertEqual(response.status_code, 200)

    def test_lots_create(self):
        data = {
            'code_lot': 'LOT-NEW',
            'produit': self.produit.pk,
            'producteur': self.producteur.pk,
            'quantite_initiale': '500.00',
            'quantite_restante': '500.00',
            'qualite': 'STANDARD',
            'etat': 'EN_STOCK',
            'date_reception': date.today().isoformat(),
            'date_expiration': (date.today() + timedelta(days=60)).isoformat(),
            'zone': self.zone.pk,
        }
        response = self.client.post(reverse('lots_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Lots.objects.filter(code_lot='LOT-NEW').exists())

    def test_lots_detail(self):
        response = self.client.get(
            reverse('lots_detail', kwargs={'pk': self.lot.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_lots_update(self):
        data = {
            'code_lot': 'LOT-001',
            'produit': self.produit.pk,
            'quantite_initiale': '1000.00',
            'quantite_restante': '700.00',
            'qualite': 'PREMIUM',
            'etat': 'PARTIELLEMENT_SORTI',
            'date_reception': date.today().isoformat(),
            'zone': self.zone.pk,
        }
        response = self.client.post(
            reverse('lots_update', kwargs={'pk': self.lot.pk}), data
        )
        self.assertEqual(response.status_code, 302)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.etat, 'PARTIELLEMENT_SORTI')

    def test_lots_delete(self):
        lot = Lots.objects.create(
            code_lot='LOT-DEL2',
            quantite_initiale=100,
            quantite_restante=100,
            date_reception=date.today(),
            produit=self.produit,
            zone=self.zone,
            user=self.user,
        )
        response = self.client.post(
            reverse('lots_delete', kwargs={'pk': lot.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Lots.objects.filter(pk=lot.pk).exists())


class VentesViewsTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='admin', password='adminpass123')

    def test_ventes_list(self):
        response = self.client.get(reverse('ventes_list'))
        self.assertEqual(response.status_code, 200)

    def test_ventes_create(self):
        data = {
            'numero_vente': 'V-CREATE',
            'client': self.client_obj.pk,
            'lot': self.lot.pk,
            'quantite_vendue': '50.00',
            'prix_unitaire': '600.00',
            'montant_total': '30000.00',
        }
        response = self.client.post(reverse('ventes_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ventes.objects.filter(numero_vente='V-CREATE').exists())


class MouvementsViewsTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='admin', password='adminpass123')

    def test_mouvements_list(self):
        response = self.client.get(reverse('mouvements_list'))
        self.assertEqual(response.status_code, 200)

    def test_mouvements_create(self):
        data = {
            'type_mouvement': 'TRANSFERT',
            'lot': self.lot.pk,
            'quantite': '50.00',
            'zone_origine': self.zone.pk,
            'zone_destination': self.zone_b.pk,
            'motif': 'Test transfert',
        }
        response = self.client.post(reverse('mouvements_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MouvementStocks.objects.filter(motif='Test transfert').exists())
        # Verify a tracability record was created
        self.assertTrue(
            HistoriqueTracabilites.objects.filter(type_action='mouvement_stock').exists()
        )

    def test_mouvements_create_historique_json(self):
        """Verify that the historique record stores JSON (not strings) for valeur fields."""
        data = {
            'type_mouvement': 'TRANSFERT',
            'lot': self.lot.pk,
            'quantite': '25.00',
            'zone_origine': self.zone.pk,
            'zone_destination': self.zone_b.pk,
            'motif': 'JSON test',
        }
        self.client.post(reverse('mouvements_create'), data)
        hist = HistoriqueTracabilites.objects.filter(
            type_action='mouvement_stock', description__contains='25'
        ).first()
        self.assertIsNotNone(hist)
        # ancienne_valeur/nouvelle_valeur should be dicts, not strings
        self.assertIsInstance(hist.ancienne_valeur, dict)
        self.assertIsInstance(hist.nouvelle_valeur, dict)


class HistoriqueViewsTest(BaseTestCase):
    def setUp(self):
        self.client.login(username='admin', password='adminpass123')

    def test_historique_list(self):
        # Create some history
        HistoriqueTracabilites.objects.create(
            type_action='test',
            date_action=timezone.now(),
            lot=self.lot,
            user=self.user,
        )
        response = self.client.get(reverse('historique_list'))
        self.assertEqual(response.status_code, 200)


# ==============================================================================
# PERMISSION TESTS
# ==============================================================================

class PermissionTest(BaseTestCase):
    """Test that views requiring specific permissions deny access to unpermissioned users."""

    def setUp(self):
        self.client.login(username='testuser', password='testpass123')

    def test_clients_create_requires_permission(self):
        response = self.client.get(reverse('clients_create'))
        self.assertEqual(response.status_code, 403)

    def test_clients_update_requires_permission(self):
        response = self.client.get(
            reverse('clients_update', kwargs={'pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_clients_delete_requires_permission(self):
        response = self.client.post(
            reverse('clients_delete', kwargs={'pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_lots_create_requires_permission(self):
        response = self.client.get(reverse('lots_create'))
        self.assertEqual(response.status_code, 403)

    def test_ventes_create_requires_permission(self):
        response = self.client.get(reverse('ventes_create'))
        self.assertEqual(response.status_code, 403)

    def test_superuser_has_all_permissions(self):
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('lots_create'))
        self.assertEqual(response.status_code, 200)

    def test_user_with_specific_permission(self):
        """User with explicit permission can access the view."""
        perm = Permission.objects.get(codename='add_lots')
        self.user.user_permissions.add(perm)
        # Clear cached permissions
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('lots_create'))
        self.assertEqual(response.status_code, 200)


# ==============================================================================
# URL TESTS
# ==============================================================================

class UrlResolutionTest(TestCase):
    """Test that all URL patterns resolve correctly."""

    def test_dashboard_url(self):
        self.assertEqual(reverse('dashboard'), '/')

    def test_clients_urls(self):
        self.assertEqual(reverse('clients_list'), '/clients/')
        self.assertEqual(reverse('clients_create'), '/clients/create/')
        self.assertEqual(reverse('clients_detail', kwargs={'pk': 1}), '/clients/1/')
        self.assertEqual(reverse('clients_update', kwargs={'pk': 1}), '/clients/1/update/')
        self.assertEqual(reverse('clients_delete', kwargs={'pk': 1}), '/clients/1/delete/')

    def test_produits_urls(self):
        self.assertEqual(reverse('produits_list'), '/produits/')
        self.assertEqual(reverse('produits_create'), '/produits/create/')

    def test_lots_urls(self):
        self.assertEqual(reverse('lots_list'), '/lots/')
        self.assertEqual(reverse('lots_create'), '/lots/create/')
        self.assertEqual(reverse('lots_detail', kwargs={'pk': 1}), '/lots/1/')

    def test_ventes_urls(self):
        self.assertEqual(reverse('ventes_list'), '/ventes/')
        self.assertEqual(reverse('ventes_create'), '/ventes/create/')

    def test_mouvements_urls(self):
        self.assertEqual(reverse('mouvements_list'), '/mouvements/')
        self.assertEqual(reverse('mouvements_create'), '/mouvements/create/')

    def test_historique_url(self):
        self.assertEqual(reverse('historique_list'), '/historique/')

    def test_stock_forecast_url(self):
        self.assertEqual(reverse('stock_prediction'), '/stock-forecast/')

    def test_entrepots_urls(self):
        self.assertEqual(reverse('entrepots_list'), '/entrepots/')
        self.assertEqual(reverse('entrepots_create'), '/entrepots/create/')

    def test_zones_urls(self):
        self.assertEqual(reverse('zones_list'), '/zones/')
        self.assertEqual(reverse('zones_create'), '/zones/create/')

    def test_producteurs_urls(self):
        self.assertEqual(reverse('producteurs_list'), '/producteurs/')
        self.assertEqual(reverse('producteurs_create'), '/producteurs/create/')

    def test_auth_urls(self):
        self.assertEqual(reverse('login'), '/login/')
        self.assertEqual(reverse('logout'), '/logout/')
