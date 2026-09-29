<!--
  File Name: gitlab-ci-cd.md
  Description: Configuration du dépôt GitLab d'Image Annotation Tool : runners, pipeline CI/CD, artefacts, releases, branches protégées et merge requests.
  Developer: ArnauldDev
  Created Date: 2026-09-23
  Last Modified: 2026-09-23
-->

# Configurer le dépôt GitLab et la CI/CD

[← Retour au README](../README.md)

Le dépôt est hébergé sur l'instance GitLab du CNRS : <https://src.koda.cnrs.fr/cbi-plateau-mecatronique/ressources/image-annotation-tool/>. Ce document explique comment automatiser les tests et la construction des exécutables avec **GitLab CI/CD**, et comment régler le dépôt (branches protégées, merge requests, versions).

## Sommaire

- [Configurer le dépôt GitLab et la CI/CD](#configurer-le-dépôt-gitlab-et-la-cicd)
  - [Sommaire](#sommaire)
  - [1. Notions de base](#1-notions-de-base)
  - [2. Les runners](#2-les-runners)
    - [Runners partagés ou runners de projet](#runners-partagés-ou-runners-de-projet)
    - [Créer un runner de projet](#créer-un-runner-de-projet)
    - [Runner Windows](#runner-windows)
    - [Runner macOS](#runner-macos)
    - [Runner Linux (Docker)](#runner-linux-docker)
  - [3. Le pipeline du projet](#3-le-pipeline-du-projet)
    - [Le job de test](#le-job-de-test)
    - [Les jobs de construction](#les-jobs-de-construction)
    - [Éviter les pipelines en double](#éviter-les-pipelines-en-double)
  - [4. Artefacts et releases](#4-artefacts-et-releases)
  - [5. Branches protégées et étiquettes](#5-branches-protégées-et-étiquettes)
    - [Branches protégées (Protected branches)](#branches-protégées-protected-branches)
    - [Étiquettes protégées](#étiquettes-protégées)
    - [Branche par défaut](#branche-par-défaut)
  - [6. Réglages des merge requests](#6-réglages-des-merge-requests)
  - [7. Publier une nouvelle version](#7-publier-une-nouvelle-version)
  - [8. Dépannage](#8-dépannage)

---

## 1. Notions de base

| Terme             | Définition                                                                                   |
| :---------------- | :------------------------------------------------------------------------------------------- |
| **Pipeline**      | Ensemble des tâches exécutées automatiquement à chaque *push*, merge request ou étiquette    |
| **Stage**         | Étape du pipeline (`test`, `build`, `release`) ; les étapes s'exécutent dans l'ordre         |
| **Job**           | Tâche élémentaire (ex. `test:linux`) exécutée par un runner                                  |
| **Runner**        | Programme (GitLab Runner) installé sur une machine, qui récupère les jobs et les exécute     |
| **Tag de runner** | Étiquette (`linux`, `windows`, `macos`) qui associe un job à un runner capable de l'exécuter |
| **Artefact**      | Fichier produit par un job (rapport de tests, exécutable) et conservé par GitLab             |
| **Release**       | Version publiée, associée à une étiquette git `vX.Y.Z`, avec des liens de téléchargement     |

Le pipeline est décrit dans le fichier [`.gitlab-ci.yml`](../.gitlab-ci.yml) à la racine du dépôt. GitLab le lit automatiquement : il suffit de le pousser.

## 2. Les runners

### Runners partagés ou runners de projet

| Type                              | Où le trouver                                                         | Avantages / limites                                                                                             |
| :-------------------------------- | :-------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------- |
| **Runners d'instance** (partagés) | fournis par les administrateurs de `src.koda.cnrs.fr`, s'ils existent | Rien à installer ; en général **Linux + Docker uniquement** : parfaits pour les tests                           |
| **Runners de groupe**             | `cbi-plateau-mecatronique > Build > Runners`                          | Partagés par tous les projets du groupe                                                                         |
| **Runners de projet**             | `Settings > CI/CD > Runners` du projet                                | Machines du laboratoire (PC Windows, Mac) : **indispensables pour construire les exécutables Windows et macOS** |

Vérifiez d'abord dans `Settings > CI/CD > Runners` quels runners d'instance sont disponibles et quelles étiquettes ils portent. Si aucun runner partagé n'existe, enregistrez un runner Linux Docker sur un serveur du laboratoire (même procédure que ci-dessous).

> [!IMPORTANT]
> PyInstaller ne fait **pas de compilation croisée** : il faut un runner **Windows** pour l'exécutable Windows et un runner **macOS** (un Mac physique) pour l'application macOS. Voir [Génération de l'exécutable](generation-executable.md).

### Créer un runner de projet

1. Dans le projet : `Settings > CI/CD > Runners > New project runner`.
2. Choisissez le système (Linux, Windows, macOS), saisissez les **tags** (`linux`, `windows` ou `macos`) et décochez « Run untagged jobs » pour que le runner n'exécute que les jobs qui lui sont destinés.
3. GitLab affiche un **jeton d'authentification** (`glrt-…`) et la commande d'enregistrement. Conservez le jeton secret.

### Runner Windows

Sur un PC ou une VM Windows dédiée (toujours allumée pendant les builds) :

1. Installez **Python 3.14** (avec le lanceur `py`) et **Git for Windows**.
2. Téléchargez `gitlab-runner-windows-amd64.exe`, renommez-le `gitlab-runner.exe` dans `C:\GitLab-Runner`.
3. Dans un PowerShell **administrateur** :

   ```powershell
   cd C:\GitLab-Runner
   .\gitlab-runner.exe register `
     --url https://src.koda.cnrs.fr `
     --token glrt-XXXXXXXXXXXXXXXX `
     --executor shell `
     --shell pwsh
   .\gitlab-runner.exe install
   .\gitlab-runner.exe start
   ```

4. Vérifiez que le runner apparaît en vert dans `Settings > CI/CD > Runners`.

Le job `build:windows` utilise l'exécuteur **shell** (PowerShell) : il crée un environnement virtuel, installe les dépendances et lance `build_exe.py`.

### Runner macOS

Sur un Mac du laboratoire :

```bash
brew install gitlab-runner python@3.14        # ou installeurs officiels
gitlab-runner register \
  --url https://src.koda.cnrs.fr \
  --token glrt-XXXXXXXXXXXXXXXX \
  --executor shell
brew services start gitlab-runner             # démarre le runner avec la session utilisateur
```

Remarques :

- le runner macOS s'exécute sous un compte utilisateur (nécessaire pour accéder au trousseau lors d'une éventuelle signature de code) ;
- l'architecture de l'application produite est celle du Mac (Apple Silicon `arm64` ou Intel `x86_64`) ;
- pour signer et notariser dans la CI, stockez les identifiants dans des **variables CI/CD masquées et protégées** (`Settings > CI/CD > Variables`), jamais dans le dépôt.

### Runner Linux (Docker)

```bash
sudo gitlab-runner register \
  --url https://src.koda.cnrs.fr \
  --token glrt-XXXXXXXXXXXXXXXX \
  --executor docker \
  --docker-image python:3.14-slim
```

Les jobs Linux s'exécutent dans un conteneur `python:3.14-slim` où le pipeline installe les bibliothèques système de Qt 6.

## 3. Le pipeline du projet

```text
 test              build                            release
┌────────────┐    ┌─────────────────────────────┐   ┌──────────┐
│ test:linux │ ─► │ build:linux   (tag linux)   │ ─►│ release  │
│  (pytest)  │    │ build:windows (tag windows) │   │ (tags    │
└────────────┘    │ build:macos   (tag macos)   │   │  vX.Y.Z) │
                  └─────────────────────────────┘   └──────────┘
```

| Job             | Quand                                                                  | Runner           | Produit                                     |
| :-------------- | :--------------------------------------------------------------------- | :--------------- | :------------------------------------------ |
| `test:linux`    | À chaque push, merge request et étiquette                              | Docker (partagé) | Rapport JUnit affiché dans la MR            |
| `build:linux`   | Automatique sur une étiquette `vX.Y.Z`, **manuel** sur `main` et `dev` | tag `linux`      | `ImageAnnotationTool-linux-x86_64`          |
| `build:windows` | idem                                                                   | tag `windows`    | `ImageAnnotationTool-windows.exe`           |
| `build:macos`   | idem                                                                   | tag `macos`      | `ImageAnnotationTool-macos-<arch>.zip`      |
| `release`       | Uniquement sur une étiquette `vX.Y.Z`                                  | Docker (partagé) | Release GitLab avec liens de téléchargement |

### Le job de test

Les tests de l'interface ouvrent de vraies fenêtres Qt. Dans un conteneur sans écran, on utilise la plateforme **offscreen** et on installe les bibliothèques système dont Qt 6 a besoin :

```yaml
test:linux:
  stage: test
  image: python:3.14-slim
  variables:
    QT_QPA_PLATFORM: "offscreen"
  before_script:
    - apt-get update -qq
    - apt-get install -y -qq --no-install-recommends libgl1 libegl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libglib2.0-0 fonts-dejavu-core
    - python -m pip install -r requirements.txt
  script:
    - python -m pytest -q --junitxml=report.xml
```

Le rapport `report.xml` est publié comme rapport JUnit : les tests en échec apparaissent directement dans la merge request.

### Les jobs de construction

- Ils ne démarrent qu'après la réussite des tests (`needs: ["test:linux"]`).
- Sur `main` et `dev`, ils sont **manuels** (bouton ▶ dans le pipeline) et `allow_failure: true` : l'absence d'un runner macOS, par exemple, ne bloque pas le pipeline.
- Sur une étiquette `vX.Y.Z`, ils s'exécutent automatiquement.
- Si un runner n'est pas encore disponible, le job reste « en attente » (*pending*) : ajoutez le runner ou supprimez le job correspondant du `.gitlab-ci.yml`.

### Éviter les pipelines en double

La section `workflow:` lance un pipeline de merge request lorsqu'une MR est ouverte et un pipeline de branche sinon, ce qui évite d'exécuter deux fois les mêmes tests.

## 4. Artefacts et releases

- **Artefacts** : chaque job de construction conserve son exécutable pendant **1 an** (`expire_in: 1 year`), téléchargeable depuis la page du job ou du pipeline (`Build > Pipelines`). Le rapport de tests est conservé 1 semaine.
- **Release** : sur une étiquette `vX.Y.Z`, le job `release` crée une page dans `Deploy > Releases` avec un lien vers l'archive des artefacts de chaque système (`…/-/jobs/artifacts/<tag>/download?job=build:windows`).
- Les liens de release pointent vers des artefacts qui expirent. Pour une conservation illimitée, cochez « Keep artifacts from most recent successful jobs » (`Settings > CI/CD > Artifacts`), ou téléversez les exécutables dans le **Generic Package Registry** du projet (`curl --header "JOB-TOKEN: $CI_JOB_TOKEN" --upload-file … "$CI_API_V4_URL/projects/$CI_PROJECT_ID/packages/generic/iat/$CI_COMMIT_TAG/…"`) et faites pointer les liens de la release vers ces paquets.

> [!NOTE]
> Le mot-clé `release:` s'appuie sur l'image `release-cli`. Sur les versions récentes de GitLab, cet outil est progressivement remplacé par la CLI `glab` (image `registry.gitlab.com/gitlab-org/cli`) ; adaptez l'image du job `release` si l'instance l'exige.

## 5. Branches protégées et étiquettes

Dans `Settings > Repository` :

### Branches protégées (Protected branches)

| Branche | Allowed to merge         | Allowed to push and merge | Force push |
| :------ | :----------------------- | :------------------------ | :--------- |
| `main`  | Maintainers              | No one                    | Non        |
| `dev`   | Developers + Maintainers | No one                    | Non        |

Ainsi, toute modification passe par une merge request (voir [Contribuer](contribuer.md)).

### Étiquettes protégées

`Protected tags` : protégez le motif `v*` (création réservée aux *Maintainers*) pour que seules les personnes habilitées puissent publier une version.

### Branche par défaut

`main` (`Settings > Repository > Branch defaults`). Pensez à cocher « Auto-close referenced issues on default branch ».

## 6. Réglages des merge requests

Dans `Settings > Merge requests` :

- **Merge method** : « Merge commit » (historique lisible des fonctionnalités) ou « Fast-forward » si l'équipe préfère un historique linéaire ;
- **Squash commits when merging** : « Encourage » pour regrouper les petits commits d'une branche ;
- **Merge checks** : cocher « Pipelines must succeed » et « All threads must be resolved » ;
- **Delete source branch** : option cochée par défaut ;
- **Approvals** (si disponible) : au moins une approbation pour les MR vers `main`.

Dans `Settings > CI/CD > General pipelines`, un délai d'expiration (*timeout*) de 1 h suffit ; activez « Auto-cancel redundant pipelines ».

## 7. Publier une nouvelle version

1. Mettez à jour le numéro de version dans `pyproject.toml` (`version`) et dans `src/iat/qt_image_editor.py` (`APP_VERSION`) sur `dev`.
2. Merge request `dev` → `main`, pipeline vert, fusion.
3. Créez l'étiquette sur `main` :

   ```bash
   git switch main && git pull
   git tag -a v1.1.0 -m "Version 1.1.0"
   git push origin v1.1.0
   ```

   (ou `Code > Tags > New tag` dans l'interface web).
4. Le pipeline d'étiquette teste, construit les trois exécutables puis crée la release.
5. Vérifiez les exécutables avec la [liste de vérification](generation-executable.md#8-liste-de-vérification-de-lexécutable).

## 8. Dépannage

| Symptôme                                                                   | Cause / solution                                                                                               |
| :------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------- |
| Job bloqué en *pending* « no runner with tags »                            | Aucun runner actif avec l'étiquette demandée : vérifier `Settings > CI/CD > Runners`                           |
| `qt.qpa.plugin: Could not load the Qt platform plugin`                     | `QT_QPA_PLATFORM=offscreen` absent ou bibliothèques système manquantes (`libegl1`, `libgl1`, `libxkbcommon0`…) |
| `ImportError: libGL.so.1` / `libEGL.so.1`                                  | Installer `libgl1` / `libegl1` dans le conteneur                                                               |
| Texte des captures en carrés                                               | Aucune police dans l'image : installer `fonts-dejavu-core`                                                     |
| `py` introuvable sur le runner Windows                                     | Installer Python avec le lanceur `py`, ou remplacer par le chemin complet de `python.exe`                      |
| Script PowerShell refusé                                                   | Politique d'exécution : `Set-ExecutionPolicy RemoteSigned` pour le compte du runner                            |
| Le binaire Linux ne démarre pas sur un vieux poste (`GLIBC_x.y not found`) | Construire dans une image plus ancienne (ex. `python:3.14-slim-bookworm`)                                      |
