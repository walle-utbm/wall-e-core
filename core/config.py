from __future__ import annotations

"""Chargement de la configuration de la passerelle (config.yaml)."""

from dataclasses import dataclass
from pathlib import Path

import yaml

# Racine du repo = dossier parent de `core/`.
ROOT = Path(__file__).resolve().parent.parent


@dataclass(slots=True)
class CoreConfig:
    host: str
    port: int
    review_queue: Path
    dataset: Path
    web: Path
    vision_src: Path

    @property
    def images_dir(self) -> Path:
        return self.dataset / "images"

    @property
    def labels_dir(self) -> Path:
        return self.dataset / "labels"

    @property
    def rejected_dir(self) -> Path:
        return self.dataset / "rejected"

    @property
    def skipped_dir(self) -> Path:
        return self.dataset / "skipped"

    @property
    def state_file(self) -> Path:
        return self.dataset / "state.json"


def _resolve(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else (root / candidate)


def load_config(config_path: Path | None = None) -> CoreConfig:
    path = config_path or (ROOT / "config.yaml")
    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    server = raw.get("server", {}) or {}
    paths = raw.get("paths", {}) or {}

    return CoreConfig(
        host=str(server.get("host", "0.0.0.0")),
        port=int(server.get("port", 8000)),
        review_queue=_resolve(ROOT, str(paths.get("review_queue", "wall-e-vision/outputs/review"))),
        dataset=_resolve(ROOT, str(paths.get("dataset", "data/dataset"))),
        web=_resolve(ROOT, str(paths.get("web", "build/web"))),
        vision_src=_resolve(ROOT, str(raw.get("vision_src", "wall-e-vision/src"))),
    )
