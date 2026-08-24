# -*- coding: utf-8 -*-
"""
Tabula Silico — Lesions in silico (H3).

H3 : l'inne et l'acquis ne sont pas deux strategies concurrentes mais
complementaires. L'inne fournit un socle immediatement fonctionnel, sur lequel
l'acquis vient s'ajuster.

Le principe de la lesion : prendre une population EVOLUEE, la faire vivre dans
des conditions ou l'on retire selectivement l'une ou l'autre composante, et
mesurer ce que chaque retrait coute. Le genome est identique dans toutes les
conditions — seule change ce qu'on lui permet d'utiliser.

QUATRE CONDITIONS
  aleatoire    genomes NON EVOLUES, plasticite gelee.
               Reference de non-fonctionnalite : ce que vaut un agent qui n'a
               ni herite ni appris.
  inne_seul    genomes evolues, plasticite gelee (= P_naif).
               Mesure pure de l'INNE.
  inne_acquis  genomes evolues, plasticite active (= P_libre).
               INNE + ACQUIS combines.
  acquis_seul  genomes evolues MAIS preferences innees remises a zero,
               plasticite active.
               Demande si l'apprentissage peut reconstruire a lui seul ce que
               l'evolution avait encode.

SOUS-TESTS DE H3
  3a  socle inne fonctionnel : inne_seul > aleatoire
  3b  l'apprentissage apporte un gain reel : inne_acquis > inne_seul
  3c  preuve comportementale : la discrimination doit PROGRESSER au fil de la
      vie chez les plastiques, et rester plate chez les figes. La comparaison
      aux figes est indispensable : elle neutralise le confondant
      d'installation spatiale identifie a l'etape 2.

Compatible Python 3.9.
"""

import os
import pickle

import numpy as np
import neat

import config
from world import Monde
from simulation import Simulation
from brain import CerveauPlastique
from genome import GenomePlastique
from evolution import fitness_individuelle


def _config_neat():
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          config.FICHIER_CONFIG_NEAT)
    return neat.Config(GenomePlastique, neat.DefaultReproduction,
                       neat.DefaultSpeciesSet, neat.DefaultStagnation, chemin)


def _genomes_aleatoires(cfg, n):
    """Genomes non evolues : la reference de non-fonctionnalite."""
    pop = neat.Population(cfg)
    return list(pop.population.values())[:n]


def _evaluer(genomes, cfg, monde, graine, plasticite, neutraliser_pref=False):
    """Fait vivre une cohorte dans des conditions donnees."""
    monde.reinitialiser_pour_evaluation()
    rng = np.random.default_rng(graine)
    prefs = ([0.0] * config.N_TYPES_NOURRITURE) if neutraliser_pref else None
    cerveaux = [CerveauPlastique(g, cfg, plasticite_active=plasticite,
                                 preferences_initiales=prefs)
                for g in genomes]
    file_attente = list(cerveaux)
    sim = Simulation(monde, rng, fabrique_controleur=lambda: file_attente.pop(0),
                     n_pascor=len(genomes))
    sim.executer_headless()
    return sim, cerveaux


def _mesures(sim, cerveaux):
    m = sim.metriques()
    fitness = np.array([fitness_individuelle(sim.pascors[i], cerveaux[i], 0.0)
                        for i in range(len(cerveaux))])
    return {
        "fitness": float(fitness.mean()),
        "fitness_et": float(fitness.std()),
        "discrimination": m["taux_discrimination"],
        "survie": m["taux_survie"],
        "repas": m["nourriture_moyenne"],
        "discrim_tiers": m["discrimination_par_tiers"],
    }


def lesionner(chemin_population, graine_eval=999):
    with open(chemin_population, "rb") as f:
        sauvegarde = pickle.load(f)

    cfg = _config_neat()
    genomes = sauvegarde["genomes"]
    n = len(genomes)

    # Le monde d'evaluation reproduit celui de fin de run : memes patchs, meme
    # type nutritif. Toutes les conditions affrontent le MEME environnement.
    monde = Monde(np.random.default_rng(sauvegarde["graine"]),
                  t_env="stable", v_vie=sauvegarde.get("v_vie", "nulle"))
    monde.centres_patchs = sauvegarde["centres_patchs"]
    monde.types_items = sauvegarde["types_items"]
    monde.type_nutritif = sauvegarde["type_nutritif"]
    monde._replacer_tous_les_items()

    conditions = [
        ("aleatoire", _genomes_aleatoires(cfg, n), False, False),
        ("inne_seul", genomes, False, False),
        ("inne_acquis", genomes, True, False),
        ("acquis_seul", genomes, True, True),
    ]

    resultats = {}
    for nom, gs, plast, neutre in conditions:
        sim, cerveaux = _evaluer(gs, cfg, monde, graine_eval, plast, neutre)
        resultats[nom] = _mesures(sim, cerveaux)

    _afficher(resultats, sauvegarde)
    return resultats


def _afficher(r, sauvegarde):
    print("=" * 74)
    print("  LESIONS IN SILICO — decomposition de l'inne et de l'acquis (H3)")
    print("  T_env=%s  v_vie=%s  lambda=%.1f  graine=%d"
          % (sauvegarde["t_env"], sauvegarde.get("v_vie", "nulle"),
             sauvegarde.get("lambda_cout", 0.0), sauvegarde["graine"]))
    print("=" * 74)
    print("%-14s %12s %16s %10s %9s"
          % ("condition", "fitness", "discrimination", "survie", "repas"))
    libelles = {
        "aleatoire": "aleatoire",
        "inne_seul": "inne seul",
        "inne_acquis": "inne+acquis",
        "acquis_seul": "acquis seul",
    }
    for cle in ("aleatoire", "inne_seul", "inne_acquis", "acquis_seul"):
        m = r[cle]
        print("%-14s %12.1f %16.3f %9.1f%% %9.1f"
              % (libelles[cle], m["fitness"], m["discrimination"],
                 100 * m["survie"], m["repas"]))

    print()
    print("  SOUS-TESTS DE H3")
    a, i, c = (r["aleatoire"]["fitness"], r["inne_seul"]["fitness"],
               r["inne_acquis"]["fitness"])
    print("    3a  socle inne fonctionnel   : inne %.1f vs aleatoire %.1f"
          "   -> %s" % (i, a, "OK" if i > a else "ECHEC"))
    print("    3b  gain de l'apprentissage  : DeltaP = %+.1f"
          "   -> %s" % (c - i, "OK" if c > i else "ECHEC"))

    tiers_p = r["inne_acquis"]["discrim_tiers"]
    tiers_f = r["inne_seul"]["discrim_tiers"]
    pente_p = tiers_p[2] - tiers_p[0]
    pente_f = tiers_f[2] - tiers_f[0]
    print("    3c  progression intra-vie    : plastiques %+.4f, figes %+.4f"
          % (pente_p, pente_f))
    print("        (seul l'EXCEDENT compte : %+.4f)" % (pente_p - pente_f))

    print()
    print("  L'apprentissage peut-il remplacer l'inne ?")
    print("    acquis seul %.1f  vs  inne seul %.1f  vs  les deux %.1f"
          % (r["acquis_seul"]["fitness"], i, c))
    print("=" * 74)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Lesions in silico (H3)")
    p.add_argument("population", help="fichier de population sauvegardee")
    p.add_argument("--seed", type=int, default=999,
                   help="graine d'evaluation (commune a toutes les conditions)")
    a = p.parse_args()
    lesionner(a.population, graine_eval=a.seed)
