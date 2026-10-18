# Roadmap & Backlog : Image Annotation Tool (IAT)

> **Instructions pour les agents IA :** Lisez le fichier `AGENTS.md` à la racine avant de modifier ce fichier ou de commencer une tâche.

## 🎯 Next (Priorité Haute - À traiter par l'IA)

> L'agent doit prendre la première tâche non cochée dans cette section.

- [ ] **[TASK-019]** Outil Annotation : Remplissage des formes (Rectangle/Cercle)
  - **Context:** Permettre de colorer le fond des formes géométriques.
  - **Spec:** Ajouter une propriété au panneau de droite, active pour les outils rectangle et cercle, permettant le remplissage de la forme avec choix de couleur. Synchroniser l'état (grisé/actif) en fonction de l'outil.
  - **Acceptance:** La couleur de remplissage est modifiable via l'UI et sauvegardée dans le fichier JSON.

- [ ] **[TASK-020]** Menu Aide : "Aide sur les outils" non bloquante
  - **Context:** Permettre à l'utilisateur de garder l'aide ouverte pendant qu'il travaille.
  - **Spec:** Remplacer la boîte de dialogue modale par une fenêtre non modale (qui reste au premier plan). Changer le bouton "Ok" en "Fermer".
  - **Acceptance:** On peut interagir avec la fenêtre principale de l'application pendant que la fenêtre "Aide sur les outils" est ouverte.

- [ ] **[TASK-021]** Interface de la fonction de réglage
  - **Context:** Permettre à l'utilisateur de régler les paramètres de l'image de manière intuitive.
  - **Spec:**
    - Remplacer le bloc de contrôle précédent par un bouton de mode de réglage trapézoïdal dédié, lorsque la fonctionnalité n'est pas activée.
    - Lorsque l'utilisateur active le mode de réglage trapézoïdal, l'aspect trapézoïdal de l'image peut être ajusté. Pour cela l'interface doit alors afficher les contrôles appropriés pour permettre ces ajustements dans le panneau de droite. Une image (..\src\iat\resources\icons\trapezoidal_overlay_control.svg) superposer au centre de l'image, représentant les contrôles (une demi sphère et des flèches de direction autour de celle-ci) de l'interface doit illustrer ces contrôles de manière claire et intuitive.
    - Ajouter le contrôle au clavier avec les touches de direction (flèches haut/bas/gauche/droite) pour ajuster l'aspect trapézoïdal de l'image.
    - La touche HOME réinitialise l'aspect trapézoïdal de l'image à sa valeur par défaut.
    - Les modifications doivent être visibles en temps réel.
  - **Acceptance:** L'utilisateur peut ajuster les paramètres trapézoïdaux de l'image via l'interface du menu de droite, ainsi qu'avec les touches de direction, et voir les changements immédiatement.

- [ ] **[TASK-022]** Intégrer les différentes polices (`..\src\iat\resources\fonts`) dans l'outil d'annotation pour le texte des étiquettes.
  - **Context:** Permettre à l'utilisateur de choisir parmi différentes polices pour le texte des étiquettes dans l'outil d'annotation.
  - **Spec:**
    - Intégrer toutes les polices disponibles dans le dossier `..\src\iat\resources\fonts`.
    - Ajouter une option dans le panneau de droite pour sélectionner la police du texte des étiquettes.
  - **Acceptance:** L'utilisateur peut choisir la police du texte des étiquettes parmi celles intégrées.

## 🔄 In Progress

Rédiger une spécification détaillée pour chaque tâche en cours de développement.

## 💡 Ideas & Vibe Backlog (Brainstorming)

> Tâches non spécifiées, à affiner avant passage dans "Next". L'agent IA ne doit pas traiter cette section de son propre chef.

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

- [ ] **[TASK-006]** Test de l'exécutable construit (PyQt6.QtSvg, themes)
  - **Assigned:** Human/Agent
  - **Context:** Vérifier que l'exécutable fonctionne correctement avec les modules PyQt6.QtSvg et les thèmes appliqués.
  - **Spec:** Lancer l'exécutable et tester les fonctionnalités principales de l'application, en particulier celles dépendant de PyQt6.QtSvg et des thèmes.
  - **Acceptance:** L'exécutable se lance sans erreur et les fonctionnalités liées à PyQt6.QtSvg et aux thèmes fonctionnent comme prévu.
  - **Notes:** Il est important de vérifier que toutes les dépendances nécessaires sont installées et que les thèmes sont correctement appliqués lors du test.

- [x] **[TASK-007]** Outil Transformation : Ajouter les boutons (slider) de réglages de luminosité et de contraste, dans le panneau de droite.
  - **Context:** Permettre à l'utilisateur de régler la luminosité et le contraste de l'image directement depuis le panneau de droite.
  - **Spec:** Ajouter des sliders pour la luminosité et le contraste dans le panneau de droite. Les valeurs doivent être appliquées en temps réel sur l'image.
  - **Acceptance:** L'utilisateur peut ajuster la luminosité et le contraste via les sliders, et les modifications sont visibles immédiatement sur l'image.

- [x] **[TASK-008]** Mettre les préréglages en premier élément des Options de l'outil Export ("Exporter l'image").
  - **Context:** Faciliter l'accès rapide aux préréglages lors de l'exportation d'une image.
  - **Spec:** Déplacer les préréglages pour qu'ils apparaissent en premier dans la liste des options de l'outil Export.
  - **Acceptance:** Les préréglages sont toujours affichés en premier dans l'outil Export.

- [x] **[TASK-009]** Ajouter de raccourcis clavier quand un objet est sélectionné, afin de permettre le déplacement rapide avec les flèches directionnelles haut et bas lorsque l'on maintient la touche Ctrl.
  - **Context:** Faciliter le déplacement rapide des objets sélectionnés dans la liste des objets.
  - **Spec:** Ajouter des raccourcis clavier pour déplacer l'objet sélectionné vers le haut ou le bas dans la liste lorsqu'on maintient la touche Ctrl et utilise les flèches directionnelles haut et bas.
  - **Acceptance:** L'utilisateur peut déplacer les objets sélectionnés dans la liste des objets à gauche en utilisant les raccourcis clavier spécifiés.

- [x] **[TASK-010]** Dans l'outil Transformation, une zone de rognagage peut déjà avoir été tracée, si l'utilisateur en trace une nouvelle et souhaite abandonner l'opération avant d'appliquer le nouveau rognage, il peut annuler l'action sans que le rognage précédent soit supprimé. Pour cela, il peut appuyer sur la touche ESC ou faire un clic droit et cliquer sur "Supprimer" dans le menu contextuel.
  - **Context:** Permettre à l'utilisateur d'annuler un rognage en cours sans écraser le rognage précédent.
  - **Spec:** Intercepter la touche ESC et le clic droit "Supprimer" pour réinitialiser le rognage en cours sans l'appliquer.
  - **Acceptance:** L'utilisateur peut annuler un rognage en cours via ESC ou le menu contextuel, et le rognage n'est pas appliqué.

- [x] **[TASK-011]** Dans l'outil loupe, ajouter un slider pour permettre le réglage de la luminosité indépendant du niveau de luminosité global.
  - **Context:** L'utilisateur souhaite ajuster la luminosité de l'image affichée dans l'outil loupe sans affecter le niveau de luminosité global de l'image.
  - **Spec:** Ajouter un slider dans l'outil loupe permettant de régler la luminosité locale de l'image affichée dans la loupe.
  - **Acceptance:** L'utilisateur peut ajuster la luminosité de l'image dans l'outil loupe indépendamment du niveau de luminosité global.

- [x] **[TASK-012]** Ajout d'une nouvelle fonction "numérotation" de l'outil "Cercle". Créer un bouton qui sera uniquement activable lorsque l'on sélectionne l'outil "Cercle", permettant d'ajouter un numéro avec incrémentation automatique dans un cercle sur l'image. Il doit être possible de positionner le cercle à l'endroit souhaité sur l'image par un simple clic gauche de la souris, et le numéro doit s'incrémenter automatiquement à chaque ajout. Les fonctions optionnelles de cette nouvelle fonction de l'outil cercle, incluent un bouton d'activation  de la numérotation, la valeur actuelle du compteur (afficher la valeur actuelle du compteur lorsque l'option "Cercle" est sélectionnée est affichée dans l'interface), ainsi qu'un bouton "RAZ", afin de donner à l'utilisateur. Dans ce mode de l'option "Cercle", la proportion du cercle reste constante (cercle parfait), et la couleur du fond est identique à la couleur du fond des étiquettes pou permettre une intégration visuelle cohérente avec un fond sombre et une couleur de police blanche. L'utilisateur a la possibilité de personnaliser l'apparence du cercle, épaisseur du contour réglable, couleur du bord réglables individuellement.
  - **Context:** Permettre à l'utilisateur d'annoter l'image avec des numéros incrémentés automatiquement.
  - **Spec:**
    - Ajouter de nouvelles fonctionnalités à l'outil d'annotation de l'outil "Cercle" avec un numéro à l'intérieur.
    - Le numéro s'incrémente automatiquement à chaque ajout. Un nouveau champs dans le fichier JSON de configuration doit être ajouté pour stocker la valeur actuelle du compteur pour les objets de type "Cercle".
    - Permettre de réinitialiser le compteur.
    - Permettre de personnaliser l'apparence du cercle : épaisseur et couleur du contour.
  - **Acceptance:** L'utilisateur peut ajouter des numéros incrémentés dans des cercles sur l'image, réinitialiser le compteur et personnaliser l'apparence des cercles.

- [x] **[TASK-013]** Dans l'outil annotation, lors du dessin d'un rectangle ou d'un cercle, lorsque l'on reprend le dessin, associer correctement la fonction permettant avec le maintien de la touche Shift de créer une forme parfaitement proportionnée.
  - **Context:** Lors du dessin d'un rectangle ou d'un cercle, l'utilisateur souhaite pouvoir maintenir la touche Shift pour créer une forme parfaitement proportionnée, mais cette fonctionnalité ne fonctionne pas correctement.
  - **Spec:** Lors du dessin d'un rectangle ou d'un cercle, si la touche Shift est maintenue, la forme doit être contrainte pour être parfaitement proportionnée (carré pour le rectangle, cercle pour le cercle).
  - **Acceptance:** Lorsqu'un utilisateur dessine un rectangle ou un cercle en maintenant la touche Shift, la forme résultante est parfaitement proportionnée.
  - **Résolu:** la contrainte Shift est associée à toutes les gestuelles des outils Rectangle/Cercle — dessin (dès la pression), reprise du tracé par-dessus une forme existante, redimensionnement par poignées, et réapplication au relâchement si Shift est maintenu (`tests/unit/test_shift_shape_constraint.py`).

- [x] **[TASK-014]** Lors de l'utilisation de la fonction "numérotation" de l'outil "Cercle", activer "Rayon" dans le volet de droite et utiliser le rayon "stroke_width" pour déterminer la taille des cercles numérotés.
  - **Context:** L'utilisateur doit pouvoir modifier le paramètre qui détermine la taille des cercles numérotés, la taille du rayon "stroke_width" est utilisée et peux être modifier dynamiquement lorsqu'il utilise la fonction "numérotation" de l'outil "Cercle". Si le bouton "numérotation" est désactivé, l'option "Rayon" doit-être également désactivée.
  - **Spec:** Activer "Rayon" dans le volet de droite et utiliser le rayon "stroke_width" pour déterminer la taille des cercles numérotés.
  - **Acceptance:** Les cercles numérotés ont une taille correspondant au rayon "stroke_width" défini dans le volet de droite.
  - **Résolu:** le spin « Rayon » du volet de droite pilote le rayon (en px d'aperçu) des cercles numérotés ; il n'est actif pour l'outil Cercle qu'en mode « Numérotation » (désactivé sinon) et conserve son sens « arrondi des coins » pour Rectangle/Étiquette. La valeur 0 = rayon par défaut (24 px, diamètre historique 48 px) pour rester rétrocompatible. Le réglage s'applique aux prochains cercles et redimensionne en temps réel le cercle numéroté sélectionné (centre et proportion préservés, contour toujours piloté par « Épaisseur »). La taille reste sérialisée via la géométrie (`x1..y2`) de la recette JSON (`tests/unit/test_circle_numbering.py`).

- [x] **[TASK-015]** Lorsque une image est chargée et qu'aucun outil n'est sélectionné, permettre de maintenir le bouton gauche de la souris pour sélectionner plusieurs objets de l'image. Identique à sélectionner des objets dans le menu de gauche.
  - **Context:** L'utilisateur souhaite pouvoir sélectionner plusieurs objets sur l'image en complément de la sélection via le menu de gauche, permet la sélection multiple directement sur l'image sans avoir à passer par le menu de gauche.
  - **Spec:** Lorsqu'aucun outil n'est sélectionné, maintenir le bouton gauche de la souris et faire glisser pour créer une zone de sélection englobant plusieurs objets.
  - **Acceptance:** L'utilisateur peut sélectionner plusieurs objets en maintenant le bouton gauche de la souris et en traçant une zone de sélection sur l'image.
  - **Résolu:** en mode « Déplacer », la pression dans le vide démarre une sélection par rectangle caoutchouc (marquee) ; le relâchement sélectionne les objets (annotations et loupes) dont la boîte englobante intersecte la zone. Sans modificateur la sélection est remplacée, avec Maj elle est étendue, avec Ctrl chaque objet intersecté est basculé — la même sémantique que la sélection multiple du menu de gauche (synchro via `item_selected`). Un clic sans glisser désélectionne, comme auparavant. Le glisser-déposer d'un objet existant et les outils de dessin ne sont pas affectés (`tests/unit/test_editing_features.py`).

- [x] **[TASK-016]** Ajouter dans le menu fichier une option pour ouvrir le dossier de l'image actuelle.
  - **Context:** Faciliter l'accès rapide au dossier contenant l'image actuellement ouverte.
  - **Spec:**
    - Ajouter une option "Ouvrir le dossier de l'image" dans le menu Fichier. Cette option doit ouvrir le gestionnaire de fichiers (Explorateur de fichiers) à l'emplacement de l'image.
    - Y associer un raccourci clavier pour ouvrir le dossier de l'image actuelle (par exemple Shift+O).
  - **Acceptance:** L'utilisateur peut ouvrir le dossier de l'image actuelle directement depuis le menu Fichier, ou via le raccourci clavier associé.

- [x] **[TASK-017]** Lorsque une nouvelle image est ouverte, réinitialiser le compteur de la fonction "numérotation" de l'outil "Cercle"
  - **Context:** Assurer que la numérotation des cercles commence toujours à partir de 1 pour chaque nouvelle image.
  - **Spec:** Réinitialiser le compteur interne de l'outil "Cercle" lors de l'ouverture d'une nouvelle image.
  - **Acceptance:** Le premier cercle ajouté à une nouvelle image est toujours numéroté "1".
  - **Résolu:** dans `load_source_image()` (point de passage unique de tous les chargements : dialogue Ouvrir, fichiers récents, glisser-déposer, image démo, ouverture depuis un JSON), `canvas.circle_counter` est remis à 1 parmi les réinitialisations d'état, **avant** le chargement éventuel de la recette associée ; si un JSON existe, `apply_recipe_to_ui()` restaure ensuite la valeur sauvegardée (continuité de session). Le libellé « Compteur » du volet droit est resynchronisé dans les deux branches. Deux tests ajoutés (`tests/unit/test_circle_numbering.py`) : image sans JSON → compteur à 1 et premier cercle numéroté « 1 » ; réouverture d'une image avec JSON → compteur restauré.

- [x] **[TASK-018]** En mode exportation, l'utilisateur ne doit pas pouvoir saisir une taille plus grande que celle de l'image originale.
  - **Context:** Empêcher l'utilisateur de définir une taille d'exportation supérieure à la taille de l'image source.
  - **Spec:**
    - Vérifier la taille saisie par l'utilisateur lors de l'exportation.
    - Si la taille dépasse celle de l'image originale, afficher un message d'erreur ou ajuster automatiquement la taille maximale.
  - **Acceptance:** L'utilisateur ne peut pas exporter une image avec des dimensions supérieures à celles de l'image originale.
  - **Résolu:** référence = dimensions de l'image source (`_export_max_width()` / `_export_max_height()`, plafond historique 20000 px sans image). Toute largeur/hauteur saisie au-delà de la source déclenche une erreur modale (`QMessageBox.warning` via `_reject_export_size()`) suivie du reclamp de la valeur, la hauteur/largeur dérivée restant proportionnelle ; un préréglage plus large que la source est refusé de la même manière (bouton resynchronisé). Au chargement d'une image, `_clamp_export_size_to_source()` reclamp silencieusement les spin boxes (`blockSignals` pour ne pas déclencher `auto_save_recipe` sur un état partiel, avant `compute_associated_paths` pour que le suffixe `-xWIDTH` reflète la valeur réelle) ; un ancien JSON surdimensionné est corrigé sans modal à l'ouverture, sans réécriture immédiate, et le premier changement utilisateur sauvegarde l'état complet avec les valeurs contraintes (régression TASK-004 couverte). Filet de sécurité moteur : `apply_recipe()` borne la demande puis garantit que le rendu final tient dans les dimensions triées de la source (un quart de tour reste autorisé). Tests : `tests/unit/test_export_size_limits.py` (8 tests), gardes moteur dans `tests/unit/test_image_processor.py`, préréglages valides réadaptés dans `tests/unit/test_editing_features.py`, nom d'export `-xWIDTH` ajusté dans `tests/unit/test_qt_editor.py`.
