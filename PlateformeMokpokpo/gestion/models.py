from django.db import models
from django.conf import settings


class Clients(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True, null=True)
    entreprise = models.CharField(max_length=150, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=150, blank=True, null=True)
    adresse = models.CharField(max_length=200, blank=True, null=True)
    date_inscription = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'clients'
        db_table_comment = 'Clients acheteurs'

    def __str__(self):
        return f"{self.nom} {self.prenom or ''}".strip()


class Entrepots(models.Model):
    STATUT_CHOICES = [
        ('ACTIF', 'Actif'),
        ('INACTIF', 'Inactif'),
    ]

    nom = models.CharField(max_length=100)
    localisation = models.CharField(max_length=150, blank=True, null=True)
    capacite_max = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_critique = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_disponible = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, blank=True, null=True)
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
    
    def __str__(self):
        return self.nom


class HistoriqueTracabilites(models.Model):
    date_action = models.DateTimeField(blank=True, null=True)
    type_action = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    lot = models.ForeignKey('Lots', on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='historique_tracabilites',
    )
    ancienne_valeur = models.JSONField(blank=True, null=True)
    nouvelle_valeur = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'historique_tracabilites'
        db_table_comment = "Historique d'audit et traçabilité"

    def __str__(self):
        return f"{self.type_action} - {self.date_action.strftime('%Y-%m-%d %H:%M:%S')}"

class Lots(models.Model):
    ETATS_CHOICES = [
        ('EN_STOCK', 'En stock'),
        ('PARTIELLEMENT_SORTI', 'Partiellement sorti'),
        ('EPUISE', 'Épuisé'),
    ]
    QUALITE_CHOICES = [
        ('PREMIUM', 'Premium'),
        ('STANDARD', 'Standard'),
        ('ECONOMIQUE', 'Économique'),
    ]

    code_lot = models.CharField(unique=True, max_length=50)
    quantite_initiale = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_restante = models.DecimalField(max_digits=10, decimal_places=2)
    qualite = models.CharField(max_length=50, choices=QUALITE_CHOICES, blank=True, null=True)
    etat = models.CharField(
        max_length=30,
        choices=ETATS_CHOICES,
        blank=True,
        null=True
    )
    date_reception = models.DateField()
    date_expiration = models.DateField(blank=True, null=True)
    produit = models.ForeignKey('Produits', on_delete=models.PROTECT)
    producteur = models.ForeignKey('Producteurs', on_delete=models.SET_NULL, blank=True, null=True)
    zone = models.ForeignKey('ZoneEntrepots', on_delete=models.PROTECT)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='lots',
    )
    observations = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'lots'
        db_table_comment = 'Lots de produits avec traçabilité'
    
    def __str__(self):
        return f"{self.code_lot} - {self.produit.nom}"
    


class MouvementStocks(models.Model):
    TYPE_MOUVEMENT_CHOICES = [
        ('ENTREE', 'Entrée'),
        ('SORTIE', 'Sortie'),
        ('TRANSFERT', 'Transfert'),
        ('AJUSTEMENT', 'Ajustement'),
    ]

    date_mouvement = models.DateTimeField(blank=True, null=True)
    type_mouvement = models.CharField(max_length=20, choices=TYPE_MOUVEMENT_CHOICES)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    motif = models.CharField(max_length=200, blank=True, null=True)
    lot = models.ForeignKey(Lots, on_delete=models.CASCADE)
    zone_origine = models.ForeignKey('ZoneEntrepots', on_delete=models.SET_NULL, blank=True, null=True)
    zone_destination = models.ForeignKey(
        'ZoneEntrepots',
        on_delete=models.SET_NULL,
        related_name='mouvementstocks_zone_destination_set',
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='mouvement_stocks',
    )
    valide = models.BooleanField(blank=True, null=True)

    class Meta:
        db_table = 'mouvement_stocks'
        db_table_comment = 'Journal des mouvements de stock'

    def __str__(self):
        return f"{self.type_mouvement} - {self.lot.code_lot} - {self.quantite}"


class Producteurs(models.Model):
    TYPE_PRODUCTEUR_CHOICES = [
        ('INDIVIDUEL', 'Individuel'),
        ('COOPERATIVE', 'Coopérative'),
        ('ENTREPRISE', 'Entreprise'),
    ]
    STATUT_CHOICES = [
        ('ACTIF', 'Actif'),
        ('INACTIF', 'Inactif'),
    ]

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    localisation = models.CharField(max_length=150, blank=True, null=True)
    numero_identification = models.CharField(max_length=50, blank=True, null=True)
    type_producteur = models.CharField(max_length=30, choices=TYPE_PRODUCTEUR_CHOICES, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, blank=True, null=True)
    date_inscription = models.DateTimeField(blank=True, null=True)
    observations = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'producteurs'
        db_table_comment = 'Producteurs de noix de cajou'

    def __str__(self):
        return f"{self.nom} {self.prenom or ''}".strip()


class Produits(models.Model):
    nom = models.CharField(max_length=100)
    categorie = models.CharField(max_length=100)
    unite = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'produits'
        db_table_comment = 'Catalogue des produits'
    
    def __str__(self):
        return f"{self.nom} ({self.categorie})"


class Ventes(models.Model):
    MODE_PAIEMENT_CHOICES = [
        ('ESPECES', 'Espèces'),
        ('CHEQUE', 'Chèque'),
        ('VIREMENT', 'Virement'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]

    numero_vente = models.CharField(unique=True, max_length=50)
    date_vente = models.DateTimeField(blank=True, null=True)
    quantite_vendue = models.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    mode_paiement = models.CharField(max_length=30, choices=MODE_PAIEMENT_CHOICES, blank=True, null=True)
    client = models.ForeignKey(Clients, on_delete=models.SET_NULL, blank=True, null=True)
    lot = models.ForeignKey(Lots, on_delete=models.PROTECT)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ventes',
    )
    observations = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'ventes'
        db_table_comment = 'Ventes enregistrées'
    
    def __str__(self):
        return f"{self.numero_vente} - {self.lot}"


class ZoneEntrepots(models.Model):
    STATUT_CHOICES = [
        ('ACTIF', 'Actif'),
        ('INACTIF', 'Inactif'),
    ]

    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    capacite = models.DecimalField(max_digits=10, decimal_places=2)
    quantite = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, blank=True, null=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='zone_entrepots_responsable',
    )
    entrepot = models.ForeignKey(Entrepots, on_delete=models.CASCADE)

    class Meta:
        db_table = 'zone_entrepots'
        unique_together = (('nom', 'entrepot'),)
        db_table_comment = "Zones à l'intérieur des entrepôts"
    
    def __str__(self):
        return f"{self.nom} ({self.entrepot.nom})"
