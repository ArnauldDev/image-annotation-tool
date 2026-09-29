<!--
  File Name: guide-utilisateur.md
  Description: Guide d'utilisation de l'application Image Annotation Tool (outils, liste des objets, raccourcis).
  Developer: ArnauldDev
  Created Date: 2026-09-23
  Last Modified: 2026-09-23
-->

<!--
  Captures d'écran attendues dans docs/images/ (générées ultérieurement) :
    - fenetre-principale.png  : vue d'ensemble de la fenêtre avec une image annotée
    - outil-annotation.png    : panneau « Annotation » et une étiquette en cours de tracé
    - outil-loupe.png         : deux loupes sur l'image et le panneau « Loupe »
    - outil-export.png        : panneau « Export » avec les préréglages de largeur
    - a-propos.png            : fenêtre « Aide > À propos »
-->

# Guide utilisateur

[← Retour au README](../README.md)

Ce guide explique comment annoter une photographie avec **Image Annotation Tool (IAT)** : ouvrir une image, la redresser, ajouter des annotations et des loupes, puis exporter le résultat.

## Sommaire

- [1. Découvrir la fenêtre](#1-découvrir-la-fenêtre)
- [2. Ouvrir une image](#2-ouvrir-une-image)
- [3. Outil « Transformation »](#3-outil--transformation-)
- [4. Outil « Annotation »](#4-outil--annotation-)
- [5. Outil « Loupe »](#5-outil--loupe-)
- [6. Déplacer, sélectionner et organiser les objets](#6-déplacer-sélectionner-et-organiser-les-objets)
- [7. Exporter l'image](#7-exporter-limage)
- [8. Grille et accrochage (Ctrl)](#8-grille-et-accrochage-ctrl)
- [9. Raccourcis clavier et souris](#9-raccourcis-clavier-et-souris)
- [10. Menus](#10-menus)
- [11. Questions fréquentes](#11-questions-fréquentes)

---

## 1. Découvrir la fenêtre

![Fenêtre principale d'Image Annotation Tool](images/fenetre-principale.png)

La fenêtre s'ouvre en plein écran, sans image chargée. Elle se compose de :

| Zone                                 | Rôle                                                                                                      |
| :----------------------------------- | :-------------------------------------------------------------------------------------------------------- |
| **Barre de menus**                   | `Fichier`, `Édition`, `Configuration`, `Aide`                                                             |
| **Barre horizontale des outils**     | Boutons texte : `Ouvrir une image` · `Transformation` · `Annotation` · `Outil loupe` · `Exporter l'image` |
| **Palette graphique des outils**     | Mêmes outils sous forme d'icônes, à gauche ; déplaçable ou flottante                                      |
| **Liste des annotations** (à gauche) | Tous les objets et traitements appliqués à l'image                                                        |
| **Zone centrale**                    | Aperçu de l'image sur lequel on dessine                                                                   |
| **Panneau « Options »** (à droite)   | Réglages de l'outil actif ou de l'objet sélectionné                                                       |
| **Barre d'état** (en bas)            | Messages (image chargée, recette synchronisée, export réalisé…) et logo du CBI                            |

Les deux barres d'outils peuvent être masquées depuis le menu `Configuration` (`Ctrl+T` pour la barre horizontale). La disposition de la fenêtre est mémorisée d'une session à l'autre.

Survolez un outil pour afficher une info-bulle explicative ; le menu `Aide > Aide sur les outils` récapitule le rôle de chaque outil.

## 2. Ouvrir une image

Trois possibilités :

- menu `Fichier > Ouvrir une image` ou `Ctrl+O` ;
- bouton `Ouvrir une image` de la barre d'outils ;
- **glisser-déposer** un fichier image depuis l'explorateur de fichiers sur la fenêtre.

Formats acceptés : PNG, JPEG, BMP, TIFF. Les dernières images ouvertes sont accessibles dans `Fichier > Fichiers récents` (10 au maximum ; `Effacer l'historique` vide la liste).

**La recette JSON est gérée automatiquement** : si un fichier `nom-de-l-image-iat.json` existe à côté de l'image, il est rechargé et appliqué ; sinon il est créé dès le premier traitement, puis mis à jour à chaque modification. Il n'y a pas de bouton « Enregistrer » : votre travail est sauvegardé en continu. Le format de ce fichier est décrit dans [Format de la recette JSON](format-recette-json.md).

> [!TIP]
> Nommez vos photographies brutes `nom-raw.jpg` : la recette s'appellera `nom-iat.json` et l'export `nom-iat-x1200.jpg`.

## 3. Outil « Transformation »

Le bouton `Transformation` affiche les réglages géométriques de l'image :

| Réglage                             | Description                                                                                                                                     |
| :---------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Afficher la grille d'alignement** | Superpose une grille (axes centraux renforcés) pour vérifier l'horizontalité                                                                    |
| **Rotation**                        | `⟲ 90°` / `⟳ 90°`, angle fin de −45° à +45°, `Réinitialiser la rotation`                                                                        |
| **Correction trapézoïdale**         | Corrige la perspective sur chacun des quatre bords (supérieur, inférieur, gauche, droit)                                                        |
| **Rognage**                         | Glissez sur l'image pour dessiner la zone à conserver, ajustez-la avec ses poignées, puis `Appliquer le rognage` (`Réinitialiser` pour annuler) |

La luminosité (−100 à +100) et le contraste (0,01× à 3×) se règlent dans le panneau `Luminosité / Contraste`, accessible depuis l'entrée correspondante de la liste des objets.

> [!NOTE]
> Modifier la rotation après un rognage réinitialise le rognage, car la zone conservée dépend de l'orientation de l'image.

## 4. Outil « Annotation »

![Panneau Annotation et étiquette en cours de tracé](images/outil-annotation.png)

Le bouton `Annotation` regroupe quatre formes, choisies en haut du panneau :

| Forme         | Utilisation                                                                                       | Modificateur                             |
| :------------ | :------------------------------------------------------------------------------------------------ | :--------------------------------------- |
| **Étiquette** | Glissez de l'emplacement du texte vers l'élément désigné : un cadre avec texte et flèche est créé | —                                        |
| **Rectangle** | Glissez pour encadrer une zone d'intérêt                                                          | `Shift` : carré parfait                  |
| **Cercle**    | Glissez pour entourer une zone (ovale)                                                            | `Shift` : cercle parfait                 |
| **Ligne**     | Glissez pour tracer une ligne ; flèches optionnelles au début et/ou à la fin                      | `Shift` : angle contraint par pas de 45° |

Options disponibles selon la forme :

- **Épaisseur** du trait (1 à 20 px) et **Rayon** des coins arrondis ;
- pour l'étiquette : **Forme** (rectangle ou rond), **Fond** opaque ou transparent, **Afficher le texte**, **Gras**, **Afficher la flèche** et épaisseur de la flèche ;
- pour la ligne : **Flèche au début**, **Flèche à la fin** ;
- **Palette de couleur** : neuf couleurs prédéfinies et `Couleur personnalisée…`. Les couleurs personnalisées sont mémorisées et enregistrées dans la recette.

La couleur et les options s'appliquent au prochain objet créé **et** à l'objet sélectionné.

Pour **modifier le texte** d'une étiquette, double-cliquez dessus.

## 5. Outil « Loupe »

![Deux loupes sur une carte électronique](images/outil-loupe.png)

Une loupe est un médaillon circulaire qui montre une zone agrandie de l'image, reliée à cette zone par une flèche.

1. Cliquez sur `Outil loupe`.
2. Glissez **de l'emplacement du médaillon vers la zone à agrandir**.
3. Ajustez les réglages dans le panneau `Loupe (calque de zoom)`.

| Réglage                       | Description                                                               |
| :---------------------------- | :------------------------------------------------------------------------ |
| `Nouvelle loupe`              | Ajoute une loupe supplémentaire (plusieurs loupes par image)              |
| `Activer la loupe`            | Affiche ou masque la loupe active                                         |
| `Loupe active`                | Loupe dont les réglages sont affichés                                     |
| `Zoom`                        | Facteur d'agrandissement de 1× à 8× (aussi à la **molette** de la souris) |
| `Rayon`                       | Taille du médaillon (20 à 400 px, par pas de 10)                          |
| `Épaisseur du contour`        | Épaisseur du cercle (1 à 20 px)                                           |
| `Épaisseur de la flèche`      | Épaisseur de la flèche, indépendante du contour                           |
| `⟲ 90°` / `⟳ 90°`, `Rotation` | Fait pivoter **le contenu agrandi** seulement (−180° à +180°)             |
| `Palette de couleur`          | Couleur du contour et de la flèche                                        |

Avec l'outil loupe actif, la molette agit sur la loupe située sous le curseur (sinon sur la loupe sélectionnée).

> [!NOTE]
> La possibilité d'ajouter plusieurs loupes dépend du drapeau `FEATURE_MULTI_LOUPE` (activé par défaut), voir [Configuration](configuration.md).

## 6. Déplacer, sélectionner et organiser les objets

### Déplacer un objet sur l'image

Cliquez-glissez le contour d'un objet déjà placé pour le déplacer : corps d'une étiquette, médaillon d'une loupe, pointe d'une flèche, coin d'un rectangle, zone de rognage… Ce déplacement fonctionne quel que soit l'outil actif. `Échap` désactive l'outil courant.

### Liste des annotations

Le panneau de gauche liste tous les objets (étiquettes, zones, lignes, loupes) et les traitements (rognage, rotation, trapèze, luminosité/contraste).

- **Cliquer** un élément le met en surbrillance sur l'image et affiche ses options à droite.
- **Sélection multiple** : `Shift+clic` sélectionne une plage, `Ctrl+clic` ajoute ou retire un élément.
- **Glisser-déposer** dans la liste modifie l'ordre des calques (le haut de la liste est au premier plan).
- **Supprimer** : bouton `Supprimer l'élément`, touche `Suppr` ou `Édition > Supprimer` (supprime tous les éléments sélectionnés).

### Menu « Édition » : annuler, copier, coller

| Commande    | Raccourci                  | Effet                                                                                           |
| :---------- | :------------------------- | :---------------------------------------------------------------------------------------------- |
| `Annuler`   | `Ctrl+Z`                   | Annule la dernière modification (jusqu'à 100 étapes)                                            |
| `Rétablir`  | `Ctrl+Y` ou `Ctrl+Shift+Z` | Rétablit la dernière modification annulée                                                       |
| `Copier`    | `Ctrl+C`                   | Copie les objets sélectionnés                                                                   |
| `Coller`    | `Ctrl+V`                   | Colle une copie **décalée** des objets copiés (chaque collage successif est décalé un peu plus) |
| `Supprimer` | `Suppr`                    | Supprime les éléments sélectionnés                                                              |

### Menu contextuel (clic droit sur l'image) : aligner et distribuer

Un **clic droit** sur l'image ouvre un menu contextuel ; l'objet situé sous le curseur est d'abord sélectionné s'il ne l'était pas.

- **Aligner** : à gauche, centrer horizontalement, à droite, en haut, centrer verticalement, en bas. Avec **un seul** objet sélectionné, l'alignement se fait **par rapport à l'image** (par exemple, centrer une étiquette) ; avec plusieurs, les objets s'alignent **entre eux**.
- **Distribuer** horizontalement ou verticalement : répartit régulièrement les objets (au moins **trois** objets sélectionnés).
- **Accrocher à la grille** : place les objets sélectionnés sur la grille.
- `Copier`, `Coller`, `Supprimer`.

## 7. Exporter l'image

![Panneau Export](images/outil-export.png)

1. Cliquez sur `Exporter l'image` (barre d'outils ou menu `Fichier`).
2. Choisissez la largeur : préréglages **800**, **1200** ou **1920 px**, ou saisie libre de la largeur ou de la hauteur (les proportions sont toujours conservées).
3. Cliquez sur `Exporter l'image annotée` et choisissez le fichier de destination (JPEG). Le nom proposé suit la convention `nom-iat-x<largeur>.jpg`.

L'export **rejoue la recette sur l'image originale en pleine résolution** (rééchantillonnage Lanczos, qualité JPEG 95) : la qualité n'est pas limitée par l'aperçu affiché à l'écran.

Une fenêtre de confirmation s'affiche après l'export ; elle peut être désactivée via `Configuration > Notification après l'export`. Le message dans la barre d'état est toujours affiché.

Le menu `Fichier` permet aussi d'**exporter** la recette vers un autre fichier JSON ou d'**importer** une recette existante.

## 8. Grille et accrochage (Ctrl)

L'accrochage à la grille est actif **uniquement tant que la touche `Ctrl` est maintenue** pendant le tracé ou le déplacement d'un objet. Sans `Ctrl`, l'objet suit librement la souris. La grille fine est centrée sur le centre de l'image ; elle peut être affichée depuis l'outil `Transformation`.

## 9. Raccourcis clavier et souris

| Raccourci                               | Action                                                   |
| :-------------------------------------- | :------------------------------------------------------- |
| `Ctrl+O`                                | Ouvrir une image                                         |
| `Ctrl+T`                                | Afficher / masquer la barre horizontale des outils       |
| `Ctrl+Z` / `Ctrl+Y` (ou `Ctrl+Shift+Z`) | Annuler / rétablir                                       |
| `Ctrl+C` / `Ctrl+V`                     | Copier / coller les objets sélectionnés                  |
| `Suppr` (ou `Retour arrière`)           | Supprimer les objets sélectionnés                        |
| `Échap`                                 | Désactiver l'outil courant                               |
| `Ctrl` maintenu                         | Accrocher à la grille pendant un tracé ou un déplacement |
| `Shift` maintenu                        | Carré / cercle parfait, ligne contrainte à 45°           |
| `Shift+clic` / `Ctrl+clic`              | Sélection multiple dans la liste des annotations         |
| Double-clic sur une étiquette           | Modifier son texte                                       |
| Molette (outil loupe)                   | Régler le zoom de la loupe                               |
| Clic droit sur l'image                  | Menu d'alignement, de distribution, copier/coller        |
| Glisser-déposer d'un fichier            | Ouvrir l'image                                           |

## 10. Menus

| Menu            | Entrées                                                                                                                                                                                           |
| :-------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Fichier`       | Ouvrir une image · Exporter l'image · Exporter les annotations au format JSON · Importer les annotations depuis un fichier JSON · Fichiers récents                                                |
| `Édition`       | Annuler · Rétablir · Copier · Coller · Supprimer                                                                                                                                                  |
| `Configuration` | Configuration `.env` · Thèmes · Langue · Chemins des ressources… · Notification après l'export · Barres d'outils · Réinitialiser les paramètres… (détails dans [Configuration](configuration.md)) |
| `Aide`          | Aide sur les outils · À propos                                                                                                                                                                    |

![Fenêtre À propos](images/a-propos.png)

La fenêtre `Aide > À propos` indique la version, la licence et un lien vers le code source.

## 11. Questions fréquentes

**Mon image d'origine a-t-elle été modifiée ?**
Non. Seuls la recette `-iat.json` et l'image exportée sont écrits.

**Comment reprendre un travail ?**
Rouvrez l'image source : la recette située dans le même dossier est rechargée automatiquement.

**Comment partager mon travail avec un collègue ?**
Transmettez l'image brute et sa recette `-iat.json` (et non seulement l'export) : il pourra continuer à modifier les annotations.

**L'apparence ne me convient pas.**
Choisissez un autre thème dans `Configuration > Thèmes disponibles` (CBI, Clair, Sombre) ; voir [Configuration](configuration.md).
