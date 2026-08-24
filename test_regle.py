# -*- coding: utf-8 -*-
"""
Tabula Silico — Test de la regle d'apprentissage, hors monde et hors evolution.

Question : la regle hebbienne modulee PEUT-ELLE apprendre une discrimination
alimentaire, dans les meilleures conditions imaginables ?

Aucune simulation, aucune selection. On nourrit directement le reseau de
motifs sensoriels et de recompenses, puis on mesure si sa reponse d'ingestion
a diverge entre les deux types.

Deux regimes d'entrainement sont compares, ce qui tranche entre deux causes
possibles a l'echec constate :

  PROPRE  : un seul type visible au moment de l'ingestion. Attribution du
            credit sans ambiguite.
  AMBIGU  : les DEUX types visibles simultanement, l'ingere plus proche que
            l'autre. C'est la situation reelle du monde, ou les deux types
            sont melanges dans chaque patch.

  - Si PROPRE fonctionne et AMBIGU echoue -> le probleme est l'ATTRIBUTION DU
    CREDIT, et c'est la disposition spatiale des types qu'il faut rouvrir.
  - Si les deux echouent -> c'est la REGLE elle-meme qui ne fait pas le
    travail, et il faut la revoir.

Compatible Python 3.9.
"""

import os

import numpy as np
import neat

import config
from brain import CerveauPlastique
from genome import GenomePlastique


def motif(type_dominant, type_secondaire=None, intensite_sec=0.6):
    """Motif sensoriel : un type au contact, eventuellement un autre plus loin."""
    e = [0.0] * config.N_ENTREES
    centre = config.N_SECTEURS // 2
    base = type_dominant * config.N_SECTEURS
    for s in range(config.N_SECTEURS):
        e[base + s] = max(0.0, 1.0 - 0.4 * abs(s - centre))
    if type_secondaire is not None:
        base2 = type_secondaire * config.N_SECTEURS
        for s in range(config.N_SECTEURS):
            e[base2 + s] = intensite_sec * max(0.0, 1.0 - 0.4 * abs(s - centre))
    e[-1] = 0.5
    return e


def sonder(cerveau):
    """Reponse d'ingestion a chaque type, plasticite gelee."""
    memoire = cerveau.plasticite_active
    cerveau.plasticite_active = False
    trace = cerveau.eligibilite.copy()
    sorties = []
    for t in range(config.N_TYPES_NOURRITURE):
        for _ in range(3):
            r = cerveau.agir(motif(t))
        sorties.append(r[2])
    cerveau.plasticite_active = memoire
    cerveau.eligibilite = trace
    return sorties


def entrainer(cerveau, nutritif, n_repas, ambigu, rng, ticks_avant_repas=6):
    """Nourrit le reseau de motifs et de recompenses."""
    toxique = 1 - nutritif
    for _ in range(n_repas):
        t = int(rng.integers(config.N_TYPES_NOURRITURE))
        secondaire = (1 - t) if ambigu else None
        for _ in range(ticks_avant_repas):
            cerveau.agir(motif(t, secondaire))
        signal = (config.VALEUR_NOURRITURE if t == nutritif
                  else -config.VALEUR_TOXIQUE)
        cerveau.recompenser(signal)
        # Quelques pas "a vide" entre deux repas, comme dans le monde reel
        for _ in range(4):
            cerveau.agir([0.0] * (config.N_ENTREES - 1) + [0.5])


def tester(n_genomes=50, n_repas=60, graine=5, eta=1.0):
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          config.FICHIER_CONFIG_NEAT)
    cfg = neat.Config(GenomePlastique, neat.DefaultReproduction,
                      neat.DefaultSpeciesSet, neat.DefaultStagnation, chemin)
    population = neat.Population(cfg)
    genomes = list(population.population.values())[:n_genomes]

    print("=" * 68)
    print("  LA REGLE HEBBIENNE PEUT-ELLE APPRENDRE UNE DISCRIMINATION ?")
    print("  %d reseaux, %d repas d'entrainement, eta = %.1f"
          % (n_genomes, n_repas, eta))
    print("=" * 68)
    print("%-34s %10s %8s %10s" % ("regime d'entrainement", "divergence",
                                   "z", "positifs"))

    resultats = {}
    for nom, ambigu in [("PROPRE  (un seul type visible)", False),
                        ("AMBIGU  (les deux visibles)", True)]:
        variations = []
        for g in genomes:
            g.eta = eta
            rng = np.random.default_rng(graine)
            nutritif = 0
            c = CerveauPlastique(g, cfg, plasticite_active=True)
            avant = sonder(c)
            entrainer(c, nutritif, n_repas, ambigu, rng)
            apres = sonder(c)
            div_av = avant[nutritif] - avant[1 - nutritif]
            div_ap = apres[nutritif] - apres[1 - nutritif]
            variations.append(div_ap - div_av)
        v = np.array(variations)
        z = v.mean() / (v.std() / np.sqrt(len(v))) if v.std() > 0 else 0.0
        resultats[nom] = (v.mean(), z)
        print("%-34s %+10.4f %8.2f %6d/%d"
              % (nom, v.mean(), z, int((v > 0).sum()), len(v)))

    print()
    z_propre = resultats["PROPRE  (un seul type visible)"][1]
    z_ambigu = resultats["AMBIGU  (les deux visibles)"][1]
    if z_propre > 2.0 and z_ambigu <= 2.0:
        print("  => ATTRIBUTION DU CREDIT. La regle fonctionne quand le repas")
        print("     est net, et echoue quand les deux types sont visibles.")
        print("     C'est le melange des types dans les patchs qu'il faut")
        print("     rouvrir, pas la regle.")
    elif z_propre > 2.0 and z_ambigu > 2.0:
        print("  => LA REGLE FONCTIONNE dans les deux regimes. L'obstacle est")
        print("     ailleurs : nombre de repas, eta, ou boucle evolutive.")
    else:
        print("  => LA REGLE ELLE-MEME NE FAIT PAS LE TRAVAIL, meme dans les")
        print("     conditions les plus favorables. C'est elle qu'il faut")
        print("     revoir, pas l'environnement.")
    print("=" * 68)
    return resultats


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--genomes", type=int, default=50)
    p.add_argument("--repas", type=int, default=60)
    p.add_argument("--eta", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=5)
    a = p.parse_args()
    tester(n_genomes=a.genomes, n_repas=a.repas, graine=a.seed, eta=a.eta)
