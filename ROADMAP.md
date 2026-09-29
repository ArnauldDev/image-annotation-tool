# Roadmap & Backlog : Image Annotation Tool (IAT)

> **Instructions pour les agents IA :** Lisez le fichier `AGENTS.md` à la racine avant de modifier ce fichier ou de commencer une tâche.

## 🎯 Next (Priorité Haute - À traiter par l'IA)

> L'agent doit prendre la première tâche non cochée dans cette section.

- [ ] **[TASK-006]** Outil Annotation : Remplissage des formes (Rectangle/Cercle)
  - **Context:** Permettre de colorer le fond des formes géométriques.
  - **Spec:** Ajouter une propriété au panneau de droite, active pour les outils rectangle et cercle, permettant le remplissage de la forme avec choix de couleur. Synchroniser l'état (grisé/actif) en fonction de l'outil.
  - **Acceptance:** La couleur de remplissage est modifiable via l'UI et sauvegardée dans le fichier JSON.

- [ ] **[TASK-007]** Menu Aide : "Aide sur les outils" non bloquante
  - **Context:** Permettre à l'utilisateur de garder l'aide ouverte pendant qu'il travaille.
  - **Spec:** Remplacer la boîte de dialogue modale par une fenêtre non modale (qui reste au premier plan). Changer le bouton "Ok" en "Fermer".
  - **Acceptance:** On peut interagir avec la fenêtre principale de l'application pendant que la fenêtre "Aide sur les outils" est ouverte.

## 🔄 In Progress

- [ ] **[TASK-008]** Test de l'exécutable construit (PyQt6.QtSvg, themes)
  - **Assigned:** Human/Agent

## 💡 Ideas & Vibe Backlog (Brainstorming)

> Tâches non spécifiées, à affiner avant passage dans "Next". L'agent IA ne doit pas traiter cette section de son propre chef.

- [ ] Outil Transformation : Ajouter les boutons (slider) de réglages de luminosité et de contraste, dans le panneau de droite.
- [ ] Outil Loupe : Toujours afficher les boutons + et - pour la rotation libre (corriger la désactivation à +/- 180°).
- [ ] Exporter : Ne pas permettre de saisir une valeur supérieure à la largeur ou hauteur maximale de l'image source.
- [ ] Exporter : Ajouter l'option de marge blanche automatique autour des objets débordants et mettre à jour les dimensions en temps réel.
- [ ] Documentation : Documenter la contribution au projet, la configuration CI/CD GitLab/Koda et l'ajout d'un serveur runner externe.
- [ ] Permettre de zoomer sur l'image avec la molette de la souris ou Ctrl + molette.
- [ ] Créer un thème pour le RdEI (Réseau des Électroniciens et Instrumentalistes).
- [ ] Ajouter la traduction de l'interface en espagnol (es).
- [ ] Ajouter la traduction de l'interface en allemand (de).

## ✅ Done

- [x] **[TASK-000]** Initialisation du projet et structure de base.
  - **Exemple de tâche pour l'interface :** Permettre de positionner les icônes de la barre d'outils à gauche, en haut ou en bas.
  - *(Les tâches historiques validées sont archivées dans le fichier `TASKS.md`, mais non versionnées ici pour ne pas alourdir le suivi des tâches actuelles.)*

- [x] **[TASK-001]** Alignement et distribution des objets
  - **Context:** Intégrer de manière intuitive un outil d'alignement des objets dans l'image.
  - **Spec:** Créer un menu contextuel (clic droit) après la sélection d'un ou plusieurs objets, permettant de les aligner et de les distribuer (vertical/horizontal) par rapport à la grille ou entre eux.
  - **Acceptance:** Le menu contextuel s'affiche au clic droit sur une sélection multiple ; les objets sont visuellement alignés selon l'option choisie.

- [x] **[TASK-002]** Outil Annotation : Copier/Coller les propriétés
  - **Context:** Faciliter la duplication des styles (couleur, épaisseur) entre objets.
  - **Spec:** Ajouter une option "Propriétés" au clic droit pour copier les propriétés de l'objet sélectionné. Ajouter une option "Coller les propriétés" au clic droit sur un autre objet pour appliquer ces propriétés.
  - **Acceptance:** Le collage applique correctement l'épaisseur du trait, la couleur et le rayon (si applicable) au nouvel objet.

- [x] **[TASK-003]** Amélioration de la sélection des lignes
  - **Context:** La sélection des objets "ligne" crée souvent un nouvel objet au lieu de sélectionner l'existant.
  - **Spec:** Améliorer la zone de détection (hitbox) ou le comportement du clic pour les lignes.
  - **Acceptance:** Un clic sur une ligne existante la sélectionne systématiquement au lieu de démarrer un nouveau dessin.

- [x] **[TASK-004]** Modèle & Persistence JSON : Corriger la perte de données au rechargement et à la mise à jour de l'export
  - **Context:** Lors de la réouverture d'une image possédant un fichier JSON, certaines données (annotations, loupes, transformations) ne sont pas intégralement restaurées en mémoire. Si l'utilisateur modifie ensuite la taille de l'export ou déplace un objet, l'application sauvegarde cet état partiel et écrase définitivement le reste du fichier JSON.
  - **Spec:**
    - Audit du cycle de vie du JSON : vérifier la fonction de lecture/chargement (`load_json`) et s'assurer que toutes les clés (`annotations`, `loupes`, `crop`, `trapezoid`, `export`, etc.) sont correctement restaurées dans l'état applicatif au démarrage.
    - S'assurer que la modification des paramètres d'exportation (`width`, `height`) met à jour la section `"export"` du JSON **sans réinitialiser ni omettre** les autres attributs.
    - Écrire/mettre à jour un test unitaire simulant le cycle complet : *Chargement d'un JSON complet $\rightarrow$ Modification de l'export / déplacement d'un objet $\rightarrow$ Sauvegarde $\rightarrow$ Relecture $\rightarrow$ Assertion sur l'intégralité des champs*.
  - **Acceptance:**
    - Aucune donnée (annotations, loupes, paramètres d'image) n'est perdue lors de la réouverture d'un fichier JSON existant.
    - La modification de la taille d'export conserve l'intégralité des autres données du JSON.
    - Le test unitaire automatisé validant ce cycle complet passe avec succès via `pytest`.

- [x] **[TASK-005]** Modèle JSON & Calques : Normaliser l'identifiant `id` des annotations et sécuriser `layer_order`
  - **Context:** Le fichier JSON utilise un `id` numérique pour les loupes (`"loupe:1"` dans `layer_order`), mais utilise encore l'index du tableau pour les annotations (`"annotation:0"`). Cela rend l'ordre des calques instable lors de la suppression d'une annotation.
  - **Spec:**
    - Ajouter un champ `"id"` (entier incrémental : `1`, `2`, `3`...) à chaque objet du tableau `annotations`.
    - Mettre à jour la logique de `layer_order` pour que les annotations utilisent leur `id` (`"annotation:<id>"`) et non leur index (`"annotation:<index>"`).
    - Un nouvelle objet ajouter sera placer en haut de la pile (`layer_order`) par défaut.
    - Assurer la rétrocompatibilité : à la lecture d'un ancien JSON (où les annotations n'ont pas d'id), attribuer un `id` automatiquement et convertir les jetons `annotation:<index>` de `layer_order` vers les nouveaux `annotation:<id>`.
  - **Acceptance:**
    - Chaque annotation sauvegardée dans le JSON possède une clé `"id"` entière.
    - `layer_order` ne contient plus aucun index relatif mais uniquement des références par ID (`"annotation:1"`, `"loupe:2"`).
    - La suppression d'une annotation ne corrompt pas l'ordre des autres calques dans `layer_order`.
    - Un test unitaire valides le chargement d'un ancien JSON et sa migration vers le nouveau format sans perte de données.
