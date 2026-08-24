# -*- coding: utf-8 -*-
"""
Tabula Silico — Analyse statistique et figures.

Lit les journaux CSV produits par evolution.py, calcule les statistiques des
trois hypotheses et produit les figures du README.

Usage :
    python analyse.py --runs runs --sortie figures

Principe de reduction des donnees : un run = UN point de donnee independant.
Les individus d'un meme run partagent une histoire evolutive (ancetres, aleas
de mutation) et ne sont pas independants entre eux — les agreger comme s'ils
l'etaient serait de la pseudo-replication (Hurlbert 1984). Chaque metrique est
donc d'abord moyennee sur les generations 20+ d'un run, puis les runs servent
d'unites statistiques.

Les 20 premieres generations sont ecartees : avant cela, les reseaux ne savent
pas encore fourrager (mesure : ~4 repas par vie a la generation 0, contre ~25
apres la generation 20), et l'apprentissage n'a pas d'occasion de s'exercer.

Compatible Python 3.9.
"""

import argparse
import csv
import os

import numpy as np

import config

GEN_MIN = 20          # generations ecartees (mise en place du fourrage)
PALETTE = config.PALETTE


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


# ---------------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------------

def charger(chemin):
    with open(chemin, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def moyenne(lignes, colonne, depuis=GEN_MIN, dernieres=None):
    v = []
    for r in lignes[depuis:]:
        try:
            x = float(r[colonne])
        except (KeyError, ValueError):
            continue
        if x == x:            # ecarte les NaN
            v.append(x)
    if dernieres:
        v = v[-dernieres:]
    return float(np.mean(v)) if v else float("nan")


def resumer_run(chemin):
    """Reduit un run a ses quelques nombres utiles."""
    L = charger(chemin)
    ecart = []
    for r in L[GEN_MIN:]:
        try:
            a = float(r["discrimination_libre"])
            b = float(r["discrimination_naif"])
        except (KeyError, ValueError):
            continue
        if a == a and b == b:
            ecart.append(a - b)
    return {
        "n_generations": len(L),
        "eta_final": moyenne(L, "eta_moyen", depuis=len(L) - 5),
        "delta_p": moyenne(L, "delta_p_moyen"),
        "ecart_discrimination": float(np.mean(ecart)) if ecart else float("nan"),
        "discrimination_naif": moyenne(L, "discrimination_naif"),
        "discrimination_libre": moyenne(L, "discrimination_libre"),
        "repas": moyenne(L, "repas_moyen_libre"),
        "survie": moyenne(L, "survie_naif"),
    }


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------

def spearman(x, y):
    """Correlation de rang de Spearman, avec p si scipy est disponible."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    try:
        from scipy import stats
        r, p = stats.spearmanr(x, y)
        return float(r), float(p)
    except ImportError:
        rx = np.argsort(np.argsort(x))
        ry = np.argsort(np.argsort(y))
        return float(np.corrcoef(rx, ry)[0, 1]), float("nan")


def test_signe(valeurs, alternative="greater"):
    """Wilcoxon des rangs signes contre zero, ou test des signes en secours."""
    v = np.asarray([x for x in valeurs if x == x], dtype=float)
    if len(v) == 0:
        return float("nan"), float("nan")
    try:
        from scipy import stats
        if len(v) < 5:
            # Trop peu d'observations pour Wilcoxon : test des signes exact
            k = int((v > 0).sum())
            p = stats.binomtest(k, len(v), 0.5,
                                alternative=alternative).pvalue
            return float(v.mean()), float(p)
        s, p = stats.wilcoxon(v, alternative=alternative)
        return float(v.mean()), float(p)
    except ImportError:
        return float(v.mean()), float("nan")


def d_cohen(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    s = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1))
                / float(na + nb - 2))
    return float((a.mean() - b.mean()) / s) if s > 0 else float("nan")


# ---------------------------------------------------------------------------
# Definition des axes experimentaux
# ---------------------------------------------------------------------------

AXE_INTRA_VIE = [
    ("nulle", 0, "vvie_nulle_s%d.csv"),
    ("lente", 1, "vvie_lente_s%d.csv"),
    ("moderee", 3, "vvie_moderee_s%d.csv"),
    ("rapide", 9, "vvie_rapide_s%d.csv"),
    ("chaotique", 29, "vvie_chaotique_s%d.csv"),
]

# Axe INTER-GENERATIONNEL : branche montante de H1.
# La condition maximale dispose de deux series de runs independants
# (h3_maximale_* et vvie_nulle_*), toutes deux a T_env=maximale, v_vie=nulle.
# Ce ne sont PAS des doublons : avant la correction de reproductibilite, la
# graine ne semait pas le module `random` utilise par les mutations, si bien
# que deux runs de meme graine divergeaient. Ils comptent donc comme des
# replicats independants.
AXE_INTER_GEN = [
    ("stable", 0.0, "h3_stable_s%d.csv"),
    ("faible", 0.02, "faible_s%d.csv"),
    ("forte", 0.20, "forte_s%d.csv"),
    ("maximale", 1.00, "h3_maximale_s%d.csv"),
]

AXE_COUT = [
    ("0", 0.0, "vvie_nulle_s%d.csv"),
    ("3.8", 3.8, "h2_c10_s%d.csv"),
    ("9.4", 9.4, "h2_c25_s%d.csv"),
    ("18.9", 18.9, "h2_c50_s%d.csv"),
]

GRAINES = (21, 22, 23)


def collecter(dossier, axe):
    """Renvoie {niveau: [resume par graine]} et la liste des niveaux."""
    donnees = {}
    for nom, valeur, motif in axe:
        runs = []
        for g in GRAINES:
            chemin = os.path.join(dossier, motif % g)
            if os.path.exists(chemin):
                runs.append(resumer_run(chemin))
        if runs:
            donnees[nom] = {"valeur": valeur, "runs": runs}
    return donnees


# ---------------------------------------------------------------------------
# Rapport
# ---------------------------------------------------------------------------

def rapport_axe(titre, donnees, prediction):
    print("=" * 76)
    print("  " + titre)
    print("  Prediction : " + prediction)
    print("=" * 76)
    print("%-12s %6s %22s %24s"
          % ("niveau", "n", "eta final", "ecart discrimination"))

    niveaux, etas_moy, x = [], [], []
    tous_x, tous_eta, tous_ecart = [], [], []
    for nom, d in donnees.items():
        etas = np.array([r["eta_final"] for r in d["runs"]])
        ecarts = np.array([r["ecart_discrimination"] for r in d["runs"]])
        niveaux.append(nom)
        etas_moy.append(etas.mean())
        x.append(d["valeur"])
        for e, c in zip(etas, ecarts):
            tous_x.append(d["valeur"])
            tous_eta.append(e)
            tous_ecart.append(c)
        print("%-12s %6d %8.3f [%s] %+10.4f [%s]"
              % (nom, len(etas), etas.mean(),
                 " ".join("%.2f" % v for v in etas),
                 ecarts.mean(), " ".join("%+.3f" % v for v in ecarts)))

    print()
    r_eta, p_eta = spearman(tous_x, tous_eta)
    r_ec, p_ec = spearman(tous_x, tous_ecart)
    print("  Spearman (n=%d runs), eta   ~ niveau : rho = %+.3f, p = %.4f"
          % (len(tous_x), r_eta, p_eta))
    print("  Spearman (n=%d runs), ecart ~ niveau : rho = %+.3f, p = %.4f"
          % (len(tous_x), r_ec, p_ec))

    # Contraste entre les deux extremes
    cles = list(donnees.keys())
    if len(cles) >= 2:
        a = [r["eta_final"] for r in donnees[cles[0]]["runs"]]
        b = [r["eta_final"] for r in donnees[cles[-1]]["runs"]]
        print("  Contraste %s vs %s : eta %.3f -> %.3f, d de Cohen = %.2f"
              % (cles[0], cles[-1], np.mean(a), np.mean(b), d_cohen(a, b)))
    print()
    return niveaux, x, donnees


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def figure_axe(donnees, titre, xlabel, chemin, log_x=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    fig.patch.set_facecolor("white")

    noms = list(donnees.keys())
    xs = [donnees[n]["valeur"] for n in noms]
    if log_x:
        xs = [v + 1 for v in xs]

    for ax, cle, libelle, couleur in [
            (axes[0], "eta_final", "Taux de plasticite herite  $\\eta$",
             _hex(PALETTE["pascor"])),
            (axes[1], "ecart_discrimination",
             "Discrimination : plastique $-$ fige", _hex(PALETTE["accent"]))]:
        moyennes, erreurs = [], []
        for n in noms:
            v = np.array([r[cle] for r in donnees[n]["runs"]])
            moyennes.append(v.mean())
            erreurs.append(v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0)
            ax.scatter([xs[noms.index(n)]] * len(v), v, s=22, alpha=0.45,
                       color=couleur, zorder=3, edgecolors="none")
        ax.errorbar(xs, moyennes, yerr=erreurs, color=couleur, lw=2.2,
                    marker="o", ms=7, capsize=4, zorder=4)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(libelle)
        if log_x:
            ax.set_xscale("log")
            ax.set_xticks(xs)
            ax.set_xticklabels([str(donnees[n]["valeur"]) for n in noms])
        ax.grid(alpha=0.25, linestyle=":")
        ax.axhline(0, color="#94a3b8", lw=0.8, zorder=1)

    fig.suptitle(titre, fontsize=13, y=1.0)
    fig.tight_layout()
    fig.savefig(chemin, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return chemin


def figure_lesions(lesions, chemin):
    """lesions : {condition: (aleatoire, inne, inne+acquis, acquis_seul)}"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    conditions = list(lesions.keys())
    libelles = ["aleatoire", "inne seul", "inne + acquis", "acquis seul"]
    couleurs = ["#94a3b8", _hex(PALETTE["nourriture"]),
                _hex(PALETTE["pascor"]), _hex(PALETTE["accent"])]

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    fig.patch.set_facecolor("white")
    largeur = 0.2
    base = np.arange(len(conditions))
    for i, (lib, coul) in enumerate(zip(libelles, couleurs)):
        vals = [np.mean([g[i] for g in lesions[c]]) for c in conditions]
        errs = [np.std([g[i] for g in lesions[c]], ddof=1) / np.sqrt(3)
                for c in conditions]
        ax.bar(base + (i - 1.5) * largeur, vals, largeur, yerr=errs,
               capsize=3, label=lib, color=coul, edgecolor="white", lw=0.6)
    ax.set_xticks(base)
    ax.set_xticklabels(conditions)
    ax.set_ylabel("Fitness (energie recoltee)")
    ax.set_title("Lesions in silico : ce que chaque composante apporte",
                 fontsize=12)
    ax.legend(frameon=False, ncol=4, fontsize=9)
    ax.grid(axis="y", alpha=0.25, linestyle=":")
    fig.tight_layout()
    fig.savefig(chemin, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return chemin


# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Analyse de Tabula Silico")
    p.add_argument("--runs", default="runs", help="dossier des journaux CSV")
    p.add_argument("--sortie", default="figures", help="dossier des figures")
    a = p.parse_args()

    if not os.path.isdir(a.sortie):
        os.makedirs(a.sortie)

    inter = collecter(a.runs, AXE_INTER_GEN)
    intra = collecter(a.runs, AXE_INTRA_VIE)
    cout = collecter(a.runs, AXE_COUT)

    if inter:
        rapport_axe(
            "H1 (branche montante) — volatilite INTER-GENERATIONNELLE",
            inter,
            "eta CROIT quand l'inne ne peut plus encoder la bonne reponse")
        figure_axe(inter,
                   "H1 — quand l'environnement change entre generations",
                   "Frequence de changement (1 / T_env)",
                   os.path.join(a.sortie, "fig_h1_inter_gen.png"))

    if intra:
        rapport_axe(
            "H1 (branche descendante) — volatilite INTRA-VIE",
            intra,
            "eta DECROIT quand l'environnement change pendant la vie")
        figure_axe(intra,
                   "H1 — quand l'environnement change pendant la vie",
                   "Basculements par vie", 
                   os.path.join(a.sortie, "fig_h1_intra_vie.png"),
                   log_x=True)

    if cout:
        rapport_axe(
            "H2 — cout de l'apprentissage",
            cout,
            "eta DECROIT quand apprendre coute plus cher")
        figure_axe(cout,
                   "H2 — le cout de l'apprentissage comme force de rappel",
                   "$\\lambda$ (penalite du cout d'apprentissage)",
                   os.path.join(a.sortie, "fig_h2_cout.png"))

    print("Figures ecrites dans %s/" % a.sortie)


if __name__ == "__main__":
    main()
