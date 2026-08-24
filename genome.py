# -*- coding: utf-8 -*-
"""
Tabula Silico — Genome avec gene de plasticite (eta).

Etend le genome NEAT standard d'UN SEUL gene supplementaire : eta, le taux de
plasticite, scalaire dans [0, 1].

  eta = 0  -> le reseau ne bouge jamais apres la naissance : comportement
              entierement INNE.
  eta = 1  -> l'experience remodele fortement le reseau au cours de la vie :
              comportement fortement ACQUIS.

eta est HERITE, donc soumis a la selection au meme titre que la topologie et
les poids. C'est le point central du dispositif : on ne decide pas si Pascor
apprend, on observe ou la selection pousse ce curseur selon l'environnement.

Choix assume : UN SEUL eta scalaire par individu, et non un coefficient de
plasticite par connexion. Une plasticite par connexion serait plus realiste
biologiquement, mais il n'y aurait alors plus de nombre unique a tracer :
il faudrait resumer des dizaines de valeurs pour dessiner la figure de H1, et
ce choix de resume serait une decision arbitraire de plus. Piste d'extension,
pas d'objectif de cette version.

Compatible Python 3.9.
"""

import random

from neat.genome import DefaultGenome

import config


class GenomePlastique(DefaultGenome):
    """Genome NEAT augmente du gene eta."""

    def configure_new(self, genome_config):
        super(GenomePlastique, self).configure_new(genome_config)
        # Initialisation uniforme sur [0, 1] : aucun a priori sur l'inne ou
        # l'acquis. C'est a la selection de trancher, pas a nous.
        self.eta = random.uniform(config.ETA_INIT_MIN, config.ETA_INIT_MAX)
        # Preferences alimentaires INNEES, une par type. C'est le socle inne de
        # la discrimination : ce avec quoi l'agent nait, avant toute
        # experience.
        self.preferences = [
            random.gauss(0.0, config.PREFERENCE_INIT_ECART)
            for _ in range(config.N_TYPES_NOURRITURE)]

    def configure_crossover(self, genome1, genome2, genome_config):
        super(GenomePlastique, self).configure_crossover(
            genome1, genome2, genome_config)
        # Moyenne parentale : eta est un trait quantitatif continu, la moyenne
        # est le modele d'heritage le plus simple et le plus standard pour ce
        # type de trait.
        e1 = getattr(genome1, "eta", config.ETA_DEFAUT)
        e2 = getattr(genome2, "eta", config.ETA_DEFAUT)
        self.eta = 0.5 * (e1 + e2)

        p1 = getattr(genome1, "preferences", None)
        p2 = getattr(genome2, "preferences", None)
        if p1 and p2:
            self.preferences = [0.5 * (a + b) for a, b in zip(p1, p2)]
        else:
            self.preferences = list(p1 or p2 or
                                    [0.0] * config.N_TYPES_NOURRITURE)

    def mutate(self, genome_config):
        super(GenomePlastique, self).mutate(genome_config)
        if random.random() < config.ETA_TAUX_MUTATION:
            self.eta += random.gauss(0.0, config.ETA_FORCE_MUTATION)
        # eta reste dans [0, 1] : une plasticite negative n'a pas de sens, et
        # au dela de 1 la regle hebbienne diverge.
        self.eta = max(0.0, min(1.0, self.eta))

        if not hasattr(self, "preferences"):
            self.preferences = [0.0] * config.N_TYPES_NOURRITURE
        for i in range(len(self.preferences)):
            if random.random() < config.PREFERENCE_TAUX_MUTATION:
                self.preferences[i] += random.gauss(
                    0.0, config.PREFERENCE_FORCE_MUTATION)
            self.preferences[i] = max(
                config.PREFERENCE_MIN,
                min(config.PREFERENCE_MAX, self.preferences[i]))

    def distance(self, other, genome_config):
        d = super(GenomePlastique, self).distance(other, genome_config)
        # eta participe a la distance genetique, donc a la speciation : deux
        # individus de meme topologie mais de strategies opposees (tout inne
        # contre tout acquis) ne sont pas le meme phenotype et ne devraient pas
        # etre systematiquement regroupes dans la meme espece.
        e1 = getattr(self, "eta", config.ETA_DEFAUT)
        e2 = getattr(other, "eta", config.ETA_DEFAUT)
        d += config.ETA_POIDS_DISTANCE * abs(e1 - e2)

        # Meme raison pour les preferences innees : deux individus de
        # preferences opposees ont des strategies alimentaires opposees.
        p1 = getattr(self, "preferences", None)
        p2 = getattr(other, "preferences", None)
        if p1 and p2:
            d += sum(abs(a - b) for a, b in zip(p1, p2)) / float(len(p1))
        return d
