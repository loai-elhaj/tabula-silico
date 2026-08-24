# -*- coding: utf-8 -*-
"""
Tabula Silico — Le monde : geometrie toroidale, nourriture, volatilite.

Le monde porte la variable independante centrale du projet : T_env, la
volatilite environnementale. Les centres des patchs de nourriture sont
retires tous les T_env generations. L'environnement reste FIXE pendant la vie
d'un individu — seule la volatilite inter-generationnelle varie, sinon
l'apprentissage individuel n'aurait plus rien de stable a apprendre.

Compatible Python 3.9.
"""

import math
import numpy as np

import config


# ---------------------------------------------------------------------------
# Geometrie toroidale
# ---------------------------------------------------------------------------

def delta_toroidal(x1, y1, x2, y2, largeur=config.LARGEUR, hauteur=config.HAUTEUR):
    """Vecteur le plus court de (x1,y1) vers (x2,y2) dans un espace toroidal."""
    dx = x2 - x1
    dy = y2 - y1
    if config.TOROIDAL:
        if dx > largeur * 0.5:
            dx -= largeur
        elif dx < -largeur * 0.5:
            dx += largeur
        if dy > hauteur * 0.5:
            dy -= hauteur
        elif dy < -hauteur * 0.5:
            dy += hauteur
    return dx, dy


def deltas_toroidaux(x, y, positions, largeur=config.LARGEUR, hauteur=config.HAUTEUR):
    """Version vectorisee : vecteurs de (x,y) vers un tableau de positions (n,2)."""
    d = positions - np.array([x, y], dtype=np.float64)
    if config.TOROIDAL:
        d[:, 0] -= largeur * np.round(d[:, 0] / largeur)
        d[:, 1] -= hauteur * np.round(d[:, 1] / hauteur)
    return d


def enrouler(x, y, largeur=config.LARGEUR, hauteur=config.HAUTEUR):
    """Ramene une position dans l'arene (rebouclage toroidal)."""
    if config.TOROIDAL:
        return x % largeur, y % hauteur
    return (min(max(x, 0.0), largeur), min(max(y, 0.0), hauteur))


def normaliser_angle(a):
    """Ramene un angle dans [-pi, pi]."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


# ---------------------------------------------------------------------------
# Le monde
# ---------------------------------------------------------------------------

class Monde(object):
    """Arene 2D toroidale contenant des patchs de nourriture renouvelable.

    La distribution spatiale de la nourriture (les centres de patchs) est
    l'information que les Pascor peuvent soit heriter genetiquement, soit
    apprendre au cours de leur vie. C'est le coeur du dispositif experimental.
    """

    def __init__(self, rng, t_env=config.T_ENV_DEFAUT,
                 v_vie=config.V_VIE_DEFAUT):
        self.rng = rng
        self.largeur = config.LARGEUR
        self.hauteur = config.HAUTEUR

        # T_env accepte soit un nom de niveau, soit un entier, soit None.
        if isinstance(t_env, str):
            self.t_env = config.T_ENV_NIVEAUX[t_env]
            self.nom_t_env = t_env
        else:
            self.t_env = t_env
            self.nom_t_env = "personnalise"

        # Volatilite INTRA-VIE : nombre de basculements de la validite des
        # types pendant une vie. C'est le second axe, celui qui permet de
        # tester la branche DESCENDANTE de la prediction de Stephens : quand
        # l'environnement change plus vite qu'un individu ne peut apprendre,
        # la plasticite perd son avantage a son tour.
        if isinstance(v_vie, str):
            self.n_inversions_vie = config.V_VIE_NIVEAUX[v_vie]
            self.nom_v_vie = v_vie
        else:
            self.n_inversions_vie = int(v_vie)
            self.nom_v_vie = "personnalise"

        self.generation = 0
        self.n_redistributions = 0
        self.tick_courant = 0
        self.n_inversions_effectuees = 0

        # Quel type de nourriture est NUTRITIF cette generation. L'autre est
        # toxique. C'est l'information imprevisible a la naissance mais
        # decouvrable au cours de la vie — le seul substrat possible de
        # l'apprentissage dans ce dispositif.
        self.type_nutritif = int(self.rng.integers(config.N_TYPES_NOURRITURE))

        # Patchs et items
        self.centres_patchs = np.zeros((config.N_PATCHS, 2), dtype=np.float64)
        n_items = config.N_PATCHS * config.ITEMS_PAR_PATCH
        self.positions_items = np.zeros((n_items, 2), dtype=np.float64)
        self.patch_de_item = np.repeat(np.arange(config.N_PATCHS),
                                       config.ITEMS_PAR_PATCH)
        # Type de chaque item, fixe pour toute la simulation. Les deux types
        # sont melanges DANS chaque patch : sinon un patch entier serait
        # toxique ou nutritif, et l'agent pourrait s'en sortir en evitant des
        # zones plutot qu'en discriminant les types.
        self.types_items = np.tile(
            np.arange(config.N_TYPES_NOURRITURE),
            int(np.ceil(n_items / float(config.N_TYPES_NOURRITURE))))[:n_items]
        self.rng.shuffle(self.types_items)

        self.items_actifs = np.ones(n_items, dtype=bool)
        self.timers_repousse = np.zeros(n_items, dtype=np.int32)

        self._tirer_patchs()
        self._replacer_tous_les_items()

    # -- Volatilite ---------------------------------------------------------

    def _tirer_patchs(self):
        """Tire de nouvelles positions pour les centres de patchs."""
        marge = config.RAYON_PATCH
        self.centres_patchs[:, 0] = self.rng.uniform(
            marge, self.largeur - marge, size=config.N_PATCHS)
        self.centres_patchs[:, 1] = self.rng.uniform(
            marge, self.hauteur - marge, size=config.N_PATCHS)

    def _replacer_tous_les_items(self):
        """Replace tous les items autour de leur patch, et les reactive."""
        for i in range(len(self.positions_items)):
            self._replacer_item(i)
        self.items_actifs[:] = True
        self.timers_repousse[:] = 0

    def _replacer_item(self, idx):
        """Place un item aleatoirement dans le disque de son patch."""
        centre = self.centres_patchs[self.patch_de_item[idx]]
        angle = self.rng.uniform(0.0, 2.0 * math.pi)
        # sqrt pour une densite uniforme sur le disque
        rayon = config.RAYON_PATCH * math.sqrt(self.rng.uniform(0.0, 1.0))
        x = centre[0] + rayon * math.cos(angle)
        y = centre[1] + rayon * math.sin(angle)
        self.positions_items[idx] = enrouler(x, y, self.largeur, self.hauteur)

    def nouvelle_generation(self):
        """A appeler entre deux generations.

        Si T_env l'impose, l'environnement change : les patchs sont retires ET
        la validite des types s'inverse (le nutritif devient toxique). C'est
        ici, et seulement ici, que l'environnement peut changer : jamais
        pendant la vie d'un individu.
        """
        self.generation += 1
        if self.t_env is not None and self.generation % self.t_env == 0:
            self._tirer_patchs()
            # Inversion de la validite des types : c'est le changement
            # fonctionnellement apprenable
            self.type_nutritif = (self.type_nutritif + 1) % config.N_TYPES_NOURRITURE
            self.n_redistributions += 1
        self._replacer_tous_les_items()
        self.tick_courant = 0
        self.n_inversions_effectuees = 0

    def reinitialiser_pour_evaluation(self):
        """Remet la nourriture a l'etat plein sans toucher aux patchs.

        Utilise pour la double evaluation d'un meme genome (P_naif puis
        P_libre) : les deux doivent affronter exactement le meme environnement,
        y compris la meme sequence de basculements intra-vie.
        """
        # Annuler les basculements intra-vie de l'evaluation precedente, pour
        # que les deux evaluations partent du meme type nutritif.
        if self.n_inversions_effectuees % config.N_TYPES_NOURRITURE:
            self.type_nutritif = (
                (self.type_nutritif - self.n_inversions_effectuees)
                % config.N_TYPES_NOURRITURE)
        self.tick_courant = 0
        self.n_inversions_effectuees = 0
        self._replacer_tous_les_items()

    # -- Dynamique de la nourriture -----------------------------------------

    def tick(self):
        """Fait avancer d'un pas de temps : repousse et volatilite intra-vie."""
        # -- Volatilite intra-vie : basculements repartis uniformement
        if self.n_inversions_vie > 0:
            intervalle = config.DUREE_VIE_MAX / float(
                self.n_inversions_vie + 1)
            attendus = int(self.tick_courant / intervalle)
            while self.n_inversions_effectuees < min(attendus,
                                                     self.n_inversions_vie):
                self.type_nutritif = ((self.type_nutritif + 1)
                                      % config.N_TYPES_NOURRITURE)
                self.n_inversions_effectuees += 1
        self.tick_courant += 1

        inactifs = ~self.items_actifs
        if not inactifs.any():
            return
        self.timers_repousse[inactifs] -= 1
        prets = inactifs & (self.timers_repousse <= 0)
        for idx in np.nonzero(prets)[0]:
            self._replacer_item(int(idx))
            self.items_actifs[idx] = True

    def positions_actives(self):
        """Positions (n,2) des items actuellement consommables, tous types."""
        return self.positions_items[self.items_actifs]

    def positions_actives_du_type(self, type_item):
        """Positions (n,2) des items actifs d'un type donne.

        Sert aux canaux sensoriels separes : l'agent percoit les deux types
        distinctement, mais RIEN ne lui indique lequel est comestible — c'est
        precisement ce qu'il doit soit avoir herite, soit apprendre.
        """
        masque = self.items_actifs & (self.types_items == type_item)
        return self.positions_items[masque]

    def est_nutritif(self, type_item):
        return int(type_item) == self.type_nutritif

    def consommer_le_plus_proche(self, x, y, rayon_agent):
        """Consomme un item si l'agent en touche un.

        Renvoie (delta_energie, index_item, type_item). delta_energie est
        POSITIF pour le type nutritif, NEGATIF pour le type toxique.
        """
        indices_actifs = np.nonzero(self.items_actifs)[0]
        if len(indices_actifs) == 0:
            return 0.0, None, None

        d = deltas_toroidaux(x, y, self.positions_items[indices_actifs],
                             self.largeur, self.hauteur)
        distances2 = d[:, 0] ** 2 + d[:, 1] ** 2
        seuil2 = (rayon_agent + config.RAYON_ITEM) ** 2
        k = int(np.argmin(distances2))
        if distances2[k] <= seuil2:
            idx = int(indices_actifs[k])
            type_item = int(self.types_items[idx])
            self.items_actifs[idx] = False
            self.timers_repousse[idx] = config.DELAI_REPOUSSE
            if self.est_nutritif(type_item):
                return config.VALEUR_NOURRITURE, idx, type_item
            return -config.VALEUR_TOXIQUE, idx, type_item
        return 0.0, None, None

    # -- Introspection ------------------------------------------------------

    def resume(self):
        nom = "stable" if self.t_env is None else str(self.t_env)
        return ("Monde[T_env=%s (%s) v_vie=%s (%d inversions) gen=%d "
                "changements=%d nutritif=type%d nourriture=%d/%d]" % (
                    nom, self.nom_t_env, self.nom_v_vie,
                    self.n_inversions_vie, self.generation,
                    self.n_redistributions, self.type_nutritif,
                    int(self.items_actifs.sum()), len(self.items_actifs)))
