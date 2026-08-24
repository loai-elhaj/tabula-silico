# -*- coding: utf-8 -*-
"""
Tabula Silico — Cerveau : reseau NEAT a plasticite hebbienne modulee.

Deux composantes distinctes, qui incarnent les deux termes du projet :

  INNE   : la topologie et les poids issus du genome NEAT. Presents des la
           naissance, hérités, independants de toute experience.
  ACQUIS : les modifications de poids survenues au cours de la vie, sous
           l'effet de la regle hebbienne modulee par recompense. Elles
           MEURENT avec l'individu et ne se transmettent pas.

Regle d'apprentissage : regle a trois facteurs (pre-synaptique,
post-synaptique, neuromodulateur), avec traces d'eligibilite.

  1. A chaque pas de temps, chaque connexion accumule une trace d'eligibilite
     proportionnelle au produit des activites pre et post :
         e_ij <- lambda * e_ij + pre_i * post_j
  2. Quand une recompense arrive (ingestion : +25 nutritif, -25 toxique), les
     poids sont mis a jour proportionnellement a leur trace :
         w_ij <- w_ij + eta * r * e_ij

La trace d'eligibilite resout le probleme d'attribution du credit : la
recompense arrive au moment de l'ingestion, mais le motif sensoriel pertinent
(voir tel type d'aliment) a precede la decision de quelques pas de temps. Sans
trace, l'agent ne pourrait pas relier la consequence a la cause.

Le signal de recompense n'est pas invente pour les besoins du modele : c'est
litteralement le gain ou la perte d'energie alimentaire.

Compatible Python 3.9.
"""

import math
import numpy as np

import config


def _tanh(x):
    """Activation tanh, identique a celle de neat-python.

    Le choix de tanh plutot que sigmoide n'est PAS cosmetique, c'est ce qui
    rend l'apprentissage discriminant possible.

    Avec une sigmoide, toutes les activations sont dans [0, 1], donc le produit
    pre x post de la trace d'eligibilite est TOUJOURS positif. Une recompense
    negative fait alors baisser tous les poids ensemble, une recompense
    positive les fait tous monter. L'agent ne peut apprendre que "manger plus"
    ou "manger moins" globalement — jamais "manger ceci plutot que cela".
    Mesure sur la version sigmoide : 48 traces positives sur 48, et les 48
    poids baissant ensemble apres une recompense negative. D'ou un DeltaP nul
    malgre des poids qui bougeaient amplement.

    Avec tanh, les activations sont dans [-1, 1] : le produit pre x post peut
    etre positif (neurones co-actifs) ou negatif (neurones en opposition). La
    mise a jour devient selective PAR VOIE, ce qui permet d'affaiblir
    "capteur type A -> ingerer" tout en renforcant "capteur type B -> ingerer".

    Le gain (config.GAIN_ACTIVATION) est volontairement plus faible que le
    2.5 par defaut de neat-python. Avec 16 entrees et des poids initiaux
    d'ecart-type 1, la somme ponderee atteint typiquement +-2, que tanh(2.5x)
    ecrase a +-1 : mesure sur la version initiale, 59 % des sorties etaient
    saturees. Un reseau sature est une fonction CONSTANTE — il ignore ses
    capteurs, et ni l'inne ni l'acquis ne peuvent s'exprimer.
    """
    return math.tanh(max(-60.0, min(60.0, config.GAIN_ACTIVATION * x)))


class CerveauPlastique(object):
    """Reseau feedforward issu d'un genome NEAT, a poids modifiables.

    Interface `agir(entrees) -> (rotation, poussee, ingestion)`, identique a
    celle de ControleurReactif : les deux sont interchangeables.
    """

    def __init__(self, genome, neat_config, eta=None, plasticite_active=True,
                 preferences_initiales=None):
        self.eta = (getattr(genome, "eta", config.ETA_DEFAUT)
                    if eta is None else eta)
        # Le gel de la plasticite est ce qui permet d'evaluer DEUX FOIS le
        # meme genome : une fois inne pur (P_naif), une fois avec apprentissage
        # (P_libre). L'ecart entre les deux est la mesure de l'acquis.
        self.plasticite_active = plasticite_active and self.eta > 0.0

        self._construire(genome, neat_config)

        # -- PREFERENCES ALIMENTAIRES : le substrat dedie de l'apprentissage
        # Valeurs INNEES conservees intactes : elles permettent de mesurer
        # exactement ce que l'individu a acquis au cours de sa vie.
        innees = getattr(genome, "preferences", None)
        if preferences_initiales is not None:
            # Permet de NEUTRALISER les preferences innees tout en gardant le
            # reseau evolue : c'est la lesion "acquis seul", qui demande si
            # l'apprentissage peut reconstruire a lui seul ce que l'evolution
            # avait encode.
            innees = list(preferences_initiales)
        if not innees:
            innees = [0.0] * config.N_TYPES_NOURRITURE
        self.preferences_innees = list(innees)
        self.preferences = list(innees)

        # Cout d'apprentissage realise : somme des |delta w| sur la vie.
        # C'est cette quantite qui sera penalisee dans la fitness (lambda_cout).
        self.cout_realise = 0.0
        self.n_mises_a_jour = 0
        # Dernier type percu au contact : sert a attribuer la recompense a la
        # bonne preference.
        self.dernier_type_au_contact = None

    # -- Construction depuis le genome NEAT ---------------------------------

    def _construire(self, genome, neat_config):
        cles_entrees = list(neat_config.genome_config.input_keys)
        cles_sorties = list(neat_config.genome_config.output_keys)

        connexions = [(cle, cg) for cle, cg in genome.connections.items()
                      if cg.enabled]

        # Ordre d'evaluation : tri topologique des noeuds internes et de sortie
        requis = set(cles_sorties)
        noeuds_evaluables = set(cles_entrees)
        ordre = []
        restants = set(genome.nodes.keys())

        # Iteration jusqu'a stabilisation : un noeud est evaluable quand toutes
        # ses entrees le sont deja.
        progres = True
        while restants and progres:
            progres = False
            for cle in sorted(restants):
                entrants = [i for (i, o), _ in connexions if o == cle]
                if all(i in noeuds_evaluables for i in entrants):
                    ordre.append(cle)
                    noeuds_evaluables.add(cle)
                    restants.discard(cle)
                    progres = True
                    break
        # Les noeuds restants font partie de cycles : on les ajoute a la fin
        # (leurs entrees non encore calculees valent 0 au premier passage).
        for cle in sorted(restants):
            ordre.append(cle)
            noeuds_evaluables.add(cle)

        self.cles_entrees = cles_entrees
        self.cles_sorties = cles_sorties
        self.ordre = ordre

        self.biais = {cle: genome.nodes[cle].bias for cle in ordre}
        # Entrants par noeud : liste de (cle_source, index_dans_poids)
        self.entrants = {cle: [] for cle in ordre}
        self.aretes = []
        poids = []
        for (i, o), cg in connexions:
            if o not in self.entrants:
                continue
            self.entrants[o].append((i, len(poids)))
            self.aretes.append((i, o))
            poids.append(cg.weight)

        # Poids INNES : conserves intacts pour pouvoir mesurer l'ampleur des
        # modifications acquises au cours de la vie.
        self.poids_innes = np.array(poids, dtype=np.float64)
        self.poids = self.poids_innes.copy()
        self.eligibilite = np.zeros(len(poids), dtype=np.float64)

        self.activations = {}

    # -- Fonctionnement -----------------------------------------------------

    def agir(self, entrees):
        a = self.activations
        for cle, valeur in zip(self.cles_entrees, entrees):
            a[cle] = float(valeur)

        for cle in self.ordre:
            total = self.biais[cle]
            for (source, idx) in self.entrants[cle]:
                total += a.get(source, 0.0) * self.poids[idx]
            a[cle] = _tanh(total)

        if self.plasticite_active:
            self._accumuler_eligibilite()

        sorties = [a.get(cle, 0.0) for cle in self.cles_sorties]
        # Les sorties tanh sont dans [-1, 1].
        # rotation  : utilisee telle quelle, le domaine correspond deja.
        # poussee   : ramenee dans [0, 1].
        # ingestion : ramenee dans [0, 1], PUIS modulee par la preference
        #             alimentaire du type percu au contact.
        rotation = sorties[0] if len(sorties) > 0 else 0.0
        poussee = 0.5 * (sorties[1] + 1.0) if len(sorties) > 1 else 0.5
        ingestion = 0.5 * (sorties[2] + 1.0) if len(sorties) > 2 else 1.0

        # -- Modulation par la preference alimentaire
        # Le type le plus proche au contact est identifie a partir des canaux
        # sensoriels, et sa preference (innee puis ajustee par l'experience)
        # pondere directement la decision d'ingerer.
        type_contact = self._type_au_contact(entrees)
        self.dernier_type_au_contact = type_contact
        if type_contact is not None:
            pref = self.preferences[type_contact]
            ingestion = ingestion + config.PREFERENCE_POIDS_DECISION * pref
            ingestion = max(0.0, min(1.0, ingestion))
        return rotation, poussee, ingestion

    def _type_au_contact(self, entrees):
        """Type d'aliment le plus proche dans le champ de vision, ou None."""
        meilleur, valeur = None, 0.25   # seuil : ignorer ce qui est lointain
        n = config.N_SECTEURS
        for t in range(config.N_TYPES_NOURRITURE):
            v = max(entrees[t * n:(t + 1) * n])
            if v > valeur:
                valeur, meilleur = v, t
        return meilleur

    def _accumuler_eligibilite(self):
        """Accumule la trace pre x post sur chaque connexion.

        Le facteur post-synaptique est RECTIFIE dans [0, 1] par (post + 1) / 2,
        alors que les activations circulent dans [-1, 1].

        Sans cette rectification, le SENS de l'apprentissage dependait du signe
        d'une activation, et non de la recompense :
          - post > 0 (agent enclin a ingerer) + recompense negative
              -> le poids baisse. Correct.
          - post < 0 (agent peu enclin)       + recompense negative
              -> pre x post est negatif, multiplie par une recompense negative,
                 le poids MONTE. L'agent devient PLUS enclin a manger le
                 toxique. Exactement l'inverse.

        Mesure de ce defaut : sur 40 reseaux, seulement 25 apprenaient dans le
        bon sens (17 avaient une sortie d'ingestion negative). Les bons et les
        mauvais sens s'annulaient en moyenne — d'ou un DeltaP nul.

        Rectification par max(0, x) et NON par (x + 1) / 2. La difference est
        decisive : (x + 1) / 2 transforme une activation nulle en 0,5, donc un
        capteur qui ne detecte RIEN accumulerait quand meme de l'eligibilite,
        et son poids serait modifie par une recompense qui ne le concerne pas.
        Mesure de cette erreur : le sens redevenait correct pour le nutritif
        (34/40) mais s'effondrait pour le toxique (14/40), la selectivite ayant
        disparu. max(0, x) preserve le zero : capteur inactif, pas
        d'eligibilite, pas d'apprentissage.

        Consequence assumee : un agent dont la sortie d'ingestion est negative
        n'apprend rien. C'est ecologiquement juste — on n'apprend pas d'un
        aliment qu'on n'a jamais goute — et cela correspond au fonctionnement
        reel, ou l'ingestion n'a lieu que si la sortie depasse le seuil.
        """
        a = self.activations
        self.eligibilite *= config.TRACE_DECROISSANCE
        for idx, (source, cible) in enumerate(self.aretes):
            pre = a.get(source, 0.0)
            if pre <= 0.0:
                continue
            post = a.get(cible, 0.0)
            if post <= 0.0:
                continue
            self.eligibilite[idx] += pre * post

    def recompenser(self, signal):
        """Applique la mise a jour hebbienne suite a un evenement d'ingestion.

        `signal` est le delta d'energie : positif pour un aliment nutritif,
        negatif pour un aliment toxique. C'est le troisieme facteur
        (neuromodulateur) de la regle.
        """
        if not self.plasticite_active or signal == 0.0:
            return

        # -- APPRENTISSAGE DE LA PREFERENCE (substrat dedie)
        # C'est ici que l'ACQUIS se construit. La preference du type qui vient
        # d'etre ingere se deplace vers la consequence subie : vers +1 si
        # l'aliment etait nutritif, vers -1 s'il etait toxique.
        #
        # Le taux est regle pour qu'une poignee de degustations suffise a
        # inverser une preference — conformement a l'aversion gustative
        # conditionnee (effet Garcia), qui est un apprentissage en un seul
        # essai, et non a une derive graduelle sur des centaines d'evenements.
        t = self.dernier_type_au_contact
        if t is not None:
            cible = 1.0 if signal > 0.0 else -1.0
            taux = self.eta * config.TAUX_APPRENTISSAGE_PREFERENCE
            avant = self.preferences[t]
            self.preferences[t] += taux * (cible - avant)
            self.preferences[t] = max(
                config.PREFERENCE_MIN,
                min(config.PREFERENCE_MAX, self.preferences[t]))
            # Le cout de l'apprentissage inclut ce deplacement : modifier une
            # preference n'est pas gratuit.
            self.cout_realise += abs(self.preferences[t] - avant)

        # -- Plasticite hebbienne sur les poids (conservee, secondaire)
        # Normalisation vers [-1, +1], chaque signe par sa propre echelle.
        #
        # Ce decouplage est deliberé : les gains alimentaires sont volontairement
        # ASYMETRIQUES (+25 / -10, cf. config), mais la SAILLANCE du signal
        # d'apprentissage, elle, reste symetrique. Sans cela, un aliment toxique
        # produirait un signal 2,5 fois plus faible qu'un nutritif, et l'agent
        # apprendrait mal l'aversion — precisement ce qu'on veut qu'il apprenne.
        echelle = (config.VALEUR_NOURRITURE if signal > 0.0
                   else config.VALEUR_TOXIQUE)
        r = signal / echelle
        delta = self.eta * config.TAUX_HEBBIEN * r * self.eligibilite

        self.poids += delta
        # Bornage : sans lui, la regle hebbienne diverge (les poids forts
        # produisent des activites fortes, qui renforcent les poids).
        np.clip(self.poids, -config.POIDS_MAX, config.POIDS_MAX,
                out=self.poids)

        # Cout realise de l'apprentissage : c'est ce que lambda_cout penalise.
        self.cout_realise += float(np.abs(delta).sum())
        self.n_mises_a_jour += 1

        # La trace est consommee par la recompense.
        self.eligibilite *= config.TRACE_APRES_RECOMPENSE

    def decroissance_homeostatique(self):
        """Ramene lentement les poids vers leurs valeurs INNEES.

        Sans ce rappel, toute modification acquise serait definitive et
        s'accumulerait sans limite au cours de la vie. Ce terme borne la
        derive, et donne un sens biologique a l'inne comme point d'equilibre
        vers lequel le systeme revient en l'absence de renforcement.
        """
        if not self.plasticite_active:
            return
        self.poids += config.DECROISSANCE_HOMEOSTATIQUE * (
            self.poids_innes - self.poids)

    # -- Introspection ------------------------------------------------------

    def derive_acquise(self):
        """Ampleur des modifications acquises, en ecart aux poids innes."""
        if len(self.poids) == 0:
            return 0.0
        return float(np.abs(self.poids - self.poids_innes).mean())

    def derive_preference(self):
        """Ecart entre preferences acquises et preferences innees.

        C'est la mesure directe de l'ACQUIS sur le substrat dedie : de combien
        l'experience de cet individu a deplace ce avec quoi il est ne.
        """
        if not self.preferences_innees:
            return 0.0
        return float(np.mean([abs(a - b) for a, b in
                              zip(self.preferences, self.preferences_innees)]))

    def discrimination_preferee(self, type_nutritif):
        """Ecart de preference en faveur du type comestible.

        Positif = l'agent prefere le nutritif au toxique. C'est la mesure de la
        qualite de sa strategie alimentaire, innee ou acquise selon qu'on
        l'interroge sur preferences_innees ou preferences.
        """
        toxique = 1 - type_nutritif
        return self.preferences[type_nutritif] - self.preferences[toxique]
