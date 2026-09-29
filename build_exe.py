#!/usr/bin/env python3
"""Script de construction d'un exécutable Windows standalone (.exe) pour Image Annotation Tool.

Utilisation :
    python build_exe.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    spec_file = project_root / "image_annotation_tool.spec"

    print("=" * 60)
    print("Construction de l'exécutable Windows (Image Annotation Tool)")
    print("=" * 60)

    # Vérification de PyInstaller
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("\n[ERREUR] PyInstaller n'est pas installé dans cet environnement Python.")
        print("Veuillez installer PyInstaller avec la commande suivante :")
        print(f"    {sys.executable} -m pip install pyinstaller")
        sys.exit(1)

    if not spec_file.exists():
        print(f"\n[ERREUR] Fichier de spécification introuvable : {spec_file}")
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec_file),
    ]

    print(f"\nExécution de la commande : {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_root)

    if result.returncode == 0:
        exe_path = project_root / "dist" / "ImageAnnotationTool.exe"
        print("\n" + "=" * 60)
        print("Succès ! L'exécutable a été généré avec succès :")
        print(f"  -> {exe_path}")
        print("=" * 60)
    else:
        print(f"\n[ERREUR] La compilation a échoué avec le code de sortie {result.returncode}.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
