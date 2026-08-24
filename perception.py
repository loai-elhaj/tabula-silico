# -*- coding: utf-8 -*-
"""
Tabula Silico — Perception vectorisee.

Calcule les entrees sensorielles de TOUS les Pascor vivants en une seule passe
numpy, au lieu d'une passe par agent et par canal.

Motivation (mesuree, pas supposee) : le profilage de la version par-agent
montrait 81 % du temps total passe dans la perception, avec 113 000 appels a
`_remplir_secteurs` pour 400 ticks — soit 3 petites operations numpy par agent
et par tick. Sur des tableaux de cette taille, c'est la surcharge fixe d'appel
de numpy qui domine, pas le calcul. Regrouper les agents transforme
300 petites operations par tick en une quinzaine de grosses.

Compatible Python 3.9.
"""

import math
import numpy as np

import config

_DEMI_CHAMP = config.CHAMP_VISION * 0.5
_LARGEUR_SECTEUR = config.CHAMP_VISION / config.N_SECTEURS
_DEUX_PI = 2.0 * math.pi


def percevoir_tous(pascors, monde, venators):
    """Renvoie la matrice (n_agents, N_ENTREES) des entrees sensorielles.

    L'ordre des colonnes est identique a `Pascor.percevoir` :
      [type A x N_SECTEURS, type B x N_SECTEURS, venator x N_SECTEURS, energie]
    """
    n = len(pascors)
    entrees = np.zeros((n, config.N_ENTREES), dtype=np.float64)
    if n == 0:
        return entrees

    xs = np.fromiter((p.x for p in pascors), dtype=np.float64, count=n)
    ys = np.fromiter((p.y for p in pascors), dtype=np.float64, count=n)
    caps = np.fromiter((p.cap for p in pascors), dtype=np.float64, count=n)

    # Un canal sensoriel par type de nourriture, puis un pour Venator.
    canaux = [monde.positions_actives_du_type(t)
              for t in range(config.N_TYPES_NOURRITURE)]
    if venators:
        canaux.append(np.array([[v.x, v.y] for v in venators],
                               dtype=np.float64))
    else:
        canaux.append(np.zeros((0, 2), dtype=np.float64))

    for i_canal, cibles in enumerate(canaux):
        m = len(cibles)
        if m == 0:
            continue

        # Deltas toroidaux, tous agents x toutes cibles d'un coup : (n, m)
        dx = cibles[None, :, 0] - xs[:, None]
        dy = cibles[None, :, 1] - ys[:, None]
        if config.TOROIDAL:
            dx -= monde.largeur * np.round(dx / monde.largeur)
            dy -= monde.hauteur * np.round(dy / monde.hauteur)

        distances = np.sqrt(dx * dx + dy * dy)

        # Relevement relatif au cap de chaque agent, ramene dans [-pi, pi]
        releves = np.arctan2(dy, dx) - caps[:, None]
        releves = (releves + math.pi) % _DEUX_PI - math.pi

        visible = (distances < config.PORTEE_VISION) & \
                  (np.abs(releves) <= _DEMI_CHAMP)
        if not visible.any():
            continue

        secteurs = ((releves + _DEMI_CHAMP) / _LARGEUR_SECTEUR).astype(np.int32)
        np.clip(secteurs, 0, config.N_SECTEURS - 1, out=secteurs)

        # Distance de la cible la plus proche dans chaque secteur.
        # np.inf marque "rien de visible", ce qui donnera un capteur a 0.
        base = i_canal * config.N_SECTEURS
        for s in range(config.N_SECTEURS):
            dans_secteur = visible & (secteurs == s)
            d_min = np.where(dans_secteur, distances, np.inf).min(axis=1)
            entrees[:, base + s] = np.where(
                np.isfinite(d_min), 1.0 - d_min / config.PORTEE_VISION, 0.0)

    # Derniere entree : energie normalisee
    energies = np.fromiter((p.energie for p in pascors),
                           dtype=np.float64, count=n)
    entrees[:, -1] = np.clip(energies / config.ENERGIE_MAX, 0.0, 1.0)
    return entrees
