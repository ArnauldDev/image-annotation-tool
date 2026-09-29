<!--
  File Name: configuration.md
  Description: Configuration de l'application Image Annotation Tool : fichier .env, menu « Configuration », thèmes, langues et préférences.
  Developer: ArnauldDev
  Created Date: 2026-09-23
  Last Modified: 2026-09-23
-->

# Configuration

[← Retour au README](../README.md)

L'application se configure à trois niveaux, du plus général au plus personnel :

1. **les valeurs par défaut** codées dans [`src/iat/config.py`](../src/iat/config.py) (classe `AppConfig`) ;
2. **un fichier `.env`** facultatif, qui adapte ces valeurs sans modifier le code (utile pour un poste ou une équipe) ;
3. **les préférences de l'utilisateur**, choisies dans le menu `Configuration` et mémorisées d'une session à l'autre (elles priment sur le `.env`).

## Sommaire

- [1. Le fichier `.env`](#1-le-fichier-env)
- [2. Variables disponibles](#2-variables-disponibles)
- [3. Le menu « Configuration »](#3-le-menu--configuration-)
- [4. Thèmes](#4-thèmes)
- [5. Pourquoi `APP_QT_STYLE=Fusion` ?](#5-pourquoi-app_qt_stylefusion-)
- [6. Langues et traductions](#6-langues-et-traductions)
- [7. Préférences mémorisées (QSettings)](#7-préférences-mémorisées-qsettings)

---

## 1. Le fichier `.env`

Un fichier `.env` est un simple fichier texte `CLE=valeur`, une variable par ligne ; les lignes commençant par `#` sont des commentaires.

### Chargement au démarrage

Au lancement, l'application cherche un fichier `.env` :

1. dans le **dossier de travail courant** (`./.env`) ;
2. à défaut, dans le dossier `src/` du projet.

Les variables déjà définies dans l'environnement du système ne sont **pas** écrasées par ce fichier au démarrage. Le chargement utilise `python-dotenv` s'il est installé, sinon un analyseur intégré équivalent.

### Chargement depuis le menu

`Configuration > Charger une configuration .env` permet de choisir n'importe quel fichier `.env`. Dans ce cas :

- ses valeurs **remplacent** les valeurs courantes (épaisseur de trait par défaut, drapeaux de fonctionnalités…) ;
- si le fichier définit `APP_THEME`, ce thème est appliqué immédiatement et remplace le thème choisi précédemment ;
- **le chemin du fichier est mémorisé** : il est rechargé automatiquement au prochain démarrage.

`Configuration > À propos des fichiers .env` rappelle ces règles dans l'application.

### Fichiers fournis

| Fichier        | Rôle                                                                           |
| :------------- | :----------------------------------------------------------------------------- |
| `.env.example` | Modèle documenté ; copiez-le en `.env` pour créer votre configuration locale   |
| `cbi.env`      | Configuration de référence du plateau (active en plus `FEATURE_CORNER_RADIUS`) |

```bash
# Windows (PowerShell)
Copy-Item .env.example .env
# Linux / macOS
cp .env.example .env
```

> [!NOTE]
> Le fichier `.env` est ignoré par git (voir `.gitignore`) : il reste propre à chaque poste.

## 2. Variables disponibles

Les valeurs booléennes acceptent `1`, `true`, `yes`, `on`, `y` (insensible à la casse) ; toute autre valeur vaut « faux ». Une valeur entière invalide est remplacée par la valeur par défaut.

### Environnement

| Variable       | Défaut       | Description                                                                   |
| :------------- | :----------- | :---------------------------------------------------------------------------- |
| `APP_ENV`      | `production` | Environnement applicatif : `production`, `development` ou `test`              |
| `APP_DEBUG`    | `false`      | Mode débogage                                                                 |
| `APP_LANGUAGE` | `fr`         | Langue de l'interface par défaut (code du fichier `translations/<code>.json`) |

### Apparence

| Variable       | Défaut   | Description                                                                                              |
| :------------- | :------- | :------------------------------------------------------------------------------------------------------- |
| `APP_THEME`    | `cbi`    | Thème appliqué par défaut : nom du fichier `themes/<nom>.qss` sans extension (`cbi`, `clair`, `sombre`…) |
| `APP_QT_STYLE` | `Fusion` | Style Qt de base sur lequel le thème est appliqué (voir [§5](#5-pourquoi-app_qt_stylefusion-))           |

### Traitement d'image

| Variable                        | Défaut | Description                                             |
| :------------------------------ | :----- | :------------------------------------------------------ |
| `DEFAULT_PREVIEW_MAX_DIMENSION` | `1600` | Plus grand côté (px) de l'aperçu de travail             |
| `DEFAULT_EXPORT_QUALITY`        | `95`   | Qualité JPEG de l'export (1 à 100)                      |
| `DEFAULT_STROKE_WIDTH`          | `3`    | Épaisseur de trait par défaut des nouvelles annotations |

### Drapeaux de fonctionnalités (`FEATURE_*`)

Les drapeaux permettent d'activer ou de masquer une fonctionnalité en cours de développement sans modifier le code.

| Variable                       | Défaut  | Description                                                   |
| :----------------------------- | :------ | :------------------------------------------------------------ |
| `FEATURE_RECENT_FILES_HISTORY` | `true`  | Historique `Fichier > Fichiers récents`                       |
| `FEATURE_TRAPEZOID_ROTATION`   | `false` | Rotation combinée à la correction trapézoïdale (expérimental) |
| `FEATURE_CORNER_RADIUS`        | `false` | Réglage du rayon des coins arrondis (expérimental)            |
| `FEATURE_MULTI_LOUPE`          | `true`  | Plusieurs loupes par image (bouton `Nouvelle loupe`)          |

> [!NOTE]
> État actuel du code (version 1.0.0) : `APP_ENV`, `APP_DEBUG`, `DEFAULT_PREVIEW_MAX_DIMENSION`, `DEFAULT_EXPORT_QUALITY`, `FEATURE_RECENT_FILES_HISTORY`, `FEATURE_TRAPEZOID_ROTATION` et `FEATURE_CORNER_RADIUS` sont lues par `AppConfig` mais **pas encore exploitées** par l'interface ou le moteur : l'aperçu est limité à 1600 px et l'export est enregistré en qualité 95, quelles que soient leurs valeurs. Elles sont réservées aux évolutions prévues. `APP_THEME`, `APP_QT_STYLE`, `APP_LANGUAGE`, `DEFAULT_STROKE_WIDTH` et `FEATURE_MULTI_LOUPE` sont, elles, effectives.

Un drapeau quelconque `FEATURE_<NOM>` peut aussi être interrogé dans le code avec `config.is_feature_enabled("<nom>")`, même s'il n'est pas déclaré dans `AppConfig` (il vaut alors `false` par défaut).

### Exemple complet

```ini
APP_ENV=production
APP_DEBUG=false
APP_LANGUAGE=fr

APP_THEME=cbi
APP_QT_STYLE=Fusion

DEFAULT_PREVIEW_MAX_DIMENSION=1600
DEFAULT_EXPORT_QUALITY=95
DEFAULT_STROKE_WIDTH=3

FEATURE_RECENT_FILES_HISTORY=true
FEATURE_TRAPEZOID_ROTATION=false
FEATURE_CORNER_RADIUS=false
FEATURE_MULTI_LOUPE=true
```

## 3. Le menu « Configuration »

La barre de menus comporte `Fichier`, `Édition`, `Configuration` et `Aide`. Le menu `Configuration` regroupe tout ce qui adapte l'application à l'utilisateur :

| Entrée                                             | Rôle                                                                                                                                                |
| :------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Charger une configuration .env`                   | Charge un fichier `.env` (voir [§1](#1-le-fichier-env)) ; son chemin est mémorisé                                                                   |
| `À propos des fichiers .env`                       | Aide sur le rôle et la persistance du `.env`                                                                                                        |
| `Thèmes disponibles`                               | Liste des thèmes du dossier des thèmes ; le choix est mémorisé (voir [§4](#4-thèmes))                                                               |
| `Charger un thème personnalisé`                    | Applique un fichier `.qss` situé n'importe où                                                                                                       |
| `Langue`                                           | Sous-menu listant `Français` et chaque fichier de traduction trouvé, par exemple `English` (voir [§6](#6-langues-et-traductions))                   |
| `Chemins des ressources…`                          | Choix des dossiers des **icônes**, des **thèmes** et des **traductions** (voir ci-dessous)                                                          |
| `Notification après l'export`                      | Case à cocher, **activée par défaut** : affiche une fenêtre de confirmation après chaque export. Le message de la barre d'état est toujours affiché |
| `Afficher/Masquer la barre horizontale des outils` | Raccourci `Ctrl+T`                                                                                                                                  |
| `Afficher/Masquer la palette graphique des outils` | Palette d'icônes à gauche                                                                                                                           |
| `Réinitialiser les paramètres…`                    | Restaure les valeurs par défaut, après confirmation (voir ci-dessous)                                                                               |

### Chemins des ressources

Par défaut, les ressources sont lues dans les dossiers livrés avec l'application :

| Ressource   | Dossier par défaut (sources) | Dossier par défaut (exécutable) |
| :---------- | :--------------------------- | :------------------------------ |
| Icônes      | `src/iat/resources/icons/`   | `iat/resources/icons/`          |
| Thèmes      | `themes/`                    | `themes/`                       |
| Traductions | `translations/`              | `translations/`                 |

La boîte de dialogue propose un champ et un bouton `Parcourir…` par ressource, ainsi qu'un bouton rétablissant les dossiers par défaut. C'est utile pour tester un jeu d'icônes, ou partager des thèmes et des traductions sur un lecteur réseau de l'équipe, sans modifier l'installation. Les chemins choisis sont mémorisés ; les menus `Thèmes disponibles` et `Langue` sont reconstruits à partir des nouveaux dossiers. Si une icône est absente du dossier choisi, l'icône livrée avec l'application est utilisée.

### Réinitialiser les paramètres

`Réinitialiser les paramètres…` efface les préférences mémorisées et revient aux valeurs par défaut pour :

- le thème (retour à `APP_THEME`, sinon `cbi`) ;
- les chemins des ressources (icônes, thèmes, traductions) ;
- la langue (retour à `APP_LANGUAGE`, sinon le français) ;
- la notification après l'export (réactivée) ;
- les couleurs personnalisées de la palette ;
- la disposition de la fenêtre (barres d'outils, panneaux) ;
- le fichier `.env` mémorisé (ses variables sont oubliées et le `.env` par défaut est relu).

Les images, recettes JSON et l'historique des fichiers récents ne sont pas touchés.

## 4. Thèmes

Les feuilles de style Qt (`themes/*.qss`) sont **la seule source de l'apparence** : couleurs, bordures, menus, champs de saisie… Aucune couleur d'interface n'est codée en dur dans le Python, et le `.env` ne contient plus de couleurs (seulement le nom du thème par défaut).

| Fichier      | Nom dans le menu | Description                                                 |
| :----------- | :--------------- | :---------------------------------------------------------- |
| `cbi.qss`    | CBI              | Charte graphique du Centre de Biologie Intégrative (défaut) |
| `clair.qss`  | Clair            | Thème clair classique                                       |
| `sombre.qss` | Sombre           | Thème sombre à fort contraste                               |

### Ordre de priorité au démarrage

1. le thème choisi dans `Configuration > Thèmes disponibles` (ou chargé via `Charger un thème personnalisé`), mémorisé ;
2. sinon le thème nommé par `APP_THEME` ;
3. sinon `cbi`.

### Créer un thème

Copiez un thème existant, renommez-le et modifiez ses couleurs. Tout fichier `.qss` du dossier des thèmes apparaît automatiquement dans le menu. Un thème peut aussi être rangé dans un sous-dossier (le menu affiche alors le nom du dossier) :

```text
themes/
├── cbi.qss
├── clair.qss
├── sombre.qss
└── mon-theme/
    ├── style.qss
    └── app_icon.ico    # facultatif : remplace l'icône de la fenêtre
```

### Directives propres à IAT

Qt ne sait pas recolorer une image depuis une feuille de style. L'application lit donc des directives placées **dans un commentaire** du `.qss` :

| Directive                         | Rôle                                                                                                                                         |
| :-------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------- |
| `iat-icon-color: #RRGGBB`         | Couleur des icônes SVG (icône « outils » de la barre horizontale, palette graphique)                                                         |
| `iat-icon-checked-color: #RRGGBB` | Couleur des icônes d'un outil actif (bouton coché, fond de couleur d'accent)                                                                 |
| `url(@icons/<nom>.svg)`           | Référence une icône fournie avec l'application (`plus.svg`, `minus.svg`, `chevron_down.svg`…), automatiquement teintée avec `iat-icon-color` |

Exemple (extrait de `themes/cbi.qss`) :

```css
/*
   iat-icon-color: #96FFC7
   iat-icon-checked-color: #414F65
*/
QSpinBox::up-button {
    image: url(@icons/plus.svg);
}
```

Pour que l'interface reste lisible, conservez au minimum les règles `QMenuBar`, `QMenuBar::item`, `QMenu`, `QMenu::item`, `QSpinBox::up-button` / `down-button` et `QToolButton:checked`.

Avant d'être appliqué, un thème est validé (fichier lisible, non vide, accolades équilibrées). En cas d'erreur, un message détaillé s'affiche et le thème courant est conservé.

Plus de détails : [`themes/README.md`](../themes/README.md).

## 5. Pourquoi `APP_QT_STYLE=Fusion` ?

Un thème QSS s'applique **par-dessus** un style Qt de base. Sous Windows 11, le style natif `windows11` **ignore une partie des feuilles de style** : menus et sous-menus, boutons `+`/`−` des champs numériques, certains sous-contrôles… Le résultat est une interface à moitié thémée, parfois illisible (texte clair sur fond clair).

Le style `Fusion`, fourni par Qt sur toutes les plateformes, respecte intégralement les QSS et donne un rendu **identique sous Windows, macOS et Linux**. C'est pourquoi il est utilisé par défaut. Vous pouvez tester un autre style (`windows11`, `windowsvista`, `macOS`…) avec `APP_QT_STYLE`, à vos risques.

## 6. Langues et traductions

L'interface est rédigée en français dans le code. Le sous-menu `Configuration > Langue` propose `Français` ainsi qu'une entrée par fichier de traduction trouvé (par exemple `English`) ; le changement est immédiat et le choix est mémorisé. Tant que l'utilisateur n'a rien choisi, la langue est donnée par `APP_LANGUAGE` (`fr` par défaut).

Les traductions sont de simples fichiers JSON dans le dossier `translations/`, nommés d'après le code de langue :

```text
translations/
└── en.json
```

Chaque fichier est un dictionnaire **texte source français → texte traduit** :

```json
{
  "_language_name": "English",
  "Ouvrir une image": "Open an image",
  "Exporter l'image": "Export the image",
  "Export terminé": "Export finished"
}
```

La clé spéciale `_language_name` donne le nom affiché dans le menu `Langue` (à défaut, le code du fichier est affiché). Un texte absent du dictionnaire reste affiché en français : une traduction peut donc être complétée progressivement. Un fichier illisible ou qui n'est pas un objet JSON est ignoré.

**Ajouter une langue** : créez `translations/<code>.json` (par exemple `es.json` avec `"_language_name": "Español"`) en partant de `en.json`, puis traduisez les valeurs. Aucune modification du code n'est nécessaire : la langue apparaît dans le menu au prochain démarrage (ou après `Chemins des ressources…`). Pensez à embarquer le dossier dans l'exécutable (voir [Génération de l'exécutable](generation-executable.md)).

> [!TIP]
> Les clés doivent reprendre **exactement** le texte français de l'interface (accents, apostrophes et ponctuation compris).

## 7. Préférences mémorisées (QSettings)

Les préférences de l'utilisateur sont enregistrées avec `QSettings("CBI", "ImageAnnotationTool")`, c'est-à-dire :

| Système | Emplacement                                                          |
| :------ | :------------------------------------------------------------------- |
| Windows | Registre : `HKEY_CURRENT_USER\Software\CBI\ImageAnnotationTool`      |
| macOS   | `~/Library/Preferences/` (fichier `com.….ImageAnnotationTool.plist`) |
| Linux   | `~/.config/CBI/ImageAnnotationTool.conf`                             |

On y trouve notamment : le thème choisi, le chemin du `.env`, la géométrie et l'état de la fenêtre, les couleurs personnalisées, la notification après l'export, les chemins des ressources et la langue.

L'historique des fichiers récents est stocké à part, dans `~/.config/iat/recent_files.json`.

Pour repartir de zéro, utilisez `Configuration > Réinitialiser les paramètres…`.
