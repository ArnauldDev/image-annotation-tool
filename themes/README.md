<!--
  File Name: README.md
  Description: Documentation des thèmes QSS de l'application Image Annotation Tool.
  Developer: ArnauldDev
  Last Modified: 2026-09-23
-->

# Thèmes IAT

Les thèmes sont **la seule source de l'apparence** de l'application (couleurs, bordures, menus, champs de saisie…).

Le fichier `.env` ne contient plus de couleurs : il indique seulement le thème appliqué par défaut via `APP_THEME`.

| Fichier       | Menu       | Description                                                   |
| ------------- | ---------- | ------------------------------------------------------------- |
| `cbi.qss`     | CBI        | Charte graphique du Centre de Biologie Intégrative (défaut)   |
| `clair.qss`   | Clair      | Thème clair classique                                         |
| `sombre.qss`  | Sombre     | Thème sombre à fort contraste (menus et sous-menus compris)   |

## Choix du thème

Ordre de priorité au démarrage :

1. le thème choisi par l'utilisateur dans `Configuration > Thèmes disponibles` (ou `Configuration > Charger un thème personnalisé`), mémorisé pour les sessions suivantes ;
2. sinon le thème nommé par `APP_THEME` dans le fichier `.env` (`cbi`, `clair`, `sombre`, ou le nom d'un thème ajouté) ;
3. sinon le thème `cbi`.

Charger un `.env` contenant `APP_THEME` (`Configuration > Charger une configuration .env`) applique ce thème immédiatement.

## Créer un thème

Copiez un thème existant et modifiez ses couleurs. Les fichiers `.qss` de ce dossier apparaissent automatiquement dans `Configuration > Thèmes disponibles`.

Ils peuvent rester directement dans ce dossier ou être rangés dans un sous-dossier par thème (le menu affiche alors le nom du dossier) :

```text
themes/
  mon-theme/
    style.qss
    app_icon.ico    # facultatif : remplace l'icône de la fenêtre
```

Deux conventions propres à l'application sont disponibles dans un thème :

- `iat-icon-color: #RRGGBB` placé dans un commentaire : couleur des icônes SVG de l'interface (icône « outils » de la barre horizontale, palette graphique des outils) ;
- `url(@icons/<nom>.svg)` : référence une icône fournie avec l'application (`src/iat/resources/icons/`, par exemple `plus.svg`, `minus.svg`, `chevron_down.svg`), automatiquement teintée avec la couleur `iat-icon-color`.

Pour que tous les éléments restent lisibles, conservez au minimum les règles `QMenuBar`, `QMenuBar::item`, `QMenu`, `QMenu::item`, `QSpinBox::up-button` / `down-button` (boutons « + » / « − ») et `QToolButton:checked`.

Le style Qt de base est « Fusion » (`APP_QT_STYLE` dans le `.env`), qui respecte intégralement les feuilles de style.

Le chargeur vérifie que le fichier est lisible, non vide et que ses accolades sont équilibrées avant de l'appliquer. Une erreur détaillée est affichée sans modifier le thème courant si cette validation échoue.

Pour une icône propre sous Windows, utilisez de préférence un fichier `.ico` multi-résolution contenant au minimum 16, 32, 48, 64, 128 et 256 pixels.

<!-- ## Vérifier visuellement un thème

```bash
python tools/ui_harness.py --theme mon-theme            # captures dans .harness/mon-theme/
python tools/ui_harness.py --theme mon-theme --style windows11
``` -->
