# Changelog

Toutes les modifications notables apportées à ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

> **Note :** l'historique des tâches validées antérieures à ce fichier est archivé dans
> `TASKS.md` et n'est volontairement pas repris ici, afin de ne pas alourdir le suivi
> des évolutions courantes.

## [1.0.0] - 2026-09-28

### Ajouté

- **[TASK-005]** Modèle JSON & Calques : Normaliser l'identifiant `id` des annotations et sécuriser `layer_order`
  - **Contexte :** Le fichier JSON utilise un `id` numérique pour les loupes (`"loupe:1"` dans `layer_order`), mais utilise encore l'index du tableau pour les annotations (`"annotation:0"`). Cela rend l'ordre des calques instable lors de la suppression d'une annotation.
  - **Spécification :**
    - Ajouter un champ `"id"` (entier incrémental : `1`, `2`, `3`...) à chaque objet du tableau `annotations`.
    - Mettre à jour la logique de `layer_order` pour que les annotations utilisent leur `id` (`"annotation:<id>"`) et non leur index (`"annotation:<index>"`).
    - Un nouvelle objet ajouter sera placer en haut de la pile (`layer_order`) par défaut.
    - Assurer la rétrocompatibilité : à la lecture d'un ancien JSON (où les annotations n'ont pas d'id), attribuer un `id` automatiquement et convertir les jetons `annotation:<index>` de `layer_order` vers les nouveaux `annotation:<id>`.
  - **Critères d'acceptation :**
    - Chaque annotation sauvegardée dans le JSON possède une clé `"id"` entière.
    - `layer_order` ne contient plus aucun index relatif mais uniquement des références par ID (`"annotation:1"`, `"loupe:2"`).
    - La suppression d'une annotation ne corrompt pas l'ordre des autres calques dans `layer_order`.
    - Un test unitaire valides le chargement d'un ancien JSON et sa migration vers le nouveau format sans perte de données.

## [1.0.0] - 2026-09-27

### Ajouté

- **[TASK-001] Alignement et distribution des objets**
  - *Contexte :* intégration d'un outil d'alignement des objets dans l'image, de manière intuitive.
  - *Spécification :* ajout d'un menu contextuel (clic droit) après sélection d'un ou plusieurs objets, permettant de les aligner et de les distribuer (verticalement/horizontalement) par rapport à la grille ou entre eux.
  - *Critères d'acceptation :* le menu contextuel s'affiche au clic droit sur une sélection multiple ; les objets sont visuellement alignés selon l'option choisie.

- **[TASK-002] Outil Annotation : copier/coller les propriétés**
  - *Contexte :* faciliter la duplication des styles (couleur, épaisseur) entre objets.
  - *Spécification :* ajout d'une option « Propriétés » au clic droit pour copier les propriétés de l'objet sélectionné, et d'une option « Coller les propriétés » au clic droit sur un autre objet pour les appliquer.
  - *Critères d'acceptation :* le collage applique correctement l'épaisseur du trait, la couleur et le rayon (si applicable) au nouvel objet.

### Corrigé

- **[TASK-003] Amélioration de la sélection des lignes**
  - *Contexte :* la sélection des objets « ligne » créait souvent un nouvel objet au lieu de sélectionner l'existant.
  - *Spécification :* amélioration de la zone de détection (hitbox) et du comportement du clic pour les lignes.
  - *Critères d'acceptation :* un clic sur une ligne existante la sélectionne systématiquement, au lieu de démarrer un nouveau dessin.

- **[TASK-004] Modèle & persistance JSON : correction de la perte de données au rechargement et à la mise à jour de l'export**
  - *Contexte :* lors de la réouverture d'une image possédant un fichier JSON, certaines données (annotations, loupes, transformations) n'étaient pas intégralement restaurées en mémoire. Toute modification ultérieure de la taille d'export ou déplacement d'un objet entraînait la sauvegarde de cet état partiel, écrasant définitivement le reste du fichier JSON.
  - *Spécification :*
    - Audit du cycle de vie du JSON : vérification de la fonction de lecture/chargement (`load_json`) afin de s'assurer que toutes les clés (`annotations`, `loupes`, `crop`, `trapezoid`, `export`, etc.) sont correctement restaurées dans l'état applicatif au démarrage.
    - Garantie que la modification des paramètres d'exportation (`width`, `height`) met à jour la section `"export"` du JSON **sans réinitialiser ni omettre** les autres attributs.
    - Écriture/mise à jour d'un test unitaire simulant le cycle complet : chargement d'un JSON complet → modification de l'export ou déplacement d'un objet → sauvegarde → relecture → assertion sur l'intégralité des champs.
  - *Critères d'acceptation :*
    - Aucune donnée (annotations, loupes, paramètres d'image) n'est perdue lors de la réouverture d'un fichier JSON existant.
    - La modification de la taille d'export conserve l'intégralité des autres données du JSON.
    - Le test unitaire automatisé validant ce cycle complet passe avec succès via `pytest`.

## [0.1.0] - 2026-08-29

### Ajouté

- **[TASK-000] Initialisation du projet et structure de base.**
  - *Exemple de tâche pour l'interface :* permettre de positionner les icônes de la barre d'outils à gauche, en haut ou en bas.
  - *(Les tâches historiques validées antérieures sont archivées dans le fichier `TASKS.md`, mais non versionnées ici pour ne pas alourdir le suivi des tâches actuelles.)*
