# -*- coding: utf-8 -*-
"""
Tabula Silico — Rendu visuel.

Objectif double : produire des images assez belles pour illustrer le README
(GIF de developpement), et rester assez lisibles pour servir de verification
scientifique (voit-on Pascor chercher la nourriture ? fuir Venator ?).

Choix d'accessibilite : Pascor et Venator ne se distinguent pas seulement par
la couleur (vert / rouge, probleme classique pour le daltonisme rouge-vert)
mais aussi par la FORME — corps arrondi vs corps anguleux.

Compatible Python 3.9.
"""

import math
import pygame
import pygame.gfxdraw

import config

PALETTE = config.PALETTE


# ---------------------------------------------------------------------------
# Utilitaires geometriques
# ---------------------------------------------------------------------------

def _pivoter(points, angle, cx, cy):
    """Fait pivoter une liste de points locaux et les translate."""
    ca = math.cos(angle)
    sa = math.sin(angle)
    return [(cx + px * ca - py * sa, cy + px * sa + py * ca)
            for (px, py) in points]


def _polygone_lisse(surface, points, couleur):
    """Polygone plein antialiase."""
    pts = [(int(round(x)), int(round(y))) for (x, y) in points]
    if len(pts) < 3:
        return
    try:
        pygame.gfxdraw.filled_polygon(surface, pts, couleur)
        pygame.gfxdraw.aapolygon(surface, pts, couleur)
    except (ValueError, OverflowError):
        pass


# ---------------------------------------------------------------------------
# Silhouettes
# ---------------------------------------------------------------------------

# Pascor : corps en goutte / feuille, arrondi, oriente vers +x.
_CORPS_PASCOR = [
    (1.65, 0.00), (1.35, 0.42), (0.75, 0.76), (0.05, 0.88),
    (-0.65, 0.72), (-1.20, 0.38), (-1.40, 0.00),
    (-1.20, -0.38), (-0.65, -0.72), (0.05, -0.88),
    (0.75, -0.76), (1.35, -0.42),
]

# Venator : corps anguleux en dard, ailes en fleche, oriente vers +x.
_CORPS_VENATOR = [
    (1.70, 0.00), (0.60, 0.40), (0.05, 0.82), (-0.60, 0.52),
    (-1.30, 0.28), (-1.55, 0.00), (-1.30, -0.28), (-0.60, -0.52),
    (0.05, -0.82), (0.60, -0.40),
]

# Position des pattes le long de l'axe du corps (x local), et leur ecartement.
_ANCRAGES_PATTES_PASCOR = [(0.75, 0.60), (0.05, 0.76), (-0.70, 0.60)]
_ANCRAGES_PATTES_VENATOR = [(0.60, 0.68), (-0.10, 0.78), (-0.85, 0.58)]

# Longueur des pattes, en multiples du rayon de l'agent. Reglees pour que les
# pattes depassent nettement de la silhouette du corps : en dessous, elles se
# reduisent a des moignons invisibles a l'echelle de rendu.
_LONGUEUR_PATTES_PASCOR = 1.00
_LONGUEUR_PATTES_VENATOR = 0.95


def _dessiner_pattes(surface, cx, cy, cap, echelle, phase, ancrages,
                     couleur, longueur, epaisseur, ecart_phase=2.1,
                     recul=0.26):
    """Dessine des pattes articulees en deux segments, animees par une demarche.

    Le coude part vers l'exterieur, le tarse revient vers l'arriere : c'est ce
    retour arriere qui donne une silhouette de patte plutot que de pique.
    Les pattes d'un meme cote sont dephasees entre elles, et les deux cotes
    sont en opposition de phase — demarche alternee credible.
    """
    for i, (ax, ay) in enumerate(ancrages):
        for cote in (1, -1):
            p = phase + i * ecart_phase + (0.0 if cote > 0 else math.pi)
            balancement = math.sin(p)

            base = (ax * echelle, ay * cote * echelle)
            # Coude : bien ecarte lateralement, legerement en arriere
            coude = (base[0] + (balancement * 0.30 - recul * 0.5) * echelle,
                     base[1] + cote * longueur * 0.75 * echelle)
            # Tarse : redescend vers l'arriere, ce qui "ferme" la patte
            bout = (coude[0] + (balancement * 0.38 - recul) * echelle,
                    coude[1] + cote * longueur * 0.45 * echelle)

            pts = _pivoter([base, coude, bout], cap, cx, cy)
            try:
                pygame.draw.lines(surface, couleur, False,
                                  [(int(round(x)), int(round(y)))
                                   for x, y in pts], epaisseur)
            except (ValueError, TypeError):
                pass


# ---------------------------------------------------------------------------
# Le moteur de rendu
# ---------------------------------------------------------------------------

class Rendu(object):

    def __init__(self, largeur_fenetre=1280, hauteur_fenetre=720,
                 sans_affichage=False):
        self.echelle = min(largeur_fenetre / config.LARGEUR,
                           hauteur_fenetre / config.HAUTEUR)
        self.largeur_fenetre = int(config.LARGEUR * self.echelle)
        self.hauteur_fenetre = int(config.HAUTEUR * self.echelle)

        if sans_affichage:
            self.surface = pygame.Surface(
                (self.largeur_fenetre, self.hauteur_fenetre))
        else:
            self.surface = pygame.display.set_mode(
                (self.largeur_fenetre, self.hauteur_fenetre))
            pygame.display.set_caption("Tabula Silico")

        self.police = pygame.font.Font(None, 22)
        self.police_titre = pygame.font.Font(None, 30)

        self._fond = self._construire_fond()
        # Halo volontairement discret : un halo trop large donnerait une fausse
        # idee de la taille reelle de la nourriture (son rayon de collision),
        # ce qui serait trompeur sur une capture destinee a illustrer le projet.
        rayon_halo = max(6, int(config.RAYON_ITEM * self.echelle * 2.6))
        self._halo_nourriture = self._construire_halo(
            rayon_halo, PALETTE["nourriture"], 46)
        self._halo_nourriture_b = self._construire_halo(
            rayon_halo, PALETTE["nourriture_b"], 46)

        # Calque translucide reutilise chaque frame. Indispensable : pygame
        # IGNORE la composante alpha des couleurs quand on dessine directement
        # sur la surface d'affichage (qui n'a pas de canal alpha). Sans ce
        # calque, les trainees ne s'estompent pas et ressemblent a des fils.
        self._calque = pygame.Surface(
            (self.largeur_fenetre, self.hauteur_fenetre), pygame.SRCALPHA)

        # Effets visuels transitoires
        self.effets = []

    # -- Preparation --------------------------------------------------------

    def _construire_fond(self):
        """Fond sombre avec un leger degrade radial et une grille discrete."""
        fond = pygame.Surface((self.largeur_fenetre, self.hauteur_fenetre))
        c1 = PALETTE["fond_clair"]
        c2 = PALETTE["fond"]
        cx = self.largeur_fenetre * 0.5
        cy = self.hauteur_fenetre * 0.5
        d_max = math.sqrt(cx * cx + cy * cy)

        # Degrade par bandes horizontales (rapide et suffisant visuellement)
        for y in range(0, self.hauteur_fenetre, 4):
            t = abs(y - cy) / d_max
            couleur = tuple(int(c1[i] + (c2[i] - c1[i]) * min(1.0, t * 1.6))
                            for i in range(3))
            pygame.draw.rect(fond, couleur, (0, y, self.largeur_fenetre, 4))

        # Grille discrete : aide a percevoir les deplacements et le rebouclage
        couleur_grille = (
            min(255, PALETTE["fond"][0] + 10),
            min(255, PALETTE["fond"][1] + 12),
            min(255, PALETTE["fond"][2] + 16),
        )
        pas = int(100 * self.echelle)
        if pas > 4:
            for x in range(0, self.largeur_fenetre, pas):
                pygame.draw.line(fond, couleur_grille, (x, 0),
                                 (x, self.hauteur_fenetre), 1)
            for y in range(0, self.hauteur_fenetre, pas):
                pygame.draw.line(fond, couleur_grille, (0, y),
                                 (self.largeur_fenetre, y), 1)
        return fond

    def _construire_halo(self, rayon, couleur, alpha_max):
        """Pre-calcule un halo radial translucide."""
        taille = rayon * 2
        surf = pygame.Surface((taille, taille), pygame.SRCALPHA)
        for r in range(rayon, 0, -1):
            a = int(alpha_max * (1.0 - r / float(rayon)) ** 2)
            pygame.draw.circle(surf, (couleur[0], couleur[1], couleur[2], a),
                               (rayon, rayon), r)
        return surf

    # -- Conversion de coordonnees -----------------------------------------

    def _ecran(self, x, y):
        return x * self.echelle, y * self.echelle

    def _positions_visibles(self, x, y, marge):
        """Positions ecran d'un objet, en dupliquant pres des bords (tore)."""
        ex, ey = self._ecran(x, y)
        positions = [(ex, ey)]
        if config.TOROIDAL:
            L = self.largeur_fenetre
            H = self.hauteur_fenetre
            dx = [0.0]
            dy = [0.0]
            if ex < marge:
                dx.append(L)
            elif ex > L - marge:
                dx.append(-L)
            if ey < marge:
                dy.append(H)
            elif ey > H - marge:
                dy.append(-H)
            positions = [(ex + a, ey + b) for a in dx for b in dy]
        return positions

    # -- Effets -------------------------------------------------------------

    DUREE_EFFET = {"repas": 18, "toxique": 24, "capture": 26}
    MAX_EFFETS = 400

    def ajouter_effet(self, x, y, type_effet, tick):
        """Enregistre un effet transitoire, date par le tick de simulation.

        Le vieillissement est indexe sur le tick de SIMULATION, pas sur le
        nombre d'appels au dessin : sinon, des qu'on ne dessine pas a chaque
        tick (mode capture, rendu accelere), les effets ne vieillissent plus et
        s'accumulent indefiniment a l'ecran.
        """
        self.effets.append({"x": x, "y": y, "tick": tick, "type": type_effet})
        if len(self.effets) > self.MAX_EFFETS:
            del self.effets[:len(self.effets) - self.MAX_EFFETS]

    def _dessiner_effets(self, tick_courant):
        restants = []
        for e in self.effets:
            duree = self.DUREE_EFFET.get(e["type"], 20)
            age = tick_courant - e["tick"]
            if age < 0 or age >= duree:
                continue
            avancement = age / float(duree)
            # La couleur de l'effet montre la CONSEQUENCE de l'ingestion
            # (gain ou intoxication), pas la nature de l'aliment : c'est
            # l'information dont dispose l'agent apres avoir goute.
            if e["type"] == "repas":
                couleur = PALETTE["nourriture"]
            elif e["type"] == "toxique":
                couleur = PALETTE["accent"]
            else:
                couleur = PALETTE["venator"]
            rayon = int((6 + 26 * avancement) * self.echelle)
            alpha = int(210 * (1.0 - avancement))
            for (ex, ey) in self._positions_visibles(e["x"], e["y"], rayon + 4):
                try:
                    pygame.draw.circle(
                        self._calque,
                        (couleur[0], couleur[1], couleur[2], alpha),
                        (int(ex), int(ey)), max(1, rayon), width=2)
                except (ValueError, OverflowError, TypeError):
                    pass
            restants.append(e)
        self.effets = restants

    # -- Elements -----------------------------------------------------------

    def _dessiner_nourriture(self, monde):
        rayon = max(2, int(round(config.RAYON_ITEM * self.echelle)))
        coeur = max(1, rayon - 2)
        demi_halo = self._halo_nourriture.get_width() // 2

        # IMPORTANT : l'apparence n'indique PAS quel type est comestible. Les
        # deux types se distinguent (couleur + forme), mais leur toxicite du
        # moment n'est lisible que dans le HUD, pour l'observateur humain.
        # L'agent, lui, doit l'avoir heritee ou l'apprendre.
        for type_item in range(config.N_TYPES_NOURRITURE):
            positions = monde.positions_actives_du_type(type_item)
            if len(positions) == 0:
                continue
            couleur = (PALETTE["nourriture"] if type_item == 0
                       else PALETTE["nourriture_b"])
            couleur_coeur = ((255, 236, 170) if type_item == 0
                             else (186, 230, 253))
            halo = (self._halo_nourriture if type_item == 0
                    else self._halo_nourriture_b)
            for (x, y) in positions:
                for (ex, ey) in self._positions_visibles(x, y, demi_halo):
                    ix, iy = int(round(ex)), int(round(ey))
                    self.surface.blit(halo, (ix - demi_halo, iy - demi_halo))
                    if type_item == 0:
                        # Type A : pastille ronde
                        try:
                            pygame.gfxdraw.filled_circle(self.surface, ix, iy,
                                                         rayon, couleur)
                            pygame.gfxdraw.aacircle(self.surface, ix, iy,
                                                    rayon, couleur)
                            pygame.gfxdraw.filled_circle(self.surface, ix, iy,
                                                         coeur, couleur_coeur)
                        except (ValueError, OverflowError):
                            pass
                    else:
                        # Type B : losange — distinction par la FORME autant
                        # que par la couleur (lisible en daltonisme)
                        r = rayon + 1
                        losange = [(ix, iy - r), (ix + r, iy),
                                   (ix, iy + r), (ix - r, iy)]
                        _polygone_lisse(self.surface, losange, couleur)
                        rc = max(1, coeur - 1)
                        coeur_pts = [(ix, iy - rc), (ix + rc, iy),
                                     (ix, iy + rc), (ix - rc, iy)]
                        _polygone_lisse(self.surface, coeur_pts, couleur_coeur)

    def _dessiner_trainee(self, pascor):
        if len(pascor.trainee) < 2:
            return
        n = len(pascor.trainee)
        couleur = PALETTE["pascor"]
        for i in range(1, n):
            x1, y1 = pascor.trainee[i - 1]
            x2, y2 = pascor.trainee[i]
            # Ne pas tracer le segment qui traverse l'ecran lors du rebouclage
            if (abs(x2 - x1) > config.LARGEUR * 0.5 or
                    abs(y2 - y1) > config.HAUTEUR * 0.5):
                continue
            avancement = i / float(n)
            alpha = int(60 * avancement ** 2.2)
            if alpha < 3:
                continue
            e1 = self._ecran(x1, y1)
            e2 = self._ecran(x2, y2)
            epaisseur = 1 if avancement < 0.6 else 2
            try:
                pygame.draw.line(
                    self._calque,
                    (couleur[0], couleur[1], couleur[2], alpha),
                    (int(e1[0]), int(e1[1])), (int(e2[0]), int(e2[1])),
                    epaisseur)
            except (ValueError, TypeError):
                pass

    def _dessiner_capteurs(self, pascor):
        """Mode debug : visualise le champ de vision sectoriel."""
        demi = config.CHAMP_VISION * 0.5
        portee = config.PORTEE_VISION * self.echelle
        ex, ey = self._ecran(pascor.x, pascor.y)
        couleur = PALETTE["accent"]
        for i in range(config.N_SECTEURS + 1):
            a = pascor.cap - demi + i * (config.CHAMP_VISION / config.N_SECTEURS)
            x2 = ex + math.cos(a) * portee
            y2 = ey + math.sin(a) * portee
            try:
                pygame.draw.line(self._calque,
                                 (couleur[0], couleur[1], couleur[2], 45),
                                 (int(ex), int(ey)), (int(x2), int(y2)), 1)
            except (ValueError, TypeError):
                pass

    def _dessiner_pascor(self, pascor):
        if not pascor.vivant:
            return
        echelle = config.RAYON_PASCOR * self.echelle
        marge = echelle * 3
        for (ex, ey) in self._positions_visibles(pascor.x, pascor.y, marge):
            _dessiner_pattes(self.surface, ex, ey, pascor.cap, echelle,
                             pascor.phase_demarche, _ANCRAGES_PATTES_PASCOR,
                             PALETTE["pascor_sombre"],
                             longueur=_LONGUEUR_PATTES_PASCOR,
                             epaisseur=max(2, int(round(2.8 * self.echelle))))
            corps = [(px * echelle, py * echelle) for (px, py) in _CORPS_PASCOR]
            _polygone_lisse(self.surface,
                            _pivoter(corps, pascor.cap, ex, ey),
                            PALETTE["pascor"])
            # Petite crete claire sur le dos, pour donner du volume
            dos = [(0.9 * echelle, 0.0), (0.1 * echelle, 0.22 * echelle),
                   (-0.7 * echelle, 0.0), (0.1 * echelle, -0.22 * echelle)]
            _polygone_lisse(self.surface, _pivoter(dos, pascor.cap, ex, ey),
                            (140, 240, 200))

    def _dessiner_venator(self, venator):
        echelle = config.RAYON_VENATOR * self.echelle
        marge = echelle * 3
        traque = venator.etat == "poursuite"
        for (ex, ey) in self._positions_visibles(venator.x, venator.y, marge):
            # Halo d'alerte quand il chasse
            if traque:
                rayon = int(echelle * 2.2)
                try:
                    pygame.gfxdraw.filled_circle(
                        self.surface, int(ex), int(ey), rayon,
                        (PALETTE["venator"][0], PALETTE["venator"][1],
                         PALETTE["venator"][2], 28))
                except (ValueError, OverflowError):
                    pass

            _dessiner_pattes(self.surface, ex, ey, venator.cap, echelle,
                             venator.phase_demarche, _ANCRAGES_PATTES_VENATOR,
                             PALETTE["venator_sombre"],
                             longueur=_LONGUEUR_PATTES_VENATOR,
                             epaisseur=max(2, int(round(3.2 * self.echelle))),
                             recul=0.30)
            # Mandibules dessinees AVANT le corps : elles emergent du nez sans
            # empieter sur la silhouette.
            for cote in (1, -1):
                mand = [(1.20 * echelle, 0.18 * cote * echelle),
                        (2.30 * echelle, 0.30 * cote * echelle),
                        (2.05 * echelle, 0.05 * cote * echelle)]
                _polygone_lisse(self.surface,
                                _pivoter(mand, venator.cap, ex, ey),
                                PALETTE["venator_sombre"])
            corps = [(px * echelle, py * echelle) for (px, py) in _CORPS_VENATOR]
            _polygone_lisse(self.surface,
                            _pivoter(corps, venator.cap, ex, ey),
                            PALETTE["venator"])
            # Arete dorsale sombre : donne du relief et marque l'axe du corps
            arete = [(1.10 * echelle, 0.0), (0.0, 0.20 * echelle),
                     (-1.10 * echelle, 0.0), (0.0, -0.20 * echelle)]
            _polygone_lisse(self.surface,
                            _pivoter(arete, venator.cap, ex, ey),
                            (190, 48, 48))

    def _dessiner_hud(self, infos):
        largeur = 296
        panneau = pygame.Surface((largeur, 24 * len(infos) + 30), pygame.SRCALPHA)
        panneau.fill((10, 16, 30, 190))
        pygame.draw.rect(panneau, (*PALETTE["accent"], 60),
                         panneau.get_rect(), width=1)
        self.surface.blit(panneau, (14, 14))

        titre = self.police_titre.render("TABULA SILICO", True, PALETTE["accent"])
        self.surface.blit(titre, (28, 24))
        y = 58
        for cle, valeur in infos:
            t1 = self.police.render(str(cle), True, PALETTE["texte_faible"])
            t2 = self.police.render(str(valeur), True, PALETTE["texte"])
            self.surface.blit(t1, (28, y))
            # Valeurs alignees a droite du panneau : evite tout chevauchement
            # quel que soit la longueur du libelle.
            self.surface.blit(t2, (14 + largeur - 14 - t2.get_width(), y))
            y += 24

    # -- Rendu complet ------------------------------------------------------

    def dessiner(self, monde, pascors, venators, infos=None, tick=0):
        self.surface.blit(self._fond, (0, 0))

        # -- Passe 1 (sous les agents) : trainees et capteurs, sur le calque
        self._calque.fill((0, 0, 0, 0))
        if config.AFFICHER_TRAINEES:
            for p in pascors:
                if p.vivant:
                    self._dessiner_trainee(p)
        if config.AFFICHER_CAPTEURS:
            for p in pascors:
                if p.vivant:
                    self._dessiner_capteurs(p)
        self.surface.blit(self._calque, (0, 0))

        # -- Corps
        self._dessiner_nourriture(monde)
        for p in pascors:
            self._dessiner_pascor(p)
        for v in venators:
            self._dessiner_venator(v)

        # -- Passe 2 (au dessus des agents) : effets transitoires
        self._calque.fill((0, 0, 0, 0))
        self._dessiner_effets(tick)
        self.surface.blit(self._calque, (0, 0))

        if config.AFFICHER_HUD and infos:
            self._dessiner_hud(infos)

    def sauvegarder(self, chemin):
        pygame.image.save(self.surface, chemin)
