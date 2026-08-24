# -*- coding: utf-8 -*-
"""
Tabula Silico — Point d'entree.

Exemples d'utilisation (Windows, invite de commandes) :

    python main.py                          fenetre visuelle, parametres par defaut
    python main.py --tenv stable            environnement stable
    python main.py --headless               sans affichage, affiche les metriques
    python main.py --captures 4             genere 4 images de verification
    python main.py --pascor 40 --seed 7     population reduite, autre graine

Compatible Python 3.9.
"""

import argparse
import os
import sys

import numpy as np

import config


def analyser_arguments():
    p = argparse.ArgumentParser(description="Tabula Silico — simulation 2D")
    p.add_argument("--seed", type=int, default=config.SEED_DEFAUT,
                   help="graine aleatoire")
    p.add_argument("--tenv", type=str, default=config.T_ENV_DEFAUT,
                   choices=sorted(config.T_ENV_NIVEAUX.keys()),
                   help="niveau de volatilite environnementale")
    p.add_argument("--pascor", type=int, default=None,
                   help="taille de population (defaut : config.N_PASCOR)")
    p.add_argument("--headless", action="store_true",
                   help="execution sans affichage, affiche les metriques")
    p.add_argument("--captures", type=int, default=0,
                   help="genere N images de verification puis quitte")
    p.add_argument("--dossier", type=str, default="captures",
                   help="dossier de sortie des captures")
    p.add_argument("--preference", type=str, default="correcte",
                   choices=["correcte", "fausse", "aucune"],
                   help="strategie innee du controleur reactif de reference : "
                        "'correcte' (etalon de calibration), 'fausse' "
                        "(preference inadaptee), 'aucune' (avale tout)")
    return p.parse_args()


def fabrique_reactif(monde, rng, mode):
    """Construit une fabrique de controleur reactif a preference innee fixee.

    L'etalon de calibration est la preference CORRECTE : c'est le meilleur
    comportement inne possible sans apprentissage. Sans preference, l'agent
    avale ~50 % de toxique et meurt — comportement attendu, mais inutilisable
    comme reference de calibration.
    """
    from agents import ControleurReactif
    if mode == "correcte":
        pref = monde.type_nutritif
    elif mode == "fausse":
        pref = 1 - monde.type_nutritif
    else:
        pref = None
    return lambda: ControleurReactif(rng, preference=pref)


def executer_captures(args):
    """Genere des images a differents moments de la simulation.

    Sert de preuve visuelle : on doit VOIR que les Pascor cherchent la
    nourriture et que les Venator chassent, avant de faire tourner quoi que ce
    soit a grande echelle.
    """
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from render import Rendu
    from world import Monde
    from simulation import Simulation

    pygame.init()
    rng = np.random.default_rng(args.seed)
    monde = Monde(rng, t_env=args.tenv)
    sim = Simulation(monde, rng, n_pascor=args.pascor,
                     fabrique_controleur=fabrique_reactif(monde, rng,
                                                          args.preference))
    rendu = Rendu(sans_affichage=True)

    if not os.path.isdir(args.dossier):
        os.makedirs(args.dossier)

    n = args.captures
    jalons = [int(config.DUREE_VIE_MAX * (i + 1) / float(n)) for i in range(n)]
    jalons[0] = min(jalons[0], 120)  # une image tot, pour voir le depart

    chemins = []
    prochain = 0
    while prochain < len(jalons) and not sim.termine():
        sim.tick()
        for (x, y, nutritif) in sim.repas_du_tick:
            rendu.ajouter_effet(x, y, "repas" if nutritif else "toxique",
                                sim.tick_courant)
        for (x, y) in sim.captures_du_tick:
            rendu.ajouter_effet(x, y, "capture", sim.tick_courant)

        if sim.tick_courant >= jalons[prochain]:
            m = sim.metriques()
            infos = [
                ("T_env", monde.nom_t_env),
                ("Tick", "%d / %d" % (sim.tick_courant, config.DUREE_VIE_MAX)),
                ("Pascor vivants", "%d / %d" % (m["n_survivants"], m["n_pascor"])),
                ("Venator", len(sim.venators)),
                ("Type nutritif", "A (ambre)" if monde.type_nutritif == 0
                 else "B (cyan)"),
                ("Nutritifs manges", int(m["nutritifs_moyen"] * m["n_pascor"])),
                ("Toxiques manges", int(m["toxiques_moyen"] * m["n_pascor"])),
                ("Discrimination",
                 ("%.0f %%" % (100 * m["taux_discrimination"]))
                 if m["taux_discrimination"] == m["taux_discrimination"]
                 else "n/a"),
                ("Captures", m["captures"]),
            ]
            rendu.dessiner(monde, sim.pascors, sim.venators, infos, tick=sim.tick_courant)
            chemin = os.path.join(args.dossier,
                                  "tick_%05d.png" % sim.tick_courant)
            rendu.sauvegarder(chemin)
            chemins.append(chemin)
            prochain += 1

    pygame.quit()
    return chemins, sim.metriques()


def afficher_metriques(m):
    print("")
    print("=" * 58)
    print("  METRIQUES DE LA COHORTE")
    print("=" * 58)
    lignes = [
        ("Ticks simules", m["ticks"]),
        ("Pascor au depart", m["n_pascor"]),
        ("Survivants", "%d  (%.1f %%)" % (m["n_survivants"],
                                          100.0 * m["taux_survie"])),
        ("Age moyen", "%.0f ticks" % m["age_moyen"]),
        ("Nourriture moyenne", "%.2f items / individu" % m["nourriture_moyenne"]),
        ("Repas / vie complete", ("%.1f" % m["repas_par_vie_complete"])
         if m["repas_par_vie_complete"] == m["repas_par_vie_complete"] else "n/a"),
        ("Nutritifs / individu", "%.2f" % m["nutritifs_moyen"]),
        ("Toxiques / individu", "%.2f" % m["toxiques_moyen"]),
        ("Discrimination", ("%.1f %%  (50 %% = hasard)"
                            % (100 * m["taux_discrimination"]))
         if m["taux_discrimination"] == m["taux_discrimination"] else "n/a"),
        ("Discrim. par tiers", " -> ".join(
            ("%.0f%%" % (100 * v)) if v == v else "n/a"
            for v in m["discrimination_par_tiers"])),
        ("Efficacite foraging", "%.5f item / unite parcourue"
         % m["efficacite_foraging"]),
        ("Rencontres Venator", m["rencontres_venator"]),
        ("Captures", m["captures"]),
        ("Taux d'evitement", ("%.3f" % m["taux_evitement"])
         if m["taux_evitement"] == m["taux_evitement"] else "n/a"),
        ("Mangee 1er tiers", ("%.2f" % m["mangee_1er_tiers"])
         if m["mangee_1er_tiers"] == m["mangee_1er_tiers"] else "n/a"),
        ("Mangee 3e tiers", ("%.2f" % m["mangee_3e_tiers"])
         if m["mangee_3e_tiers"] == m["mangee_3e_tiers"] else "n/a"),
    ]
    for cle, valeur in lignes:
        print("  %-24s %s" % (cle, valeur))
    print("  %-24s %s" % ("Causes de mort", m["causes_mort"]))
    print("=" * 58)

    # Verification de la cible de calibration
    bas, haut = config.CIBLE_SURVIE_GEN0
    taux = m["taux_survie"]
    causes = m["causes_mort"]
    n = float(m["n_pascor"]) or 1.0
    part_predation = causes.get("predation", 0) / n
    part_famine = causes.get("famine", 0) / n

    if taux < bas:
        # Diagnostiquer la VRAIE cause avant d'accuser Venator : allonger la
        # duree de vie augmente l'exposition a la predation, mais un deficit
        # alimentaire produit le meme symptome pour une raison opposee.
        if part_predation > part_famine:
            print("  [CALIBRATION] Survie %.0f %% < cible %.0f %% — dominee par"
                  " la PREDATION (%.0f %%). Baisser"
                  " PORTEE_DETECTION_VENATOR ou VITESSE_POURSUITE."
                  % (100 * taux, 100 * bas, 100 * part_predation))
        else:
            print("  [CALIBRATION] Survie %.0f %% < cible %.0f %% — dominee par"
                  " la FAMINE (%.0f %%). Venator n'est pas en cause."
                  % (100 * taux, 100 * bas, 100 * part_famine))
            if m["taux_discrimination"] == m["taux_discrimination"] and \
                    m["taux_discrimination"] < 0.6:
                print("               Discrimination a %.0f %% (~hasard) : c'est"
                      " attendu sans preference innee. Utiliser"
                      " --preference correcte comme etalon."
                      % (100 * m["taux_discrimination"]))
    elif taux > haut:
        print("  [CALIBRATION] Survie %.0f %% > cible %.0f %% : Venator trop"
              " faible (augmenter PORTEE_DETECTION_VENATOR ou"
              " VITESSE_POURSUITE)." % (100 * taux, 100 * haut))
    else:
        print("  [CALIBRATION] Survie %.0f %% : dans la cible %.0f-%.0f %%. OK."
              % (100 * taux, 100 * bas, 100 * haut))
    print("")


def main():
    args = analyser_arguments()

    if args.captures > 0:
        chemins, m = executer_captures(args)
        print("Captures generees :")
        for c in chemins:
            print("  " + c)
        afficher_metriques(m)
        return

    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from world import Monde
        from simulation import Simulation
        rng = np.random.default_rng(args.seed)
        monde = Monde(rng, t_env=args.tenv)
        sim = Simulation(monde, rng, n_pascor=args.pascor,
                         fabrique_controleur=fabrique_reactif(
                             monde, rng, args.preference))
        m = sim.executer_headless()
        print(monde.resume())
        afficher_metriques(m)
        return

    from simulation import executer_visuel
    m = executer_visuel(seed=args.seed, t_env=args.tenv, n_pascor=args.pascor,
                        preference=args.preference)
    afficher_metriques(m)


if __name__ == "__main__":
    sys.exit(main())
