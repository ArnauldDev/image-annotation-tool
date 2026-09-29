# Instructions pour les Agents IA (Vibe Coding & Développement Autonome)

Ce fichier définit les règles strictes d'interaction entre l'agent IA et le dépôt du projet Image Annotation Tool (IAT).

## 1. Flux de travail (Workflow)

Avant de commencer une tâche, l'agent **DOIT** lire le fichier `ROADMAP.md` à la racine du dépôt.\
L'agent ne doit JAMAIS toucher aux tâches situées dans `## 🔄 In Progress`. L'agent prend la première tâche de Next, l'exécute, et la déplace directement dans Done une fois validée.

1. **Sélection :** Prends la **première tâche non cochée** `[ ]` dans la section `## 🎯 Next`.
2. **Exécution :** Implémente la fonctionnalité en respectant la section **Spec**.
3. **Validation :** Vérifie que la section **Acceptance** est pleinement satisfaite (tests unitaires validés, comportement de l'UI conforme).
4. **Mise à jour :** 
   - Coche la case `[x]` de la tâche dans `ROADMAP.md`.
   - Déplace la tâche dans la section `## ✅ Done`.
   - **NE JAMAIS** supprimer une tâche de la liste.

## 2. Convention de nommage et Git

- L'identifiant de la tâche (ex: `[TASK-001]`) est crucial.
- **Branches :** Si l'agent doit créer une branche, utiliser le format `feat/task-001-description-courte`. (Identifiant en minuscules).
- **Messages de commit :** Le message **DOIT** inclure l'identifiant de la tâche à la fin, selon le format Conventional Commits.
  - Exemple : `feat: implement objects alignment and distribution [TASK-001]`
  - Exemple : `fix: improve line selection hitbox [TASK-004]`

## 3. Périmètre d'action (Guardrails)

- **Section `## 💡 Ideas & Vibe Backlog` :** L'agent n'est **PAS AUTORISÉ** à sélectionner des tâches dans cette section de manière autonome. Ce sont des brouillons. L'agent ne doit traiter que ce qui est dans `## 🎯 Next`.
- **Cohérence :** Maintenez la cohérence avec le style architectural existant (PyQt6). Ne modifiez pas l'arborescence des répertoires sans consigne explicite.
- **Sauvegarde :** Toute modification des propriétés visuelles d'un objet (Annotation, Loupe, Transformation) doit être sérialisable et reflétée dans le mécanisme de sauvegarde JSON existant de l'application.
