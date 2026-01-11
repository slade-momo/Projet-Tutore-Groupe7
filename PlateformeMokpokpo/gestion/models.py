from django.db import models
from django.conf import settings


class Clients(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True, null=True)
    entreprise = models.CharField(max_length=150, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=150, blank=True, null=True)
    adresse = models.CharField(max_length=200, blank=True, null=True)
    date_inscription = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'clients'
        db_table_comment = 'Clients acheteurs'


class Entrepots(models.Model):
    nom = models.CharField(max_length=100)
    localisation = models.CharField(max_length=150, blank=True, null=True)
    capacite_max = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_critique = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_disponible = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    statut = models.CharField(max_length=30, blank=True, null=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='entrepots_responsable',
    )
    date_creation = models.DateTimeField(blank=True, null=True)
    date_maj = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'entrepots'
        db_table_comment = 'Entrepôts de stockage'


class HistoriqueTracabilites(models.Model):
    date_action = models.DateTimeField(blank=True, null=True)
    type_action = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    lot = models.ForeignKey('Lots', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name='historique_tracabilites',
    )
    ancienne_valeur = models.JSONField(blank=True, null=True)
    nouvelle_valeur = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'historique_tracabilites'
        db_table_comment = "Historique d'audit et traçabilité"


class Lots(models.Model):
    code_lot = models.CharField(unique=True, max_length=50)
    quantite_initiale = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_restante = models.DecimalField(max_digits=10, decimal_places=2)
    qualite = models.CharField(max_length=50, blank=True, null=True)
    etat = models.CharField(max_length=30, blank=True, null=True)
    date_reception = models.DateField()
    date_expiration = models.DateField(blank=True, null=True)
    produit = models.ForeignKey('Produits', models.DO_NOTHING)
    producteur = models.ForeignKey('Producteurs', models.DO_NOTHING, blank=True, null=True)
    zone = models.ForeignKey('ZoneEntrepots', models.DO_NOTHING)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name='lots',
    )
    observations = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'lots'
        db_table_comment = 'Lots de produits avec traçabilité'


class MouvementStocks(models.Model):
    date_mouvement = models.DateTimeField(blank=True, null=True)
    type_mouvement = models.CharField(max_length=20)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    motif = models.CharField(max_length=200, blank=True, null=True)
    lot = models.ForeignKey(Lots, models.DO_NOTHING)
    zone_origine = models.ForeignKey('ZoneEntrepots', models.DO_NOTHING, blank=True, null=True)
    zone_destination = models.ForeignKey(
        'ZoneEntrepots',
        models.DO_NOTHING,
        related_name='mouvementstocks_zone_destination_set',
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name='mouvement_stocks',
    )
    valide = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'mouvement_stocks'
        db_table_comment = 'Journal des mouvements de stock'


class Producteurs(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    localisation = models.CharField(max_length=150, blank=True, null=True)
    numero_identification = models.CharField(max_length=50, blank=True, null=True)
    type_producteur = models.CharField(max_length=30, blank=True, null=True)
    statut = models.CharField(max_length=20, blank=True, null=True)
    date_inscription = models.DateTimeField(blank=True, null=True)
    observations = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'producteurs'
        db_table_comment = 'Producteurs de noix de cajou'


class Produits(models.Model):
    nom = models.CharField(max_length=100)
    categorie = models.CharField(max_length=100)
    unite = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'produits'
        db_table_comment = 'Catalogue des produits'


class Ventes(models.Model):
    numero_vente = models.CharField(unique=True, max_length=50)
    date_vente = models.DateTimeField(blank=True, null=True)
    quantite_vendue = models.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    mode_paiement = models.CharField(max_length=30, blank=True, null=True)
    client = models.ForeignKey(Clients, models.DO_NOTHING, blank=True, null=True)
    lot = models.ForeignKey(Lots, models.DO_NOTHING)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name='ventes',
    )
    observations = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'ventes'
        db_table_comment = 'Ventes enregistrées'


class ZoneEntrepots(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    capacite = models.DecimalField(max_digits=10, decimal_places=2)
    quantite = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    statut = models.CharField(max_length=30, blank=True, null=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='zone_entrepots_responsable',
    )
    entrepot = models.ForeignKey(Entrepots, models.DO_NOTHING)

    class Meta:
        db_table = 'zone_entrepots'
        unique_together = (('nom', 'entrepot'),)
        db_table_comment = "Zones à l'intérieur des entrepôts"
