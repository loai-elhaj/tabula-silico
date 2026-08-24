# -*- coding: utf-8 -*-
"""
Tabula Silico — Boucle evolutive et double evaluation.

C'est ce module qui transforme "une simulation" en "une experience" :
sans boucle evolutive, T_env ne sert a rien et eta ne peut pas evoluer.

DOUBLE EVALUATION — le coeur du dispositif de mesure.
Chaque generation, la MEME population de genomes est evaluee deux fois, dans
deux mondes identiques (memes patchs, meme type nutritif, meme graine) :

  P_naif : plasticite gelee des la naissance (eta force a 0). Le reseau tourne
           uniquement sur ses poids herites. Mesure pure de l'INNE.
  P_libre: plasticite active. Mesure combinee INNE + ACQUIS.
  DeltaP = P_libre - P_naif : ce que l'apprentissage apporte reellement.

La fitness qui pilote la selection est celle de P_libre : c'est la vie que
l'organisme mene reellement. P_naif est une mesure, pas une vie.

Compatible Python 3.9.
"""

import csv
import os
import random
import time

import numpy as np
import neat

import config
from world import Monde
from simulation import Simulation
from brain import CerveauPlastique
from genome import GenomePlastique


# ---------------------------------------------------------------------------
# Evaluation d'une cohorte
# ---------------------------------------------------------------------------

def evaluer_cohorte(genomes, neat_config, monde, graine, plasticite):
    """Fait vivre une cohorte de genomes dans un monde, renvoie (sim, cerveaux).

    `plasticite=False` gele l'apprentissage : c'est la condition P_naif.
    La graine est passee explicitement pour que les deux evaluations d'une
    meme generation affrontent exactement les memes aleas.
    """
    monde.reinitialiser_pour_evaluation()
    rng = np.random.default_rng(graine)

    cerveaux = [CerveauPlastique(g, neat_config, plasticite_active=plasticite)
                for _, g in genomes]

    file_attente = list(cerveaux)

    def fabrique():
        return file_attente.pop(0)

    sim = Simulation(monde, rng, fabrique_controleur=fabrique,
                     n_pascor=len(genomes))
    sim.executer_headless()
    return sim, cerveaux


def fitness_individuelle(pascor, cerveau, lambda_cout):
    """Fitness d'un individu : energie alimentaire nette reellement recoltee.

    La fitness compte l'ENERGIE (+25 par nutritif, -10 par toxique), et non le
    NOMBRE d'items. La distinction est decisive.

    Version precedente : `nutritifs - toxiques`, soit un comptage d'items
    symetrique — un toxique pesait autant en negatif qu'un nutritif en positif.
    Cela contredisait l'ecologie du modele, ou les gains sont volontairement
    asymetriques (+25 / -10). Un agent mangeant au hasard obtenait donc une
    fitness d'environ zero, exactement comme un agent ne mangeant rien, alors
    qu'ecologiquement il recoltait +7,5 d'energie par repas.

    Consequence mesuree : en environnement tres volatil, la selection
    eliminait le comportement alimentaire lui-meme (4,1 repas par vie, 1,2 % de
    survie). L'asymetrie energetique avait ete introduite pour rendre le fait
    de gouter rentable, mais n'avait pas ete propagee a la fitness — la
    pression de selection restait celle du regime symetrique.

    Structure d'incitations retablie :
      ne rien manger        ->  0
      manger au hasard      ->  +7,5 par repas   (gouter vaut mieux que
                                                  s'abstenir)
      discriminer           ->  +25 par repas    (bien gouter vaut beaucoup
                                                  mieux)

    Le terme de survie evite que la fitness ne sature une fois la
    discrimination acquise par toute la population : sans lui, tous les bons
    discriminateurs auraient la meme fitness et le gradient disparaitrait.
    """
    energie_recoltee = (config.VALEUR_NOURRITURE * pascor.nutritifs_manges
                        - config.VALEUR_TOXIQUE * pascor.toxiques_manges)
    survie = pascor.age / float(config.DUREE_VIE_MAX)
    return (energie_recoltee + config.POIDS_SURVIE_FITNESS * survie
            - lambda_cout * cerveau.cout_realise)


# ---------------------------------------------------------------------------
# Un run evolutif complet
# ---------------------------------------------------------------------------

def _compter_lignes(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def executer_run(t_env=config.T_ENV_DEFAUT, lambda_cout=0.0,
                 graine=config.SEED_DEFAUT, n_generations=None,
                 chemin_journal=None, verbeux=True, ecraser=False,
                 v_vie=config.V_VIE_DEFAUT, chemin_population=None):
    """Execute un run evolutif complet et journalise chaque generation."""
    n_generations = n_generations or config.N_GENERATIONS

    # Initialiser TOUTES les sources d'alea, pas seulement celle de numpy.
    # neat-python et genome.py utilisent le module `random` de la
    # bibliotheque standard pour les mutations (eta, preferences, poids,
    # topologie). Ne semer que numpy laissait donc toute l'evolution genetique
    # non reproductible : deux runs de meme condition et meme graine donnaient
    # des resultats differents (mesure : eta = 0,587 contre 0,499). Un depot
    # scientifique doit permettre de refaire tourner ses propres chiffres.
    random.seed(graine)

    chemin_config = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 config.FICHIER_CONFIG_NEAT)
    neat_config = neat.Config(GenomePlastique,
                              neat.DefaultReproduction,
                              neat.DefaultSpeciesSet,
                              neat.DefaultStagnation,
                              chemin_config)

    population = neat.Population(neat_config)

    rng_monde = np.random.default_rng(graine)
    monde = Monde(rng_monde, t_env=t_env, v_vie=v_vie)

    journal = []
    t_depart = time.time()

    # Journal ecrit de facon INCREMENTALE, une ligne par generation.
    # Un run complet dure plusieurs dizaines de minutes ; n'ecrire qu'a la fin
    # ferait tout perdre en cas d'interruption (fermeture du terminal, veille
    # de la machine, plantage). Le fichier est aussi lisible pendant le run,
    # ce qui permet de suivre l'avancement sans attendre la fin.
    fichier_journal = None
    writer = None
    if chemin_journal:
        dossier = os.path.dirname(os.path.abspath(chemin_journal))
        if dossier and not os.path.isdir(dossier):
            os.makedirs(dossier)
        # Refus d'ecraser un journal existant. Le mode "w" tronque le fichier
        # des l'ouverture : un run relance par megarde detruirait des heures de
        # calcul deja effectuees, silencieusement. Sur une campagne de plusieurs
        # dizaines d'heures, c'est inacceptable.
        if os.path.exists(chemin_journal) and not ecraser:
            raise SystemExit(
                "\n  ARRET : le journal '%s' existe deja.\n"
                "  Il contient %d generation(s) deja calculee(s).\n\n"
                "  Choisis :\n"
                "    - un autre nom de fichier (recommande), ou\n"
                "    - --ecraser pour effacer volontairement l'existant.\n"
                % (chemin_journal, max(0, _compter_lignes(chemin_journal) - 1)))
        fichier_journal = open(chemin_journal, "w", newline="",
                               encoding="utf-8")

    for generation in range(n_generations):
        genomes = list(population.population.items())

        # Graine commune aux deux evaluations : elles doivent differer par la
        # SEULE plasticite, pas par les aleas de placement ou de patrouille.
        graine_gen = int(rng_monde.integers(1 << 30))

        sim_naif, cerveaux_naif = evaluer_cohorte(
            genomes, neat_config, monde, graine_gen, plasticite=False)
        sim_libre, cerveaux_libre = evaluer_cohorte(
            genomes, neat_config, monde, graine_gen, plasticite=True)

        # La selection s'appuie sur la vie reellement vecue (P_libre)
        for i, (_, genome) in enumerate(genomes):
            genome.fitness = fitness_individuelle(
                sim_libre.pascors[i], cerveaux_libre[i], lambda_cout)

        p_naif = np.array([fitness_individuelle(sim_naif.pascors[i],
                                                cerveaux_naif[i], 0.0)
                           for i in range(len(genomes))])
        p_libre = np.array([fitness_individuelle(sim_libre.pascors[i],
                                                 cerveaux_libre[i], 0.0)
                            for i in range(len(genomes))])
        delta_p = p_libre - p_naif

        etas = np.array([getattr(g, "eta", config.ETA_DEFAUT)
                         for _, g in genomes])
        m_naif = sim_naif.metriques()
        m_libre = sim_libre.metriques()

        ligne = {
            "generation": generation,
            "t_env": monde.nom_t_env,
            "v_vie": monde.nom_v_vie,
            "n_inversions_vie": monde.n_inversions_vie,
            "lambda_cout": lambda_cout,
            "graine": graine,
            "eta_moyen": float(etas.mean()),
            "eta_ecart_type": float(etas.std()),
            "p_naif_moyen": float(p_naif.mean()),
            "p_libre_moyen": float(p_libre.mean()),
            "delta_p_moyen": float(delta_p.mean()),
            "fitness_max": float(max(g.fitness for _, g in genomes)),
            "survie_naif": m_naif["taux_survie"],
            "survie_libre": m_libre["taux_survie"],
            "discrimination_naif": m_naif["taux_discrimination"],
            "discrimination_libre": m_libre["taux_discrimination"],
            "discrim_tiers1_libre": m_libre["discrimination_par_tiers"][0],
            "discrim_tiers3_libre": m_libre["discrimination_par_tiers"][2],
            "discrim_tiers1_naif": m_naif["discrimination_par_tiers"][0],
            "discrim_tiers3_naif": m_naif["discrimination_par_tiers"][2],
            # Nombre d'evenements d'apprentissage disponibles. Metrique
            # critique : sans repas, aucune regle d'apprentissage ne peut rien
            # extraire. A la generation 0, les reseaux aleatoires ne savent pas
            # fourrager (mesure : ~4 repas par vie), et l'absence de DeltaP y
            # est un artefact, pas un resultat.
            "repas_moyen_libre": float(np.mean(
                [p.nourriture_mangee for p in sim_libre.pascors])),
            "repas_moyen_naif": float(np.mean(
                [p.nourriture_mangee for p in sim_naif.pascors])),
            "nutritifs_moyen_libre": float(np.mean(
                [p.nutritifs_manges for p in sim_libre.pascors])),
            "toxiques_moyen_libre": float(np.mean(
                [p.toxiques_manges for p in sim_libre.pascors])),
            "cout_apprentissage_moyen": float(np.mean(
                [c.cout_realise for c in cerveaux_libre])),
            "derive_acquise_moyenne": float(np.mean(
                [c.derive_acquise() for c in cerveaux_libre])),
            # Ecart entre preferences acquises et innees : mesure directe de
            # l'ACQUIS sur le substrat dedie.
            "derive_preference_moyenne": float(np.mean(
                [c.derive_preference() for c in cerveaux_libre])),
            "n_especes": len(population.species.species),
            "complexite_moyenne": float(np.mean(
                [len(g.connections) for _, g in genomes])),
        }
        journal.append(ligne)

        if writer is None and fichier_journal is not None:
            writer = csv.DictWriter(fichier_journal,
                                    fieldnames=list(ligne.keys()))
            writer.writeheader()
        if writer is not None:
            writer.writerow(ligne)
            fichier_journal.flush()   # visible immediatement, resiste au crash

        if verbeux:
            print("gen %3d | eta %.3f | repas %4.1f | P_naif %6.2f "
                  "P_libre %6.2f dP %+5.2f | discrim naif %.2f libre %.2f "
                  "| %.0fs"
                  % (generation, ligne["eta_moyen"], ligne["repas_moyen_libre"],
                     ligne["p_naif_moyen"], ligne["p_libre_moyen"],
                     ligne["delta_p_moyen"],
                     ligne["discrimination_naif"],
                     ligne["discrimination_libre"],
                     time.time() - t_depart))

        # Generation suivante
        population.population = population.reproduction.reproduce(
            neat_config, population.species,
            neat_config.pop_size, population.generation)
        if not population.species.species:
            population.population = population.reproduction.create_new(
                neat_config.genome_type, neat_config.genome_config,
                neat_config.pop_size)
        population.species.speciate(neat_config, population.population,
                                    population.generation)
        population.generation += 1

        monde.nouvelle_generation()

    if fichier_journal is not None:
        fichier_journal.close()

    # Sauvegarde de la population finale, pour les lesions in silico (H3).
    # Sans cela, analyser une population evoluee imposerait de relancer tout
    # le run a chaque nouvelle question posee.
    if chemin_population:
        import pickle
        dossier = os.path.dirname(os.path.abspath(chemin_population))
        if dossier and not os.path.isdir(dossier):
            os.makedirs(dossier)
        with open(chemin_population, "wb") as f:
            pickle.dump({
                "genomes": list(population.population.values()),
                "type_nutritif": monde.type_nutritif,
                "centres_patchs": monde.centres_patchs,
                "types_items": monde.types_items,
                "t_env": t_env,
                "v_vie": v_vie,
                "lambda_cout": lambda_cout,
                "graine": graine,
            }, f)
    return journal


def ecrire_journal(journal, chemin):
    if not journal:
        return
    dossier = os.path.dirname(os.path.abspath(chemin))
    if dossier and not os.path.isdir(dossier):
        os.makedirs(dossier)
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(journal[0].keys()))
        writer.writeheader()
        for ligne in journal:
            writer.writerow(ligne)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Tabula Silico — run evolutif")
    p.add_argument("--tenv", default=config.T_ENV_DEFAUT,
                   choices=sorted(config.T_ENV_NIVEAUX.keys()))
    p.add_argument("--cout", type=float, default=0.0,
                   help="lambda_cout : penalite du cout d'apprentissage")
    p.add_argument("--seed", type=int, default=config.SEED_DEFAUT)
    p.add_argument("--generations", type=int, default=None)
    p.add_argument("--journal", type=str, default=None,
                   help="chemin du CSV de sortie")
    p.add_argument("--ecraser", action="store_true",
                   help="autorise l'ecrasement d'un journal existant")
    p.add_argument("--population", type=str, default=None,
                   help="chemin ou sauvegarder la population finale (H3)")
    p.add_argument("--vvie", default=config.V_VIE_DEFAUT,
                   choices=sorted(config.V_VIE_NIVEAUX.keys()),
                   help="volatilite INTRA-VIE : nombre de basculements de la "
                        "validite des types pendant une vie")
    a = p.parse_args()
    executer_run(t_env=a.tenv, lambda_cout=a.cout, graine=a.seed,
                 n_generations=a.generations, chemin_journal=a.journal,
                 ecraser=a.ecraser, v_vie=a.vvie,
                 chemin_population=a.population)
