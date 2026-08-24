# Tabula Silico — journal de bord

*Document annexe. Le [README principal](README.md) présente le projet et ses résultats ; celui-ci conserve le détail des diagnostics menés pendant le développement.*

---

## Pourquoi ce document

La simulation n'a pas fonctionné du premier coup. Neuf obstacles successifs ont dû être identifiés et levés avant que le mécanisme central — la sélection d'un taux d'apprentissage en fonction de l'environnement — se manifeste.

Chacun a été traité de la même façon : formuler une hypothèse sur la cause, la tester par une mesure, accepter le verdict. **Quatre de ces hypothèses ont été réfutées par les données** — l'explication qui semblait la plus plausible s'est révélée fausse, et il a fallu chercher ailleurs.

Ce document conserve ces mesures, y compris celles qui ont invalidé une piste. Il est écrit dans l'ordre chronologique du développement, ce qui explique que certaines sections décrivent un état du modèle depuis dépassé — c'est volontaire : elles montrent ce qu'on savait au moment de décider.

**Résumé des neuf diagnostics** : voir le tableau dans le README principal.

---

## Décisions d'architecture

**Espace toroïdal.** Les bords se rebouclent. Des murs durs créeraient des
coins fonctionnant soit comme pièges soit comme refuges — un effet de bord
sans rapport avec la pression écologique étudiée.

**Venator est scripté, pas évolutif.** Une coévolution proie-prédateur ferait
varier la difficulté de l'environnement indépendamment des deux axes
expérimentaux (volatilité, coût d'apprentissage), et les confondrait.

**L'environnement est fixe pendant la vie d'un individu.** Seule la volatilité
*inter-générationnelle* varie. Si l'environnement changeait en cours de vie,
l'apprentissage individuel n'aurait plus rien de stable à apprendre. Invariant
vérifié par test : déplacement de 0,0 sur 1500 ticks.

**Le contrôleur est une interface.** `ControleurReactif` est un réflexe
provisoire sans apprentissage ni évolution, servant uniquement à valider
l'environnement. Tout contrôleur exposant `agir(entrées) -> (rotation,
poussée)` peut le remplacer — c'est par là qu'arrivera le réseau NEAT.

**Distinction par la forme autant que par la couleur.** Pascor (corps arrondi)
et Venator (corps anguleux) restent distinguables en cas de daltonisme
rouge-vert.

## Les deux types de nourriture

Deux types perceptivement distincts (canaux sensoriels séparés, couleurs et
formes différentes à l'écran) :

| Type | Apparence |
|---|---|
| A | pastille ronde ambre |
| B | losange cyan |

À chaque changement d'environnement, **l'un est nutritif (+25 énergie) et
l'autre toxique (−25), et lequel s'inverse**. Rien dans l'apparence n'indique
lequel est comestible : l'agent doit soit l'avoir hérité (inné), soit le
découvrir en goûtant (acquis). Le HUD l'affiche, mais pour l'observateur
humain uniquement.

Ce dispositif remplace la volatilité de position des patchs, qui ne pouvait
rien apporter : avec des capteurs égocentriques, la stratégie optimale est la
même où que soient les patchs. L'apprentissage n'avait aucun substrat.

Deux propriétés le rendent adapté : le **signal de renforcement** de la
plasticité hebbienne est le gain/perte d'énergie lui-même (rien d'artificiel à
inventer), et le **coût de l'apprentissage** est intrinsèque — pour savoir
quel type est bon, il faut goûter le mauvais et le payer (Johnston 1982,
Dukas 1998).

### La décision d'ingestion

Le réseau a une troisième sortie : ingérer ou non. Sans elle, l'agent avale
automatiquement ce qu'il touche et la discrimination ne peut s'exprimer que
par la navigation — impossible dans un patch où les deux types sont mélangés.
Mesure : le portail fait passer la discrimination d'un agent à préférence
correcte de 65 % à 76 %.

## Volatilité environnementale (T_env)

`T_env` = nombre de générations entre deux changements d'environnement (patchs
retirés **et** validité des types inversée). Vérifié sur 50 générations :

| Niveau | T_env | Redistributions sur 50 générations |
|---|---|---|
| `stable` | ∞ | 0 |
| `faible` | 50 | 1 |
| `intermediaire` | 15 | 3 |
| `forte` | 5 | 10 |
| `maximale` | 1 | 50 |

**À savoir :** `--headless` et `--captures` ne simulent qu'**une seule
génération**. À graine égale, les cinq niveaux de T_env y donnent donc des
résultats strictement identiques — ce n'est pas un bug, c'est l'invariant
« l'environnement ne change jamais pendant une vie ». L'effet de T_env
n'apparaîtra qu'avec la boucle évolutive (étape 3).

## Calibration

`main.py` vérifie automatiquement la cible de survie (30–50 %) après chaque
exécution et indique dans quel sens ajuster Venator si on en sort.

Référence de mesure : le **contrôleur réactif**, pas des réseaux NEAT de la
génération 0 — des réseaux initialisés au hasard font bien pire et donneraient
une référence instable d'un run à l'autre.

### État calibré

| Stratégie innée du contrôleur réactif | Survie | Repas/vie | Discrimination |
|---|---|---|---|
| Préférence **correcte** | 31 % | 38 | 76 % |
| Préférence **fausse** | 0 % | — | 25 % |
| **Aucune** (avale tout) | 0 % | — | 49 % |

Le contraste est net et conforme à la théorie : une préférence innée juste
suffit à survivre, une préférence innée fausse est létale, et l'absence de
discrimination l'est tout autant.

### Note sur le nombre d'événements d'apprentissage

Ce qui détermine si un apprentissage est possible n'est pas la durée de vie en
ticks, mais le **nombre de dégustations par vie**. Les paramètres initiaux
(64 items, repousse 200 ticks, vie 1500) donnaient 7,1 repas par vie — soit
~3,5 par type, insuffisant pour apprendre une discrimination binaire, et déjà
létal côté toxique. Après ajustement (140 items, repousse 60 ticks, vie 3000) :
**38 à 54 repas par vie**, dans la cible visée de 40-70.

Augmenter la densité de nourriture coûte moins cher en calcul qu'allonger la
vie (numpy vectorisé contre boucle Python), ce qui préserve le budget pour la
réplication statistique.

### Recalibration de Venator

Doubler la durée de vie a mécaniquement doublé l'exposition cumulée à la
prédation, qui est passée de 35 % à 58 % des morts. Portée de détection
ramenée de 220 à 130 et satiété de 150 à 300 ticks : la prédation redescend à
~29 %, en équilibre avec la famine.

## Métrique de H3c : ce qui marche et ce qui ne marche pas

Deux métriques candidates ont été testées sur le contrôleur réactif, qui n'a
**aucune** capacité d'apprentissage. Une bonne métrique doit être plate chez
un tel agent :

| Métrique candidate | Pente 1er → 3e tiers sans apprentissage | Verdict |
|---|---|---|
| Quantité de nourriture mangée | **+0,39 item** (positive dans 6 runs / 8) | ⚠️ confondue |
| **Taux de discrimination** | **−1,39 point** (± 2,89, centrée sur zéro) | ✅ retenue |

La quantité mangée augmente au fil de la vie même sans apprentissage :
installation spatiale plus survie sélective — les individus qui atteignent la
fin de vie sont ceux qui ont trouvé un patch et s'y sont fixés. Le taux de
discrimination ne souffre pas de ce biais : s'installer près d'un patch
n'améliore en rien la capacité à distinguer le comestible du toxique.

Toute pente de discrimination positive chez un agent plastique sera donc bien
attribuable à l'apprentissage.

## Avertissement méthodologique

Le contrôleur réactif n'a **aucune** capacité d'apprentissage, et montre
pourtant une amélioration du 1er au 3e tiers de vie (+0,39 item en moyenne,
positive dans 6 runs sur 8). Il s'agit très probablement d'un effet
d'installation spatiale combiné à la survie sélective : les individus qui
atteignent la fin de vie sont ceux qui ont trouvé un patch et s'y sont fixés.

**Conséquence :** comparer le 1er et le 3e tiers d'un agent plastique à
lui-même produirait un faux positif d'apprentissage. Cette comparaison doit se
faire entre agents plastiques et agents figés, et seul l'excédent compte.

## Prochaine étape

Étape 3 : architecture de Pascor — NEAT, plasticité hebbienne modulée par
récompense, gène héritable du taux de plasticité (η), coût métabolique de
l'apprentissage.

---

## Étape 3 : NEAT, plasticité et boucle évolutive

### Modules ajoutés

| Fichier | Rôle |
|---|---|
| `perception.py` | Perception vectorisée : tous les agents en une passe numpy |
| `genome.py` | Génome NEAT augmenté du gène η (taux de plasticité) |
| `brain.py` | Réseau plastique : règle hebbienne à trois facteurs, traces d'éligibilité |
| `evolution.py` | Boucle évolutive, double évaluation P_naïf / P_libre, journalisation CSV |
| `neat_config.txt` | Configuration NEAT (16 entrées, 3 sorties) |

```
python evolution.py --tenv intermediaire --seed 1 --generations 150 --journal runs/r1.csv
```

### Optimisation : perception vectorisée

Le profilage montrait **81 % du temps dans la perception**, avec 3 petites
opérations numpy par agent et par tick (113 000 appels pour 400 ticks). Sur des
tableaux de cette taille, c'est la surcharge d'appel de numpy qui domine, pas le
calcul.

Regroupement de tous les agents en une passe : **×4,8** (24,6 s → 5,2 s pour
3000 ticks), sorties identiques au bit près. Le plan expérimental complet passe
d'environ 276 h à ~58 h de calcul.

### Ce qui est vérifié

- La boucle évolutive tourne de bout en bout et journalise 22 colonnes par génération
- **L'évolution progresse** : la discrimination passe de 0,60 à 0,68 en 30 générations
- **T_env produit l'effet attendu** : à l'inversion des types (génération 15, T_env=15),
  la discrimination s'effondre de 0,67 à 0,37 et la fitness de 8,3 à 0,45, puis remonte.
  La préférence innée acquise devient brutalement létale — exactement le mécanisme
  que le dispositif doit capturer.

### Ce qui ne marche pas encore

**ΔP est nul** (−0,07 sur les 10 premières générations, −0,01 sur les 10 dernières).
La plasticité n'apporte aucun bénéfice mesurable : les agents figés discriminent
aussi bien que les plastiques (0,685 contre 0,674).

La hausse de η (0,50 → 0,69) n'est donc **pas** un signal de sélection : sans
bénéfice et sans coût (λ=0), η est neutre et dérive librement.

Pistes à examiner en phase pilote (étape 4), par ordre de vraisemblance :
1. `TAUX_HEBBIEN` (0,02) trop faible pour modifier le comportement en une vie
2. Test mené à durée de vie réduite (1500 ticks ≈ 20 repas) alors que ~40 sont
   nécessaires — à refaire à 3000 ticks
3. `DECROISSANCE_HOMEOSTATIQUE` qui ramène peut-être trop vite vers les poids innés
4. Structure de la trace d'éligibilité et attribution du crédit

Tant que ΔP reste nul, H1 et H2 ne sont pas testables : si la plasticité n'apporte
rien, η n'a aucune raison de répondre à T_env.

---

## Étape 4 (en cours) : diagnostic de la plasticité

### Le problème

Après l'étape 3, **ΔP est nul** : les agents à plasticité gelée discriminent
aussi bien que les plastiques. Trois hypothèses ont été testées.

| Hypothèse | Test | Verdict |
|---|---|---|
| `TAUX_HEBBIEN` trop faible | Dérive des poids = 0,084, coût cumulé = 6,47 | ❌ réfutée — les poids bougent amplement |
| Règle non sélective | Après récompense négative : \|Δ\| = 0,14 sur les voies du type ingéré, **0,00** sur l'autre | ❌ réfutée — sélectivité par magnitude, nette |
| Saturation du réseau | 59 % des sorties saturées (\|tanh\| > 0,99) | ✅ **confirmée et corrigée** → 0 % |

Un réseau saturé est une fonction constante : il ignore ses capteurs, et ni
l'inné ni l'acquis ne peuvent s'exprimer. Correctifs : `GAIN_ACTIVATION` 2,5 →
0,8, `weight_init_stdev` et `bias_init_stdev` 1,0 → 0,4.

Ce bug devait être corrigé, mais **ce n'était pas la cause de ΔP nul**.

### La vraie raison : un test mal posé

Le diagnostic isolé (`diagnostic.py`) montre qu'à la **génération 0**, les
réseaux aléatoires ne savent pas fourrager : **50 agents sur 60 mangent moins
de 5 fois** dans toute leur vie, alors qu'il en faut ~40 pour apprendre une
discrimination binaire. Aucune règle d'apprentissage ne peut rien extraire de
4 événements de récompense.

Ce n'est pas un état permanent — la compétence de fourrage évolue :

| Générations | Survie | P_naïf | Discrimination |
|---|---|---|---|
| 0–4 | 2 % | 2,71 | 0,54 |
| 10–14 | 12 % | 9,90 | 0,70 |

Deux conséquences :
1. **La plasticité ne peut pas être diagnostiquée à la génération 0** — il faut
   d'abord un socle inné capable de trouver et d'ingérer la nourriture. C'est
   H3 (complémentarité) rencontrée comme contrainte pratique, pas comme
   prédiction théorique.
2. Le test avait été mené à `T_env = 15`, où l'environnement reste stable
   quinze générations — largement de quoi fixer génétiquement la bonne
   préférence (discrimination des figés : 0,716 dès la génération 12).
   **C'est la prédiction de H1 : à faible volatilité, l'inné gagne.** La
   plasticité était testée dans la condition la moins favorable possible.

### Test décisif restant

Comparer `T_env = stable` et `T_env = maximale` (inversion à chaque
génération, où aucune préférence héritée ne peut jamais être correcte), sur
assez de générations pour que le fourrage se développe (≥ 25).

```
python evolution.py --tenv stable   --seed 21 --generations 60 --journal runs/stable_s21.csv
python evolution.py --tenv maximale --seed 21 --generations 60 --journal runs/maximale_s21.csv
```

Le journal est écrit **une ligne par génération, avec vidage immédiat** : un
run interrompu ne perd rien, et le CSV est lisible pendant l'exécution pour
suivre l'avancement.


### Résultat du test décisif (60 générations, T_env stable vs maximale)

**ΔP nul dans les deux conditions** : +0,025 (z = 0,18) en stable, −0,002
(z = −0,10) en maximale. La plasticité n'apportait rien, y compris dans la
condition censée lui être la plus favorable.

**Mais η bouge dans le sens prédit par H1** : 0,504 → 0,325 en stable
(la sélection pousse vers l'inné), 0,529 → 0,562 en maximale (neutre, dérive).
Explication cohérente : en stable, la solution innée fonctionne
(discrimination 0,697), donc la plasticité ne fait que perturber un optimum
déjà atteint. Une seule graine par condition — signal encourageant, pas
résultat.

### La faille : gains symétriques et piège de la poule et de l'œuf

En condition maximale, les repas s'effondraient de 4,0 à **0,5** par vie et la
survie tombait à 0,1 %. Les agents évoluaient vers le refus total de
s'alimenter.

Cause arithmétique : avec nutritif +25 et toxique −25, manger au hasard a une
espérance de gain **nulle**. Aucun bénéfice, mais de la variance ajoutée — et
près du seuil de mort (énergie 0), la variance tue. La sélection éliminait
donc le comportement de manger, et l'agent mourait de faim.

Fatal pour la question du projet : pour apprendre quel type est comestible, il
faut goûter ; mais goûter était si dangereux que la sélection supprimait le
fait de goûter **avant** que l'apprentissage puisse devenir rentable.

**Correctif — gains asymétriques (+25 / −10)** :

| Stratégie | Espérance, gains symétriques | Espérance, gains asymétriques |
|---|---|---|
| Manger au hasard | 0,0 | **+7,5** |
| Discriminer | +25 | +25 |

Goûter devient rentable (l'apprentissage reçoit des données), et discriminer
reste nettement meilleur (l'apprentissage a une raison de payer).

Effet mesuré en condition maximale : les repas passent de **0,5 à 12,9** par
vie, soit un facteur 26.

**Conséquence sur le signal d'apprentissage.** La saillance du renforcement est
découplée de la magnitude énergétique : chaque signe est normalisé par sa
propre échelle, donc un aliment toxique produit un signal de −1 et un nutritif
de +1. Sans ce découplage, l'aversion s'apprendrait 2,5 fois moins bien que
l'appétence. C'est biologiquement fondé : l'aversion gustative conditionnée
(effet Garcia) est justement remarquable par le fait qu'une seule expérience
toxique produit une aversion forte et durable, hors de proportion avec le coût
physiologique subi.


### Protection du journal

Le journal ne peut plus écraser un fichier existant. Le mode d'ouverture `"w"`
tronque le fichier dès l'ouverture : un run relancé par mégarde détruisait
silencieusement des heures de calcul déjà effectuées (constaté en pratique —
deux runs complets de 60 générations perdus de cette façon).

Si le fichier existe, le programme s'arrête avec un message indiquant combien
de générations s'y trouvent. `--ecraser` permet de forcer.


### Cause racine de ΔP nul : la direction de l'apprentissage

`test_regle.py` teste la règle hebbienne **hors monde et hors évolution** :
on nourrit directement le réseau de motifs et de récompenses, puis on mesure
si sa réponse d'ingestion a divergé entre les deux types. Le test s'exécute en
quelques secondes, là où diagnostiquer par des runs évolutifs prenait une
heure.

Verdict initial : la règle échouait **même dans les conditions idéales**
(60 repas parfaitement nets, η = 1,0, divergence −0,012, z = −0,22).

En instrumentant le sens des variations de poids : **25 réseaux sur 40**
apprenaient dans le bon sens — à peine mieux que pile ou face.

**Le mécanisme du défaut.** La trace d'éligibilité vaut `pre × post`. Avec
tanh, `post` peut être négatif :

| Situation | Récompense | Effet sur le poids | |
|---|---|---|---|
| `post > 0` (enclin à ingérer) | négative | baisse | correct |
| `post < 0` (peu enclin) | négative | **monte** | inverse |

17 réseaux sur 40 avaient une sortie d'ingestion négative. Bons et mauvais sens
s'annulaient en moyenne — d'où ΔP nul.

**Régression introduite en corrigeant la saturation.** La sigmoïde d'origine
n'avait pas ce défaut (activations toujours positives), mais saturait à 59 %.
Le passage à tanh a corrigé la saturation et créé ce défaut de signe. C'est
pourquoi les trois correctifs suivants (test à la génération 0, condition à
faible volatilité, gains symétriques) n'ont rien débloqué : chacun levait un
vrai obstacle, mais celui-ci restait dessous et suffisait à tout annuler.

**Correctif — rectification `max(0, x)`.** Le facteur `(x + 1) / 2` a d'abord
été essayé et rejeté : il transforme une activation nulle en 0,5, donc un
capteur qui ne détecte rien accumule quand même de l'éligibilité, ce qui
détruit la sélectivité (nutritif 34/40 mais toxique 14/40). `max(0, x)`
préserve le zéro.

| Version | Sens correct, nutritif | Sens correct, toxique | Divergence (z) |
|---|---|---|---|
| tanh brut | 25/40 | 25/40 | −0,22 |
| `(x+1)/2` | 34/40 | 14/40 | — |
| **`max(0, x)`** | **16/16** | **27/27** | **+6,65** |

Conséquence assumée : un agent dont la sortie d'ingestion est négative
n'apprend rien. C'est écologiquement juste — on n'apprend pas d'un aliment
qu'on n'a jamais goûté — et cela correspond au fonctionnement réel, où
l'ingestion n'a lieu que si la sortie dépasse le seuil.

**Hypothèse réfutée au passage.** Le régime *ambigu* (les deux types visibles
simultanément, situation réelle des patchs mixtes) apprend aussi bien que le
régime *propre* : +0,199 contre +0,161. L'attribution du crédit n'était donc
pas en cause, et il n'y a pas lieu de rouvrir le mélange des types dans les
patchs.


### Le seuil dur d'ingestion bloquait la traduction en comportement

Après correction du sens de l'apprentissage, la règle fonctionne (z = 6,65 en
isolation) mais ΔP restait nul en simulation (z = 0,93 et 0,82). Trois
hypothèses ont été écartées par mesure :

| Hypothèse | Test | Verdict |
|---|---|---|
| Trop peu de repas | La règle apprend dès **4 repas** (z = 3,17) | ❌ |
| `TAUX_HEBBIEN` trop faible | Au-delà de 0,05, divergence **négative** (z = −3,74 à 0,20) — instabilité | ❌ |
| Décroissance homéostatique | +0,020 avec contre +0,030 sans | ❌ |

**Cause réelle : l'échelle.** Dans les conditions exactes de la simulation, la
divergence vaut +0,020 — soit un déplacement de **2 % du seuil de décision**.
L'apprentissage était réel au niveau des poids, mais la sortie d'ingestion ne
franchissait jamais le seuil de 0,5. Aucune décision ne changeait, donc aucun
effet sur la fitness, donc rien à sélectionner.

**Correctif — ingestion probabiliste.** La sortie *est* la probabilité
d'ingérer, au lieu d'être comparée à un seuil. Le moindre déplacement se
traduit immédiatement en changement de comportement, de façon graduelle. Plus
plausible biologiquement : aucun animal n'applique un seuil parfaitement net à
une tendance comportementale.

Effet mesuré (T_env maximale, 14 générations, une graine) :

| | seuil dur | probabiliste |
|---|---|---|
| ΔP | +0,043 (z = 0,82) | **+0,212 (z = 1,65)** |
| Discrimination plastique − figée | −0,002 | **+0,008** |
| Repas / vie | 3,9 | 7,5 |

**Non concluant** : z = 1,65 reste sous le seuil de 2, sur 14 générations et
une seule graine. Ce qui distingue ce signal des précédents est qu'il avait une
explication mécanique établie *avant* la mesure — la règle apprend, le seuil
empêchait la traduction — et non trouvée après coup dans les données.

Réplication sur plusieurs graines nécessaire pour trancher.


### H1 réfutée dans le dispositif à gains symétriques — puis cause identifiée

Quatre niveaux de volatilité, trois graines chacun (12 runs de 60 générations).
Critère de réfutation posé **avant** de voir les données : si l'écart de
discrimination plastique − figée reste sous 0,01 dans les quatre conditions,
la plasticité alimentaire ne s'exprime dans aucun régime.

| T_env | Repas/vie | Survie | ΔP | Discrim. plast. − figée |
|---|---|---|---|---|
| stable | 24,9 | 24,5 % | +0,216 | +0,0013 |
| faible | 21,6 | 21,0 % | +0,156 | +0,0034 |
| forte | 7,6 | 3,0 % | +0,062 | −0,0060 |
| maximale | 4,1 | 1,2 % | +0,025 | −0,0067 |

Critère atteint : les quatre écarts sont sous 0,01 et changent de signe. Aucune
courbe en cloche — ΔP décroît **monotonement** avec la volatilité, l'inverse de
la prédiction de Stephens. Et ΔP suivait le nombre de repas, pas la volatilité :
c'était un effet de volume d'expérience, pas d'adaptation.

**Cause : une incohérence entre l'écologie et la fitness.** L'énergie était
asymétrique (+25 / −10), mais la fitness comptait `nutritifs − toxiques`, soit
des **items**, symétriquement. Un agent mangeant au hasard obtenait donc une
fitness d'environ zéro, exactement comme un agent ne mangeant rien — alors
qu'écologiquement il récoltait +7,5 d'énergie par repas. L'asymétrie avait été
introduite pour rendre le fait de goûter rentable, mais n'avait jamais été
propagée à la fitness : la pression de sélection restait celle du régime
symétrique.

**Correctif — fitness en énergie récoltée** : `25 × nutritifs − 10 × toxiques`.

| Stratégie | Fitness avant | Fitness après |
|---|---|---|
| Ne rien manger | 0 | 0 |
| Manger au hasard (n repas) | ≈ 0 | **+7,5 n** |
| Discriminer | +n | +25 n |

Effet mesuré en condition maximale (14 générations) :

| | avant | après |
|---|---|---|
| Repas / vie | 4,1 | **25,7** |
| P_naïf | 1,8 | 230 |

L'effondrement alimentaire n'était donc pas un phénomène écologique, mais la
conséquence d'une pression de sélection incohérente avec l'écologie du modèle.

**Non résolu à ce stade** : la discrimination reste à 0,50 en maximale sur
14 générations, et l'écart plastique − figé reste nul. Le préalable est levé
(les agents ont enfin de quoi apprendre), mais l'apprentissage ne se manifeste
pas encore dans le comportement.


---

## Déblocage : un substrat d'apprentissage dédié

### Le diagnostic

Après sept correctifs, l'écart de discrimination plastique − figée restait nul
dans toutes les conditions, alors que les poids bougeaient (dérive 0,067). Ce
n'était plus un faisceau de bugs indépendants mais un signal.

L'information à apprendre est littéralement **un bit** : quel type est
comestible cette génération-ci. La règle hebbienne devait le découvrir en
modifiant des dizaines de poids d'un réseau gérant simultanément le
déplacement, le fourrage et la fuite. Ce bit y était **dilué**.

Les implémentations qui reproduisent l'effet Baldwin (Hinton & Nowlan 1987,
Mayley 1996) font toutes apprendre sur un substrat **dédié et de basse
dimension**, pas sur l'ensemble des paramètres du contrôleur.

C'est aussi plus juste biologiquement : l'aversion gustative conditionnée
(effet Garcia) est un apprentissage **en un seul essai**. Une plasticité
synaptique graduelle et diffuse est un mauvais modèle de ce mécanisme.

### Le dispositif

Pascor porte une **préférence alimentaire** explicite, un scalaire par type,
qui pondère directement sa décision d'ingestion.

| | |
|---|---|
| **Inné** | valeur initiale des préférences, encodée dans le génome, héritée |
| **Acquis** | leur mise à jour au cours de la vie, par expérience directe |
| **η** | taux de cette mise à jour, hérité, sous sélection |

La question du projet est inchangée : le curseur inné/acquis reste η, la
prédiction reste la fenêtre de Stephens.

### Effet mesuré

| | plasticité diffuse | substrat dédié |
|---|---|---|
| Divergence (20 repas, η = 0,6) | +0,030 (z = 4,4) | **+1,05 (z = 15,1)** |
| Discrimination plastique − figée | −0,0015 | **+0,07** |
| ΔP | ≈ 0 | **+30 à +90** |

En condition `maximale`, la validité des types s'inverse à chaque génération :
aucune préférence héritée ne peut être correcte. Les agents figés sont donc
condamnés au hasard — observé : 0,50 à 0,53. Les plastiques atteignent 0,57 à
0,62, parce qu'ils découvrent au cours de leur vie quel type est comestible.

C'est le mécanisme que le projet cherche à démontrer, observé pour la première
fois.

### Ce qui reste à faire

Balayage complet des quatre niveaux de volatilité, trois graines chacun, pour
tester la courbe en cloche de H1. Puis l'axe λ_coût pour H2.


## Le second axe : volatilité intra-vie

### Résultat du balayage inter-générationnel (substrat dédié, 1 graine)

| T_env | Repas | Discrim. figée | Discrim. plastique | Écart | η final |
|---|---|---|---|---|---|
| stable | 21,4 | 0,687 | 0,752 | +0,065 (z=27) | **0,330** |
| faible | 18,4 | 0,623 | 0,677 | +0,054 (z=8) | 0,405 |
| forte | 10,1 | 0,502 | 0,568 | +0,066 (z=15) | 0,431 |
| maximale | 18,8 | 0,510 | 0,606 | +0,096 (z=40) | **0,441** |

L'apprentissage fonctionne dans les quatre conditions. **η croît de façon
monotone avec la volatilité** (0,330 → 0,441, corrélation de rang **0,925**) :
la branche montante de H1 est confirmée, avec un mécanisme visible — en stable
l'inné atteint 0,687 de discrimination et l'apprentissage est superflu ; en
volatil l'inné tombe à 0,50 et seule la plasticité fait mieux.

Mais **pas de redescente** à l'extrême. H1 prédisait une cloche.

### Pourquoi la cloche ne pouvait pas apparaître

Chez Stephens, la redescente vient de ce que l'environnement change **au cours
de la vie** : ce qui est appris devient obsolète avant de servir.

Or le dispositif fixait l'environnement pendant toute la vie (invariant vérifié
par test : déplacement 0,0 sur 3000 ticks). Ce choix était justifié — sans
stabilité intra-vie, l'apprentissage n'aurait eu aucun substrat stable — mais
il **excluait par construction** le régime où la plasticité cesse d'être utile.
La branche descendante n'a pas échoué à apparaître : elle ne pouvait pas
exister.

### Le paramètre ajouté

`--vvie` : nombre de basculements de la validité des types **pendant une vie**,
répartis uniformément sur les 3000 ticks.

| Niveau | Basculements | Interprétation |
|---|---|---|
| `nulle` | 0 | comportement d'origine |
| `lente` | 1 | l'agent doit réapprendre une fois |
| `moderee` | 3 | l'apprentissage a encore le temps de servir |
| `rapide` | 9 | ce qui est appris devient vite obsolète |
| `chaotique` | 29 | la plasticité ne peut plus rien apporter |

Vérifié : le nombre de basculements observés correspond exactement à l'attendu
aux cinq niveaux. Les deux évaluations d'une même génération (P_naïf et
P_libre) affrontent la même séquence de basculements.

### Vérification de la branche descendante

À volatilité inter-générationnelle identique (`maximale`) :

| Volatilité intra-vie | Écart discrim. plastique − figée |
|---|---|
| `nulle` | **+0,096** (z = 40) |
| `chaotique` | **≈ 0,00** |

La plasticité perd tout avantage quand l'environnement change plus vite que
l'individu ne peut apprendre. Les deux branches de la cloche existent
désormais dans le modèle.

### Plan expérimental

Le dispositif a maintenant **deux axes de volatilité** — entre générations
(T_env) et pendant la vie (v_vie) — ce qui permet de tester H1 dans sa forme
complète.
