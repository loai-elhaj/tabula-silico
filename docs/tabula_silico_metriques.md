# Tabula Silico — Spécification des métriques

Document de référence technique. À consulter pendant le développement pour éviter toute ambiguïté sur ce qui est mesuré, comment, et à quelle fréquence.

---

## 1. Principe de décomposition inné / acquis

Pour chaque individu échantillonné, on évalue **le même génome dans deux conditions** :

- **P_naïf** : plasticité gelée dès la naissance (réseau figé aux poids hérités du génome NEAT, aucune mise à jour hebbienne appliquée pendant toute la vie). Mesure pure de l'inné.
- **P_libre** : plasticité active normalement pendant toute la vie. Mesure combinée inné + acquis.
- **ΔP = P_libre − P_naïf** : gain apporté par l'apprentissage. Mesure de l'acquis.
- **ΔP relatif = ΔP / P_naïf** : gain normalisé, utile pour comparer des conditions où P_naïf diffère beaucoup.

Cette décomposition est calculée à **chaque génération**, idéalement sur **toute la population** plutôt que sur un sous-échantillon : évaluer un individu deux fois (figé, puis plastique) reste peu coûteux comparé au coût total de l'expérience (plus de générations, plus de runs), donc autant éliminer complètement le bruit d'échantillonnage à ce niveau. Le vrai enjeu statistique est ailleurs — voir §8.

Effet de bord à surveiller (non prévu comme hypothèse centrale, mais mesuré gratuitement) : si P_naïf augmente lui-même au fil des générations, cela indiquerait une forme d'assimilation génétique du socle inné — à documenter si observé.

---

## 2. Traits génétiques (héréditaires, sous sélection)

| Métrique | Symbole | Définition | Fréquence |
|---|---|---|---|
| Taux de plasticité | η | Scalaire génétique unique par individu (0 à 1), multiplie l'amplitude de toutes les mises à jour hebbiennes | Moyenne ± écart-type population, chaque génération |
| Complexité du réseau | — | Nombre de nœuds / connexions du génome NEAT | Moyenne population, chaque génération (métrique de contrôle) |

**Simplification assumée** : η est un scalaire unique par individu (pas un taux par connexion comme potentiellement dans Triturus Silico). Choix délibéré pour garder un chiffre unique et traçable.

---

## 3. Performance décomposée

| Métrique | Symbole | Fréquence de mesure |
|---|---|---|
| Performance innée | P_naïf | Échantillon de la population, chaque génération |
| Performance combinée | P_libre | Même échantillon, chaque génération |
| Gain acquis absolu | ΔP | Calculé à partir des deux ci-dessus |
| Gain acquis relatif | ΔP / P_naïf | Calculé à partir des deux ci-dessus |

---

## 4. Métriques comportementales / éthologiques

| Métrique | Définition | Ce qu'elle capture |
|---|---|---|
| Efficacité de foraging | Nourriture consommée / distance parcourue (ou / temps de vie) | Qualité de la stratégie de recherche |
| Taux d'évitement de Venator | Proportion des rencontres/détections de Venator terminées en survie | Qualité de l'évitement du danger |
| Taux de discrimination alimentaire | Nutritifs ingérés / total ingéré. 0,5 = hasard, 1,0 = discrimination parfaite | Métrique centrale du dispositif : mesure la qualité de la stratégie alimentaire, innée ou apprise |
| **Discrimination par tiers de vie** | Taux de discrimination sur le 1er, 2e et 3e tiers de vie, chez les individus ayant vécu les trois tiers | **Test de H3c.** Validée empiriquement comme exempte de confondant : pente de −1,39 point (± 2,89) chez un agent sans plasticité. À comparer entre plastiques et figés (§9.4) |
| Courbe de quantité mangée intra-vie | Nourriture consommée : 1er tiers vs dernier tiers | ⚠️ **Confondue** — augmente de +0,39 item même sans apprentissage (installation spatiale + survie sélective). Conservée comme diagnostic, **jamais comme preuve d'apprentissage** |
| Coût réalisé de l'apprentissage | Somme des \|Δw\| des mises à jour hebbiennes sur la vie entière | Vérifie que le coût pénalise effectivement la fitness comme prévu |

---

## 5. Paramètres indépendants (manipulés expérimentalement)

| Paramètre | Symbole | Opérationnalisation |
|---|---|---|
| Volatilité environnementale | T_env | Nombre de générations entre deux changements d'environnement. Un changement = les patchs sont retirés **et la validité des types de nourriture s'inverse** (le nutritif devient toxique). Environnement **fixe pendant la vie d'un individu** — seule la volatilité *inter-générationnelle* varie |
| Coût de l'apprentissage | λ_coût | Coefficient pénalisant la fitness proportionnellement au coût réalisé (voir §4) |

### Le dispositif à deux types de nourriture

Ce dispositif a remplacé la seule volatilité de position des patchs, qui ne pouvait **rien** apporter : avec des capteurs purement égocentriques, la stratégie optimale (« je vois de la nourriture dans le secteur 3 → je tourne vers 3 ») est identique quelle que soit la position des patchs. L'apprentissage n'avait donc aucun substrat, et η aurait convergé vers 0 dans toutes les conditions — un résultat dégénéré.

Deux types de nourriture, perceptivement distincts (canaux sensoriels séparés). À chaque changement d'environnement, l'un est nutritif (+25 énergie), l'autre toxique (−25), et lequel s'inverse :

- **Stratégie innée** : préférence fixe héritée pour un type. Gagne si l'environnement est stable, devient létale s'il s'inverse.
- **Stratégie acquise** : goûter, subir la conséquence, ajuster sa préférence.

Trois propriétés rendent ce dispositif adapté :
1. **Le signal de renforcement est intrinsèque** — le gain ou la perte d'énergie *est* le signal de récompense de la plasticité hebbienne modulée. Rien d'artificiel à inventer.
2. **Le coût de l'apprentissage est intrinsèque** — pour découvrir quel type est bon, il faut goûter le mauvais et le payer. C'est exactement le coût décrit par Johnston (1982) et Dukas (1998), pas un terme ajouté à la main.
3. **C'est de l'éthologie réelle** — aversion gustative conditionnée (effet Garcia), apprentissage des préférences alimentaires.

**Une troisième sortie du réseau est nécessaire : la décision d'ingestion.** Sans elle, l'agent avale automatiquement ce qu'il touche, et la discrimination ne peut s'exprimer que par la navigation — impossible dans un patch où les deux types sont mélangés. Mesure : le portail d'ingestion fait passer la discrimination d'un agent à préférence correcte de 65 % à 76 %.

**Valeurs exactes et grille expérimentale** : voir §9 — fixées précisément pour T_env, calibrées par une procédure explicite pour λ_coût (qui ne peut pas recevoir de valeur absolue arbitraire tant que l'échelle de la simulation n'existe pas).

---

## 6. Fonction de fitness

Avec deux types de nourriture, la fitness doit refléter la **discrimination**, pas le volume ingéré : un agent qui avale tout mange beaucoup et meurt quand même.

```
fitness = (nutritifs_mangés − toxiques_mangés) − λ_coût × coût_réalisé_apprentissage
```

La mort (Venator ou famine) met fin prématurément à l'accumulation — pas de terme de survie séparé nécessaire. Un agent indiscriminé obtient une fitness proche de zéro par construction (il mange ~50 % de chaque type), ce qui est le comportement voulu.

**Note :** la formule exacte reste à confirmer à l'étape 3c (boucle évolutive), notamment s'il faut ajouter un terme de survie pour éviter que la fitness ne sature une fois la discrimination acquise par toute la population.

---

## 7. Décisions d'architecture à figer avant le codage de l'environnement

| Décision | Choix proposé | Raison |
|---|---|---|
| Venator évolue-t-il ? | **Non — comportement scripté fixe** (ex. poursuite simple du Pascor le plus proche dans un rayon donné) | Évite une coévolution proie-prédateur qui confondrait la difficulté de l'environnement avec les deux axes expérimentaux (volatilité, coût) |
| Durée de vie | T_max ticks fixes, mort anticipée possible (Venator ou épuisement énergétique) | Nécessaire pour définir une fenêtre de vie comparable entre individus |
| Découpage intra-vie | Tiers de vie (1er tiers = "naïf comportemental", dernier tiers = "rodé") plutôt que fenêtre glissante | Plus simple à coder et interpréter pour la courbe d'apprentissage intra-vie |
| Échantillonnage pour P_naïf/P_libre | Toute la population, chaque génération | Le surcoût (double évaluation) reste faible comparé au coût total ; élimine le bruit d'échantillonnage à ce niveau |
| Perception de Pascor | Capteurs à rayons (façon Boids/robotique), quelques directions autour de lui | Approche standard en robotique évolutionnaire, facile à faire évoluer avec NEAT ; nombre exact de rayons et champ de vision à fixer lors du design de l'architecture d'entrée/sortie du réseau |
| Espace de mouvement | Continu (position x,y flottante, vitesse/angle) | Cohérent avec les capteurs à rayons ; plus réaliste qu'une grille discrète pour un comportement de recherche/fuite |
| Taille de population Pascor | N = 100 (par défaut, à valider au pilote) | Standard en littérature NEAT, assez grand pour éviter une convergence par pure dérive génétique. Le vrai goulot d'étranglement statistique est le nombre de *runs* indépendants (§8), pas la taille de la population dans un run — donc N sera revu à la baisse si le temps de calcul par génération, mesuré au pilote, limite trop le nombre de runs affordables |
| Densité et calibration de Venator | Ratio ~1 Venator pour 20 Pascor (donc 5 pour N=100). Comportement (rayon de détection, vitesse) calibré pour viser un taux de survie jusqu'à l'âge adulte de 30-50% à la génération 0 (population non évoluée) | Le ratio découple la pression de prédation de la taille de population choisie. La calibration sur un taux de survie cible évite les deux écueils : extinction totale (pression trop forte, aucune sélection possible) ou prédation négligeable (Venator décoratif, pas de vraie contrainte de fuite) |

---

## 8. Plan de logging et de réplication statistique

**Deux niveaux de réplication, à ne pas confondre :**

- **Niveau 1 — individus par génération** (pour P_naïf/P_libre) : toute la population, comme fixé au §1/§7. Peu coûteux, élimine le bruit à ce niveau.
- **Niveau 2 — runs évolutifs indépendants (seeds différentes) par condition (T_env × λ_coût)** : c'est le **véritable** niveau de réplication statistique. Les individus d'un même run partagent une histoire évolutive commune (ancêtres, hasards de mutation) — ils ne sont pas des observations indépendantes entre elles. Comparer des conditions entre elles nécessite plusieurs runs indépendants par condition, pas plus d'individus par run (risque classique de pseudo-réplication, cf. Hurlbert 1984).

**Comment fixer le nombre de runs par condition** : ne pas choisir un nombre arbitraire à l'avance. Utiliser le pilote déjà prévu (todo, étape 4) pour lancer quelques seeds indépendantes (ex. 5) sur une ou deux conditions repères, mesurer la variance inter-runs sur les métriques clés (η final, ΔP), puis en déduire par un calcul de puissance statistique (taille d'effet visée, seuil α, puissance ~80%) le nombre de runs réellement nécessaire par condition.

**Contrainte pratique** : coût total ≈ (nombre de conditions) × (runs par condition) × (durée d'un run). Préférer une grille de conditions plus grossière mais bien répliquée plutôt qu'une grille fine sous-répliquée.

**Format de logging** :
- Un fichier par run évolutif, une ligne par génération : η moyen ± écart-type, P_naïf moyen, P_libre moyen, ΔP moyen, ΔP relatif moyen, fitness moyenne, complexité réseau moyenne.
- Traces détaillées tick-par-tick uniquement pour un sous-échantillon d'individus, à quelques générations clés (début, milieu, fin) — pas à toutes les générations.

---

## 9. Grille expérimentale, valeurs numériques et critères de falsification

Ce qui suit fonctionne comme un pré-enregistrement : les seuils et tests sont fixés **avant** de lancer les expériences complètes, pour ne pas les ajuster après coup selon ce qu'on observera.

### 9.1 Ce qui peut être fixé exactement maintenant

**Durée d'un run** : G_total = 150 générations par défaut (ordre de grandeur standard pour un run NEAT). Hypothèse de travail à valider au pilote — si les courbes (η, fitness) n'ont pas convergé à 150 générations, on rallongera.

**Niveaux de T_env** (nombre de générations entre deux redistributions de nourriture), espacés géométriquement pour bien résoudre un éventuel pic (H1 prédit une relation en cloche, il faut au moins 3-5 points pour la voir) :

| Niveau | T_env | Nombre de redistributions sur 150 générations |
|---|---|---|
| Stable | ∞ (jamais, un seul tirage au début du run) | 0 |
| Faible volatilité | 50 | ~3 |
| Volatilité intermédiaire | 15 | ~10 |
| Forte volatilité | 5 | ~30 |
| Volatilité maximale | 1 (chaque génération) | 150 |

### 9.2 Ce qui doit être calibré (pas de valeur arbitraire) : λ_coût

λ_coût multiplie une quantité (le coût réalisé cumulé, Σ|Δw|) dont l'échelle n'existe pas encore — elle dépend de l'architecture du réseau et de la formule hebbienne, qu'on n'a pas codées. Fixer un chiffre absolu maintenant (ex. "λ_coût = 0.5") serait arbitraire et sans signification tant qu'on ne connaît pas l'échelle des poids et de la fitness. À la place, on fixe des **niveaux relatifs** (fraction de la fitness typique consommée par le coût), et une **procédure de calibration exacte** à exécuter pendant le pilote :

| Niveau | Cible : coût en % de la fitness typique sans coût |
|---|---|
| Contrôle | 0 % |
| Faible | 10 % |
| Moyen | 25 % |
| Élevé | 50 % |

**Procédure de calibration** (à exécuter une fois l'environnement codé, avant le pilote) :
1. Faire tourner quelques génomes avec η élevé (proche de 1) et λ_coût = 0, sur une vie complète.
2. Mesurer la fitness moyenne obtenue (F̄) et le coût réalisé moyen cumulé (C̄ = Σ|Δw| moyen).
3. Pour chaque niveau cible (10 %, 25 %, 50 %), calculer : `λ_coût = (fraction_cible × F̄) / C̄`.

Ça garantit que "coût élevé" veut dire la même chose dans le contexte réel de la simulation, plutôt qu'un chiffre choisi au hasard.

### 9.3 Grille expérimentale : plan en croix plutôt que factoriel complet

Un plan factoriel complet (5 niveaux de T_env × 4 niveaux de λ_coût = 20 conditions) est hors de portée si chaque condition nécessite plusieurs runs indépendants. On adopte un **plan en croix**, séquentiel :

1. **Étape A (teste H1)** : λ_coût = 0 fixé, T_env variant sur les 5 niveaux → 5 conditions. On identifie le niveau de T_env qui maximise η_final (le "pic").
2. **Étape B (teste H2)** : T_env fixé à la valeur du pic identifié en étape A, λ_coût variant sur les 4 niveaux → 4 conditions (la condition λ_coût=0 est déjà connue si le pic coïncide avec un niveau testé en étape A, sinon à relancer).

Soit 8-9 conditions au total plutôt que 20. **Limite assumée** : on ne teste pas l'interaction T_env × λ_coût (est-ce que l'effet du coût dépend du niveau de volatilité) — à envisager plus tard en factoriel partiel si le budget de calcul le permet après le pilote.

### 9.4 Critères de falsification et tests statistiques, par hypothèse

**H1 — Fenêtre de plasticité**
- Données : η_final (moyenne population, dernière génération) pour chaque niveau de T_env, sur N runs indépendants par niveau.
- Test : régression quadratique η_final ~ a + b·f + c·f² où f = 1/T_env (fréquence de changement).
- **Confirmé si** : c significativement négatif (test unilatéral, α = 0.05) ET le niveau intermédiaire montre un η_final significativement supérieur à au moins un des deux extrêmes (Mann-Whitney, correction de Holm sur les comparaisons multiples).
- **Réfuté si** : c non significatif, ou relation monotone (pas de pic), ou pic situé à une extrémité.

**H2 — Coût comme force de rappel**
- Données : η_final aux 4 niveaux de λ_coût (T_env fixé au pic), N runs indépendants par niveau.
- Test : Jonckheere-Terpstra (test de tendance ordonnée, plus approprié qu'une corrélation simple pour une hypothèse de tendance monotone entre groupes ordonnés).
- **Confirmé si** : tendance décroissante significative (p < 0.05, unilatéral).
- **Réfuté si** : pas de tendance significative, ou tendance inverse.

**H3 — Complémentarité inné/acquis** (sur les runs de la condition "pic", λ_coût = 0)
- **3a (socle inné fonctionnel)** : P_naïf comparé à la performance d'un génome aléatoire non évolué (référence non-fonctionnelle). Mann-Whitney, P_naïf significativement supérieur.
- **3b (l'apprentissage apporte un gain réel)** : Wilcoxon apparié sur ΔP, significativement > 0 (unilatéral).
- **3c (preuve comportementale)** : **taux de discrimination alimentaire** (nutritifs / total ingéré) mesuré par tiers de vie. Comparaison de la pente (3e tiers − 1er tiers) entre agents plastiques et agents figés. Wilcoxon apparié sur les mêmes génomes ; seul l'**excédent** de pente des plastiques sur les figés compte comme apprentissage.
- **Pourquoi cette métrique et pas la quantité mangée.** Deux métriques candidates ont été testées empiriquement sur un contrôleur **sans aucune plasticité** :

  | Métrique candidate | Pente 1er → 3e tiers sans apprentissage | Verdict |
  |---|---|---|
  | Quantité de nourriture mangée | **+0,39 item** (positive dans 6 runs sur 8) | Confondue — produit un faux positif |
  | **Taux de discrimination** | **−1,39 point** (écart-type 2,89, centrée sur zéro) | Exempte de confondant — retenue |

  La quantité mangée augmente mécaniquement au fil de la vie par installation spatiale combinée à la survie sélective : les individus qui atteignent la fin de vie sont ceux qui ont trouvé un patch et s'y sont fixés, donc ils mangent plus en fin de vie sans avoir rien appris. Le taux de discrimination ne souffre pas de ce biais : s'installer près d'un patch n'améliore en rien la capacité à distinguer le comestible du toxique. Toute pente positive observée chez un agent plastique est donc bien attribuable à l'apprentissage.
- **Confirmé si** : les trois sous-tests significatifs dans le sens attendu.
- **Réfuté si** : au moins un échoue (ex. P_naïf indiscernable du hasard = pas de socle inné réel ; ΔP indiscernable de zéro = apprentissage sans effet ; pente de discrimination des plastiques indiscernable de celle des figés = pas de preuve comportementale d'apprentissage).

### 9.5 Paramètres statistiques globaux

- Seuil de significativité : α = 0.05 pour tous les tests.
- Correction de comparaisons multiples : Holm-Bonferroni au sein de chaque hypothèse.
- Puissance visée pour le calcul du nombre de runs (§8) : 80 %.
- Taille d'effet par défaut (en l'absence de meilleure estimation) : effet moyen, d de Cohen ≈ 0.5 — à remplacer par la variance réellement observée dès que le pilote aura tourné (voir §8).

---

## 10. Correspondance métriques ↔ hypothèses

| Hypothèse | Métriques mobilisées |
|---|---|
| H1 — Fenêtre de plasticité | η moyen de la population, tracé en fonction de T_env |
| H2 — Coût comme force de rappel | η moyen, tracé en fonction de λ_coût, à T_env fixé |
| H3 — Complémentarité inné/acquis | P_naïf, P_libre, ΔP sur les populations évoluées ; **pente du taux de discrimination par tiers de vie**, comparée entre agents plastiques et agents figés (§9.4) |
