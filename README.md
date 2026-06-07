# wall-e-core

Repo **parent / passerelle** du robot autonome de tri de déchets **WALL·E** (UTBM).

Il regroupe les sous-systèmes du robot sous forme de **sous-modules Git** et fournit le code de
liaison (« le pont ») entre eux. Aujourd'hui il relie la **vision** et le **dashboard** ; la
préhension des déchets et la navigation autonome viendront s'y greffer plus tard.

```
┌─────────────────┐   image brute + bbox   ┌──────────────┐   validation humaine   ┌──────────────┐
│  wall-e-vision  │ ─────────────────────► │  file disque │ ─────────────────────► │  dataset     │
│  (détection)    │   data/review_queue/   │ review_queue │   core/ (FastAPI +     │  YOLO /      │
│                 │                        │              │   dashboard)           │  rejected /  │
└─────────────────┘                        └──────────────┘                        │  skipped     │
                                                                                   └──────────────┘
```

## Sous-modules

| Chemin             | Dépôt                         | Rôle                                     |
| ------------------ | ----------------------------- | ---------------------------------------- |
| `wall-e-vision`    | `walle-utbm/wall-e-vision`    | Inférence edge YOLO, détection déchets   |
| `dashboard-wall-e` | `walle-utbm/dashboard-wall-e` | Dashboard web (FastAPI + front statique) |

Les sous-modules restent des composants **autonomes** : toute la logique de liaison vit dans
`core/`. (Seule exception : un export d'images *désactivé par défaut* dans la vision, cf. plus bas.)

## Le pont : vision → validation → dataset

1. La vision dépose, pour chaque frame détectée, une paire `<id>.jpg` (image **vierge**) +
   `<id>.json` (métadonnées : classe, bbox en pixels) dans la file `review_queue/`.
2. Le service `core/` (FastAPI) sert le dashboard et expose la file à la page **CLASSIFICATION**.
3. L'opérateur valide l'image :
   - **CORRECT** → l'image est ajoutée au **dataset YOLO** : `dataset/images/<id>.jpg` +
     `dataset/labels/<id>.txt` (une ligne `cls cx cy w h` normalisée par détection).
   - **INCORRECT** → l'image est déplacée dans `dataset/rejected/`.
   - **PASSER** (image non exploitable) → l'image est déplacée dans `dataset/skipped/`.

Le dataset (`data/dataset/`) est ainsi prêt à réentraîner le modèle de la vision.

## Installation

```bash
git clone --recurse-submodules https://github.com/walle-utbm/wall-e-core.git
cd wall-e-core
# (si déjà cloné sans --recurse-submodules)
git submodule update --init --recursive

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Démarrage

```bash
bash scripts/run.sh          # assemble le front + lance le serveur sur :8000
```

Puis ouvrir <http://localhost:8000> → onglet **CLASSIFICATION**.

### Activer l'export depuis la vision (sur la Rubik Pi 3)

Dans `wall-e-vision/config.yaml`, mettre `runtime.review_export: true`, puis lancer la vision
(`python wall-e-vision/main.py`). Les images détectées alimenteront alors automatiquement la file.

## Configuration

Voir [`config.yaml`](config.yaml) : ports, chemins de la file, du dataset, du front assemblé.

## Structure

```
core/                  Code de la passerelle (FastAPI + logique dataset YOLO)
scripts/               build_frontend.sh (assemblage front), run.sh (lancement)
config.yaml            Configuration du pont
data/                  Runtime (file + dataset) — gitignored
build/web/             Front-end assemblé — gitignored
wall-e-vision/         Sous-module
dashboard-wall-e/      Sous-module
```
