from __future__ import annotations

"""Service passerelle FastAPI : API de validation + télémétrie + dashboard statique.

Lancement : `uvicorn core.server:app` (voir scripts/run.sh).
"""

import asyncio
import json
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import load_config
from .review_store import ReviewStore

config = load_config()
store = ReviewStore(config)

app = FastAPI(title="wall-e-core bridge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _telemetry() -> dict:
    pending = store.next_pending()
    last_class = "null"
    if pending and pending.get("detections"):
        last_class = pending["detections"][0].get("class_name", "null")
    return {
        "robot": "wall-e",
        "timestamp": time.time(),
        "speed": 0,
        "battery": 80,
        "temperature": 38.0,
        "processing_time": 0.0,
        "nb_objects_correct": store.counters["nb_objects_correct"],
        "nb_objects_incorrect": store.counters["nb_objects_incorrect"],
        "pending": store.pending_count(),
        "last_class": last_class,
    }


@app.get("/data")
def get_data() -> dict:
    return _telemetry()


@app.get("/stream")
async def stream() -> StreamingResponse:
    async def generator():
        while True:
            yield f"data: {json.dumps(_telemetry())}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/command")
async def receive_command(request: Request) -> dict:
    body = await request.json()
    part = body.get("part")
    action = body.get("action")
    print(f"[CMD] {part} --> {action}")
    return {"status": "ok", "ack": f"{part}:{action} reçu"}


@app.get("/api/review/next")
def review_next() -> Response:
    item = store.next_pending()
    if item is None:
        return Response(status_code=204)
    detections = item.get("detections", [])
    return JSONResponse(
        {
            "id": item["id"],
            "timestamp": item.get("timestamp"),
            "image": item.get("image", {}),
            "detections": detections,
            "predicted_class": detections[0].get("class_name") if detections else None,
            "confidence": detections[0].get("confidence") if detections else None,
            "pending": store.pending_count(),
        }
    )


@app.get("/api/review/image/{item_id}")
def review_image(item_id: str) -> Response:
    path = store.image_path(item_id)
    if path is None:
        return Response(status_code=404)
    # Pas de cache : chaque item est unique et éphémère.
    return FileResponse(str(path), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.post("/api/review/validate")
async def review_validate(request: Request) -> Response:
    body = await request.json()
    item_id = body.get("id")
    decision = body.get("decision")
    if not item_id or decision not in {"correct", "incorrect", "skip"}:
        return JSONResponse({"status": "error", "message": "id ou decision invalide"}, status_code=400)

    try:
        if decision == "correct":
            result = store.accept(item_id)
        elif decision == "incorrect":
            result = store.reject(item_id)
        else:
            result = store.skip(item_id)
    except FileNotFoundError:
        return JSONResponse({"status": "error", "message": "item introuvable (déjà traité ?)"}, status_code=404)
    except Exception as exc:  # pragma: no cover - garde-fou
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

    return {"status": "ok", "decision": decision, "result": result}


if config.web.is_dir():
    app.mount("/", StaticFiles(directory=str(config.web), html=True), name="dashboard")
else:  # pragma: no cover
    print(f"[WARN] Front-end introuvable dans {config.web}. Lance d'abord scripts/build_frontend.sh")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("core.server:app", host=config.host, port=config.port)
