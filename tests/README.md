# Architecture et arborescence du projet

Une organisation rigoureuse du dossier de tests est essentielle pour maintenir la qualité d'une application Python au fil de son évolution.

**Sommaire :**



---

<br />

## 1. Arborescence et structure du répertoire

L'approche standard et la plus évolutive consiste à **séparer le code source des tests** à la racine du projet, tout en miroitant l'architecture du module principal.

```text
mon_projet/
├── src/
│   └── mon_app/
│       ├── __init__.py
│       ├── core.py
│       └── utils.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Fixtures globales pytest
│   ├── unit/                # Tests unitaires rapides
│   │   ├── test_core.py
│   │   └── test_utils.py
│   ├── integration/         # Tests d'intégration (base de données, API externe, UI)
│   │   ├── conftest.py      # Fixtures spécifiques à l'intégration (ex: QApplication)
│   │   └── test_db.py
│   └── fixtures/            # Données de test fixes (fichiers JSON, CSV, mock payloads)
│       └── sample_data.json
├── pyproject.toml           # Configuration pytest, coverage, ruff
└── README.md

```

### Règles de nommage

* Prefixez toujours les fichiers de test par `test_` (ex: `test_core.py`) pour permettre la **découverte automatique par Pytest**.
* Prefixez les fonctions de test par `test_` et nommez-les explicitement selon leur intention : `test_calcul_remise_avec_code_valide()`.

---

## 2. Typologie et catégorisation des tests

Il est crucial de bien isoler les tests selon leur portée et leur temps d'exécution.

* **Tests unitaires (`tests/unit/`)** : Isolés, rapides, sans dépendance externe lente ou instable (pas de réseau, pas de vraie base de données, pas de service tiers). L'usage de `tmp_path` pour valider une sérialisation (JSON, fichiers) reste un test unitaire : ce n'est pas parce qu'un test touche le disque qu'il devient un test d'intégration, tant qu'il reste rapide, déterministe et centré sur une seule responsabilité.
* **Tests d'intégration (`tests/integration/`)** : Valident la communication entre plusieurs composants ou avec des services externes (ex: requêtes SQL, requêtes HTTP réelles ou émulées). Rentrent également dans cette catégorie les tests qui instancient un composant lourd de l'application (fenêtre Qt complète, ORM, client HTTP réel), du fait de leur coût de démarrage et de leurs dépendances à un environnement particulier.
* **Marqueurs Pytest (`pytest.mark`)** : Categorisez vos tests pour exécuter rapidement sous-ensembles spécifiques :

```python
import pytest

@pytest.mark.slow
def test_traitement_lourd():
    ...

@pytest.mark.integration
def test_connexion_bdd():
    ...

@pytest.mark.gui
def test_ouverture_fenetre_principale():
    ...

```

Lancement ciblé via la ligne de commande :
`pytest -m "not slow"` ou `pytest tests/unit/`

Sur un poste sans environnement graphique ou sans PyQt6 installé, exclure les tests d'interface :
`pytest -m "not gui"`

---

## 3. Gestion des fixtures et état (`conftest.py`)

Le fichier `conftest.py` est automatiquement détecté par Pytest et permet de partager du code de préparation sans imports explicites. Un `conftest.py` peut être défini à la racine de `tests/` pour des fixtures globales, et/ou dans chaque sous-dossier (`tests/unit/conftest.py`, `tests/integration/conftest.py`) pour des fixtures propres à cette catégorie de tests.

* **Portée adaptée (`scope`)** : Limitez la portée des fixtures (`function`, `module`, `session`) pour optimiser la vitesse de suite de tests.
* **Clean-up automatique** : Utilisez `yield` au lieu de `return` dans vos fixtures pour garantir la libération des ressources (fermeture de sockets, suppression de fichiers temporaires).

```python
import pytest
import tmpdir

@pytest.fixture(scope="function")
def fichier_temp(tmp_path):
    # Setup
    p = tmp_path / "test.txt"
    p.write_text("donnees")
    yield p
    # Teardown (si nécessaire au-delà du nettoyage automatique tmp_path)

```

### Cas particulier : fixture `QApplication` pour les tests Qt/PyQt

Une application Qt ne tolère qu'**une seule instance de `QApplication` par process**. Ne redéfinissez jamais cette fixture localement dans chaque fichier de test : centralisez-la une bonne fois dans `tests/integration/conftest.py`, avec un `scope="session"`, pour que tous les tests GUI du dossier la partagent sans risque de collision.

```python
# tests/integration/conftest.py
import os
import pytest

# À définir avant toute création de QApplication : permet de lancer les tests
# sans serveur d'affichage (CI, headless).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app

```

---

## 4. Bonnes pratiques de rédaction des tests

### Le pattern AAA (Arrange - Act - Assert)

Chaque test doit être lisible comme une histoire courte structurée en trois phases distinctes :

```python
def test_calcul_prix_ttc():
    # Arrange (Préparation)
    prix_ht = 100.0
    taux_tva = 0.20
    
    # Act (Action)
    resultat = calculer_ttc(prix_ht, taux_tva)
    
    # Assert (Vérification)
    assert resultat == 120.0

```

### Mocks et Isolation

* Utilisez `unittest.mock` ou `pytest-mock` pour isoler le code testé des dépendances externes lourdes ou instables.
* Privilégiez l'injection de dépendances au mocking d'implémentation interne dès que c'est possible.

### Tests de non-régression issus d'un bug

Quand un test naît d'un bug réel constaté en production ou remonté par un utilisateur :

* **Nommez-le d'après le comportement corrigé**, pas d'après le numéro de ticket : `test_export_resize_preserves_recipe`, pas `test_bug_1234`. Le nom du fichier reste compréhensible même une fois le ticket archivé.
* **Rejouez si possible les données réelles** ayant révélé le bug comme fixtures (`tests/fixtures/`), plutôt que des données inventées après coup. Elles documentent le cas concret et protègent spécifiquement contre une régression sur des données de forme identique — un cas rencontré une fois en pratique a plus de chances de se reproduire qu'un cas purement théorique.
* Documentez la cause racine en tête de fichier (docstring de module), pour qu'un futur lecteur comprenne *pourquoi* le test existe sans devoir remonter au ticket ou à l'historique Git.

---

## 5. Outillage et automatisation CI/CD

Une bonne suite de tests repose sur une configuration centralisée et un contrôle automatisé.

### Configuration centralisée (`pyproject.toml`)

Regroupez la configuration des outils sous un même fichier racine :

```toml
[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "gui: marks tests requiring PyQt6 and a Qt platform plugin (offscreen in CI)",
]

[tool.coverage.run]
source = ["src"]
branch = true

```

### Automatisation

* **Couverture de code (`pytest-cov`)** : Mesurez le code exécuté, mais ne cherchez pas le 100 % à tout prix. Ciblez la couverture des branches critiques.
* **Pre-commit hooks & CI** : Intégrez l'exécution rapide des tests unitaires dans vos pipelines GitLab CI ou GitHub Actions à chaque push. Réservez les tests marqués `integration`/`gui` à une étape dédiée (plus lente, éventuellement avec `xvfb` sur les runners Linux sans affichage) plutôt qu'à chaque commit.
