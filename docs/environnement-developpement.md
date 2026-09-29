<!--
  File Name: environnement-developpement.md
  Description: Mise en place de l'environnement de développement d'Image Annotation Tool (Python, venv, tests, organisation du projet).
  Developer: ArnauldDev
  Created Date: 2026-09-23
  Last Modified: 2026-09-29
-->

<h3>Environnement de développement</h3>

[← Retour au README](../README.md)

Ce document explique comment installer les outils, lancer l'application depuis les sources et exécuter les tests, sous Windows, macOS et Linux.

<h4><u>Sommaire</u> :</h4>

- [1. Prérequis](#1-prérequis)
- [2. Récupérer les sources](#2-récupérer-les-sources)
- [3. Créer l'environnement virtuel](#3-créer-lenvironnement-virtuel)
- [4. Installer les dépendances](#4-installer-les-dépendances)
- [5. Lancer l'application](#5-lancer-lapplication)
- [6. Exécuter les tests](#6-exécuter-les-tests)
  - [Tests sans écran (offscreen)](#tests-sans-écran-offscreen)
- [7. Organisation du projet](#7-organisation-du-projet)
- [8. Dépannage](#8-dépannage)

---

## 1. Prérequis

Vérifiez que vous avez installé les outils suivants :

| Outil  | Version                                                    | Remarque                                                            |
| :----- | :--------------------------------------------------------- | :------------------------------------------------------------------ |
| Python | **3.10 minimum** (`requires-python` dans `pyproject.toml`) | Développement et tests réalisés en Python 3.14, version recommandée |
| Git    | récente                                                    | Pour cloner le dépôt et contribuer                                  |
| pip    | fournie avec Python                                        | Mettez-la à jour dans l'environnement virtuel                       |

<br />

Installation de Python :

- **Windows** : [Python install manager](https://docs.python.org/3.14/using/windows.html#python-install-manager) ou l'installeur de [python.org](https://www.python.org/downloads/) (cochez « Add python.exe to PATH ») ;
- **macOS** : installeur de [python.org](https://www.python.org/downloads/macos/) ou `brew install python@3.14` ;
- **Linux** : paquet de la distribution (`sudo apt install python3 python3-venv python3-pip` sous Debian/Ubuntu), voir [Utilisation de Python sur Unix](https://docs.python.org/3.14/using/unix.html).

Sous Linux, Qt 6 a besoin de quelques bibliothèques système pour afficher des fenêtres (Debian/Ubuntu) :

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1 libgl1 libfontconfig1 libdbus-1-3
```

## 2. Récupérer les sources

```bash
git clone https://src.koda.cnrs.fr/cbi-plateau-mecatronique/ressources/image-annotation-tool.git
cd image-annotation-tool
git switch dev          # branche de développement
```

## 3. Créer l'environnement virtuel

Un environnement virtuel (`.venv/`, ce dossier local pèse environ 250 Mo et sera ignoré par git pour ne pas alourdir le dépôt) isole les dépendances du projet de celles du système.\
Afin de respecter les versions de dépendances spécifiées, le développement et les tests se font à l'intérieur de cet environnement.

**Windows (PowerShell)** :

```powershell
py -m venv .venv            # ou : python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> [!TIP]
> Si PowerShell refuse d'exécuter le script d'activation : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**macOS / Linux (bash, zsh)** :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Une fois activé, l'invite affiche `(.venv)`, cela confirme que vous êtes dans l'environnement virtuel.\
Pour en sortir quand vous avez fini, tapez simplement : `deactivate`.

## 4. Installer les dépendances

Deux méthodes équivalentes :

```bash
python -m pip install --upgrade pip

# a) Installation avec les versions figées du fichier requirements.txt
#    (c'est la méthode la plus simple, si vous souhaitez seulement utiliser le projet sans installer les outils de construction de l'exécutable)
python -m pip install -r requirements.txt
```

```bash
# b) Ou installation « éditable » du paquet avec les outils de développement (pytest, PyInstaller)
python -m pip install -e ".[dev]"
```

| Fichier            | Contenu                                                                                                    |
| :----------------- | :--------------------------------------------------------------------------------------------------------- |
| `pyproject.toml`   | Métadonnées, dépendances minimales (`pillow`, `PyQt6`, `python-dotenv`), extra `dev`, configuration pytest |
| `requirements.txt` | Versions figées utilisées par l'équipe (PyQt6 6.11, Pillow 12.3, pytest 9.1…)                              |

L'installation éditable (`-e`) crée aussi la commande `image-annotation-tool` et permet d'importer `iat` depuis n'importe quel dossier.

> [!TIP]
> Sans activer l'environnement, appelez directement son interpréteur : `.\.venv\Scripts\python.exe -m pip …` (Windows) ou `.venv/bin/python -m pip …` (macOS/Linux).

## 5. Lancer l'application

Depuis la racine du dépôt :

```bash
python main.py            # lanceur racine (ajoute src/ au chemin Python)
python -m iat             # module du paquet (après pip install -e, ou avec src/ dans PYTHONPATH)
image-annotation-tool     # commande installée par pip install -e
```

Pour tester une configuration particulière, placez un fichier `.env` à la racine (voir [Configuration](configuration.md)).

## 6. Exécuter les tests

La suite utilise **pytest** ; sa configuration est centralisée dans `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["src"]`, marqueurs `slow` et `integration`).

```bash
python -m pytest -q                    # toute la suite ................................... [Windows fatal exception: access violation]
python -m pytest tests/unit            # tests unitaires seulement ........................ [Windows fatal exception: access violation]
python -m pytest tests/integration     # tests d'intégration seulement .................... [passed]
python -m pytest -m "not slow"         # sans les tests lents ............................. [Windows fatal exception: access violation]
python -m pytest tests/unit/test_multi_loupe.py -k layer   # un fichier, filtré par nom ... [2 passed, 10 deselected]
```

### Tests sans écran (offscreen)

Les tests de l'interface créent de vraies fenêtres Qt. Sur un serveur sans affichage (CI, SSH), utilisez la plateforme Qt `offscreen` :

```bash
# Linux / macOS
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

```powershell
# Windows (PowerShell)
$env:QT_QPA_PLATFORM = "offscreen"; python -m pytest -q  # tests sans affichage (offscreen) ... [Windows fatal exception: access violation]
```

> [!NOTE]
> `tests/conftest.py` isole automatiquement `QSettings` et l'historique des fichiers récents dans un dossier temporaire : les tests ne modifient jamais vos préférences réelles.

Les bonnes pratiques de rédaction des tests sont décrites dans [`tests/README.md`](../tests/README.md).

## 7. Organisation du projet

```text
image-annotation-tool/
├── main.py                        # Lanceur racine (python main.py)
├── src/
│   └── iat/                       # Paquet Python de l'application
│       ├── __init__.py
│       ├── __main__.py            # Permet « python -m iat »
│       ├── main.py                # Point d'entrée (commande image-annotation-tool)
│       ├── config.py              # Harness .env : AppConfig, feature flags
│       ├── image_processor.py     # Moteur Pillow + recette JSON (ProcessingRecipe)
│       ├── qt_image_editor.py     # Interface PyQt6 (ImageCanvas, ImageEditorWindow)
│       └── resources/
│           ├── logo_app_iat.svg   # Logo (fenêtre « À propos »)
│           └── icons/             # Icônes SVG (teintées par le thème), app_icon.ico
├── themes/                        # Thèmes QSS : cbi (défaut), clair, sombre + README
├── translations/                  # Traductions de l'interface (<code>.json)
├── tests/
│   ├── conftest.py                # Fixtures pytest (images synthétiques, isolation QSettings)
│   ├── unit/                      # Tests unitaires (moteur, recette, IHM, configuration, multi-loupe)
│   ├── integration/               # Cycle complet image brute → JSON → export JPEG
│   ├── fixtures/                  # Recettes JSON de référence
│   └── README.md                  # Bonnes pratiques de test
├── images/                        # Captures et photographies d'exemple
├── docs/                          # Documentation (ce dossier)
├── .env.example, cbi.env          # Modèles de configuration
├── pyproject.toml                 # Packaging, dépendances, configuration pytest
├── requirements.txt               # Dépendances figées
├── image_annotation_tool.spec     # Configuration PyInstaller
├── build_exe.py                   # Script de construction de l'exécutable
└── .gitlab-ci.yml                 # Pipeline GitLab CI/CD
```

Principe d'architecture : **le moteur (`image_processor.py`) ne dépend pas de Qt**. L'interface construit une `ProcessingRecipe` et le moteur la rejoue en pleine résolution. On peut ainsi tester le rendu sans interface et traiter des images par script (voir [Format de la recette JSON](format-recette-json.md)).

## 8. Dépannage

| Symptôme                                              | Solution                                                                                               |
| :---------------------------------------------------- | :----------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'iat'`          | Lancez `python main.py`, ou installez le paquet avec `pip install -e .`                                |
| Linux : `Could not load the Qt platform plugin "xcb"` | Installez `libxcb-cursor0` et les bibliothèques listées au §1                                          |
| Interface partiellement thémée sous Windows           | Vérifiez `APP_QT_STYLE=Fusion` (voir [Configuration](configuration.md#5-pourquoi-app_qt_stylefusion-)) |
| Les tests modifient `os.environ`                      | Utilisez `monkeypatch.setenv` puis `update_config_in_place(AppConfig())`                               |
