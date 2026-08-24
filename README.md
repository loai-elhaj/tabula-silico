# Tabula Silico

**Quand la sélection naturelle favorise-t-elle un comportement inné, et quand favorise-t-elle la capacité d'apprendre ?**

Une simulation de vie artificielle où des agents dotés de réseaux de neurones évoluent dans un environnement 2D, et où le degré de plasticité comportementale est lui-même un caractère héréditaire soumis à la sélection.

![Aperçu de la simulation](figures/apercu.gif)

Les **Pascor** (vert, corps arrondi) cherchent de la nourriture ; les **Venator** (rouge, corps anguleux) les chassent. Deux types d'aliments — pastilles ambre et losanges cyan — dont l'un est nutritif et l'autre toxique. Rien dans leur apparence ne dit lequel : c'est ce que l'agent doit avoir hérité, ou apprendre.

Sur cette capture, la discrimination atteint 77 % et les pastilles ambre (nutritives ici) sont visiblement plus rares que les losanges cyan : les agents mangent les unes et laissent les autres. La stratégie alimentaire se lit directement dans ce qui reste au sol.

---

## Résumé

Ce projet teste, dans un modèle d'agents situés, trois prédictions classiques de l'écologie comportementale sur l'évolution de l'apprentissage.

Cent agents virtuels évoluent pendant 60 générations sous l'algorithme NEAT. Chacun porte un gène **η** qui détermine dans quelle mesure son comportement alimentaire est fixé à la naissance ou façonné par son expérience. Ce gène est hérité et muté comme n'importe quel autre : la simulation ne décide pas si les agents apprennent, elle observe où la sélection pousse ce curseur selon les conditions.

Trois résultats principaux, chacun répliqué sur trois runs indépendants :

1. **Quand l'environnement change pendant la vie d'un individu, la sélection abandonne l'apprentissage.** η passe de 0,50 à 0,12 (ρ = −0,764, p = 0,0009), et l'avantage conféré par la plasticité s'effondre d'un facteur 80 (ρ = −0,917, p < 0,0001).
2. **Quand l'apprentissage coûte, la sélection revient vers l'inné, alors même que l'apprentissage continue de fonctionner.** η passe de 0,50 à 0,19 (ρ = −0,820, p = 0,0011).
3. **La part respective de l'inné et de l'acquis dépend de l'environnement.** Effacer les préférences innées d'une population évoluée coûte 42 points de fitness en environnement stable, mais en fait gagner 32 en environnement volatil (p = 0,050).

Un quatrième résultat, attendu mais non confirmé statistiquement : l'avantage de la plasticité croît nettement avec la volatilité entre générations (ρ = +0,820, p = 0,0011), mais la réponse évolutive de η n'atteint pas le seuil de significativité sur trois runs (p = 0,139).

---

## 1. Introduction

### 1.1 La question

En 1689, dans son *Essai sur l'entendement humain*, John Locke propose que l'esprit humain naisse comme une *tabula rasa* — une table rase, une surface vierge sur laquelle seule l'expérience viendra écrire. Trois siècles de biologie évolutive ont nuancé cette image. Aucun organisme ne naît véritablement vierge : un nouveau-né sait téter, un poussin se fige devant l'ombre qui passe au-dessus de lui, une larve de triton sait nager. Mais aucun organisme n'est non plus un automate figé : l'apprentissage — l'ajustement du comportement à l'expérience individuelle — existe bel et bien, et confère un avantage réel dans un monde qui change.

La vraie question n'est donc pas *« inné ou acquis ? »*, faux dilemme tranché depuis longtemps, mais :

> **Sous quelles conditions la sélection naturelle favorise-t-elle un comportement câblé dès la naissance, sous quelles conditions favorise-t-elle un comportement plastique, et que gagne-t-on concrètement à combiner les deux ?**

C'est cette question que Tabula Silico met à l'épreuve.

### 1.2 Ce que prédit la théorie

Trois éléments de théorie structurent le projet.

**La variabilité environnementale est le facteur déterminant.** Si l'environnement est parfaitement stable d'une génération à l'autre, l'inné domine : il ne coûte rien à acquérir, il est fiable dès la naissance, et l'apprentissage n'apporte qu'un coût — temps, erreurs, énergie — sans bénéfice compensatoire. À l'inverse, si l'environnement change trop vite, ni l'information héritée ni l'apprentissage individuel ne servent : ce qu'un individu découvre devient obsolète avant qu'il puisse l'exploiter. L'apprentissage n'est donc réellement avantageux que dans une **fenêtre intermédiaire** : l'environnement doit changer assez pour que l'information héritée des parents devienne caduque, mais rester assez stable pendant une vie pour que ce qu'on apprend serve encore. C'est le résultat central de Stephens (1991).

**L'apprentissage n'est jamais gratuit.** Johnston (1982) et Dukas (1998) insistent sur ses coûts : risque accru pendant la phase d'essai-erreur, temps perdu, coût métabolique et neural du système d'apprentissage lui-même. Un modèle qui ferait gagner l'apprentissage sans compter ce coût raconterait une histoire biologiquement fausse — c'est un piège classique de la modélisation.

**Inné et acquis sont complémentaires, pas concurrents.** Le résultat le plus intéressant de la littérature n'est pas « l'un bat l'autre » mais la façon dont ils se combinent : un socle inné donne un comportement de base immédiatement fonctionnel — il évite la mort avant même que l'apprentissage ait pu opérer — sur lequel vient se greffer un ajustement appris qui affine ce socle selon le contexte local. C'est l'architecture formalisée par Mayley (1996) et par les travaux de robotique évolutionnaire.

### 1.3 Ce que ce projet ajoute

Ce cadre théorique est solide et largement consensuel. Sa vérification, en revanche, repose le plus souvent sur des modèles mathématiques abstraits ou sur des génomes-jouets — chez Hinton & Nowlan (1987), l'organisme est une chaîne de bits, et « apprendre » consiste à tirer au hasard les positions indéterminées.

Tabula Silico teste ces prédictions dans un agent **situé** : un agent qui doit réellement se déplacer dans un espace, détecter sa nourriture avec des capteurs limités, éviter un prédateur, gérer son énergie, et dont le comportement est produit par un réseau de neurones et non par une règle explicite. L'apprentissage doit y émerger d'une interaction écologique réelle, pas d'un opérateur mathématique.

Cette différence a des conséquences que le développement a révélées : plusieurs mécanismes qui « devraient » fonctionner en théorie ne fonctionnent pas dans un agent situé, pour des raisons qui tiennent à l'écologie du modèle et non à la théorie (voir §8).

---

## 2. Hypothèses

Les hypothèses et leurs critères de réfutation ont été fixés **avant** toute collecte de données, sur le modèle d'un pré-enregistrement. Cette discipline évite le *HARKing* — formuler une hypothèse après avoir vu les résultats et la présenter comme une prédiction.

### H1 — La fenêtre de plasticité

> **La sélection ne retient un taux de plasticité élevé que dans une zone intermédiaire de volatilité environnementale.**

**Raisonnement.** En environnement stable, une préférence alimentaire héritée reste correcte indéfiniment : l'apprentissage ne peut que reproduire à grands frais une information déjà disponible gratuitement. En environnement très volatil, ce qu'un individu apprend devient faux avant qu'il en tire profit. Entre les deux, l'information héritée est périmée mais l'expérience individuelle reste valide assez longtemps pour payer.

**Deux branches, deux mécanismes distincts.** Cette prédiction combine en réalité deux phénomènes différents, qu'il faut mesurer séparément :

- **Branche montante** — la volatilité *entre générations* rend l'inné obsolète. Le génome ne peut plus encoder la bonne réponse, la plasticité devient la seule voie.
- **Branche descendante** — la volatilité *pendant la vie* rend l'acquis obsolète. Ce qui est appris ne survit pas assez longtemps pour servir.

Le dispositif expérimental manipule donc **deux axes indépendants** (§4.1), ce qui constitue une différence notable avec les formulations habituelles où la volatilité est traitée comme une grandeur unique.

**Confirmée si** le taux de plasticité η et l'avantage conféré par la plasticité augmentent avec la volatilité inter-générationnelle, et diminuent avec la volatilité intra-vie.

**Réfutée si** aucune relation n'apparaît, ou si la relation est monotone là où une réponse en cloche est attendue.

### H2 — Le coût comme force de rappel

> **À volatilité favorable, augmenter le coût de l'apprentissage fait refluer la sélection vers l'inné.**

**Raisonnement.** L'avantage de la plasticité n'est pas absolu, il est *net* : bénéfice moins coût. Un apprentissage qui améliore réellement le comportement peut néanmoins être éliminé par la sélection s'il coûte plus qu'il ne rapporte. La prédiction distingue donc l'efficacité (l'apprentissage fonctionne-t-il ?) de la rentabilité (vaut-il son prix ?).

**Confirmée si** η décroît quand le coût augmente, **et** que l'avantage brut de la plasticité reste positif — ce qui montrerait que la sélection abandonne un mécanisme qui fonctionne encore.

**Réfutée si** η ne répond pas au coût, ou si la baisse de η s'explique simplement par un arrêt du fonctionnement de l'apprentissage.

### H3 — Complémentarité plutôt que compétition

> **Les populations évoluées ne montrent ni un comportement purement inné ni un comportement purement appris, mais une architecture en deux temps — et la part respective des deux dépend de l'environnement.**

**Raisonnement.** L'apprentissage a besoin d'un socle : pour apprendre quel aliment est comestible, encore faut-il savoir s'approcher d'un aliment et l'ingérer. Ce socle ne peut venir que de l'inné. Inversement, l'inné ne peut encoder que ce qui est stable ; le reste doit être appris. La prédiction forte est que **l'importance relative des deux bascule avec les conditions**.

**Trois sous-tests :**

- **3a** — le socle inné est fonctionnel : une population évoluée, plasticité gelée, doit surpasser nettement des génomes non évolués.
- **3b** — l'apprentissage apporte un gain réel : la même population, plasticité active, doit surpasser sa version gelée.
- **3c** — preuve comportementale : la qualité de la discrimination alimentaire doit *progresser au cours de la vie* chez les agents plastiques, et rester plate chez les agents gelés.

**Confirmée si** les trois sous-tests réussissent, et si la lésion des préférences innées coûte davantage en environnement stable qu'en environnement volatil.

**Réfutée si** l'un des sous-tests échoue — par exemple si la performance innée est indiscernable du hasard, ou si l'apprentissage n'apporte rien.

---

## 3. Méthodes

### 3.1 Vue d'ensemble

Une **simulation** fait vivre simultanément 100 agents herbivores et 5 prédateurs dans une arène 2D pendant 3000 pas de temps. Chaque herbivore est piloté par un réseau de neurones issu de son génome.

Un **run évolutif** enchaîne 60 générations. À chaque génération, la population entière est évaluée deux fois (§3.12), les fitness servent à la sélection, et l'algorithme NEAT produit la génération suivante par mutation et croisement.

Une **condition expérimentale** est une combinaison de paramètres environnementaux. Chaque condition est répliquée sur 3 runs indépendants, et c'est le **run** qui sert d'unité statistique (§4.5).

### 3.2 L'environnement

| Paramètre | Valeur | Justification |
|---|---|---|
| Dimensions de l'arène | 1600 × 900 unités | Densité permettant à 100 agents de ne pas s'entasser |
| Géométrie | **Toroïdale** (les bords se rebouclent) | Des murs créeraient des coins fonctionnant soit comme pièges soit comme refuges — un effet de bord sans rapport avec la pression écologique étudiée |
| Zones de nourriture | 10 patchs, rayon 110 | Distribution en agrégats plutôt qu'uniforme, comme la plupart des ressources naturelles |
| Items par patch | 14 (140 au total) | Calibré pour atteindre la cible d'événements alimentaires (§3.5) |
| Délai de repousse | 60 pas de temps | Un item consommé réapparaît, ce qui maintient une pression de recherche sans que l'environnement se vide |

Les deux types d'aliments sont **mélangés à l'intérieur de chaque patch**. Ce choix est délibéré : les séparer spatialement aurait permis une stratégie d'évitement de zone, qui contournerait la discrimination alimentaire au lieu de l'exiger.

### 3.3 La tâche : discriminer deux aliments

C'est le cœur du dispositif expérimental.

Il existe **deux types d'aliments**, perceptivement distincts — pastilles ambre (type A) et losanges cyan (type B), avec des canaux sensoriels séparés. À chaque changement d'environnement :

- l'un devient **nutritif** : +25 unités d'énergie ;
- l'autre devient **toxique** : −10 unités d'énergie ;
- et **lequel est lequel s'inverse**.

Rien dans l'apparence d'un aliment n'indique sa comestibilité du moment. L'agent dispose donc de deux stratégies possibles :

| Stratégie | Mécanisme | Quand elle gagne |
|---|---|---|
| **Innée** | Préférence fixe héritée pour un type | L'environnement est stable — la préférence reste correcte |
| **Acquise** | Goûter, subir la conséquence, ajuster | L'environnement change — seule l'expérience directe informe |

**Pourquoi ce dispositif plutôt qu'un autre.** Trois propriétés le rendent adapté :

1. **Le signal de renforcement est intrinsèque.** Le gain ou la perte d'énergie *est* le signal d'apprentissage. Il n'y a rien d'artificiel à ajouter au modèle : le renforcement tombe de l'écologie elle-même.
2. **Le coût de l'apprentissage est intrinsèque.** Pour découvrir quel type est bon, il faut nécessairement goûter le mauvais et le payer. C'est exactement le coût décrit par Johnston et Dukas, et non un terme ajouté à la main.
3. **C'est de l'éthologie documentée.** L'aversion gustative conditionnée — l'effet Garcia (Garcia & Koelling 1966) — est un phénomène réel et bien étudié.

**Pourquoi les gains sont asymétriques (+25 / −10).** Avec des gains symétriques, manger un aliment au hasard aurait une espérance de gain nulle : aucun bénéfice, mais une variance ajoutée — et près du seuil de mort par famine, la variance tue. La sélection éliminerait alors le comportement alimentaire lui-même, ce qui a été effectivement mesuré (4,1 repas par vie, 1,2 % de survie ; voir §8). L'asymétrie garantit que goûter reste rentable en moyenne (+7,5 par repas au hasard), tout en rendant la discrimination bien meilleure encore (+25 par repas).

### 3.4 Perception de Pascor

Pascor perçoit son environnement par **capteurs sectoriels**, une approche standard en robotique évolutionnaire. Son champ de vision de 180°, centré sur son cap, est découpé en 5 secteurs égaux. Chaque secteur renvoie la proximité de l'objet le plus proche qu'il contient : 1,0 si l'objet touche l'agent, 0,0 si rien n'est perçu dans ce secteur.

Ces 5 secteurs sont dupliqués sur **trois canaux indépendants** :

| Canal | Contenu | Entrées |
|---|---|---|
| 1 | Aliments de type A | 5 |
| 2 | Aliments de type B | 5 |
| 3 | Venator | 5 |
| — | Énergie normalisée | 1 |
| | **Total** | **16** |

La séparation des canaux alimentaires est indispensable : sans elle, l'agent ne pourrait pas distinguer les deux types, et aucune discrimination — innée ou apprise — ne serait possible. En revanche, **rien dans la perception n'indique lequel est comestible**. C'est précisément l'information que l'agent doit soit avoir héritée, soit découvrir.

La portée de vision est de 260 unités, soit environ 16 % de la largeur de l'arène : l'agent est loin d'avoir une vision globale, il doit explorer.

### 3.5 Action, énergie et mort

Le réseau produit **trois sorties** :

| Sortie | Domaine | Effet |
|---|---|---|
| Rotation | −1 à +1 | Changement de cap, jusqu'à 0,16 radian par pas |
| Poussée | 0 à 1 | Vitesse, jusqu'à 2,6 unités par pas |
| **Ingestion** | 0 à 1 | **Probabilité** d'avaler l'aliment au contact |

**Pourquoi une décision d'ingestion.** Sans cette troisième sortie, l'agent avalerait automatiquement tout ce qu'il touche, et la discrimination ne pourrait s'exprimer que par la navigation — impossible dans un patch où les deux types sont mélangés. La mesure confirme son importance : ajouter ce portail fait passer la discrimination d'un agent à préférence correcte de 65 % à 76 %.

**Pourquoi probabiliste plutôt qu'un seuil.** Avec un seuil fixe, la sortie devait franchir 0,5 pour que quoi que ce soit change. Or l'apprentissage déplaçait cette sortie de 2 % seulement : il était réel au niveau des poids, mais aucune décision ne changeait, donc aucun effet sur la fitness, donc rien à sélectionner. En probabiliste, la sortie *est* la probabilité d'ingérer, et le moindre déplacement se traduit immédiatement en changement de comportement. C'est aussi plus plausible biologiquement — aucun animal n'applique un seuil parfaitement net à une tendance comportementale.

**Bilan énergétique.**

| Poste | Valeur |
|---|---|
| Énergie initiale | 100 |
| Plafond | 200 |
| Coût métabolique de base | 0,08 par pas |
| Coût du mouvement | jusqu'à 0,05 par pas |
| Durée de vie maximale | 3000 pas |

Sur une vie complète, le coût métabolique cumulé atteint environ 350 unités, soit bien plus que la réserve initiale : **un agent qui ne mange pas meurt**, quelle que soit sa stratégie. Un agent qui mange sans discriminer récolte environ +7,5 par repas et survit médiocrement. Un agent qui discrimine récolte +25 par repas et prospère.

**Trois causes de mort** : famine (énergie épuisée), prédation (capture par Venator), et vieillesse (fin de la durée de vie maximale). Seules les deux premières comptent comme des échecs — mourir de vieillesse est un succès biologique.

**Le nombre d'événements d'apprentissage est un paramètre critique.** Ce n'est pas la durée de vie en pas de temps qui détermine si un apprentissage est possible, mais le **nombre de dégustations**. Les paramètres initiaux donnaient 7,1 repas par vie, soit environ 3,5 par type — bien trop peu pour extraire une discrimination binaire, et déjà létal côté toxique. Les paramètres actuels donnent **20 à 27 repas par vie**.

### 3.6 Venator, la pression de sélection

Venator possède un comportement **scripté**, en trois états :

| État | Comportement |
|---|---|
| Patrouille | Errance à cap dérivant lentement, vitesse 1,5 |
| Poursuite | Fonce sur le Pascor le plus proche détecté dans un rayon de 130 unités, vitesse 3,0 ; abandonne après 180 pas |
| Satiété | Après une capture, 300 pas d'inactivité prédatrice |

**Venator n'évolue pas et n'apprend pas.** Ce choix est délibéré et important pour la validité de l'expérience : une coévolution proie-prédateur ferait varier la difficulté de l'environnement indépendamment des axes manipulés, et confondrait cette variation avec l'effet de la volatilité ou du coût. Venator est un instrument, pas un sujet d'étude.

Sa densité est fixée en **ratio** (1 pour 20 Pascor, soit 5 au total) plutôt qu'en nombre absolu, de sorte que la pression de prédation reste comparable si la taille de population change.

Sa létalité a été calibrée par balayage pour viser 30-50 % de survie chez un agent de référence compétent. La prédation représente environ 29 % des morts, en équilibre avec la famine.

### 3.7 Le contrôleur : NEAT

Le comportement de Pascor est produit par un réseau de neurones évolué par **NEAT** (*NeuroEvolution of Augmenting Topologies*, Stanley & Miikkulainen 2002). NEAT fait évoluer conjointement les poids **et la topologie** du réseau : il part de réseaux minimaux et ajoute progressivement neurones et connexions par mutation, en protégeant les innovations récentes par un mécanisme de spéciation.

| Paramètre NEAT | Valeur |
|---|---|
| Taille de population | 100 |
| Entrées / sorties | 16 / 3 |
| Topologie initiale | connexions directes entrées→sorties, sans couche cachée |
| Activation | tanh, gain 0,8 |
| Écart-type des poids initiaux | 0,4 |
| Élitisme | 2 génomes |
| Seuil de compatibilité (spéciation) | 3,0 |

**Le gain d'activation à 0,8** est nettement inférieur au 2,5 par défaut de la bibliothèque. Avec 16 entrées et des poids d'écart-type 1, la somme pondérée atteignait couramment ±2, que tanh(2,5x) écrase à ±1 : 59 % des sorties étaient **saturées**. Un réseau saturé est une fonction constante — il ignore ses capteurs, et ni l'inné ni l'acquis ne peuvent s'exprimer. Après correction : 0 % de saturation.

### 3.8 L'inné, l'acquis, et le curseur entre les deux

C'est ici que se situe le dispositif central du projet.

Chaque Pascor porte, **en plus** de son réseau NEAT, une **préférence alimentaire** explicite : un scalaire par type d'aliment, borné dans [−1, +1], qui pondère directement sa décision d'ingérer.

```
probabilité d'ingérer = sortie_réseau + préférence(type au contact)
```

Cette variable se décompose exactement selon les deux termes du projet :

| | Définition | Transmission |
|---|---|---|
| **Inné** | La valeur initiale des préférences, encodée dans le génome | **Héritée**, moyenne des deux parents, mutable |
| **Acquis** | Leur déplacement au cours de la vie, par expérience directe | **Meurt avec l'individu**, jamais transmise |
| **η** | Le taux de ce déplacement, dans [0, 1] | **Hérité**, mutable, **soumis à la sélection** |

η est le point crucial : **on ne décide pas si Pascor apprend, la sélection en décide**. Un individu avec η = 0 conserve toute sa vie les préférences avec lesquelles il est né — comportement purement inné. Un individu avec η = 1 reformate fortement ses préférences selon son expérience — comportement fortement acquis. Comme η est hérité et muté, sa valeur moyenne dans la population évolue, et c'est cette évolution qui constitue la mesure principale du projet.

| Paramètre du gène η | Valeur |
|---|---|
| Initialisation | uniforme sur [0, 1] — aucun a priori inné/acquis |
| Probabilité de mutation | 0,25 par génération |
| Amplitude de mutation | gaussienne, écart-type 0,12 |
| Poids dans la distance génétique | 1,0 |

η participe à la **distance génétique** utilisée pour la spéciation : deux individus de topologie identique mais de stratégies opposées — tout inné contre tout acquis — ne sont pas le même phénotype et ne doivent pas être systématiquement regroupés dans la même espèce.

**Pourquoi un seul η scalaire.** Une plasticité définie connexion par connexion serait plus réaliste biologiquement — toutes les synapses ne sont pas également plastiques. Mais il n'y aurait alors plus de nombre unique à tracer : il faudrait résumer des dizaines de valeurs pour produire la mesure centrale du projet, et ce choix de résumé serait une décision arbitraire supplémentaire. C'est une simplification assumée, et une piste d'extension identifiée.

**Pourquoi un substrat dédié plutôt qu'une plasticité synaptique diffuse.** Le projet a d'abord tenté de faire porter l'apprentissage sur l'ensemble des poids du réseau, par une règle hebbienne modulée par récompense. Cela n'a produit aucun effet mesurable, pour une raison identifiée après diagnostic : l'information à apprendre est littéralement **un bit** — quel type est comestible cette génération — et la règle devait le découvrir en modifiant des dizaines de poids d'un réseau gérant aussi le déplacement et la fuite. Ce bit y était dilué. Les implémentations qui reproduisent l'effet Baldwin (Hinton & Nowlan 1987, Mayley 1996) font toutes apprendre sur un substrat dédié et de basse dimension. Passer au substrat dédié a multiplié l'effet de l'apprentissage par **35**, à règle inchangée. C'est aussi plus juste biologiquement : l'effet Garcia est un apprentissage **en un seul essai**, pas une dérive synaptique graduelle.

### 3.9 La règle d'apprentissage

À chaque ingestion, la préférence du type qui vient d'être avalé se déplace vers la conséquence subie :

```
préférence[type] ← préférence[type] + η × 0,35 × (cible − préférence[type])
```

où la cible vaut **+1** si l'aliment était nutritif et **−1** s'il était toxique.

Le taux de 0,35 est réglé pour qu'une poignée de dégustations suffise à inverser une préférence, conformément à l'apprentissage en un essai de l'aversion gustative conditionnée — et non à une dérive graduelle nécessitant des centaines d'événements.

Le déplacement de préférence est comptabilisé comme **coût réalisé de l'apprentissage**, quantité utilisée pour tester H2 : modifier une préférence n'est pas gratuit.

Une plasticité hebbienne modulée par récompense subsiste sur les poids du réseau, avec traces d'éligibilité, mais elle joue désormais un rôle secondaire.

### 3.10 La fonction de fitness

```
fitness = 25 × (aliments nutritifs ingérés)
        − 10 × (aliments toxiques ingérés)
        + 25 × (âge atteint / 3000)
        −  λ × (coût d'apprentissage réalisé)
```

La fitness compte **l'énergie réellement récoltée**, et non le nombre d'items. La distinction est décisive : une version antérieure comptait `nutritifs − toxiques`, un décompte symétrique qui contredisait l'écologie asymétrique du modèle. Un agent mangeant au hasard obtenait alors une fitness d'environ zéro, exactement comme un agent ne mangeant rien — alors qu'écologiquement il récoltait +7,5 par repas. Conséquence mesurée : en environnement volatil, la sélection éliminait le comportement alimentaire lui-même. La correction a fait passer le nombre de repas de 4,1 à 25,7 par vie.

Le terme de survie évite que la fitness ne sature une fois la discrimination acquise par toute la population : sans lui, tous les bons discriminateurs auraient la même fitness et le gradient de sélection disparaîtrait.

Le terme λ est nul sauf dans les expériences de H2.

### 3.11 La boucle évolutive

Chaque génération suit le même cycle :

1. **Évaluation** — les 100 génomes vivent simultanément dans une simulation de 3000 pas, deux fois (§3.12).
2. **Attribution des fitness** — sur la base de la vie réellement vécue, plasticité active.
3. **Sélection et reproduction** — NEAT applique spéciation, élitisme (2 génomes conservés), croisement et mutation.
4. **Changement d'environnement** — si le paramètre de volatilité l'impose, les patchs sont redistribués et la validité des types s'inverse.

**Invariant vérifié :** l'environnement ne change **jamais** pendant la vie d'un individu sur l'axe inter-générationnel — testé explicitement, déplacement de 0,0 sur 3000 pas. Sans cette stabilité intra-vie, l'apprentissage n'aurait aucun substrat stable à exploiter. L'axe intra-vie (§4.1) lève délibérément cet invariant, et c'est précisément ce qui permet de tester la branche descendante de H1.

### 3.12 La double évaluation : mesurer l'inné et l'acquis séparément

C'est le dispositif de mesure central.

Chaque génération, **le même génome est évalué deux fois**, dans deux mondes strictement identiques — mêmes positions de patchs, même type nutritif, même graine aléatoire, donc mêmes positions initiales et mêmes trajectoires de Venator :

| Condition | Plasticité | Ce que ça mesure |
|---|---|---|
| **P_naïf** | Gelée dès la naissance | L'**inné** pur — ce que l'individu sait faire sans jamais rien apprendre |
| **P_libre** | Active toute la vie | **Inné + acquis** combinés |
| **ΔP = P_libre − P_naïf** | — | Ce que l'**apprentissage** apporte réellement |

Les deux évaluations ne diffèrent que par la plasticité. Tout écart entre elles est donc attribuable à l'apprentissage, et à rien d'autre.

La fitness qui pilote la sélection est celle de **P_libre** : c'est la vie que l'organisme mène réellement. P_naïf est une mesure, pas une vie.

Cette double évaluation double le coût de calcul, mais elle fournit à chaque génération une décomposition directe de la contribution de chaque composante — sans quoi il faudrait inférer indirectement ce que l'apprentissage apporte.

---

## 4. Plan expérimental

### 4.1 Les deux axes de volatilité

| Axe | Paramètre | Signification | Branche de H1 testée |
|---|---|---|---|
| **Inter-générationnel** | `T_env` | Nombre de générations entre deux changements d'environnement | **Montante** — l'inné devient obsolète |
| **Intra-vie** | `v_vie` | Nombre d'inversions de la validité des types **pendant** une vie | **Descendante** — l'acquis devient obsolète |

**Niveaux de l'axe inter-générationnel**, espacés géométriquement pour bien résoudre une éventuelle réponse en cloche :

| Niveau | T_env | Changements sur 60 générations |
|---|---|---|
| stable | ∞ | 0 |
| faible | 50 | 1 |
| forte | 5 | 12 |
| maximale | 1 | 60 |

**Niveaux de l'axe intra-vie**, les inversions étant réparties uniformément sur les 3000 pas de la vie :

| Niveau | Inversions | Repas disponibles entre deux inversions |
|---|---|---|
| nulle | 0 | — (environnement fixe) |
| lente | 1 | ~10 |
| moderee | 3 | ~5 |
| rapide | 9 | ~2 |
| chaotique | 29 | <1 |

Cette dernière colonne est essentielle à l'interprétation : elle indique combien de dégustations l'agent peut effectuer avant que ce qu'il a appris ne devienne faux.

L'axe intra-vie est testé à `T_env = maximale`, où **aucune préférence héritée ne peut jamais être correcte**. C'est la condition qui isole proprement l'effet de la volatilité intra-vie, puisque l'inné n'y apporte rien par construction.

### 4.2 L'axe du coût (H2)

Le paramètre λ pénalise la fitness proportionnellement au coût d'apprentissage réalisé. Ses valeurs ne sont pas arbitraires : elles ont été **calibrées** pour représenter une fraction cible de la fitness typique, par la procédure `λ = fraction × F / C` où F est la fitness moyenne mesurée (234,8) et C le coût d'apprentissage réalisé moyen (6,21) dans la condition de référence.

| λ | Coût représentant |
|---|---|
| 0 | témoin |
| 3,8 | ~10 % de la fitness |
| 9,4 | ~25 % |
| 18,9 | ~50 % |

Cette calibration est indispensable : un λ choisi arbitrairement n'aurait aucune signification interprétable, puisque son effet dépend entièrement des échelles relatives de la fitness et du coût.

### 4.3 Les lésions in silico (H3)

Une population **évoluée** est soumise à quatre conditions, dans un environnement identique. Le génome est le même partout ; seul change ce qu'on lui permet d'utiliser.

| Condition | Génomes | Plasticité | Préférences innées | Question posée |
|---|---|---|---|---|
| **aléatoire** | non évolués | gelée | aléatoires | Que vaut un agent qui n'a ni hérité ni appris ? |
| **inné seul** | évolués | gelée | intactes | Que vaut l'inné seul ? |
| **inné + acquis** | évolués | active | intactes | Que valent les deux ensemble ? |
| **acquis seul** | évolués | active | **remises à zéro** | L'apprentissage peut-il reconstruire ce que l'évolution avait encodé ? |

La quatrième condition est la plus informative : elle efface l'information héritée tout en conservant le réseau évolué et la capacité d'apprendre.

Trois environnements sont testés, choisis pour couvrir les trois régimes identifiés : `stable` (l'inné suffit), `maximale` (seul l'acquis peut aider), `chaotique` (rien ne peut aider).

### 4.4 Les métriques

| Métrique | Définition | Ce qu'elle mesure |
|---|---|---|
| **η moyen** | Moyenne du gène de plasticité dans la population | La réponse de la **sélection** — vers l'inné ou vers l'acquis |
| **Taux de discrimination** | Nutritifs ingérés / total ingéré. 0,5 = hasard, 1,0 = parfait | La qualité de la **stratégie alimentaire** |
| **Écart plastique − figé** | Discrimination de P_libre moins celle de P_naïf | Ce que l'apprentissage apporte **au comportement** |
| **ΔP** | P_libre − P_naïf en fitness | Ce que l'apprentissage apporte **à la fitness** |
| **Repas par vie** | Nombre d'ingestions | Contrôle : l'agent a-t-il eu de quoi apprendre ? |
| **Discrimination par tiers de vie** | Taux de discrimination sur chaque tiers | La **progression intra-vie** (test de H3c) |

**Une métrique écartée, et pourquoi.** La quantité de nourriture consommée par tiers de vie avait d'abord été retenue comme preuve d'apprentissage. Elle s'est révélée **confondue** : un contrôleur sans aucune plasticité montrait déjà +0,39 item d'amélioration entre le premier et le dernier tiers, positive dans 6 runs sur 8. L'explication est un effet d'installation spatiale combiné à la survie sélective — les individus qui atteignent la fin de vie sont ceux qui ont trouvé un patch et s'y sont fixés, donc ils mangent mécaniquement plus tard dans leur vie, sans avoir rien appris. Le **taux de discrimination** ne souffre pas de ce biais : s'installer près d'un patch n'améliore en rien la capacité à distinguer le comestible du toxique. Vérification sur un agent sans plasticité : pente de −1,39 point (± 2,89), centrée sur zéro.

Cet épisode illustre un principe méthodologique appliqué tout au long du projet : **toute métrique censée prouver l'apprentissage doit d'abord être testée sur un agent incapable d'apprendre**. Si elle produit un signal positif dans ce cas, elle est inutilisable.

### 4.5 Réplication et analyse statistique

**L'unité statistique est le run, pas l'individu.** Les 100 individus d'un même run partagent une histoire évolutive — mêmes ancêtres, mêmes hasards de mutation et de sélection — et ne constituent pas des observations indépendantes. Les traiter comme telles serait de la **pseudo-réplication** (Hurlbert 1984), et gonflerait artificiellement la significativité. Chaque métrique est donc d'abord moyennée à l'intérieur d'un run, puis les runs servent d'unités.

**Trois runs indépendants par condition** (graines 21, 22, 23). C'est peu, et cette limite est discutée au §7.

**Les 20 premières générations sont écartées** de toutes les analyses. Avant ce seuil, les réseaux ne savent pas encore fourrager : la mesure donne environ 4 repas par vie à la génération 0, contre 25 après la génération 20. Un agent qui ne mange pas ne peut pas apprendre, et l'absence d'effet de la plasticité y est un artefact et non un résultat.

**Tests employés :**

- **Corrélation de rang de Spearman** entre le niveau du facteur manipulé et la métrique, calculée sur l'ensemble des runs. Non paramétrique, donc sans hypothèse sur la forme de la relation ni sur la normalité.
- **Mann-Whitney** pour les comparaisons entre conditions.
- **d de Cohen** pour la taille d'effet — parce qu'un p petit sur un effet minuscule n'a aucun intérêt biologique.

---

## 5. Résultats

### 5.1 H1, branche montante : la volatilité entre générations

![H1 inter-générationnel](figures/fig_h1_inter_gen.png)

| Volatilité (1/T_env) | η final | Écart plastique − figé | Repas/vie |
|---|---|---|---|
| stable (0) | 0,339 | +0,045 | 26 |
| faible (0,02) | 0,423 | +0,053 | 22 |
| **forte (0,20)** | **0,556** | +0,078 | 21 |
| maximale (1,0) | 0,461 | **+0,080** | 19 |

**L'avantage de la plasticité croît nettement avec la volatilité** : ρ = +0,820, **p = 0,0011**. C'est le mécanisme attendu, et il est solidement établi. Sa **conséquence** est directe : plus l'environnement change entre générations, plus une préférence héritée a de chances d'être fausse à la naissance, et plus l'agent a intérêt à découvrir par lui-même. Le tableau montre d'ailleurs le mécanisme sous-jacent — la discrimination des agents **figés** chute de 0,743 en environnement stable à 0,547 en environnement volatil, se rapprochant du hasard : l'inné cesse littéralement de pouvoir encoder la bonne réponse.

**Mais la réponse évolutive de η n'atteint pas la significativité** : ρ = +0,453, **p = 0,139**, avec une dispersion importante entre runs (0,70 / 0,54 / 0,43 au niveau `forte`). La tendance va dans le sens prédit, mais trois runs ne suffisent pas à l'affirmer.

Un détail oriente les réplications futures : le maximum de η se situe à `forte` (0,556) et non à `maximale` (0,461). Ce serait précisément l'**optimum intermédiaire** prédit par Stephens. Le signal est trop bruité pour être affirmé, mais il désigne exactement où chercher.

**Conclusion de cette section** : la branche montante est établie au niveau du bénéfice de la plasticité, mais pas au niveau de la réponse évolutive de η. C'est la partie la moins solide du travail, et elle est présentée comme telle.

### 5.2 H1, branche descendante : la volatilité pendant la vie

![H1 intra-vie](figures/fig_h1_intra_vie.png)

| Inversions/vie | η final | Écart plastique − figé | Repas/vie |
|---|---|---|---|
| 0 | 0,499 | +0,083 | 19 |
| 1 | 0,386 | +0,085 | 18 |
| **3** | **0,187** | **+0,015** | 27 |
| 9 | 0,123 | +0,001 | 23 |
| 29 | 0,199 | −0,000 | 21 |

**η : ρ = −0,764, p = 0,0009. Écart de discrimination : ρ = −0,917, p < 0,0001.** Contraste entre les extrêmes : **d de Cohen = 2,51**, une taille d'effet considérable.

**Ce que ces chiffres signifient.** L'avantage de la plasticité s'effondre d'un facteur 80 entre 1 et 3 inversions par vie. En parallèle, la sélection réduit η de moitié. Autrement dit : dès que l'environnement change plus vite que l'individu ne peut apprendre, non seulement l'apprentissage cesse d'être utile, mais **la sélection élimine activement la capacité d'apprendre**.

**Le seuil est quantifiable, et c'est ce qui rend le résultat interprétable.** Avec environ 20 repas par vie, une inversion laisse une dizaine de dégustations pour réapprendre — largement assez. Trois inversions n'en laissent que cinq, ce qui est déjà insuffisant. Le seuil ne se situe pas à une fréquence arbitraire : il se situe là où **le nombre d'occasions d'apprendre tombe sous ce que l'apprentissage exige**. La transition n'est donc pas graduelle mais franche, comme le montre la figure.

**Un contrôle involontaire mais informatif.** Le nombre de repas ne diminue pas avec la volatilité intra-vie — il augmente même légèrement (19 → 27). L'effondrement de l'avantage plastique n'est donc pas dû à un manque d'occasions d'apprendre, mais bien à l'obsolescence de ce qui est appris. C'est exactement la distinction que la branche descendante devait établir.

**Le point à 29 inversions.** η remonte légèrement (0,199), avec une dispersion très forte entre runs (0,37 / 0,14 / 0,09). L'interprétation est cohérente avec la théorie : quand la plasticité ne sert plus à rien, **η n'est plus sous sélection et devient un gène neutre**, qui dérive librement. La forte dispersion entre runs est la signature attendue d'une dérive génétique, et non un contre-exemple.

### 5.3 H2 : le coût de l'apprentissage

![H2 coût](figures/fig_h2_cout.png)

| λ | Coût ≈ | η final | Écart plastique − figé |
|---|---|---|---|
| 0 | — | **0,499** | +0,083 |
| 3,8 | 10 % | 0,343 | +0,064 |
| 9,4 | 25 % | 0,308 | +0,069 |
| 18,9 | 50 % | **0,185** | +0,054 |

**ρ = −0,820, p = 0,0011. d de Cohen = 5,18** — une taille d'effet très importante.

**Le résultat le plus significatif de cette section n'est pas la baisse de η, mais ce qui l'accompagne.** L'écart de discrimination reste **positif à tous les niveaux de coût** : +0,054 même à λ maximal, contre +0,083 sans coût. Autrement dit, **la plasticité continue de fonctionner** — elle rend toujours l'agent meilleur discriminateur — et pourtant la sélection l'abandonne, réduisant η de 63 %.

**Conséquence.** Ce n'est pas que l'apprentissage cesse de marcher, c'est qu'il cesse d'être **rentable**. La sélection n'optimise pas l'efficacité comportementale, elle optimise le bénéfice net. Un mécanisme qui améliore réellement le comportement peut être éliminé s'il coûte trop cher — ce qui est exactement la prédiction de Johnston (1982) et Dukas (1998), et ce qui distingue une explication adaptationniste naïve d'une analyse coût-bénéfice.

C'est aussi une réponse à une objection courante en biologie évolutive : « si ce trait est utile, pourquoi n'est-il pas universel ? » Ce résultat montre qu'un trait peut être utile et néanmoins contre-sélectionné.

### 5.4 H3 : la répartition inné/acquis dépend de l'environnement

![H3 lésions](figures/fig_h3_lesions.png)

Fitness moyenne des quatre conditions de lésion, dans trois environnements :

| Condition | stable | maximale | chaotique |
|---|---|---|---|
| aléatoire (ni hérité ni appris) | 45,8 | 41,7 | 47,9 |
| inné seul | 431,3 | 210,8 | 191,4 |
| inné + acquis | 433,5 | 246,9 | 186,2 |
| acquis seul (préférences effacées) | 389,0 | 243,2 | 161,9 |

**3a — le socle inné est fonctionnel.** Toutes conditions confondues, les génomes évolués à plasticité gelée atteignent 277,8 contre 45,1 pour des génomes non évolués : un facteur 6, **p = 0,0002**. L'évolution produit bien un comportement de base opérationnel, indépendamment de tout apprentissage.

**3b — l'apprentissage n'apporte un gain que là où il est utile.**

| Environnement | ΔP | Les trois runs |
|---|---|---|
| stable | +2,2 | −8, +24, −9 |
| **maximale** | **+36,1** | **+43, +27, +38** |
| chaotique | −5,2 | −38, −24, +46 |

En `maximale`, les trois runs sont positifs et cohérents. Ailleurs, ΔP oscille autour de zéro. Mann-Whitney maximale contre les deux autres : p = 0,083 — la tendance est nette mais la taille d'échantillon plafonne la significativité (§7).

**Le résultat le plus fort — effacer l'inné :**

| Environnement | Effet de la lésion |
|---|---|
| stable | **−42,3** |
| maximale | **+32,4** |
| chaotique | −29,5 |

Mann-Whitney maximale contre stable : **p = 0,050**.

**Ce que cela signifie.** En environnement stable, effacer les préférences innées coûte cher : elles y encodent une information correcte et précieuse. En environnement maximalement volatil, les effacer **améliore** la performance. La raison est directe : une préférence héritée y a une chance sur deux d'être fausse, et une préférence fausse n'est pas neutre — elle pousse activement l'agent vers l'aliment toxique. L'agent s'en sort mieux en partant de zéro et en découvrant par lui-même.

C'est H3 dans sa forme forte. Non seulement les deux composantes contribuent, mais **laquelle porte l'information utile bascule complètement avec l'environnement**. L'inné n'est pas « toujours un peu utile » : il peut être un handicap net.

---

## 6. Discussion

### 6.1 Trois chemins distincts vers l'inné

Le résultat le plus général du travail est que **trois mécanismes différents mènent à la même conclusion évolutive** — l'abandon de la plasticité — pour des raisons qui n'ont rien à voir entre elles.

| Situation | Pourquoi l'inné gagne | Mesure |
|---|---|---|
| **Environnement stable** | Il n'y a **rien à apprendre** : l'information héritée est déjà correcte | Discrimination innée à 0,743 ; effacer l'inné coûte −42,3 |
| **Changement trop rapide** | Il est **impossible d'apprendre** : l'acquis devient faux avant de servir | η : 0,499 → 0,123 (p = 0,0009) |
| **Apprentissage coûteux** | Il n'est **pas rentable**, bien qu'il fonctionne toujours | η : 0,499 → 0,185 (p = 0,0011) ; avantage brut toujours positif |

Cette convergence par trois voies indépendantes est ce qui donne du poids à l'ensemble : aucun artefact commun ne peut expliquer simultanément une réponse à la volatilité intra-vie, une réponse au coût, et une inversion du signe de la lésion selon l'environnement.

Elle a aussi une portée générale. Observer qu'une espèce a un comportement essentiellement inné ne permet pas de conclure sur son environnement : la même observation est compatible avec un milieu très stable, avec un milieu trop imprévisible, ou avec un apprentissage trop coûteux. **Il faut mesurer le mécanisme, pas seulement le résultat.**

### 6.2 Deux axes plutôt qu'un

La prédiction de Stephens est habituellement formulée sur une variabilité environnementale unique. Le développement de ce projet a montré que cette formulation masque deux phénomènes distincts.

Une première version du dispositif fixait l'environnement pendant toute la vie d'un individu — un choix justifié à l'époque, puisque sans stabilité intra-vie l'apprentissage n'aurait aucun substrat stable. Résultat : η croissait de façon **monotone** avec la volatilité, sans jamais redescendre. La branche descendante n'avait pas échoué à apparaître, elle était **exclue par construction**.

L'ajout d'un second axe — la volatilité pendant la vie — a fait apparaître la branche descendante immédiatement, et avec une significativité supérieure à celle de la branche montante.

La leçon est méthodologique autant que théorique : **une prédiction en cloche exige que les deux mécanismes qui produisent ses deux branches soient tous deux présents dans le modèle**. Un dispositif qui n'en implémente qu'un ne peut pas la tester, quelle que soit la finesse du reste.

### 6.3 Un seuil quantifiable plutôt qu'une tendance

La plupart des résultats de ce type se présentent comme des tendances : « plus l'environnement change, moins la plasticité est favorisée ». Le dispositif permet ici d'aller un cran plus loin.

L'effondrement se produit entre 1 et 3 inversions par vie, ce qui correspond au passage de ~10 à ~5 dégustations disponibles entre deux changements. Comme la règle d'apprentissage a un taux connu (0,35), on peut estimer indépendamment combien de dégustations sont nécessaires pour inverser une préférence — et retrouver le même ordre de grandeur.

Le seuil n'est donc pas une propriété émergente inexpliquée : il se déduit du rapport entre **la vitesse de changement de l'environnement** et **la vitesse d'apprentissage de l'organisme**. C'est cette commensurabilité qui rend le résultat transposable au-delà du modèle.

---

## 7. Limites

**Réplication.** Trois runs par condition. C'est suffisant pour distinguer un effet réel d'une dérive, mais insuffisant pour la puissance statistique. Avec n = 3, un test des signes ne peut mathématiquement pas descendre sous p = 0,125, ce qui **plafonne mécaniquement** H3b à p = 0,083 malgré trois runs concordants. Ce n'est pas un défaut de signal mais de dimensionnement. Cinq à dix runs par condition seraient nécessaires pour une conclusion ferme.

**La branche montante de H1 n'est pas établie.** L'avantage de la plasticité croît nettement avec la volatilité inter-générationnelle (p = 0,001), mais la réponse évolutive de η n'atteint pas le seuil (p = 0,139). Une réplication plus large est nécessaire, notamment pour trancher si le maximum de η se situe bien à volatilité intermédiaire — ce que les données suggèrent sans le démontrer.

**Venator ne coévolue pas.** Choix délibéré, justifié pour ne pas confondre les axes expérimentaux, mais qui exclut une dimension réelle de l'écologie : dans la nature, le prédateur s'adapte aussi.

**Un seul η par individu.** Simplification assumée (§3.8) : une plasticité par connexion serait plus réaliste mais rendrait la mesure centrale ambiguë.

**Le substrat d'apprentissage est dédié.** La discrimination alimentaire s'apprend sur une variable explicite plutôt que sur l'ensemble des poids du réseau. Ce choix est justifié théoriquement et biologiquement (§3.8), mais il reste une simplification par rapport à une plasticité synaptique généralisée — et il signifie que le modèle démontre l'évolution du *taux* d'apprentissage, pas l'émergence de la *capacité* d'apprendre.

**Reproductibilité partielle des runs antérieurs.** Jusqu'à une correction tardive, la graine n'initialisait que le générateur de numpy, non le module `random` utilisé par NEAT pour les mutations. Les runs antérieurs à cette correction ne sont donc pas rejouables à l'identique. Le code actuel initialise toutes les sources d'aléa, ce qui a été vérifié par comparaison bit à bit de deux exécutions.

**Un seul niveau de population et de durée de vie.** Les résultats n'ont pas été testés en faisant varier la taille de population (100) ni la durée de vie (3000 pas). Le seuil de la branche descendante étant exprimé en nombre de dégustations, il devrait être robuste à ces variations — mais cela reste à vérifier.

---

## 8. Démarche de développement

Le mécanisme central n'est pas apparu du premier coup. Neuf obstacles ont dû être identifiés et levés, chacun traité de la même façon : formuler une hypothèse sur la cause, la tester par une mesure, accepter le verdict. **Quatre de ces hypothèses ont été réfutées par les données.**

| # | Hypothèse | Test | Verdict |
|---|---|---|---|
| 1 | Métriques mal définies | Mort de vieillesse comptée comme échec ; chaque pas de poursuite compté comme une rencontre distincte | ✅ corrigé — facteur 3 d'erreur sur le taux d'évitement |
| 2 | Métrique d'apprentissage confondue | Un agent **sans** plasticité montrait +0,39 item d'amélioration intra-vie (6 runs sur 8) | ✅ métrique remplacée |
| 3 | Coût de calcul prohibitif | 276 h estimées ; profilage : 81 % du temps dans la perception | ✅ vectorisation, **×4,8**, sorties identiques au bit près |
| 4 | Taux d'apprentissage trop faible | Dérive des poids mesurée à 0,067 — les poids bougeaient amplement | ❌ **réfutée** |
| 5 | Saturation du réseau | 59 % des sorties saturées (\|tanh\| > 0,99) | ✅ corrigée → 0 % |
| 6 | Direction de l'apprentissage | Seuls 25 réseaux sur 40 apprenaient dans le bon sens — à peine mieux que le hasard | ✅ corrigée → 100 % |
| 7 | Attribution du crédit (types mélangés) | Régime ambigu testé contre régime propre : +0,199 contre +0,161 | ❌ **réfutée** |
| 8 | Gains symétriques | Manger au hasard avait une espérance nulle : la sélection éliminait l'alimentation (4,1 repas/vie, 1,2 % de survie) | ✅ gains asymétriques |
| 9 | Fitness incohérente avec l'écologie | Énergie asymétrique (+25/−10) mais fitness en **items**, symétrique | ✅ fitness en énergie, repas 4,1 → 25,7 |

### Le déblocage

Après ces neuf correctifs, l'avantage de la plasticité restait nul. Le diagnostic final a porté sur l'architecture plutôt que sur les paramètres : l'information à apprendre étant **un seul bit**, la faire porter par des dizaines de poids d'un réseau polyvalent la diluait au point de la rendre inopérante. Le passage à un substrat dédié a multiplié l'effet par **35**, à règle d'apprentissage inchangée.

| | plasticité diffuse | substrat dédié |
|---|---|---|
| Divergence après 20 repas (η = 0,6) | +0,030 (z = 4,4) | **+1,05 (z = 15,1)** |
| Écart de discrimination | −0,0015 | **+0,07** |

### Trois leçons méthodologiques

**Un banc de test rapide vaut mieux que des runs longs.** Les correctifs 4 à 6 ont été diagnostiqués par des runs évolutifs d'une heure, alors qu'un test isolant la règle d'apprentissage hors du monde et de l'évolution (`test_regle.py`) donne un verdict en quelques secondes. Construire cet outil plus tôt aurait économisé plusieurs jours.

**Les bugs les plus coûteux ne font rien planter.** Le correctif 9 était une incohérence entre deux parties du modèle modifiées à des moments différents : le code tournait, les chiffres sortaient, et ils étaient faux. Aucune exception, aucun avertissement.

**Une seule graine ne prouve rien, même avec une belle corrélation.** La branche montante affichait ρ = 0,925 sur un run unique ; avec trois runs, la réponse de η retombe à p = 0,139. Seul l'écart de discrimination a survécu à la réplication.

Le détail complet de ces diagnostics — mesures, hypothèses réfutées, raisonnements — est conservé dans le [journal de bord](README_journal_de_bord.md).

---

## 9. Reproduire ces résultats

### Installation

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Python 3.9 ou supérieur. Dépendances : numpy, pygame, neat-python 2.0.0.

### Visualiser la simulation

```bash
python main.py                          # paramètres par défaut
python main.py --tenv stable            # environnement stable
python main.py --preference correcte    # agent de référence à préférence innée juste
```

Commandes clavier (compatibles AZERTY) : `ESPACE` pause, `S` capteurs, `T` traînées, `F` interface, `O`/`P` vitesse, `R` relancer, `ÉCHAP` quitter.

### Lancer un run évolutif

```bash
python evolution.py --tenv maximale --vvie nulle --seed 21 \
    --generations 60 --journal runs/exemple.csv --population pops/exemple.pkl
```

Chaque run produit un CSV comportant 29 colonnes, une ligne par génération, écrit **de façon incrémentale** — un run interrompu ne perd rien, et le fichier est lisible pendant l'exécution.

Durée : environ 25 minutes par run sur un cœur moderne.

### Lésions et analyse

```bash
python lesions.py pops/exemple.pkl                # décomposition inné/acquis
python analyse.py --runs runs --sortie figures    # statistiques et figures
python test_regle.py                              # test rapide de la règle
```

### Reproduire la campagne complète

Les scripts PowerShell du dossier `scripts/` lancent les campagnes complètes en parallèle, avec vérification préalable de l'environnement, journalisation des erreurs et bilan final :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\lancer.ps1
```

Les données brutes de tous les runs présentés ici sont incluses dans `runs/`, ce qui permet de recalculer les statistiques et de regénérer les figures sans relancer les simulations.

---

## 10. Organisation du code

| Fichier | Rôle |
|---|---|
| `config.py` | Tous les paramètres, avec justification en commentaire |
| `world.py` | Monde toroïdal, patchs, les deux axes de volatilité |
| `agents.py` | Pascor (corps, capteurs, énergie) et Venator (scripté) |
| `perception.py` | Perception vectorisée — tous les agents en une passe numpy |
| `genome.py` | Génome NEAT augmenté de η et des préférences innées |
| `brain.py` | Réseau, préférences alimentaires et règle d'apprentissage |
| `evolution.py` | Boucle évolutive, double évaluation, journalisation |
| `simulation.py` | Boucle de simulation et agrégation des métriques |
| `lesions.py` | Lésions in silico (H3) |
| `analyse.py` | Statistiques et figures |
| `test_regle.py` | Banc de test isolant la règle d'apprentissage |
| `diagnostic.py` | Diagnostic de l'apprentissage isolé de l'évolution |
| `render.py` | Rendu pygame |
| `main.py` | Visualisation interactive |

Les trois derniers outils de diagnostic ne servent pas à produire les résultats mais à vérifier que les mécanismes fonctionnent — ils ont été déterminants pendant le développement et sont conservés à ce titre.

---

## 11. Prolongements

- **Répliquer plus largement la branche montante** de H1 et vérifier si le maximum de η se situe à volatilité intermédiaire.
- **Croiser les deux axes** de volatilité en plan factoriel complet, pour vérifier que la fenêtre de Stephens apparaît comme une surface et non seulement comme deux coupes orthogonales.
- **Tester l'interaction volatilité × coût**, jamais explorée : le coût qui fait basculer vers l'inné dépend-il du régime de volatilité ?
- **Faire coévoluer Venator**, une fois les axes principaux solidement établis.
- **Plasticité par connexion**, pour tester si la sélection concentre la plasticité sur les voies liées à l'alimentation plutôt qu'à la fuite — ce qui serait une forme de modularité émergente.

---

## Références

- Dukas, R. (1998). *Cognitive Ecology: The Evolutionary Ecology of Information Processing and Decision Making*. University of Chicago Press.
- Garcia, J. & Koelling, R. A. (1966). Relation of cue to consequence in avoidance learning. *Psychonomic Science*, 4, 123-124.
- Hinton, G. E. & Nowlan, S. J. (1987). How learning can guide evolution. *Complex Systems*, 1, 495-502.
- Hurlbert, S. H. (1984). Pseudoreplication and the design of ecological field experiments. *Ecological Monographs*, 54(2), 187-211.
- Johnston, T. D. (1982). Selective costs and benefits in the evolution of learning. *Advances in the Study of Behavior*, 12, 65-106.
- Mayley, G. (1996). Landscapes, learning costs and genetic assimilation. *Evolutionary Computation*, 4(3), 213-234.
- Stanley, K. O. & Miikkulainen, R. (2002). Evolving neural networks through augmenting topologies. *Evolutionary Computation*, 10(2), 99-127.
- Stephens, D. W. (1991). Change, regularity, and value in the evolution of animal learning. *Behavioral Ecology*, 2(1), 77-89.
