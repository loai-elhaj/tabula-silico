# -*- coding: utf-8 -*-
"""
Tabula Silico — Configuration centrale.

Tous les parametres de la simulation sont regroupes ici. Les valeurs marquees
[CALIBRER] doivent etre ajustees empiriquement lors du pilote (etape 4 de la
todo), pas choisies arbitrairement.

Compatible Python 3.9.
"""

import math

# ---------------------------------------------------------------------------
# PALETTE
# ---------------------------------------------------------------------------
# Palette unique du projet. A reutiliser telle quelle dans les figures
# matplotlib de l'analyse statistique, pour que la simulation et les graphiques
# du README se repondent visuellement.

PALETTE = {
    "fond":          (15, 23, 42),      # #0F172A ardoise tres sombre
    "fond_clair":    (26, 37, 62),      # variation pour le degrade de fond
    "nourriture":    (251, 191, 36),    # #FBBF24 ambre dore (type A)
    "nourriture_b":  (56, 189, 248),    # #38BDF8 cyan (type B)
    "pascor":        (52, 211, 153),    # #34D399 emeraude
    "pascor_sombre": (16, 122, 90),     # ombre / pattes de Pascor
    "venator":       (239, 68, 68),     # #EF4444 rouge corail
    "venator_sombre": (140, 30, 30),    # ombre / pattes de Venator
    "accent":        (167, 139, 250),   # #A78BFA violet doux (capteurs, HUD)
    "texte":         (241, 245, 249),   # #F1F5F9 blanc casse
    "texte_faible":  (110, 125, 150),   # texte secondaire
}

# ---------------------------------------------------------------------------
# ARENE
# ---------------------------------------------------------------------------

LARGEUR = 1600.0
HAUTEUR = 900.0

# Espace toroidal : les bords se rebouclent (facon Pac-Man). Evite les coins
# qui deviendraient des pieges ou des refuges artificiels, sans rapport avec la
# pression ecologique etudiee.
TOROIDAL = True

# ---------------------------------------------------------------------------
# NOURRITURE, TYPES ET VOLATILITE ENVIRONNEMENTALE
# ---------------------------------------------------------------------------

# DEUX TYPES DE NOURRITURE, perceptivement distincts (canaux sensoriels
# separes, couleurs et formes distinctes a l'ecran). A chaque changement
# d'environnement, l'un est NUTRITIF et l'autre TOXIQUE, et lequel est lequel
# s'inverse.
#
# C'est LE dispositif central du projet. L'apprentissage n'a de sens que s'il
# existe une information imprevisible a la naissance mais decouvrable au cours
# de la vie : ici, quel type est comestible cette generation-ci.
#   - Strategie INNEE   : preference fixe pour un type, heritee. Gagne si
#                         l'environnement est stable.
#   - Strategie ACQUISE : gouter, subir la consequence, ajuster. Gagne si
#                         l'environnement change entre generations.
#
# Le cout de l'apprentissage est ici INTRINSEQUE, pas ajoute a la main : pour
# decouvrir quel type est bon, il faut gouter le mauvais et le payer. C'est
# exactement le cout decrit par Johnston (1982) et Dukas (1998).

N_TYPES_NOURRITURE = 2
N_PATCHS = 10              # nombre de zones de nourriture
ITEMS_PAR_PATCH = 14       # items de nourriture par zone
RAYON_PATCH = 110.0        # dispersion des items autour du centre de la zone
RAYON_ITEM = 6.0           # rayon de collision d'un item
VALEUR_NOURRITURE = 25.0   # energie gagnee en mangeant le type NUTRITIF
VALEUR_TOXIQUE = 10.0      # energie PERDUE en mangeant le type TOXIQUE
#
# ASYMETRIE VOLONTAIRE (+25 / -10), et non symetrie (+25 / -25).
#
# Avec des gains symetriques, manger un aliment AU HASARD a une esperance de
# gain nulle : (25 - 25) / 2 = 0. Aucun benefice, mais de la variance ajoutee —
# et pres du seuil de mort (energie 0), la variance tue. La selection elimine
# alors le comportement de manger lui-meme.
#
# Mesure de ce piege (run T_env=maximale, 60 generations, gains symetriques) :
# les repas passent de 4,0 a 0,5 par vie et la survie tombe a 0,1 %. Les agents
# evoluent vers le refus total de s'alimenter, et meurent de faim.
#
# C'est fatal pour la question du projet : pour apprendre quel type est
# comestible, il faut gouter ; mais gouter etait si dangereux que la selection
# supprimait le fait de gouter AVANT que l'apprentissage puisse devenir
# rentable. Probleme de la poule et de l'oeuf.
#
# Avec l'asymetrie :
#   manger au hasard  -> esperance (25 - 10) / 2 = +7,5  : gouter est rentable,
#                        donc les agents mangent, donc l'apprentissage recoit
#                        des donnees.
#   discriminer       -> esperance +25            : discriminer reste nettement
#                        meilleur, donc l'apprentissage a une raison de payer.
# Le gradient necessaire existe enfin : gouter > s'abstenir, bien gouter >
# gouter au hasard.
DELAI_REPOUSSE = 60        # ticks avant qu'un item consomme reapparaisse

# T_env : nombre de generations entre deux changements d'environnement.
# Un changement d'environnement = les centres de patchs sont retires ET la
# validite des types s'inverse (le nutritif devient toxique et inversement).
# C'est LE parametre manipule pour l'hypothese H1.
# None = environnement stable (un seul tirage au debut du run).
#
# Note : avec des capteurs purement egocentriques, seule l'inversion de
# validite des types est fonctionnellement apprenable. Le deplacement des
# patchs ne change rien a la strategie optimale ("je vois de la nourriture
# dans le secteur 3 -> je tourne vers 3"), il n'est conserve que pour eviter
# toute memorisation implicite de la disposition entre generations.
T_ENV_NIVEAUX = {
    "stable":         None,
    "faible":         50,
    "intermediaire":  15,
    "forte":          5,
    "maximale":       1,
}
T_ENV_DEFAUT = "intermediaire"

# ---------------------------------------------------------------------------
# VOLATILITE INTRA-VIE : le second axe, indispensable a H1
# ---------------------------------------------------------------------------
# T_env ci-dessus gouverne la volatilite INTER-GENERATIONNELLE. Elle permet de
# tester la branche MONTANTE de la prediction de Stephens : plus
# l'environnement change entre generations, plus l'inne devient inutile et
# plus la selection favorise la plasticite.
#
# Mais la branche DESCENDANTE de la cloche vient d'un autre phenomene : quand
# l'environnement change AU COURS DE LA VIE d'un individu, ce qu'il apprend
# devient obsolete avant de servir, et la plasticite perd son avantage a son
# tour.
#
# Le dispositif initial fixait l'environnement pendant toute la vie (invariant
# verifie par test : deplacement 0,0 sur 3000 ticks). Ce choix etait justifie —
# sans stabilite intra-vie, l'apprentissage n'aurait eu aucun substrat stable —
# mais il excluait PAR CONSTRUCTION le regime ou la plasticite cesse d'etre
# utile. Mesure : eta croit de facon monotone avec la volatilite
# inter-generationnelle (0,330 -> 0,441, correlation de rang 0,925), sans
# jamais redescendre.
#
# N_INVERSIONS_INTRA_VIE = nombre de basculements de la validite des types
# pendant une vie (repartis uniformement sur DUREE_VIE_MAX).
#   0  : environnement stable pendant la vie (comportement d'origine)
#   1  : un basculement a mi-vie — l'agent doit reapprendre une fois
#   3  : trois basculements — l'apprentissage a encore le temps de servir
#   9  : basculements frequents — ce qui est appris devient vite obsolete
#  29  : quasi-imprevisible — la plasticite ne peut plus rien apporter
V_VIE_NIVEAUX = {
    "nulle":     0,
    "lente":     1,
    "moderee":   3,
    "rapide":    9,
    "chaotique": 29,
}
V_VIE_DEFAUT = "nulle"

# ---------------------------------------------------------------------------
# PASCOR (herbivore — le sujet d'etude)
# ---------------------------------------------------------------------------

N_PASCOR = 100             # taille de population (a valider au pilote)
RAYON_PASCOR = 9.0

# Perception : capteurs sectoriels facon robotique evolutionnaire.
# Le champ de vision est decoupe en N_SECTEURS secteurs egaux ; chaque secteur
# renvoie la proximite de l'objet le plus proche (1 = colle, 0 = hors portee).
N_SECTEURS = 5
CHAMP_VISION = math.radians(180.0)   # etendue totale, centree sur le cap
PORTEE_VISION = 260.0

# Entrees du reseau (point 3) : N_SECTEURS (nourriture type A)
# + N_SECTEURS (nourriture type B) + N_SECTEURS (Venator)
# + 1 (energie normalisee) = 16 entrees.
# Les deux types de nourriture ont des canaux SEPARES : sans cela, l'agent ne
# pourrait pas les distinguer, et aucune discrimination — innee ou apprise —
# ne serait possible.
N_ENTREES = 3 * N_SECTEURS + 1
# Sorties : rotation (-1..1), poussee (0..1), ingestion (0..1).
#
# L'ingestion est une DECISION, pas un automatisme. Sans cette sortie, l'agent
# avale tout ce qu'il touche et la discrimination alimentaire ne peut
# s'exprimer que par la navigation — impossible dans un patch ou les deux
# types sont melanges. C'est cette porte qui rend l'aversion alimentaire
# (innee ou apprise) exprimable, et donc mesurable.
N_SORTIES = 3

# INGESTION PROBABILISTE plutot que seuil dur.
#
# Avec un seuil dur, la sortie d'ingestion devait franchir 0,5 pour changer
# quoi que ce soit. Or l'apprentissage hebbien deplace cette sortie de ~2 %
# seulement (mesure : divergence +0,020 dans les conditions exactes de la
# simulation, z = 4,79). L'apprentissage etait donc REEL au niveau des poids,
# mais ne franchissait jamais le seuil : aucune decision ne changeait, donc
# aucun effet sur la fitness, donc rien a selectionner. C'est ce qui produisait
# un DeltaP nul malgre une regle qui fonctionne.
#
# En probabiliste, la sortie EST la probabilite d'ingerer. Le moindre
# deplacement se traduit immediatement en changement de comportement, de facon
# graduelle. La non-linearite qui bloquait tout disparait.
#
# C'est aussi plus plausible biologiquement : aucun animal n'applique un seuil
# parfaitement net a une tendance comportementale.
INGESTION_PROBABILISTE = True
SEUIL_INGESTION = 0.5           # utilise seulement si INGESTION_PROBABILISTE

VITESSE_MAX_PASCOR = 2.6        # unites / tick
ROTATION_MAX_PASCOR = 0.16      # radians / tick

# Energie
ENERGIE_INITIALE = 100.0
ENERGIE_MAX = 200.0
COUT_BASAL = 0.08               # energie perdue par tick, immobile
COUT_MOUVEMENT = 0.05           # energie perdue par tick, a poussee maximale

DUREE_VIE_MAX = 3000            # T_max, en ticks

# Cible : nombre d'evenements alimentaires par vie complete. C'est CE nombre,
# et non la duree de vie en ticks, qui determine si un apprentissage est
# possible : la plasticite hebbienne modulee par recompense a besoin d'un
# nombre suffisant de degustations pour extraire quel type est comestible.
# Avec les parametres initiaux (64 items, repousse 200 ticks, vie 1500), la
# mesure donnait 7,1 repas par vie — soit ~3,5 degustations par type, trop peu
# pour apprendre quoi que ce soit, et deja letal cote toxique.
CIBLE_REPAS_PAR_VIE = (40, 70)

# ---------------------------------------------------------------------------
# VENATOR (carnivore — pression de selection, comportement scripte)
# ---------------------------------------------------------------------------
# Venator n'evolue PAS. C'est une decision d'architecture deliberee : une
# coevolution proie-predateur ferait varier la difficulte de l'environnement
# independamment de nos deux axes experimentaux (volatilite, cout), et les
# confondrait.

RATIO_VENATOR = 20              # 1 Venator pour 20 Pascor
RAYON_VENATOR = 13.0

PORTEE_DETECTION_VENATOR = 130.0   # calibre (voir note ci-dessous)
RAYON_CAPTURE = 14.0               # distance de capture effective
VITESSE_PATROUILLE = 1.5
VITESSE_POURSUITE = 3.0            # [CALIBRER] ~1.15x la vitesse max de Pascor
ROTATION_MAX_VENATOR = 0.10
DUREE_POURSUITE_MAX = 180          # ticks avant abandon de la poursuite
SATIETE_APRES_CAPTURE = 300        # ticks d'inactivite predatrice apres capture
DERIVE_PATROUILLE = 0.05           # amplitude du changement de cap en patrouille

# CALIBRATION EFFECTUEE. La portee de detection et la satiete ont ete reglees
# par balayage APRES l'allongement de la duree de vie (1500 -> 3000 ticks) :
# doubler la duree de vie double mecaniquement l'exposition cumulee a la
# predation, qui etait passee de 35 % a 58 % des morts. Valeurs retenues :
# portee 130, satiete 300 -> ~29 % de predation, equilibre avec la famine.
#
# Cible de calibration (pilote) : viser 30-50 % de survie jusqu'au terme de la
# duree de vie. En dessous : la pression est si forte que le signal de fitness
# s'aplatit (presque tout le monde meurt tot, la selection n'a plus de prise).
# Au dessus : Venator devient decoratif.
#
# IMPORTANT — reference de mesure : cette cible se mesure avec le CONTROLEUR
# REACTIF (agents.ControleurReactif), pas avec des reseaux NEAT de la
# generation 0. Des reseaux initialises aleatoirement font bien pire que le
# controleur reflexe, et donneraient une reference instable d'un run a l'autre.
# Le controleur reactif fournit un etalon deterministe et reproductible d'un
# comportement "competent mais non evolue".
CIBLE_SURVIE_GEN0 = (0.30, 0.50)

# ---------------------------------------------------------------------------
# PLASTICITE : LE GENE ETA
# ---------------------------------------------------------------------------
# eta est un scalaire dans [0, 1], HERITE, qui multiplie l'amplitude de toutes
# les mises a jour hebbiennes. C'est la variable centrale du projet : la
# selection le pousse vers 0 (tout inne) ou vers 1 (tout acquis) selon
# l'environnement, et c'est precisement ce qu'on mesure.

ETA_DEFAUT = 0.5
ETA_INIT_MIN = 0.0              # initialisation uniforme sur [0, 1] :
ETA_INIT_MAX = 1.0              # aucun a priori inne/acquis au depart
ETA_TAUX_MUTATION = 0.25        # probabilite de muter eta a chaque generation
ETA_FORCE_MUTATION = 0.12       # ecart-type de la mutation gaussienne
ETA_POIDS_DISTANCE = 1.0        # poids d'eta dans la distance genetique

# ---------------------------------------------------------------------------
# PREFERENCE ALIMENTAIRE : LE SUBSTRAT DEDIE DE L'APPRENTISSAGE
# ---------------------------------------------------------------------------
# Pascor porte une preference alimentaire explicite : un scalaire par type,
# qui pondere directement sa decision d'ingestion.
#
#   INNE   : la valeur initiale de ces preferences, encodee dans le genome,
#            heritee, presente des la naissance.
#   ACQUIS : leur mise a jour au cours de la vie, par experience directe
#            (gouter -> subir la consequence). Meurt avec l'individu.
#   eta    : le taux de cette mise a jour, toujours herite, toujours soumis a
#            la selection. La question du projet est inchangee.
#
# POURQUOI un substrat dedie plutot que la plasticite hebbienne diffuse.
#
# L'information a apprendre ici est litteralement UN BIT : quel type est
# comestible cette generation-ci. La regle hebbienne devait le decouvrir en
# modifiant des dizaines de poids d'un reseau qui gere simultanement le
# deplacement, le fourrage et la fuite. Ce bit y etait DILUE — mesure sur
# 12 runs de 60 generations et quatre niveaux de volatilite : l'ecart de
# discrimination plastique-figee est reste sous 0,01 dans TOUTES les
# conditions, alors meme que les poids bougeaient (derive 0,067).
#
# Les implementations qui reproduisent l'effet Baldwin (Hinton & Nowlan 1987,
# Mayley 1996) font toutes apprendre sur un substrat dedie et de basse
# dimension, pas sur l'ensemble des parametres du controleur.
#
# C'est aussi plus juste biologiquement. L'aversion gustative conditionnee
# (effet Garcia) est un apprentissage EN UN SEUL ESSAI : un rat qui tombe
# malade apres avoir goute une saveur l'evite definitivement. Une plasticite
# synaptique graduelle et diffuse est un mauvais modele de ce mecanisme ; les
# systemes d'aversion alimentaire sont dedies, rapides et specialises.

# Amplitude de la preference. La decision d'ingestion combine la sortie du
# reseau et la preference du type percu au contact.
PREFERENCE_INIT_ECART = 0.5     # ecart-type des preferences innees initiales
PREFERENCE_MIN = -1.0
PREFERENCE_MAX = 1.0
PREFERENCE_POIDS_DECISION = 1.0 # poids de la preference dans la decision

# Taux d'apprentissage de la preference, multiplie par eta. Regle pour qu'une
# poignee de degustations suffise a inverser une preference — conformement a
# l'apprentissage en un essai de l'effet Garcia.
TAUX_APPRENTISSAGE_PREFERENCE = 0.35

# Taux de mutation et amplitude des preferences innees (genome)
PREFERENCE_TAUX_MUTATION = 0.3
PREFERENCE_FORCE_MUTATION = 0.20

# ---------------------------------------------------------------------------
# REGLE HEBBIENNE MODULEE PAR RECOMPENSE (conservee, secondaire)
# ---------------------------------------------------------------------------

GAIN_ACTIVATION = 0.8           # gain de tanh (defaut neat-python : 2.5)
                                # abaisse pour eviter la saturation du reseau
TAUX_HEBBIEN = 0.02             # amplitude de base des mises a jour
TRACE_DECROISSANCE = 0.92       # decroissance de la trace d'eligibilite / tick
TRACE_APRES_RECOMPENSE = 0.10   # residu de trace apres consommation
POIDS_MAX = 8.0                 # bornage des poids (sinon divergence)
DECROISSANCE_HOMEOSTATIQUE = 0.0005   # rappel lent vers les poids innes

# ---------------------------------------------------------------------------
# BOUCLE EVOLUTIVE
# ---------------------------------------------------------------------------

N_GENERATIONS = 150             # duree d'un run

# Poids du terme de survie dans la fitness. La fitness principale est l'energie
# alimentaire nette recoltee (echelle ~ +25 par repas nutritif) ; ce terme est
# mis a la meme echelle pour que la survie compte sans ecraser la
# discrimination.
POIDS_SURVIE_FITNESS = 25.0
FICHIER_CONFIG_NEAT = "neat_config.txt"

# ---------------------------------------------------------------------------
# RENDU
# ---------------------------------------------------------------------------

FPS = 60
AFFICHER_TRAINEES = True
LONGUEUR_TRAINEE = 22           # nombre de positions memorisees par Pascor
AFFICHER_CAPTEURS = False       # mode debug : dessine les secteurs de vision
AFFICHER_HUD = True

# Commandes clavier compatibles AZERTY (on evite les touches chiffres, A, Z,
# Q, W, M dont la position differe entre QWERTY et AZERTY).
#   ESPACE : pause
#   S      : capteurs
#   T      : trainees
#   F      : HUD
#   O / P  : ralentir / accelerer
#   ECHAP  : quitter

# ---------------------------------------------------------------------------
# DIVERS
# ---------------------------------------------------------------------------

SEED_DEFAUT = 42
