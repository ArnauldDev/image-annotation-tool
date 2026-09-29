<!--
  File Name: contribuer.md
  Description: Guide de contribution au projet Image Annotation Tool (branches, commits, conventions de code, tests).
  Developer: ArnauldDev
  Created Date: 2026-09-23
  Last Modified: 2026-09-26
-->

# Contribuer au projet

[← Retour au README](../README.md)

Merci de votre intérêt pour Image Annotation Tool ! Ce guide rassemble les règles communes pour que le code reste lisible, testé et cohérent. Commencez par installer l'[environnement de développement](environnement-developpement.md).

## Sommaire

- [Contribuer au projet](#contribuer-au-projet)
  - [Sommaire](#sommaire)
  - [1. Signaler un problème ou proposer une idée](#1-signaler-un-problème-ou-proposer-une-idée)
  - [2. Organisation des branches](#2-organisation-des-branches)
  - [3. Messages de commit](#3-messages-de-commit)
  - [4. Conventions de code](#4-conventions-de-code)
    - [En-tête de fichier](#en-tête-de-fichier)
    - [Docstring des fonctions](#docstring-des-fonctions)
    - [Langues](#langues)
    - [Apparence : jamais de couleur en dur](#apparence--jamais-de-couleur-en-dur)
    - [Autres règles](#autres-règles)
  - [5. Tests](#5-tests)
  - [6. Compatibilité de la recette JSON](#6-compatibilité-de-la-recette-json)
  - [7. Documentation](#7-documentation)
  - [8. Liste de vérification d'une merge request](#8-liste-de-vérification-dune-merge-request)
  - [9. Politique concernant l'IA](#9-politique-concernant-lia)

---

## 1. Signaler un problème ou proposer une idée

Le fichier `ROADMAP.md` contient la feuille de route du projet. Vous y trouverez les fonctionnalités prévues, les améliorations à apporter et les priorités de développement. N'hésitez pas à le consulter avant de proposer une idée ou de signaler un problème.

Ouvrez un ticket (*issue*) sur le [dépôt GitLab](https://src.koda.cnrs.fr/cbi-plateau-mecatronique/ressources/image-annotation-tool/-/issues) en précisant :

- ce que vous avez fait, ce que vous attendiez et ce qui s'est produit ;
- votre système (Windows, macOS, Linux), la version de l'application (`Aide > À propos`) et le thème utilisé ;
- si possible une capture d'écran et la recette `-iat.json` concernée.

## 2. Organisation des branches

| Branche              | Rôle                                                                          | Protection                          |
| :------------------- | :---------------------------------------------------------------------------- | :---------------------------------- |
| `main`               | Version stable, publiée ; chaque version est marquée d'une étiquette `vX.Y.Z` | Protégée : merge request uniquement |
| `dev`                | Intégration des développements en cours                                       | Protégée : merge request uniquement |
| `feature/…`, `fix/…` | Une branche par tâche, créée depuis `dev`                                     | Libre                               |

Déroulement type :

```bash
git switch dev
git pull
git switch -c feature/export-presets        # nom court et explicite

# ... développement, tests, commits ...

git push -u origin feature/export-presets
```

1. Ouvrez une **merge request** de `feature/…` vers **`dev`**.
2. Le pipeline CI doit être vert (voir [GitLab CI/CD](gitlab-ci-cd.md)) et une relecture est demandée.
3. Lorsque `dev` est stable, une merge request **`dev` → `main`** prépare la version, puis une étiquette `vX.Y.Z` déclenche la construction des exécutables.

## 3. Messages de commit

Le dépôt utilise un préfixe indiquant la nature du changement, suivi d'une description courte :

| Préfixe     | Usage                                             | Exemple tiré de l'historique                                                    |
| :---------- | :------------------------------------------------ | :------------------------------------------------------------------------------ |
| `feat:`     | Nouvelle fonctionnalité ou évolution              | `feat: add rotation feature for loupe and update toolbar label`                 |
| `fix:`      | Correction de bogue                               | `fix: update color change for selected shapes and enlarge current color swatch` |
| `bug:`      | Correction d'un bogue bloquant (erreur, plantage) | `bug: NameError: name 'QToolBar' is not defined`                                |
| `docs:`     | Documentation uniquement                          | `docs: split README into docs/`                                                 |
| `test:`     | Ajout ou correction de tests                      | `test: cover legacy single loupe recipes`                                       |
| `refactor:` | Restructuration sans changement de comportement   | `refactor: extract theme loader`                                                |
| `ci:`       | Pipeline, build, packaging                        | `ci: add macOS build job`                                                       |

Conseils :

- une ligne de titre de 72 caractères maximum, à l'impératif (« add », « ajoute ») ;
- un commit = une modification cohérente ; évitez les commits « fourre-tout » ;
- détaillez si besoin dans le corps du message (pourquoi, et non seulement quoi).

## 4. Conventions de code

### En-tête de fichier

Chaque fichier source commence par un en-tête :

```python
#!/usr/bin/env python3
# File Name: image_processor.py
# Description: Moteur de traitement d'image et recette JSON (annotations, loupes, export).
# Developer: ArnauldDev
# Created Date: 2026-09-08
# Last Modified: 2026-09-23
```

Les fichiers Markdown utilisent le même en-tête dans un commentaire HTML (`<!-- … -->`). Mettez à jour `Last Modified` à chaque modification.

### Docstring des fonctions

```python
def export_notification_enabled(self) -> bool:
    """
    Description: Whether the notification window is shown after an export (enabled by default).

    @author ArnauldDev
    @created 2026-09-23
    @modified 2026-09-23
    @version 1

    @param name     (une ligne par paramètre)
    @returns
    """
```

Incrémentez `@version` et mettez à jour `@modified` à chaque modification de la fonction.

### Langues

| Élément                                      | Langue                                                    |
| :------------------------------------------- | :-------------------------------------------------------- |
| Identifiants (variables, fonctions, classes) | Anglais                                                   |
| Commentaires dans le code                    | Français                                                  |
| Textes de l'interface                        | Français (clé des traductions `translations/<code>.json`) |
| Documentation                                | Français                                                  |

Les textes affichés à l'utilisateur passent par la fonction de traduction `tr("…")` avec le texte français comme clé, afin de pouvoir être traduits (voir [Configuration](configuration.md#6-langues-et-traductions)).

### Apparence : jamais de couleur en dur

Aucune couleur d'interface ne doit être codée dans le Python (`setStyleSheet("color: #…")`, `QColor` pour un widget…). L'apparence est définie **uniquement** dans les thèmes `themes/*.qss` :

- utilisez un `objectName` ou un état (`:checked`, `:disabled`) et stylez-le dans **les trois thèmes** (`cbi`, `clair`, `sombre`) ;
- pour les icônes, utilisez les directives `iat-icon-color`, `iat-icon-checked-color` et `url(@icons/<nom>.svg)` ;
- les icônes SVG monochromes utilisent le gris `#444444`, remplacé à la volée par la couleur du thème.

Les couleurs des **annotations** (contenu de l'image) ne sont pas concernées : elles font partie de la recette.

### Autres règles

- **Espaces de coordonnées** : les champs de l'interface sont en pixels de l'**aperçu** ; la recette JSON est en pixels de l'**image originale** (facteur `preview_scale`).
- **Calques** : `layer_order` contient des jetons `annotation:<index>` et `loupe:<id>`, du premier plan vers l'arrière-plan.
- **Accrochage à la grille** : uniquement lorsque `Ctrl` est maintenu.
- Une nouvelle fonctionnalité expérimentale peut être protégée par un drapeau `FEATURE_*` dans `AppConfig` (voir [Configuration](configuration.md#drapeaux-de-fonctionnalités-feature_)).
- Toute nouvelle ressource lue à l'exécution doit être ajoutée aux `datas` du `.spec` (voir [Génération de l'exécutable](generation-executable.md)).

## 5. Tests

- **Tout nouveau comportement s'accompagne d'un test** dans `tests/unit/` (un fichier par thème fonctionnel) ; un bogue corrigé reçoit un test qui le reproduit.
- Le rendu du moteur se teste dans `test_image_processor.py` / `test_multi_loupe.py` ; l'interface dans `test_qt_editor.py` / `test_ui_configuration.py` ; la configuration dans `test_config.py`.
- Ne jamais écrire dans les vraies préférences : `tests/conftest.py` isole déjà `QSettings` et les fichiers récents.
- Un test qui charge un `.env` doit utiliser `monkeypatch.setenv`, puis restaurer la configuration (`monkeypatch.undo()` et `update_config_in_place(AppConfig())`).
- Avant de pousser :

  ```bash
  python -m pytest -q
  ```

- Pour un changement visuel (thème, menu, panneau), vérifiez les captures du harness local `tools/ui_harness.py` dans les trois thèmes.

## 6. Compatibilité de la recette JSON

Les recettes `-iat.json` sont conservées à côté des images, parfois pendant des années. **Un fichier produit par une version précédente doit toujours se charger.**

- Un nouveau champ doit avoir une **valeur par défaut** dans `from_dict()` (`data.get("champ", défaut)`).
- Ne renommez pas et ne supprimez pas un champ existant ; si un format change, convertissez l'ancien format au chargement (exemples : `"loupe"` → `"loupes"`, `trapezoid` à 2 valeurs → 4 valeurs).
- Ajoutez un test avec une recette « ancienne » dans `tests/fixtures/` ou dans le test lui-même.
- Mettez à jour [Format de la recette JSON](format-recette-json.md).

## 7. Documentation

- La documentation est en **français**, dans `README.md` (présentation) et `docs/` (détails).
- Une nouvelle fonctionnalité visible est décrite dans le [Guide utilisateur](guide-utilisateur.md) ; un nouveau paramètre dans [Configuration](configuration.md).
- Les captures d'écran sont rangées dans `docs/images/`.

## 8. Liste de vérification d'une merge request

- [ ] Branche créée depuis `dev`, merge request vers `dev`.
- [ ] Messages de commit préfixés (`feat:`, `fix:`, `bug:`…).
- [ ] En-têtes et docstrings à jour (`Last Modified`, `@modified`, `@version`).
- [ ] Aucune couleur d'interface en dur ; les trois thèmes sont à jour si besoin.
- [ ] Textes d'interface en français, passés par `tr()`.
- [ ] Tests ajoutés, `python -m pytest -q` vert, pipeline CI vert.
- [ ] Anciennes recettes JSON toujours lisibles.
- [ ] Documentation mise à jour.

## 9. Politique concernant l'IA

Les contributions générées par IA ou via vibe coding sont acceptées, à condition que le code soit vérifié, fonctionnel et documenté. Merci de préciser dans votre PR si vous avez utilisé des assistants IA.
