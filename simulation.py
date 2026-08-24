# -*- coding: utf-8 -*-
"""
Tabula Silico — Boucle de simulation.

Deux modes, prevus des l'architecture pour ne pas avoir a tout retravailler
au moment des balayages de parametres :
  - mode visuel   : fenetre pygame, pour le pilote, la calibration et les GIF ;
  - mode headless : aucun affichage, beaucoup plus rapide, pour les series
                    experimentales.

Les metriques collectees suivent la specification (tabula_silico_metriques.md).

Compatible Python 3.9.
"""

import math
import numpy as np

import config
from world import Monde
from agents import Pascor, Venator, ControleurReactif
from perception import percevoir_tous


class Simulation(object):
    """Une evaluation : une cohorte de Pascor vivant dans un monde donne."""

    def __init__(self, monde, rng, fabrique_controleur=None, n_pascor=None):
        self.monde = monde
        self.rng = rng
        self.tick_courant = 0

        if fabrique_controleur is None:
            fabrique_controleur = lambda: ControleurReactif(rng)

        n = n_pascor if n_pascor is not None else config.N_PASCOR
        self.pascors = []
        for _ in range(n):
            self.pascors.append(Pascor(
                x=rng.uniform(0.0, monde.largeur),
                y=rng.uniform(0.0, monde.hauteur),
                cap=rng.uniform(0.0, 2.0 * math.pi),
                controleur=fabrique_controleur()))

        n_venator = max(1, n // config.RATIO_VENATOR)
        self.venators = []
        for _ in range(n_venator):
            self.venators.append(Venator(
                x=rng.uniform(0.0, monde.largeur),
                y=rng.uniform(0.0, monde.hauteur),
                cap=rng.uniform(0.0, 2.0 * math.pi),
                rng=rng))

        # Journal des evenements du tick courant (pour les effets visuels)
        self.repas_du_tick = []
        self.captures_du_tick = []

    # -- Dynamique ----------------------------------------------------------

    def tick(self):
        """Un pas de temps de la simulation entiere."""
        self.repas_du_tick = []
        self.captures_du_tick = []

        self.monde.tick()

        # Perception de tous les agents vivants en une seule passe numpy.
        vivants = [p for p in self.pascors if p.vivant]
        lot_entrees = percevoir_tous(vivants, self.monde, self.venators)

        for i, p in enumerate(vivants):
            idx_item, delta = p.avancer(self.monde, self.venators,
                                        entrees=lot_entrees[i])
            if idx_item is not None:
                self.repas_du_tick.append((p.x, p.y, delta > 0.0))

        for v in self.venators:
            proie = v.avancer(self.monde, self.pascors)
            if proie is not None:
                self.captures_du_tick.append((proie.x, proie.y))

        self.tick_courant += 1

    def termine(self):
        """La simulation s'arrete quand tout le monde est mort ou trop vieux."""
        if self.tick_courant >= config.DUREE_VIE_MAX:
            return True
        return not any(p.vivant for p in self.pascors)

    def executer_headless(self, max_ticks=None):
        """Fait tourner la simulation sans aucun affichage."""
        limite = max_ticks if max_ticks is not None else config.DUREE_VIE_MAX
        while self.tick_courant < limite and not self.termine():
            self.tick()
        return self.metriques()

    # -- Metriques ----------------------------------------------------------

    def metriques(self):
        """Metriques agregees de la cohorte, conformes a la specification."""
        n = len(self.pascors)
        # "Survivre" = atteindre le terme de sa duree de vie. Mourir de
        # vieillesse est un succes biologique, pas un echec : ne comptent comme
        # morts que la famine et la predation.
        survivants = [p for p in self.pascors
                      if p.vivant or p.cause_mort == "vieillesse"]
        mangee = np.array([p.nourriture_mangee for p in self.pascors],
                          dtype=np.float64)
        distances = np.array([p.distance_parcourue for p in self.pascors],
                             dtype=np.float64)
        ages = np.array([p.age for p in self.pascors], dtype=np.float64)

        # Efficacite de foraging : nourriture par unite de distance parcourue
        with np.errstate(divide="ignore", invalid="ignore"):
            efficacite = np.where(distances > 0.0, mangee / distances, 0.0)

        # Taux d'evitement de Venator
        rencontres = sum(p.rencontres_venator for p in self.pascors)
        predations = sum(1 for p in self.pascors if p.cause_mort == "predation")
        taux_evitement = (1.0 - predations / float(rencontres)
                          if rencontres > 0 else float("nan"))

        # Courbe d'apprentissage intra-vie : 1er tiers vs dernier tiers.
        # N'a de sens que pour les individus ayant reellement vecu les trois
        # tiers ; les morts precoces biaiseraient la comparaison.
        seuil_age = int(config.DUREE_VIE_MAX * 0.99)
        complets = [p for p in self.pascors if p.age >= seuil_age]

        if complets:
            premier_tiers = float(np.mean([p.mangee_par_tiers[0]
                                           for p in complets]))
            dernier_tiers = float(np.mean([p.mangee_par_tiers[2]
                                           for p in complets]))
        else:
            premier_tiers = float("nan")
            dernier_tiers = float("nan")

        # -- Discrimination alimentaire (metrique centrale du dispositif)
        nutritifs = np.array([p.nutritifs_manges for p in self.pascors],
                             dtype=np.float64)
        toxiques = np.array([p.toxiques_manges for p in self.pascors],
                            dtype=np.float64)
        total_repas = nutritifs.sum() + toxiques.sum()
        # 0.5 = aucune discrimination (hasard), 1.0 = discrimination parfaite
        taux_discrimination = (float(nutritifs.sum() / total_repas)
                               if total_repas > 0 else float("nan"))

        # Taux de discrimination par tiers de vie, sur les individus ayant
        # vecu les trois tiers. C'est la mesure de H3c : chez un agent
        # plastique, ce taux doit AUGMENTER au fil de la vie. Chez un agent
        # fige, il doit rester plat — c'est la ligne de base indispensable
        # pour ne pas confondre apprentissage et installation spatiale.
        discrimination_par_tiers = []
        for t in range(3):
            nut = sum(p.nutritifs_par_tiers[t] for p in complets)
            tox = sum(p.toxiques_par_tiers[t] for p in complets)
            discrimination_par_tiers.append(
                nut / float(nut + tox) if (nut + tox) > 0 else float("nan"))

        causes = {}
        for p in self.pascors:
            cle = p.cause_mort if p.cause_mort else "vivant"
            causes[cle] = causes.get(cle, 0) + 1

        return {
            "n_pascor": n,
            "n_survivants": len(survivants),
            "taux_survie": len(survivants) / float(n) if n else 0.0,
            "nourriture_moyenne": float(mangee.mean()) if n else 0.0,
            "nourriture_totale": float(mangee.sum()),
            "nutritifs_moyen": float(nutritifs.mean()) if n else 0.0,
            "toxiques_moyen": float(toxiques.mean()) if n else 0.0,
            "taux_discrimination": taux_discrimination,
            "discrimination_par_tiers": discrimination_par_tiers,
            "repas_par_vie_complete": (
                float(np.mean([p.nourriture_mangee for p in complets]))
                if complets else float("nan")),
            "age_moyen": float(ages.mean()) if n else 0.0,
            "efficacite_foraging": float(efficacite.mean()) if n else 0.0,
            "rencontres_venator": rencontres,
            "captures": predations,
            "taux_evitement": taux_evitement,
            "mangee_1er_tiers": premier_tiers,
            "mangee_3e_tiers": dernier_tiers,
            "causes_mort": causes,
            "ticks": self.tick_courant,
        }


# ---------------------------------------------------------------------------
# Mode visuel
# ---------------------------------------------------------------------------

def executer_visuel(seed=config.SEED_DEFAUT, t_env=config.T_ENV_DEFAUT,
                    n_pascor=None, preference="correcte"):
    """Lance la simulation dans une fenetre pygame.

    Commandes (compatibles AZERTY) :
      ESPACE  pause          S  capteurs       T  trainees
      F       HUD            O  ralentir       P  accelerer
      R       relancer       ECHAP  quitter
    """
    import pygame
    from render import Rendu

    pygame.init()
    rng = np.random.default_rng(seed)
    monde = Monde(rng, t_env=t_env)

    def _fabrique(m):
        if preference == "correcte":
            pref = m.type_nutritif
        elif preference == "fausse":
            pref = 1 - m.type_nutritif
        else:
            pref = None
        return lambda: ControleurReactif(rng, preference=pref)

    sim = Simulation(monde, rng, n_pascor=n_pascor,
                     fabrique_controleur=_fabrique(monde))
    rendu = Rendu()
    horloge = pygame.time.Clock()

    en_pause = False
    vitesse = 1
    actif = True

    while actif:
        for evenement in pygame.event.get():
            if evenement.type == pygame.QUIT:
                actif = False
            elif evenement.type == pygame.KEYDOWN:
                if evenement.key == pygame.K_ESCAPE:
                    actif = False
                elif evenement.key == pygame.K_SPACE:
                    en_pause = not en_pause
                elif evenement.key == pygame.K_s:
                    config.AFFICHER_CAPTEURS = not config.AFFICHER_CAPTEURS
                elif evenement.key == pygame.K_t:
                    config.AFFICHER_TRAINEES = not config.AFFICHER_TRAINEES
                elif evenement.key == pygame.K_f:
                    config.AFFICHER_HUD = not config.AFFICHER_HUD
                elif evenement.key == pygame.K_o:
                    vitesse = max(1, vitesse - 1)
                elif evenement.key == pygame.K_p:
                    vitesse = min(10, vitesse + 1)
                elif evenement.key == pygame.K_r:
                    rng = np.random.default_rng(rng.integers(1 << 30))
                    monde = Monde(rng, t_env=t_env)
                    sim = Simulation(monde, rng, n_pascor=n_pascor,
                                     fabrique_controleur=_fabrique(monde))

        if not en_pause:
            for _ in range(vitesse):
                if sim.termine():
                    break
                sim.tick()
                for (x, y, nutritif) in sim.repas_du_tick:
                    rendu.ajouter_effet(
                        x, y, "repas" if nutritif else "toxique",
                        sim.tick_courant)
                for (x, y) in sim.captures_du_tick:
                    rendu.ajouter_effet(x, y, "capture", sim.tick_courant)

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
            ("Discrimination", ("%.0f %%" % (100 * m["taux_discrimination"]))
             if m["taux_discrimination"] == m["taux_discrimination"] else "n/a"),
            ("Captures", m["captures"]),
            ("Vitesse", "x%d%s" % (vitesse, "  [PAUSE]" if en_pause else "")),
        ]
        rendu.dessiner(monde, sim.pascors, sim.venators, infos, tick=sim.tick_courant)
        pygame.display.flip()
        horloge.tick(config.FPS)

    pygame.quit()
    return sim.metriques()
