# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class Clients(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True, null=True)
    entreprise = models.CharField(max_length=150, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=150, blank=True, null=True)
    adresse = models.CharField(max_length=200, blank=True, null=True)
    date_inscription = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'clients'
        db_table_comment = 'Clients acheteurs'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class Entrepots(models.Model):
    nom = models.CharField(max_length=100)
    localisation = models.CharField(max_length=150, blank=True, null=True)
    capacite_max = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_critique = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_disponible = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    statut = models.CharField(max_length=30, blank=True, null=True)
    responsable_id = models.IntegerField(blank=True, null=True)
    date_creation = models.DateTimeField(blank=True, null=True)
    date_maj = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'entrepots'
        db_table_comment = 'Entrepôts de stockage'


class HistoriqueTracabilites(models.Model):
    date_action = models.DateTimeField(blank=True, null=True)
    type_action = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    lot = models.ForeignKey('Lots', models.DO_NOTHING, blank=True, null=True)
    user_id = models.IntegerField()
    ancienne_valeur = models.JSONField(blank=True, null=True)
    nouvelle_valeur = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
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
    user_id = models.IntegerField()
    observations = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lots'
        db_table_comment = 'Lots de produits avec traçabilité'


class MouvementStocks(models.Model):
    date_mouvement = models.DateTimeField(blank=True, null=True)
    type_mouvement = models.CharField(max_length=20)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    motif = models.CharField(max_length=200, blank=True, null=True)
    lot = models.ForeignKey(Lots, models.DO_NOTHING)
    zone_origine = models.ForeignKey('ZoneEntrepots', models.DO_NOTHING, blank=True, null=True)
    zone_destination = models.ForeignKey('ZoneEntrepots', models.DO_NOTHING, related_name='mouvementstocks_zone_destination_set', blank=True, null=True)
    user_id = models.IntegerField()
    valide = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
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
        managed = False
        db_table = 'producteurs'
        db_table_comment = 'Producteurs de noix de cajou'


class Produits(models.Model):
    nom = models.CharField(max_length=100)
    categorie = models.CharField(max_length=100)
    unite = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
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
    user_id = models.IntegerField()
    observations = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ventes'
        db_table_comment = 'Ventes enregistrées'


class ZoneEntrepots(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    capacite = models.DecimalField(max_digits=10, decimal_places=2)
    quantite = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    statut = models.CharField(max_length=30, blank=True, null=True)
    responsable_id = models.IntegerField(blank=True, null=True)
    entrepot = models.ForeignKey(Entrepots, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'zone_entrepots'
        unique_together = (('nom', 'entrepot'),)
        db_table_comment = "Zones à l'intérieur des entrepôts"
