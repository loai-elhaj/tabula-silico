# -*- coding: utf-8 -*-
"""
Tabula Silico — Diagnostic : le mecanisme d'apprentissage fonctionne-t-il ?

Isole completement l'APPRENTISSAGE de l'EVOLUTION. Aucune selection, aucune
reproduction : on prend des genomes fixes, on les fait vivre une vie, et on
mesure si leur reponse d'ingestion est devenue dependante du type d'aliment.

Protocole, pour chaque genome :
  1. SONDE AVANT : on presente au reseau deux motifs sensoriels synthetiques
     (type A seul au contact, puis type B seul au contact) et on releve la
     sortie d'ingestion pour chacun.
  2. VIE : l'agent vit une vie complete dans le monde, plasticite active, et
     recoit de vraies recompenses alimentaires.
  3. SONDE APRES : memes deux motifs, on releve a nouveau l'ingestion.

Mesure cle — la DIVERGENCE :
     divergence = [ingestion(nutritif) - ingestion(toxique)]
Si l'apprentissage fonctionne, cette divergence doit AUGMENTER au cours de la
vie : l'agent doit devenir plus enclin a ingerer le nutritif et moins enclin a
ingerer le toxique.

Les sondes sont faites plasticite temporairement gelee, pour ne pas
contaminer les traces d'eligibilite avec les motifs de test eux-memes.

Compatible Python 3.9.
"""

import os

import numpy as np
import neat

import config
from world import Monde
from simulation import Simulation
from brain import CerveauPlastique
from genome import GenomePlastique


def motif_sensoriel(type_present, intensite=1.0):
    """Motif synthetique : un seul type d'aliment au contact, rien d'autre."""
    e = [0.0] * config.N_ENTREES
    base = type_present * config.N_SECTEURS
    # Secteur central sature (aliment droit devant, au contact), voisins moindres
    centre = config.N_SECTEURS // 2
    for s in range(config.N_SECTEURS):
        ecart = abs(s - centre)
        e[base + s] = intensite * max(0.0, 1.0 - 0.4 * ecart)
    e[-1] = 0.5          # energie a mi-course
    return e


def sonder(cerveau):
    """Renvoie (ingestion_type0, ingestion_type1), plasticite gelee."""
    memoire = cerveau.plasticite_active
    cerveau.plasticite_active = False
    trace = cerveau.eligibilite.copy()
    activations = dict(cerveau.activations)

    sorties = []
    for t in range(config.N_TYPES_NOURRITURE):
        # Quelques passes pour laisser le reseau se stabiliser sur le motif
        for _ in range(3):
            r = cerveau.agir(motif_sensoriel(t))
        sorties.append(r[2])

    cerveau.plasticite_active = memoire
    cerveau.eligibilite = trace
    cerveau.activations = activations
    return sorties


def diagnostiquer(n_genomes=40, graine=11, t_env="intermediaire", eta=1.0):
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          config.FICHIER_CONFIG_NEAT)
    cfg = neat.Config(GenomePlastique, neat.DefaultReproduction,
                      neat.DefaultSpeciesSet, neat.DefaultStagnation, chemin)
    population = neat.Population(cfg)
    genomes = list(population.population.values())[:n_genomes]
    for g in genomes:
        g.eta = eta

    rng = np.random.default_rng(graine)
    monde = Monde(rng, t_env=t_env)
    nutritif = monde.type_nutritif
    toxique = 1 - nutritif

    cerveaux = [CerveauPlastique(g, cfg, plasticite_active=True)
                for g in genomes]
    avant = [sonder(c) for c in cerveaux]

    file_attente = list(cerveaux)
    sim = Simulation(monde, rng, fabrique_controleur=lambda: file_attente.pop(0),
                     n_pascor=len(cerveaux))
    sim.executer_headless()

    apres = [sonder(c) for c in cerveaux]

    # Divergence : ingestion(nutritif) - ingestion(toxique)
    div_avant = np.array([a[nutritif] - a[toxique] for a in avant])
    div_apres = np.array([a[nutritif] - a[toxique] for a in apres])
    variation = div_apres - div_avant

    repas_nut = np.array([p.nutritifs_manges for p in sim.pascors])
    repas_tox = np.array([p.toxiques_manges for p in sim.pascors])
    couts = np.array([c.cout_realise for c in cerveaux])
    derives = np.array([c.derive_acquise() for c in cerveaux])

    print("=" * 66)
    print("  DIAGNOSTIC DU MECANISME D'APPRENTISSAGE")
    print("  (evolution desactivee, eta force a %.1f)" % eta)
    print("=" * 66)
    print("  genomes testes            : %d" % len(genomes))
    print("  type nutritif             : %d   (toxique : %d)"
          % (nutritif, toxique))
    print()
    print("  -- L'agent a-t-il eu de quoi apprendre ?")
    print("     repas nutritifs / vie  : %.1f  (min %d, max %d)"
          % (repas_nut.mean(), repas_nut.min(), repas_nut.max()))
    print("     repas toxiques / vie   : %.1f  (min %d, max %d)"
          % (repas_tox.mean(), repas_tox.min(), repas_tox.max()))
    print("     mises a jour de poids  : cout cumule moyen %.3f" % couts.mean())
    print("     derive des poids       : %.4f" % derives.mean())
    print()
    print("  -- La reponse d'ingestion a-t-elle diverge ?")
    print("     divergence AVANT vie   : %+.4f" % div_avant.mean())
    print("     divergence APRES vie   : %+.4f" % div_apres.mean())
    print("     variation              : %+.4f  (ecart-type %.4f)"
          % (variation.mean(), variation.std()))
    print("     variations positives   : %d / %d"
          % (int((variation > 0).sum()), len(variation)))
    print()

    # Test de signe : la variation est-elle significativement positive ?
    n_pos = int((variation > 0).sum())
    n_tot = len(variation)
    erreur_type = variation.std() / np.sqrt(max(1, n_tot))
    z = variation.mean() / erreur_type if erreur_type > 0 else 0.0
    print("     z approx (variation / erreur-type) : %+.2f" % z)
    if z > 2.0:
        print()
        print("  => LE MECANISME FONCTIONNE : la reponse d'ingestion devient")
        print("     dependante du type au cours de la vie.")
    elif abs(z) <= 2.0:
        print()
        print("  => LE MECANISME NE PRODUIT RIEN d'exploitable : la reponse")
        print("     d'ingestion ne diverge pas plus que le hasard.")
    else:
        print()
        print("  => DIVERGENCE INVERSEE : l'agent apprend le CONTRAIRE.")
    print("=" * 66)
    return {"variation": variation, "z": z,
            "repas_nut": repas_nut, "repas_tox": repas_tox}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Diagnostic de l'apprentissage")
    p.add_argument("--genomes", type=int, default=40)
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--eta", type=float, default=1.0)
    p.add_argument("--tenv", default="intermediaire",
                   choices=sorted(config.T_ENV_NIVEAUX.keys()))
    a = p.parse_args()
    diagnostiquer(n_genomes=a.genomes, graine=a.seed, t_env=a.tenv, eta=a.eta)
