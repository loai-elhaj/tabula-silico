# -*- coding: utf-8 -*-
"""
Tabula Silico — Les agents.

Pascor  : l'herbivore, sujet d'etude. Corps + capteurs sectoriels. Son
          comportement est delegue a un CONTROLEUR (interface `agir`), qui sera
          remplace au point 3 par un reseau NEAT a plasticite hebbienne.
Venator : le carnivore, pression de selection. Comportement SCRIPTE, non
          evolutif, non modifiable par la selection.

Compatible Python 3.9.
"""

import math
import numpy as np

import config
from world import (delta_toroidal, deltas_toroidaux, enrouler,
                   normaliser_angle)


# ---------------------------------------------------------------------------
# Controleurs
# ---------------------------------------------------------------------------

class ControleurReactif(object):
    """Controleur reflexe PROVISOIRE, sans apprentissage ni evolution.

    Sert de reference et a valider l'environnement (etape 4 : le pilote). Il
    sera remplace au point 3 par un reseau NEAT. Toute la logique de Pascor
    passe par la meme interface `agir(entrees) -> (rotation, poussee)`, donc
    l'echange est trivial.

    `preference` modelise une STRATEGIE INNEE de discrimination alimentaire :
      - 0 ou 1 : attirance exclusive pour ce type de nourriture, cablee. C'est
        l'equivalent d'une preference alimentaire heritee. Elle gagne si
        l'environnement est stable, et devient letale s'il s'inverse.
      - None   : aucune discrimination, attirance pour les deux types. Mange
        donc ~50 % de toxique — l'etalon du "pas de strategie du tout".
    Aucune de ces variantes n'apprend : c'est justement ce qui les rend utiles
    comme lignes de base.
    """

    def __init__(self, rng, preference=None):
        self.rng = rng
        self.preference = preference
        self._derive = 0.0

    def agir(self, entrees):
        n = config.N_SECTEURS
        capteurs_type_a = entrees[0:n]
        capteurs_type_b = entrees[n:2 * n]
        capteurs_venator = entrees[2 * n:3 * n]

        # Poids d'attirance selon la preference innee
        if self.preference == 0:
            poids_a, poids_b = 1.0, 0.0
        elif self.preference == 1:
            poids_a, poids_b = 0.0, 1.0
        else:
            poids_a, poids_b = 1.0, 1.0

        # Chaque secteur i a une direction relative connue.
        largeur_secteur = config.CHAMP_VISION / n
        directions = [(-config.CHAMP_VISION * 0.5
                       + (i + 0.5) * largeur_secteur) for i in range(n)]

        rotation = 0.0
        for i in range(n):
            rotation += poids_a * capteurs_type_a[i] * directions[i]
            rotation += poids_b * capteurs_type_b[i] * directions[i]
            rotation -= 2.5 * capteurs_venator[i] * directions[i]

        danger = max(capteurs_venator) if n > 0 else 0.0
        attirance = 0.0
        for i in range(n):
            attirance = max(attirance,
                            poids_a * capteurs_type_a[i],
                            poids_b * capteurs_type_b[i])

        # Errance quand rien d'interessant n'est percu : marche aleatoire lissee
        if danger < 0.01 and attirance < 0.01:
            self._derive += self.rng.normal(0.0, 0.12)
            self._derive = max(-1.0, min(1.0, self._derive * 0.92))
            rotation = self._derive

        rotation = max(-1.0, min(1.0, rotation))
        poussee = 1.0 if danger > 0.05 else 0.75

        # Decision d'ingestion. L'agent infere le type de ce qu'il touche a
        # partir de ses canaux sensoriels : un item au contact sature le
        # secteur correspondant de son canal. Une preference innee se traduit
        # donc par "j'avale si le plus proche est de mon type prefere".
        proche_a = max(capteurs_type_a) if n > 0 else 0.0
        proche_b = max(capteurs_type_b) if n > 0 else 0.0
        if self.preference == 0:
            ingestion = 1.0 if proche_a >= proche_b else 0.0
        elif self.preference == 1:
            ingestion = 1.0 if proche_b >= proche_a else 0.0
        else:
            ingestion = 1.0        # aucune discrimination : avale tout

        return rotation, poussee, ingestion


# ---------------------------------------------------------------------------
# Pascor
# ---------------------------------------------------------------------------

class Pascor(object):
    """Herbivore. Doit trouver de la nourriture tout en evitant Venator."""

    __slots__ = ("x", "y", "cap", "energie", "vivant", "age", "controleur",
                 "nourriture_mangee", "distance_parcourue", "cause_mort",
                 "phase_demarche", "trainee", "rencontres_venator",
                 "rencontres_survecues", "mangee_par_tiers", "_derniere_poussee",
                 "nutritifs_manges", "toxiques_manges",
                 "nutritifs_par_tiers", "toxiques_par_tiers")

    def __init__(self, x, y, cap, controleur):
        self.x = x
        self.y = y
        self.cap = cap
        self.controleur = controleur

        self.energie = config.ENERGIE_INITIALE
        self.vivant = True
        self.age = 0
        self.cause_mort = None

        # Metriques individuelles (cf. spec des metriques, section 4)
        self.nourriture_mangee = 0        # total, tous types confondus
        self.nutritifs_manges = 0
        self.toxiques_manges = 0
        self.distance_parcourue = 0.0
        self.rencontres_venator = 0
        self.rencontres_survecues = 0
        # Comptes par tiers de vie : permettent la courbe d'apprentissage
        # intra-vie (1er tiers "naif" vs dernier tiers "rode"). La metrique qui
        # compte pour la discrimination est le RATIO nutritifs / total.
        self.mangee_par_tiers = [0, 0, 0]
        self.nutritifs_par_tiers = [0, 0, 0]
        self.toxiques_par_tiers = [0, 0, 0]

        # Cosmetique
        self.phase_demarche = 0.0
        self.trainee = []
        self._derniere_poussee = 0.0

    # -- Perception ---------------------------------------------------------

    def percevoir(self, monde, venators):
        """Renvoie le vecteur d'entrees du controleur.

        Format : [type A x N_SECTEURS, type B x N_SECTEURS,
                  venator x N_SECTEURS, energie]
        Chaque capteur vaut 1.0 si un objet est colle a l'agent, 0.0 si rien
        n'est percu dans ce secteur.

        Les deux types de nourriture ont des canaux SEPARES, mais rien dans la
        perception n'indique lequel est comestible : c'est ce que l'agent doit
        soit avoir herite (inne), soit decouvrir en goutant (acquis).
        """
        n = config.N_SECTEURS
        entrees = [0.0] * (3 * n + 1)

        # -- canaux nourriture, un par type
        for type_item in range(config.N_TYPES_NOURRITURE):
            positions = monde.positions_actives_du_type(type_item)
            if len(positions) > 0:
                self._remplir_secteurs(entrees, type_item * n, positions, monde)

        # -- canal Venator
        if venators:
            pos_v = np.array([[v.x, v.y] for v in venators], dtype=np.float64)
            self._remplir_secteurs(entrees, config.N_TYPES_NOURRITURE * n,
                                   pos_v, monde)

        # -- energie normalisee
        entrees[3 * n] = max(0.0, min(1.0, self.energie / config.ENERGIE_MAX))
        return entrees

    def _remplir_secteurs(self, entrees, decalage, positions, monde):
        """Remplit N_SECTEURS entrees a partir d'un nuage de positions."""
        d = deltas_toroidaux(self.x, self.y, positions,
                             monde.largeur, monde.hauteur)
        distances = np.sqrt(d[:, 0] ** 2 + d[:, 1] ** 2)
        dans_portee = distances < config.PORTEE_VISION
        if not dans_portee.any():
            return

        d = d[dans_portee]
        distances = distances[dans_portee]

        # Relevement relatif au cap de l'agent
        releves = np.arctan2(d[:, 1], d[:, 0]) - self.cap
        releves = (releves + math.pi) % (2.0 * math.pi) - math.pi

        demi_champ = config.CHAMP_VISION * 0.5
        visible = np.abs(releves) <= demi_champ
        if not visible.any():
            return

        releves = releves[visible]
        distances = distances[visible]

        largeur_secteur = config.CHAMP_VISION / config.N_SECTEURS
        indices = ((releves + demi_champ) / largeur_secteur).astype(np.int32)
        np.clip(indices, 0, config.N_SECTEURS - 1, out=indices)

        for s in range(config.N_SECTEURS):
            m = indices == s
            if m.any():
                d_min = float(distances[m].min())
                entrees[decalage + s] = 1.0 - d_min / config.PORTEE_VISION

    # -- Action -------------------------------------------------------------

    def avancer(self, monde, venators, entrees=None):
        """Un pas de temps : perception -> decision -> deplacement -> energie.

        `entrees` permet de fournir un vecteur sensoriel deja calcule (par
        perception.percevoir_tous, qui traite tous les agents en une passe).
        Si None, l'agent calcule sa propre perception — plus lent, conserve
        pour les usages ponctuels et les tests.
        """
        if not self.vivant:
            return None, 0.0

        if entrees is None:
            entrees = self.percevoir(monde, venators)
        sorties = self.controleur.agir(entrees)
        rotation, poussee, ingestion = sorties

        rotation = max(-1.0, min(1.0, float(rotation)))
        poussee = max(0.0, min(1.0, float(poussee)))
        ingestion = max(0.0, min(1.0, float(ingestion)))
        self._derniere_poussee = poussee

        # Deplacement
        self.cap = normaliser_angle(self.cap + rotation * config.ROTATION_MAX_PASCOR)
        vitesse = poussee * config.VITESSE_MAX_PASCOR
        self.x, self.y = enrouler(self.x + math.cos(self.cap) * vitesse,
                                  self.y + math.sin(self.cap) * vitesse,
                                  monde.largeur, monde.hauteur)
        self.distance_parcourue += vitesse
        self.phase_demarche += vitesse * 0.35

        if config.AFFICHER_TRAINEES:
            self.trainee.append((self.x, self.y))
            if len(self.trainee) > config.LONGUEUR_TRAINEE:
                self.trainee.pop(0)

        # Energie
        self.energie -= config.COUT_BASAL + config.COUT_MOUVEMENT * poussee

        # Alimentation, conditionnee a la DECISION d'ingerer. delta est
        # POSITIF (nutritif) ou NEGATIF (toxique). Le signal de recompense
        # necessaire a la plasticite hebbienne modulee (point 3) est
        # exactement ce delta : il n'y a rien d'artificiel a inventer, le
        # renforcement tombe du dispositif ecologique lui-meme.
        idx_item, delta = None, 0.0
        if ingestion >= config.SEUIL_INGESTION:
            delta, idx_item, type_item = monde.consommer_le_plus_proche(
                self.x, self.y, config.RAYON_PASCOR)
        if idx_item is not None:
            self.energie = min(config.ENERGIE_MAX, self.energie + delta)
            self.nourriture_mangee += 1
            tiers = self._tiers_courant()
            self.mangee_par_tiers[tiers] += 1
            if delta > 0.0:
                self.nutritifs_manges += 1
                self.nutritifs_par_tiers[tiers] += 1
            else:
                self.toxiques_manges += 1
                self.toxiques_par_tiers[tiers] += 1

            # Signal de renforcement transmis au cerveau. C'est ici que
            # l'ecologie et l'apprentissage se rejoignent : le troisieme
            # facteur de la regle hebbienne (le neuromodulateur) est
            # litteralement le gain ou la perte d'energie alimentaire.
            recompenser = getattr(self.controleur, "recompenser", None)
            if recompenser is not None:
                recompenser(delta)

        # Rappel lent des poids vers leurs valeurs innees
        homeostasie = getattr(self.controleur, "decroissance_homeostatique",
                              None)
        if homeostasie is not None:
            homeostasie()

        self.age += 1

        # Mort
        if self.energie <= 0.0:
            self.vivant = False
            self.cause_mort = "famine"
        elif self.age >= config.DUREE_VIE_MAX:
            self.vivant = False
            self.cause_mort = "vieillesse"

        return idx_item, delta

    def _tiers_courant(self):
        """Index du tiers de vie courant (0, 1 ou 2)."""
        t = int(3 * self.age / config.DUREE_VIE_MAX)
        return max(0, min(2, t))

    def tuer(self):
        self.vivant = False
        self.cause_mort = "predation"


# ---------------------------------------------------------------------------
# Venator
# ---------------------------------------------------------------------------

class Venator(object):
    """Carnivore scripte. N'evolue pas, n'apprend pas.

    Trois etats : patrouille (errance), poursuite (fonce sur la proie la plus
    proche detectee), satiete (inactif un moment apres une capture).
    """

    __slots__ = ("x", "y", "cap", "rng", "etat", "ticks_poursuite",
                 "ticks_satiete", "captures", "cible", "phase_demarche")

    def __init__(self, x, y, cap, rng):
        self.x = x
        self.y = y
        self.cap = cap
        self.rng = rng
        self.etat = "patrouille"
        self.ticks_poursuite = 0
        self.ticks_satiete = 0
        self.captures = 0
        self.cible = None
        self.phase_demarche = 0.0

    def avancer(self, monde, pascors):
        """Un pas de temps. Renvoie le Pascor capture, ou None."""
        # -- Satiete : ne chasse pas, derive doucement
        if self.ticks_satiete > 0:
            self.ticks_satiete -= 1
            self.etat = "satiete"
            self._patrouiller(monde, vitesse=config.VITESSE_PATROUILLE * 0.5)
            return None

        vivants = [p for p in pascors if p.vivant]

        # -- Recherche d'une cible
        cible = None
        if vivants:
            meilleure_d2 = config.PORTEE_DETECTION_VENATOR ** 2
            for p in vivants:
                dx, dy = delta_toroidal(self.x, self.y, p.x, p.y,
                                        monde.largeur, monde.hauteur)
                d2 = dx * dx + dy * dy
                if d2 < meilleure_d2:
                    meilleure_d2 = d2
                    cible = p

        if cible is None:
            self.etat = "patrouille"
            self.ticks_poursuite = 0
            self.cible = None
            self._patrouiller(monde)
            return None

        # -- Poursuite
        nouvelle_poursuite = (self.etat != "poursuite") or (self.cible is not cible)
        if self.etat != "poursuite":
            self.etat = "poursuite"
            self.ticks_poursuite = 0
        self.cible = cible
        self.ticks_poursuite += 1

        # La proie enregistre la rencontre. On ne compte qu'une rencontre par
        # poursuite DISTINCTE : compter chaque tick de poursuite gonflerait
        # artificiellement le denominateur du taux d'evitement (une poursuite de
        # 180 ticks compterait pour 180 rencontres).
        if nouvelle_poursuite:
            cible.rencontres_venator += 1

        if self.ticks_poursuite > config.DUREE_POURSUITE_MAX:
            self.etat = "patrouille"
            self.ticks_poursuite = 0
            self.cible = None
            self._patrouiller(monde)
            return None

        dx, dy = delta_toroidal(self.x, self.y, cible.x, cible.y,
                                monde.largeur, monde.hauteur)
        cap_voulu = math.atan2(dy, dx)
        self._tourner_vers(cap_voulu, config.ROTATION_MAX_VENATOR)
        self._deplacer(monde, config.VITESSE_POURSUITE)

        # -- Capture ?
        dx, dy = delta_toroidal(self.x, self.y, cible.x, cible.y,
                                monde.largeur, monde.hauteur)
        if dx * dx + dy * dy <= config.RAYON_CAPTURE ** 2:
            cible.tuer()
            self.captures += 1
            self.ticks_satiete = config.SATIETE_APRES_CAPTURE
            self.etat = "satiete"
            self.ticks_poursuite = 0
            self.cible = None
            return cible

        return None

    # -- Deplacement --------------------------------------------------------

    def _patrouiller(self, monde, vitesse=None):
        self.cap = normaliser_angle(
            self.cap + self.rng.normal(0.0, config.DERIVE_PATROUILLE))
        self._deplacer(monde, vitesse if vitesse is not None
                       else config.VITESSE_PATROUILLE)

    def _tourner_vers(self, cap_voulu, rotation_max):
        ecart = normaliser_angle(cap_voulu - self.cap)
        ecart = max(-rotation_max, min(rotation_max, ecart))
        self.cap = normaliser_angle(self.cap + ecart)

    def _deplacer(self, monde, vitesse):
        self.x, self.y = enrouler(self.x + math.cos(self.cap) * vitesse,
                                  self.y + math.sin(self.cap) * vitesse,
                                  monde.largeur, monde.hauteur)
        self.phase_demarche += vitesse * 0.3
