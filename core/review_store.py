from __future__ import annotations

"""File d'attente de validation + écriture du dataset YOLO.

Protocole de file (sur disque, alimentée par wall-e-vision) :
  <id>.jpg   — image brute (vierge)
  <id>.json  — sidecar : { id, timestamp, image: {width, height},
                           detections: [ {class_id, class_name, confidence,
                                          bbox_xyxy: [x1, y1, x2, y2]} ] }

Décisions :
  accept  -> dataset/images/<id>.jpg + dataset/labels/<id>.txt (YOLO)
  reject  -> dataset/rejected/<id>.jpg
  skip    -> dataset/skipped/<id>.jpg
"""

import json
import shutil
import threading
from pathlib import Path
from typing import Any

from .config import CoreConfig
from .yolo import load_class_names, to_yolo_line, write_classes_txt, write_data_yaml


class ReviewStore:
    def __init__(self, config: CoreConfig) -> None:
        self.config = config
        self._lock = threading.Lock()
        self._ensure_layout()
        self.class_names = load_class_names(config.vision_src)
        if self.class_names:
            write_classes_txt(config.dataset / "classes.txt", self.class_names)
            write_data_yaml(config.dataset / "data.yaml", config.dataset, self.class_names)
        self.counters = self._load_counters()

    def _ensure_layout(self) -> None:
        self.config.review_queue.mkdir(parents=True, exist_ok=True)
        for directory in (
            self.config.images_dir,
            self.config.labels_dir,
            self.config.rejected_dir,
            self.config.skipped_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def _load_counters(self) -> dict[str, int]:
        if self.config.state_file.exists():
            try:
                raw = json.loads(self.config.state_file.read_text(encoding="utf-8"))
                return {
                    "nb_objects_correct": int(raw.get("nb_objects_correct", 0)),
                    "nb_objects_incorrect": int(raw.get("nb_objects_incorrect", 0)),
                }
            except Exception:
                pass
        return {"nb_objects_correct": 0, "nb_objects_incorrect": 0}

    def _save_counters(self) -> None:
        self.config.state_file.write_text(
            json.dumps(self.counters, indent=2), encoding="utf-8"
        )

    def _sidecar_path(self, item_id: str) -> Path:
        return self.config.review_queue / f"{item_id}.json"

    def image_path(self, item_id: str) -> Path | None:
        # `item_id` vient d'un sidecar interne, mais on garde une garde simple.
        candidate = self.config.review_queue / f"{item_id}.jpg"
        try:
            candidate.relative_to(self.config.review_queue)
        except ValueError:
            return None
        return candidate if candidate.exists() else None

    def next_pending(self) -> dict[str, Any] | None:
        """Renvoie le sidecar (dict) du plus ancien item en attente, ou None."""
        with self._lock:
            # FIFO : plus ancien d'abord (mtime), nom en départage pour un ordre stable.
            sidecars = sorted(
                self.config.review_queue.glob("*.json"),
                key=lambda p: (p.stat().st_mtime, p.name),
            )
            for sidecar in sidecars:
                item_id = sidecar.stem
                if not (self.config.review_queue / f"{item_id}.jpg").exists():
                    continue  # image manquante : on ignore l'orphelin
                try:
                    data = json.loads(sidecar.read_text(encoding="utf-8"))
                except Exception:
                    continue
                data["id"] = item_id
                return data
        return None

    def pending_count(self) -> int:
        return sum(
            1
            for sidecar in self.config.review_queue.glob("*.json")
            if (self.config.review_queue / f"{sidecar.stem}.jpg").exists()
        )

    def accept(self, item_id: str) -> dict[str, Any]:
        with self._lock:
            sidecar = self._sidecar_path(item_id)
            image = self.config.review_queue / f"{item_id}.jpg"
            if not sidecar.exists() or not image.exists():
                raise FileNotFoundError(item_id)

            data = json.loads(sidecar.read_text(encoding="utf-8"))
            img = data.get("image", {})
            width = int(img.get("width", 0))
            height = int(img.get("height", 0))
            if width <= 0 or height <= 0:
                raise ValueError(f"Dimensions d'image invalides pour {item_id}")

            lines = [
                to_yolo_line(det["bbox_xyxy"], width, height, int(det["class_id"]))
                for det in data.get("detections", [])
                if det.get("bbox_xyxy") is not None and int(det.get("class_id", -1)) >= 0
            ]

            label_path = self.config.labels_dir / f"{item_id}.txt"
            label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            shutil.move(str(image), str(self.config.images_dir / f"{item_id}.jpg"))
            sidecar.unlink(missing_ok=True)

            self.counters["nb_objects_correct"] += 1
            self._save_counters()
            return {"saved_label": str(label_path), "boxes": len(lines)}

    def reject(self, item_id: str) -> dict[str, Any]:
        result = self._discard(item_id, self.config.rejected_dir)
        with self._lock:
            self.counters["nb_objects_incorrect"] += 1
            self._save_counters()
        return result

    def skip(self, item_id: str) -> dict[str, Any]:
        return self._discard(item_id, self.config.skipped_dir)

    def _discard(self, item_id: str, destination: Path) -> dict[str, Any]:
        with self._lock:
            sidecar = self._sidecar_path(item_id)
            image = self.config.review_queue / f"{item_id}.jpg"
            if not sidecar.exists() and not image.exists():
                raise FileNotFoundError(item_id)
            if image.exists():
                shutil.move(str(image), str(destination / f"{item_id}.jpg"))
            sidecar.unlink(missing_ok=True)
            return {"moved_to": str(destination)}
