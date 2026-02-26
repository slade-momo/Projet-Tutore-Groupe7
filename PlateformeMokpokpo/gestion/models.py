from django.db import models
from django.conf import settings


# ==================== CHOICES ====================

CLIENT_TYPE_CHOICES = [
    ('REGULIER', 'Régulier'),
    ('VIP', 'VIP'),
    ('OCCASIONNEL', 'Occasionnel'),
]

PRODUCTEUR_TYPE_CHOICES = [
    ('INDIVIDUEL', 'Individuel'),
    ('COOPERATIVE', 'Coopérative'),
    ('ENTREPRISE', 'Entreprise'),
]

PRODUCTEUR_STATUT_CHOICES = [
    ('ACTIF', 'Actif'),
    ('INACTIF', 'Inactif'),
    ('SUSPENDU', 'Suspendu'),
]

ENTREPOT_STATUT_CHOICES = [
    ('OPERATIONNEL', 'Opérationnel'),
    ('EN_ALERTE', 'En alerte'),
    ('CRITIQUE', 'Critique'),
    ('EN_MAINTENANCE', 'En maintenance'),
]

ZONE_STATUT_CHOICES = [
    ('DISPONIBLE', 'Disponible'),
    ('PLEINE', 'Pleine'),
    ('EN_MAINTENANCE', 'En maintenance'),
    ('FERMEE', 'Fermée'),
]

LOT_ETAT_CHOICES = [
    ('EN_STOCK', 'En stock'),
    ('PARTIELLEMENT_SORTI', 'Partiellement sorti'),
    ('EPUISE', 'Épuisé'),
    ('RESERVE', 'Réservé'),
]

LOT_QUALITE_CHOICES = [
    ('PREMIUM', 'Premium'),
    ('STANDARD', 'Standard'),
    ('ECONOMIQUE', 'Économique'),
]

MOUVEMENT_TYPE_CHOICES = [
    ('ENTREE', 'Entrée'),
    ('SORTIE', 'Sortie'),
    ('TRANSFERT', 'Transfert'),
    ('AJUSTEMENT', 'Ajustement'),
    ('RESERVATION', 'Réservation'),
    ('LIBERATION', 'Libération'),
]

VENTE_MODE_PAIEMENT_CHOICES = [
    ('ESPECES', 'Espèces'),
    ('CHEQUE', 'Chèque'),
    ('VIREMENT', 'Virement'),
    ('MOBILE_MONEY', 'Mobile Money'),
]

VENTE_TYPE_CHOICES = [
    ('IMMEDIATE', 'Immédiate'),
    ('SUR_COMMANDE', 'Sur commande'),
    ('URGENTE', 'Urgente'),
]

COMMANDE_STATUT_CHOICES = [
    ('EN_ATTENTE', 'En attente'),
    ('CONFIRMEE', 'Confirmée'),
    ('RESERVEE', 'Réservée'),
    ('EN_ATTENTE_REAPPRO', 'En attente réappro.'),
    ('LIVREE', 'Livrée'),
    ('ANNULEE', 'Annulée'),
]

COMMANDE_PRIORITE_CHOICES = [
    ('NORMALE', 'Normale'),
    ('URGENTE', 'Urgente'),
]

AFFECTATION_LOT_STATUT_CHOICES = [
    ('RESERVE', 'Réservé'),
    ('SERVI', 'Servi'),
    ('ANNULE', 'Annulé'),
]

ALERTE_STOCK_STATUT_CHOICES = [
    ('ACTIVE', 'Active'),
    ('TRAITEE', 'Traitée'),
    ('IGNOREE', 'Ignorée'),
]

DEMANDE_ACHAT_STATUT_CHOICES = [
    ('BROUILLON', 'Brouillon'),
    ('ENVOYEE', 'Envoyée'),
    ('VALIDEE', 'Validée'),
    ('COMMANDEE', 'Commandée'),
    ('RECEPTIONNEE', 'Réceptionnée'),
    ('ANNULEE', 'Annulée'),
]

DEMANDE_ACHAT_PRIORITE_CHOICES = [
    ('NORMAL', 'Normal'),
    ('URGENT', 'Urgent'),
]

LIGNE_COMMANDE_STATUT_CHOICES = [
    ('EN_ATTENTE', 'En attente'),
    ('RESERVEE', 'Réservée'),
    ('SERVIE', 'Servie'),
    ('EN_ATTENTE_REAPPRO', 'En attente réappro.'),
]

PREPARATION_STATUT_CHOICES = [
    ('EN_ATTENTE', 'En attente'),
    ('EN_COURS', 'En cours'),
    ('TERMINEE', 'Terminée'),
    ('ANNULEE', 'Annulée'),
]

VENTE_IMMEDIATE_TYPE_CHOICES = [
    ('TOTALE', 'Totale'),
    ('PARTIELLE', 'Partielle'),
    ('URGENTE', 'Urgente'),
]


# ==================== MODELS ====================

class Client(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True, null=True)
    entreprise = models.CharField(max_length=150, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=150, blank=True, null=True)
    adresse = models.CharField(max_length=200, blank=True, null=True)
    type_client = models.CharField(
        max_length=30, choices=CLIENT_TYPE_CHOICES, blank=True, null=True
    )
    date_inscription = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'client'

    def __str__(self):
        return f"{self.nom} {self.prenom or ''}".strip()


class Produit(models.Model):
    nom = models.CharField(max_length=100)
    categorie = models.CharField(max_length=100)
    unite = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    prix_unitaire = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    stock_physique = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    stock_reserve = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    stock_tampon_comptoir = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    seuil_alerte = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    quantite_optimale_commande = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    stock_disponible = models.GeneratedField(
        expression=models.F('stock_physique') - models.F('stock_reserve') - models.F('stock_tampon_comptoir'),
        output_field=models.DecimalField(max_digits=10, decimal_places=2),
        db_persist=True,
    )
    date_dernier_reappro = models.DateTimeField(blank=True, null=True)
    date_creation = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'produit'

    def __str__(self):
        return self.nom


class Producteur(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    localisation = models.CharField(max_length=150, blank=True, null=True)
    numero_identification = models.CharField(max_length=50, blank=True, null=True)
    type_producteur = models.CharField(
        max_length=30, choices=PRODUCTEUR_TYPE_CHOICES, blank=True, null=True
    )
    statut = models.CharField(
        max_length=20, choices=PRODUCTEUR_STATUT_CHOICES, blank=True, null=True
    )
    date_inscription = models.DateTimeField(blank=True, null=True)
    observations = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'producteur'

    def __str__(self):
        return f"{self.nom} {self.prenom or ''}".strip()


class Entrepot(models.Model):
    nom = models.CharField(max_length=100)
    localisation = models.CharField(max_length=150, blank=True, null=True)
    capacite_max = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_critique = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_disponible = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    statut = models.CharField(
        max_length=30, choices=ENTREPOT_STATUT_CHOICES, blank=True, null=True
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='responsable_id', blank=True, null=True,
        related_name='entrepots_geres'
    )
    date_creation = models.DateTimeField(blank=True, null=True)
    date_maj = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'entrepot'

    def __str__(self):
        return self.nom


class ZoneEntrepot(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    capacite = models.DecimalField(max_digits=10, decimal_places=2)
    quantite = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    statut = models.CharField(
        max_length=30, choices=ZONE_STATUT_CHOICES, blank=True, null=True
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='responsable_id', blank=True, null=True,
        related_name='zones_gerees'
    )
    entrepot = models.ForeignKey(Entrepot, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'zone_entrepot'
        unique_together = (('nom', 'entrepot'),)

    def __str__(self):
        return f"{self.nom} ({self.entrepot.nom})"


class Lot(models.Model):
    code_lot = models.CharField(unique=True, max_length=50)
    quantite_initiale = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_restante = models.DecimalField(max_digits=10, decimal_places=2)
    qualite = models.CharField(
        max_length=50, choices=LOT_QUALITE_CHOICES, blank=True, null=True
    )
    etat = models.CharField(
        max_length=30, choices=LOT_ETAT_CHOICES, blank=True, null=True
    )
    date_reception = models.DateField()
    date_expiration = models.DateField(blank=True, null=True)
    produit = models.ForeignKey(Produit, models.DO_NOTHING)
    producteur = models.ForeignKey(
        Producteur, models.DO_NOTHING, blank=True, null=True
    )
    zone = models.ForeignKey(ZoneEntrepot, models.DO_NOTHING)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id', related_name='lots'
    )
    quantite_reservee = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    observations = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lot'

    def __str__(self):
        return self.code_lot


class Commande(models.Model):
    numero_commande = models.CharField(unique=True, max_length=50)
    date_commande = models.DateTimeField(blank=True, null=True)
    date_livraison_souhaitee = models.DateField(blank=True, null=True)
    date_livraison_effective = models.DateField(blank=True, null=True)
    statut = models.CharField(
        max_length=30, choices=COMMANDE_STATUT_CHOICES, blank=True, null=True
    )
    client = models.ForeignKey(Client, models.DO_NOTHING)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id', related_name='commandes'
    )
    quantite_demandee = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_reservee = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    quantite_servie = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    reste_a_livrer = models.GeneratedField(
        expression=models.F('quantite_demandee') - models.F('quantite_servie'),
        output_field=models.DecimalField(max_digits=10, decimal_places=2),
        db_persist=True,
    )
    priorite = models.CharField(
        max_length=20, choices=COMMANDE_PRIORITE_CHOICES, blank=True, null=True
    )
    observations = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'commande'

    def __str__(self):
        return self.numero_commande


class MouvementStock(models.Model):
    date_mouvement = models.DateTimeField(blank=True, null=True)
    type_mouvement = models.CharField(
        max_length=20, choices=MOUVEMENT_TYPE_CHOICES
    )
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    motif = models.CharField(max_length=200, blank=True, null=True)
    lot = models.ForeignKey(Lot, models.DO_NOTHING)
    zone_origine = models.ForeignKey(
        ZoneEntrepot, models.DO_NOTHING,
        blank=True, null=True, related_name='mouvements_origine'
    )
    zone_destination = models.ForeignKey(
        ZoneEntrepot, models.DO_NOTHING,
        blank=True, null=True, related_name='mouvements_destination'
    )
    commande = models.ForeignKey(
        Commande, models.DO_NOTHING, blank=True, null=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id', related_name='mouvements'
    )
    valide = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mouvement_stock'

    def __str__(self):
        return f"{self.type_mouvement} - {self.lot.code_lot} ({self.quantite})"


class Vente(models.Model):
    numero_vente = models.CharField(unique=True, max_length=50)
    date_vente = models.DateTimeField(blank=True, null=True)
    quantite_vendue = models.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant_total = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    mode_paiement = models.CharField(
        max_length=30, choices=VENTE_MODE_PAIEMENT_CHOICES, blank=True, null=True
    )
    client = models.ForeignKey(
        Client, models.DO_NOTHING, blank=True, null=True
    )
    lot = models.ForeignKey(Lot, models.DO_NOTHING)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id', related_name='ventes'
    )
    commande = models.ForeignKey(
        Commande, models.DO_NOTHING, blank=True, null=True
    )
    type_vente = models.CharField(
        max_length=20, choices=VENTE_TYPE_CHOICES, blank=True, null=True
    )
    observations = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'vente'

    def __str__(self):
        return self.numero_vente


class HistoriqueTracabilite(models.Model):
    date_action = models.DateTimeField(blank=True, null=True)
    type_action = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    lot = models.ForeignKey(Lot, models.DO_NOTHING, blank=True, null=True)
    commande = models.ForeignKey(
        Commande, models.DO_NOTHING, blank=True, null=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id', related_name='historiques'
    )
    ancienne_valeur = models.JSONField(blank=True, null=True)
    nouvelle_valeur = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'historique_tracabilite'

    def __str__(self):
        return f"{self.type_action} - {self.date_action}"


class AffectationLot(models.Model):
    commande = models.ForeignKey(Commande, models.DO_NOTHING)
    lot = models.ForeignKey(Lot, models.DO_NOTHING)
    quantite_affectee = models.DecimalField(max_digits=10, decimal_places=2)
    date_affectation = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id', related_name='affectations_lot'
    )
    statut = models.CharField(
        max_length=30, choices=AFFECTATION_LOT_STATUT_CHOICES,
        blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = 'affectation_lot'
        unique_together = (('commande', 'lot'),)

    def __str__(self):
        return f"Affectation {self.lot} → {self.commande}"


class AlerteStock(models.Model):
    produit = models.ForeignKey(Produit, models.DO_NOTHING)
    date_alerte = models.DateTimeField(blank=True, null=True)
    stock_actuel = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_alerte = models.DecimalField(max_digits=10, decimal_places=2)
    statut = models.CharField(
        max_length=30, choices=ALERTE_STOCK_STATUT_CHOICES,
        blank=True, null=True
    )
    demande_achat_generee = models.BooleanField(blank=True, null=True)
    date_traitement = models.DateTimeField(blank=True, null=True)
    user_traitement = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id_traitement', blank=True, null=True,
        related_name='alertes_traitees'
    )
    observations = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'alerte_stock'

    def __str__(self):
        return f"Alerte {self.produit} - {self.statut}"


class DemandeAchat(models.Model):
    numero_da = models.CharField(unique=True, max_length=50)
    date_creation = models.DateTimeField(blank=True, null=True)
    produit = models.ForeignKey(Produit, models.DO_NOTHING)
    stock_actuel = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_alerte = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_a_commander = models.DecimalField(max_digits=10, decimal_places=2)
    priorite = models.CharField(
        max_length=20, choices=DEMANDE_ACHAT_PRIORITE_CHOICES,
        blank=True, null=True
    )
    statut = models.CharField(
        max_length=30, choices=DEMANDE_ACHAT_STATUT_CHOICES,
        blank=True, null=True
    )
    alerte = models.ForeignKey(
        AlerteStock, models.DO_NOTHING, blank=True, null=True
    )
    user_createur = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id_createur', related_name='demandes_creees'
    )
    user_valideur = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id_valideur', blank=True, null=True,
        related_name='demandes_validees'
    )
    date_validation = models.DateTimeField(blank=True, null=True)
    observations = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'demande_achat'

    def __str__(self):
        return self.numero_da


class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, models.DO_NOTHING)
    produit = models.ForeignKey(Produit, models.DO_NOTHING)
    quantite_demandee = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_reservee = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    quantite_servie = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    reste_a_livrer = models.GeneratedField(
        expression=models.F('quantite_demandee') - models.F('quantite_servie'),
        output_field=models.DecimalField(max_digits=10, decimal_places=2),
        db_persist=True,
    )
    prix_unitaire = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    statut_ligne = models.CharField(
        max_length=30, choices=LIGNE_COMMANDE_STATUT_CHOICES,
        blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = 'ligne_commande'

    def __str__(self):
        return f"Ligne {self.commande} - {self.produit}"


class PreparationCommande(models.Model):
    commande = models.ForeignKey(Commande, models.DO_NOTHING)
    date_debut = models.DateTimeField(blank=True, null=True)
    date_fin = models.DateTimeField(blank=True, null=True)
    prepareur = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='prepareur_id', blank=True, null=True,
        related_name='preparations'
    )
    zone = models.ForeignKey(ZoneEntrepot, models.DO_NOTHING)
    statut = models.CharField(
        max_length=30, choices=PREPARATION_STATUT_CHOICES,
        blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = 'preparation_commande'

    def __str__(self):
        return f"Préparation {self.commande} - {self.statut}"


class VenteImmediate(models.Model):
    numero_vente = models.CharField(unique=True, max_length=50)
    date_vente = models.DateTimeField(blank=True, null=True)
    produit = models.ForeignKey(Produit, models.DO_NOTHING)
    quantite_demandee = models.DecimalField(max_digits=10, decimal_places=2)
    quantite_servie_maintenant = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    type_vente = models.CharField(
        max_length=30, choices=VENTE_IMMEDIATE_TYPE_CHOICES,
        blank=True, null=True
    )
    commande_associee = models.ForeignKey(
        Commande, models.DO_NOTHING, blank=True, null=True
    )
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    prix_majore_urgence = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        db_column='prix_majoré_urgence',
    )
    montant_total = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    client = models.ForeignKey(
        Client, models.DO_NOTHING, blank=True, null=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.DO_NOTHING,
        db_column='user_id', related_name='ventes_immediates'
    )

    class Meta:
        managed = False
        db_table = 'vente_immediate'

    def __str__(self):
        return self.numero_vente
