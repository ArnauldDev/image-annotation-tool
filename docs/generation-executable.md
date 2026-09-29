<!--
  File Name: generation-executable.md
  Description: Génération de l'exécutable autonome d'Image Annotation Tool avec PyInstaller (Windows, macOS, Linux).
  Developer: ArnauldDev
  Created Date: 2026-09-23
  Last Modified: 2026-09-27
-->

<h3>Génération de l'exécutable</h3>

[← Retour au README](../README.md)

Pour distribuer l'application sur des postes **sans Python**, on la « gèle » avec [PyInstaller](https://pyinstaller.org/) : Python, PyQt6, Pillow, les thèmes et les icônes sont regroupés dans un exécutable autonome.

<h4><u>Sommaire</u> :</h4>

- [1. Principe et limites](#1-principe-et-limites)
- [2. Préparer l'environnement](#2-préparer-lenvironnement)
- [3. Le fichier `image_annotation_tool.spec`](#3-le-fichier-image_annotation_toolspec)
  - [Données embarquées (`datas`)](#données-embarquées-datas)
- [4. Construire](#4-construire)
- [5. Windows](#5-windows)
- [6. macOS](#6-macos)
- [7. Linux](#7-linux)
- [8. Liste de vérification de l'exécutable](#8-liste-de-vérification-de-lexécutable)
- [9. Dépannage](#9-dépannage)

---

## 1. Principe et limites

- PyInstaller analyse `main.py`, suit les imports et copie l'interpréteur, les bibliothèques et les fichiers de données déclarés.
- L'exécutable produit est **mono-fichier** (`onefile`) : au lancement, il se décompresse dans un dossier temporaire (`sys._MEIPASS`), d'où l'application lit ses thèmes et icônes.
- **PyInstaller ne fait pas de compilation croisée** : un exécutable Windows se construit sous Windows, une application macOS sous macOS, un binaire Linux sous Linux. Pour produire les trois, construisez sur chaque système ou utilisez des *runners* GitLab CI dédiés (voir [GitLab CI/CD](gitlab-ci-cd.md)).
- Construisez sur la **plus ancienne version** du système que vous devez supporter (surtout sous Linux, à cause de la glibc) : un binaire construit sur un système récent peut refuser de démarrer sur un système plus ancien.

## 2. Préparer l'environnement

Dans l'environnement virtuel du projet (voir [Environnement de développement](environnement-developpement.md)) :

```bash
python -m pip install -e ".[dev]"      # installe PyInstaller (>= 6.0) et pytest
python -m pytest -q                     # toujours vérifier les tests avant un build
```

## 3. Le fichier `image_annotation_tool.spec`

Le fichier [`image_annotation_tool.spec`](../image_annotation_tool.spec) décrit la construction. Points importants :

| Élément         | Valeur                                                                                         | Pourquoi                                                                                               |
| :-------------- | :--------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------- |
| Script d'entrée | `main.py`                                                                                      | Lanceur racine                                                                                         |
| `pathex`        | `['.', 'src']`                                                                                 | Permet de trouver le paquet `iat` dans `src/`                                                          |
| `hiddenimports` | modules `iat.*`, `PyQt6.QtCore/QtGui/QtWidgets`, **`PyQt6.QtSvg`**, `PyQt6.sip`, modules `PIL` | `QtSvg` est indispensable pour afficher les icônes SVG et le logo ; sans lui, les icônes restent vides |
| `datas`         | voir ci-dessous                                                                                | Fichiers non Python embarqués                                                                          |
| `excludes`      | `tkinter`, `matplotlib`, `scipy`, `numpy`, `pytest`                                            | Réduit la taille de l'exécutable                                                                       |
| `console`       | `False`                                                                                        | Pas de fenêtre de terminal au lancement                                                                |
| `upx`           | `True`                                                                                         | Compression si [UPX](https://upx.github.io/) est installé (ignoré sinon)                               |
| `icon`          | `src/iat/resources/icons/app_icon.ico`                                                         | Icône de l'exécutable (Windows ; convertie sous macOS)                                                 |
| `name`          | `ImageAnnotationTool`                                                                          | Nom du fichier produit                                                                                 |

### Données embarquées (`datas`)

| Source (dépôt)      | Destination (dans l'exécutable) | Contenu                                                                |
| :------------------ | :------------------------------ | :--------------------------------------------------------------------- |
| `src/iat/resources` | `iat/resources`                 | Icônes SVG/ICO, logo de l'application, logo CBI                        |
| `themes`            | `themes`                        | Thèmes QSS : **sans eux, l'application n'a plus d'apparence**          |
| `images`            | `images`                        | Images d'exemple                                                       |
| `translations`      | `translations`                  | Fichiers de langue `<code>.json` (à ajouter à `datas` avec le dossier) |

Lorsque l'application est gelée, elle cherche ses thèmes dans `<_MEIPASS>/themes` au lieu de `<projet>/themes` : toute nouvelle ressource lue à l'exécution doit être ajoutée à `datas`, sinon elle manquera dans l'exécutable.

```python
datas = [
    ('src/iat/resources', 'iat/resources'),
    ('images', 'images'),
    ('themes', 'themes'),
    ('translations', 'translations'),
]
```

## 4. Construire

Le script [`build_exe.py`](../build_exe.py) vérifie la présence de PyInstaller et du `.spec`, puis lance :

```bash
python -m PyInstaller --noconfirm --clean image_annotation_tool.spec
```

Utilisation, depuis la racine du dépôt et l'environnement virtuel actif :

```bash
python build_exe.py
```

Le résultat se trouve dans `dist/` ; les fichiers intermédiaires dans `build/` (les deux dossiers sont ignorés par git).

> [!NOTE]
> Les messages de `build_exe.py` mentionnent `dist/ImageAnnotationTool.exe` quel que soit le système : sous macOS et Linux, le fichier produit s'appelle `dist/ImageAnnotationTool` (sans extension).

## 5. Windows

- **Produit** : `dist\ImageAnnotationTool.exe`, exécutable unique qui se lance sans console.
- **Icône** : `app_icon.ico` doit être un `.ico` **multi-résolution** (16, 32, 48, 64, 128 et 256 px) pour être net dans l'explorateur et la barre des tâches.
- **Antivirus / SmartScreen** : un exécutable non signé, surtout compressé par UPX, peut déclencher un avertissement « Windows a protégé votre ordinateur ». Pour une diffusion large, signez-le avec un certificat de signature de code (`signtool sign /fd SHA256 /a dist\ImageAnnotationTool.exe`) ou désactivez UPX (`upx=False`).
- **Démarrage** : le mode mono-fichier se décompresse à chaque lancement (quelques secondes). Un mode dossier (`onedir`) démarre plus vite mais se distribue sous forme d'archive.

```powershell
.\.venv\Scripts\Activate.ps1
python build_exe.py
.\dist\ImageAnnotationTool.exe
```

## 6. macOS

Le `.spec` actuel produit un **binaire Unix** `dist/ImageAnnotationTool`, utilisable depuis le Terminal. Pour obtenir une vraie application `.app` (double-clic dans le Finder, icône dans le Dock), ajoutez un bloc `BUNDLE` à la fin du `.spec` :

```python
app = BUNDLE(
    exe,
    name='ImageAnnotationTool.app',
    icon='src/iat/resources/icons/app_icon.icns',   # icône au format macOS
    bundle_identifier='fr.cbi-toulouse.image-annotation-tool',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
)
```

Points d'attention :

- **Icône** : macOS utilise le format `.icns`. PyInstaller sait convertir un `.ico` si Pillow est installé, mais un `.icns` dédié donne un meilleur rendu. Création depuis un PNG 1024×1024 : dossier `app_icon.iconset/` (tailles 16 à 512 et `@2x`), puis `iconutil -c icns app_icon.iconset`. Le `pyproject.toml` prévoit déjà les fichiers `*.icns` dans `iat.resources.icons`.
- **Architecture** : un build sur Mac Apple Silicon produit un binaire `arm64`, sur Mac Intel un binaire `x86_64`. `target_arch='universal2'` n'est possible que si Python et toutes les dépendances sont eux-mêmes `universal2`.
- **Signature et notarisation** : sans signature, **Gatekeeper** bloque l'application téléchargée (« impossible de vérifier le développeur »). Pour une diffusion hors du laboratoire :
  1. signez avec un certificat *Developer ID Application* (compte Apple Developer) : renseignez `codesign_identity` dans le `.spec`, ou `codesign --deep --force --options runtime --sign "Developer ID Application: …" dist/ImageAnnotationTool.app` ;
  2. notarisez : `xcrun notarytool submit ImageAnnotationTool.zip --keychain-profile <profil> --wait` ;
  3. agrafez le ticket : `xcrun stapler staple dist/ImageAnnotationTool.app`.
- **Usage interne sans signature** : clic droit sur l'application > `Ouvrir` (une seule fois), ou `xattr -dr com.apple.quarantine ImageAnnotationTool.app`.
- **Distribution** : compressez l'application (`ditto -c -k --keepParent dist/ImageAnnotationTool.app ImageAnnotationTool-macos.zip`) ou créez une image disque `.dmg` (`hdiutil create`).

## 7. Linux

- **Produit** : binaire `dist/ImageAnnotationTool` (rendez-le exécutable avec `chmod +x` si besoin). L'icône du `.spec` est ignorée sous Linux.
- **Bibliothèques système** : les *wheels* PyQt6 embarquent Qt, mais pas toutes les bibliothèques du système graphique. Sur le poste de construction **et** sur les postes utilisateurs (Debian/Ubuntu) :

  ```bash
  sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 \
                   libxcb-shape0 libegl1 libgl1 libfontconfig1 libdbus-1-3
  ```

  Sans `libxcb-cursor0`, Qt 6.5+ échoue avec `Could not load the Qt platform plugin "xcb"`. Pour diagnostiquer : `QT_DEBUG_PLUGINS=1 ./ImageAnnotationTool`.
- **Wayland** : l'application fonctionne via XWayland ; pour forcer Wayland natif, `QT_QPA_PLATFORM=wayland` (paquet `qt6-wayland` parfois nécessaire).
- **Intégration au bureau** : créez un fichier `~/.local/share/applications/image-annotation-tool.desktop` :

  ```ini
  [Desktop Entry]
  Type=Application
  Name=Image Annotation Tool
  Exec=/opt/iat/ImageAnnotationTool
  Icon=/opt/iat/app_icon.png
  Categories=Graphics;Science;
  ```

- **AppImage (optionnel)** : pour un fichier unique portable entre distributions, construisez en mode `onedir`, placez le dossier dans une arborescence `AppDir` (avec `AppRun`, le `.desktop` et l'icône), puis générez l'image avec [`appimagetool`](https://appimage.github.io/appimagetool/). Construisez sur une distribution ancienne (par exemple Ubuntu 22.04) pour une compatibilité maximale.

## 8. Liste de vérification de l'exécutable

Testez **sur un poste sans Python** (ou un compte utilisateur neuf) avant toute diffusion :

- [ ] L'exécutable démarre sans fenêtre de console et sans message d'erreur.
- [ ] Le thème **CBI** est appliqué au démarrage ; `Configuration > Thèmes disponibles` liste **CBI, Clair, Sombre** et chacun s'applique.
- [ ] Les **icônes SVG** s'affichent (palette graphique des outils, boutons `+`/`−` des champs numériques) et prennent la couleur du thème.
- [ ] `Fichier > Ouvrir une image` ouvre une photo ; le glisser-déposer d'un fichier fonctionne.
- [ ] Une annotation et une loupe se tracent ; la recette `-iat.json` est créée à côté de l'image.
- [ ] L'export JPEG (800, 1200, 1920 px) produit un fichier correct, à la bonne largeur.
- [ ] `Configuration > Langue > English` traduit l'interface (fichiers `translations/` embarqués).
- [ ] `Aide > À propos` affiche le **logo**, la version, la licence et le lien vers le code source.
- [ ] L'icône de l'application apparaît dans la barre des tâches / le Dock.
- [ ] Les préférences (thème, disposition) sont conservées après fermeture et réouverture.

## 9. Dépannage

| Symptôme                                      | Cause probable / solution                                                             |
| :-------------------------------------------- | :------------------------------------------------------------------------------------ |
| Interface sans couleurs (style Qt brut)       | Dossier `themes` absent de `datas`                                                    |
| Icônes vides ou logo absent                   | `PyQt6.QtSvg` manquant dans `hiddenimports`, ou `src/iat/resources` absent de `datas` |
| Interface restée en français malgré le choix  | Dossier `translations` absent de `datas`                                              |
| `ModuleNotFoundError` au lancement            | Module importé dynamiquement : l'ajouter à `hiddenimports`                            |
| Voir les erreurs d'un exécutable sans console | Construire temporairement avec `console=True` (ou `debug=True`) dans le `.spec`       |
| Exécutable bloqué par l'antivirus             | Désactiver UPX (`upx=False`) et/ou signer l'exécutable                                |
| Linux : `xcb` introuvable                     | Installer `libxcb-cursor0` et les bibliothèques du §7                                 |
| macOS : « application endommagée »            | Attribut de quarantaine : `xattr -dr com.apple.quarantine ImageAnnotationTool.app`    |
