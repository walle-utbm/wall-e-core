from __future__ import annotations

"""Utilitaires format YOLO : conversion bbox + génération data.yaml / classes.txt.

La liste des classes est importée depuis le sous-module vision
(`walle_vision.utils.labels.CLASS_NAMES`) pour éviter toute duplication.
"""

import sys
from pathlib import Path
from typing import Sequence

# Coordonnées xyxy en pixels : (x1, y1, x2, y2).
BBoxXYXY = Sequence[float]


def load_class_names(vision_src: Path) -> list[str]:
    """Importe CLASS_NAMES depuis le sous-module vision.

    Renvoie une liste vide si le sous-module n'est pas disponible (le pont peut
    tourner sans, les sidecars portent déjà `class_name`).
    """
    src = str(vision_src)
    if src not in sys.path:
        sys.path.insert(0, src)
    try:
        from walle_vision.utils.labels import CLASS_NAMES  # type: ignore
    except Exception:
        return []
    return list(CLASS_NAMES)


def to_yolo_line(bbox_xyxy: BBoxXYXY, img_w: int, img_h: int, class_id: int) -> str:
    """Convertit une bbox xyxy (pixels) en ligne YOLO normalisée.

    Format : `class_id x_center y_center width height`, valeurs ∈ [0, 1].
    """
    x1, y1, x2, y2 = (float(v) for v in bbox_xyxy)
    x_min, x_max = sorted((x1, x2))
    y_min, y_max = sorted((y1, y2))

    cx = ((x_min + x_max) / 2.0) / img_w
    cy = ((y_min + y_max) / 2.0) / img_h
    w = (x_max - x_min) / img_w
    h = (y_max - y_min) / img_h

    clamp = lambda v: max(0.0, min(1.0, v))
    return f"{int(class_id)} {clamp(cx):.6f} {clamp(cy):.6f} {clamp(w):.6f} {clamp(h):.6f}"


def write_classes_txt(path: Path, class_names: list[str]) -> None:
    path.write_text("\n".join(class_names) + ("\n" if class_names else ""), encoding="utf-8")


def write_data_yaml(path: Path, dataset_dir: Path, class_names: list[str]) -> None:
    """Écrit un data.yaml Ultralytics minimal pointant sur images/ (train et val)."""
    names_block = "\n".join(f"  {i}: {name}" for i, name in enumerate(class_names))
    content = (
        f"# Généré par wall-e-core — dataset de validation humaine\n"
        f"path: {dataset_dir}\n"
        f"train: images\n"
        f"val: images\n"
        f"nc: {len(class_names)}\n"
        f"names:\n{names_block}\n"
    )
    path.write_text(content, encoding="utf-8")
