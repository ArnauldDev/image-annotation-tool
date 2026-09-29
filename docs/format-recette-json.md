<!--
  File Name: format-recette-json.md
  Description: Description du format de la recette JSON (*-iat.json) produite par Image Annotation Tool.
  Developer: ArnauldDev
  Created Date: 2026-09-23
  Last Modified: 2026-09-23
-->

# Format de la recette JSON (`*-iat.json`)

[← Retour au README](../README.md)

La **recette** est un fichier JSON qui décrit *toutes* les opérations appliquées à une image : rotation, correction trapézoïdale, rognage, luminosité/contraste, annotations, loupes, taille d'export. L'image originale n'est **jamais modifiée** : l'export final rejoue la recette sur l'image source en pleine résolution.

Le format est défini dans [`src/iat/image_processor.py`](../src/iat/image_processor.py) par les classes `ProcessingRecipe`, `Annotation` et `LoupeSpec`.

## Sommaire

- [1. Convention de nommage](#1-convention-de-nommage)
- [2. Principe : aperçu et pleine résolution](#2-principe--aperçu-et-pleine-résolution)
- [3. Champs de premier niveau](#3-champs-de-premier-niveau)
- [4. Annotations](#4-annotations)
- [5. Loupes](#5-loupes)
- [6. Ordre des calques (`layer_order`)](#6-ordre-des-calques-layer_order)
- [7. Ordre d'application des traitements](#7-ordre-dapplication-des-traitements)
- [8. Rétrocompatibilité](#8-rétrocompatibilité)
- [9. Exemple complet](#9-exemple-complet)
- [10. Utiliser une recette depuis un script Python](#10-utiliser-une-recette-depuis-un-script-python)

---

## 1. Convention de nommage

| Type de fichier     | Modèle de nom                 | Exemple                    | Description                             |
| :------------------ | :---------------------------- | :------------------------- | :-------------------------------------- |
| **Image originale** | `nom-de-l-image-raw.jpg`      | `carte-mere-raw.jpg`       | Photographie brute, jamais modifiée     |
| **Recette JSON**    | `nom-de-l-image-iat.json`     | `carte-mere-iat.json`      | Paramètres et annotations à appliquer   |
| **Export final**    | `nom-de-l-image-iat-x<L>.jpg` | `carte-mere-iat-x1200.jpg` | Image annotée, `<L>` = largeur d'export |

Règles appliquées par `compute_associated_paths()` :

- le suffixe `-raw` (ou `_raw`) est retiré puis remplacé par `-iat` ;
- une image sans suffixe `-raw` reçoit simplement `-iat` (`photo.png` → `photo-iat.json`) ;
- le nom d'export proposé ajoute la largeur choisie (`-x1200`) avant l'extension `.jpg`.

La recette est enregistrée **dans le même dossier que l'image source**. Elle est rechargée automatiquement à l'ouverture de l'image, créée au premier traitement et synchronisée à chaque modification.

## 2. Principe : aperçu et pleine résolution

L'éditeur travaille sur un **aperçu réduit** (plus grand côté limité à 1600 px) pour rester fluide. Toutes les coordonnées enregistrées dans la recette sont en revanche exprimées en **pixels de l'image originale**. La même recette peut donc être rejouée plus tard, sans interface, pour produire un résultat identique au pixel près.

## 3. Champs de premier niveau

| Champ           | Type                         | Défaut                        | Description                                                                              |
| :-------------- | :--------------------------- | :---------------------------- | :--------------------------------------------------------------------------------------- |
| `source_image`  | chaîne                       | `""`                          | Chemin de l'image source (absolu ou relatif au dossier de travail)                       |
| `angle`         | nombre                       | `0.0`                         | Rotation totale en degrés                                                                |
| `brightness`    | nombre                       | `0.0`                         | Luminosité, de `-100` à `+100`                                                           |
| `contrast`      | nombre                       | `1.0`                         | Facteur de contraste (`0.01` à `3.0`)                                                    |
| `trapezoid`     | liste de 4 nombres           | `[0, 0, 0, 0]`                | Correction trapézoïdale `[haut, bas, gauche, droite]` (fractions de la taille)           |
| `crop`          | liste de 4 nombres ou `null` | `null`                        | Zone conservée `[x1, y1, x2, y2]` après rotation                                         |
| `export`        | objet                        | `{width: null, height: null}` | Taille d'export ; si `width` est fourni, la hauteur est déduite (proportions conservées) |
| `stroke_width`  | entier                       | `3`                           | Épaisseur de trait par défaut                                                            |
| `annotations`   | liste d'objets               | `[]`                          | Annotations vectorielles (voir §4)                                                       |
| `loupes`        | liste d'objets               | `[]`                          | Loupes d'agrandissement (voir §5)                                                        |
| `custom_colors` | liste de chaînes `#RRGGBB`   | `[]`                          | Couleurs personnalisées, pour retrouver la même palette sur un autre poste               |
| `layer_order`   | liste de chaînes             | `[]`                          | Ordre d'empilement des calques, du premier plan vers l'arrière-plan (voir §6)            |

## 4. Annotations

Chaque élément de `annotations` possède un `type` : `label`, `rect`, `circle`, `line` (ou `text`, conservé pour les anciennes recettes).

| Champ                | Type    | Défaut    | Concerne        | Description                                               |
| :------------------- | :------ | :-------- | :-------------- | :-------------------------------------------------------- |
| `type`               | chaîne  | —         | tous            | `label`, `rect`, `circle`, `line`, `text`                 |
| `x1`, `y1`           | nombres | `0.0`     | tous            | Premier point (pour `label` : position de l'étiquette)    |
| `x2`, `y2`           | nombres | `0.0`     | tous            | Second point (pour `label` : cible pointée par la flèche) |
| `text`               | chaîne  | `""`      | `label`, `text` | Texte affiché                                             |
| `color`              | chaîne  | `#FFFF00` | tous            | Couleur du trait                                          |
| `stroke_width`       | entier  | `3`       | tous            | Épaisseur du trait (px)                                   |
| `font_size`          | entier  | `28`      | `label`, `text` | Taille de police                                          |
| `border_radius`      | entier  | `0`       | `rect`, `label` | Rayon des coins arrondis (0 = coins vifs)                 |
| `shape`              | chaîne  | `rect`    | `label`         | Forme du cadre : `rect` (rectangle) ou `round` (ellipse)  |
| `show_arrow`         | booléen | `true`    | `label`         | Affiche la flèche vers la cible                           |
| `arrow_stroke_width` | entier  | `2`       | `label`         | Épaisseur de la flèche, indépendante du cadre             |
| `show_text`          | booléen | `true`    | `label`         | Affiche le texte dans le cadre                            |
| `fill_enabled`       | booléen | `true`    | `label`         | Fond opaque (sinon transparent)                           |
| `bold_text`          | booléen | `false`   | `label`         | Texte en gras                                             |
| `line_arrow_start`   | booléen | `false`   | `line`          | Pointe de flèche au début                                 |
| `line_arrow_end`     | booléen | `false`   | `line`          | Pointe de flèche à la fin                                 |

## 5. Loupes

Une recette peut contenir **plusieurs loupes** dans la liste `loupes`. Chaque loupe possède un identifiant unique `id` (1, 2, 3…), attribué automatiquement : le prochain identifiant est le plus grand `id` existant + 1 (`next_loupe_id()`).

| Champ                            | Type    | Défaut    | Description                                                      |
| :------------------------------- | :------ | :-------- | :--------------------------------------------------------------- |
| `id`                             | entier  | `1`       | Identifiant unique, référencé dans `layer_order` (`loupe:<id>`)  |
| `enabled`                        | booléen | `false`   | Loupe visible (rendue à l'export)                                |
| `center_x`, `center_y`           | nombres | `0.0`     | Centre du médaillon                                              |
| `radius`                         | nombre  | `120.0`   | Rayon du médaillon                                               |
| `zoom`                           | nombre  | `2.0`     | Facteur d'agrandissement (1× à 8× dans l'interface)              |
| `arrow_start_x`, `arrow_start_y` | nombres | `0.0`     | Départ de la flèche (bord du médaillon)                          |
| `arrow_end_x`, `arrow_end_y`     | nombres | `0.0`     | Zone agrandie, pointée par la flèche                             |
| `color`                          | chaîne  | `#66D9EF` | Couleur du contour et de la flèche                               |
| `stroke_width`                   | entier  | `4`       | Épaisseur du contour circulaire                                  |
| `arrow_stroke_width`             | entier  | `2`       | Épaisseur de la flèche, indépendante du contour                  |
| `rotation`                       | nombre  | `0.0`     | Rotation (degrés, sens horaire) du **contenu agrandi** seulement |

Au chargement, un `id` manquant ou dupliqué est renuméroté pour garantir l'unicité.

## 6. Ordre des calques (`layer_order`)

`layer_order` liste les calques **du premier plan vers l'arrière-plan**. Deux types de jetons existent :

- `annotation:<i>` : l'annotation d'indice `<i>` (à partir de 0) dans la liste `annotations` ;
- `loupe:<id>` : la loupe dont l'identifiant vaut `<id>` (et non sa position dans la liste).

Exemple : `["loupe:2", "annotation:1", "loupe:1", "annotation:0"]` dessine d'abord `annotation:0` (tout au fond), puis `loupe:1`, `annotation:1`, et enfin `loupe:2` par-dessus tout le reste.

Règles complémentaires :

- si `layer_order` est absent ou vide, l'ordre par défaut est : toutes les annotations dans l'ordre de la liste, puis les loupes visibles ;
- une loupe visible absente de `layer_order` est rendue à l'arrière-plan.

L'ordre est modifié dans l'interface par glisser-déposer dans la liste des objets.

## 7. Ordre d'application des traitements

À l'export (`apply_recipe()`), les étapes sont toujours appliquées dans cet ordre :

1. rotation (`angle`) ;
2. correction trapézoïdale (`trapezoid`) ;
3. rognage (`crop`) ;
4. luminosité / contraste ;
5. annotations et loupes, selon `layer_order` ;
6. redimensionnement final (`export`, rééchantillonnage Lanczos) ;
7. enregistrement JPEG (qualité 95).

## 8. Rétrocompatibilité

Les anciennes recettes restent lisibles :

| Ancien format                                 | Traitement au chargement                                    |
| :-------------------------------------------- | :---------------------------------------------------------- |
| objet unique `"loupe": { … }` (sans `loupes`) | converti en une liste d'une loupe, qui devient la loupe `1` |
| jeton `"loupe"` dans `layer_order`            | remplacé par le jeton de la première loupe (`loupe:1`)      |
| `trapezoid` à 2 valeurs `[haut, bas]`         | complété à 4 valeurs `[haut, bas, 0, 0]`                    |
| champs d'annotation absents                   | valeurs par défaut du tableau §4                            |
| `layer_order` absent                          | ordre par défaut (§6)                                       |

La propriété Python `ProcessingRecipe.loupe` (première loupe) est conservée pour les anciens scripts.

> [!IMPORTANT]
> Toute évolution du format doit rester **rétrocompatible** : un fichier produit par une version précédente doit toujours se charger. Voir [Contribuer](contribuer.md).

## 9. Exemple complet

<details>
<summary>Exemple de fichier <code>*-iat.json</code> avec deux loupes (cliquez pour déplier)</summary>

```json
{
  "source_image": "images/photo-carte-electronique-raw.jpg",
  "angle": 0.0,
  "brightness": 10.0,
  "contrast": 1.2,
  "trapezoid": [0.0, 0.0, 0.0, 0.0],
  "crop": null,
  "export": {
    "width": 1600,
    "height": 1200
  },
  "stroke_width": 3,
  "annotations": [
    {
      "type": "rect",
      "x1": 150.0,
      "y1": 200.0,
      "x2": 450.0,
      "y2": 500.0,
      "text": "",
      "color": "#FFFF00",
      "stroke_width": 3,
      "font_size": 28,
      "border_radius": 0
    },
    {
      "type": "label",
      "x1": 500.0,
      "y1": 180.0,
      "x2": 450.0,
      "y2": 250.0,
      "text": "Microcontrôleur U1",
      "color": "#66D9EF",
      "stroke_width": 3,
      "font_size": 28,
      "border_radius": 8,
      "shape": "rect",
      "show_arrow": true,
      "arrow_stroke_width": 2,
      "show_text": true,
      "fill_enabled": true,
      "bold_text": false
    }
  ],
  "loupes": [
    {
      "id": 1,
      "enabled": true,
      "center_x": 1200.0,
      "center_y": 400.0,
      "radius": 120.0,
      "zoom": 2.5,
      "arrow_start_x": 1200.0,
      "arrow_start_y": 400.0,
      "arrow_end_x": 450.0,
      "arrow_end_y": 300.0,
      "color": "#66D9EF",
      "stroke_width": 4,
      "rotation": 0.0,
      "arrow_stroke_width": 2
    },
    {
      "id": 2,
      "enabled": true,
      "center_x": 300.0,
      "center_y": 900.0,
      "radius": 100.0,
      "zoom": 3.0,
      "arrow_start_x": 300.0,
      "arrow_start_y": 900.0,
      "arrow_end_x": 600.0,
      "arrow_end_y": 700.0,
      "color": "#FF3B30",
      "stroke_width": 4,
      "rotation": 0.0,
      "arrow_stroke_width": 2
    }
  ],
  "custom_colors": ["#AA5500"],
  "layer_order": ["loupe:2", "annotation:1", "loupe:1", "annotation:0"]
}
```

</details>

Un exemple réel est fourni dans [`images/exemple/photo-carte-electronique-iat.json`](../images/exemple/photo-carte-electronique-iat.json).

## 10. Utiliser une recette depuis un script Python

La recette peut être rejouée sans interface graphique, par exemple pour traiter un lot d'images :

```python
from iat.image_processor import ProcessingRecipe, process_image_with_recipe

recette = ProcessingRecipe.load("images/exemple/photo-carte-electronique-iat.json")
recette.export_width = 800           # nouvelle largeur, hauteur déduite
recette.export_height = None
process_image_with_recipe(recette, "images/exemple/photo-carte-electronique-iat-x800.jpg")
```

> [!NOTE]
> `source_image` doit pointer vers un fichier accessible depuis le dossier de travail courant (chemin absolu ou relatif).
