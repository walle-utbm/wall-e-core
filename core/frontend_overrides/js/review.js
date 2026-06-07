//  review.js — Pilote la page CLASSIFICATION depuis l'API de validation du pont.
//  Ajouté par wall-e-core (overlay). Charge les images depuis la file de la
//  vision (/api/review/*) au lieu de l'image statique current.jpg, DESSINE les
//  bounding boxes pour aider la validation, et envoie les décisions
//  (correct / incorrect / skip) au backend qui construit le dataset YOLO.
//
//  Les boîtes sont rendues côté navigateur, sur un <canvas>, dans les
//  coordonnées pixel natives de l'image : l'image sur disque reste VIERGE
//  (indispensable pour le dataset YOLO), seul l'affichage est annoté.
//
//  Dépend de : config.js (BASE_URL), ui.js (showFeedback, optionnel).

(function () {
  let currentReviewId = null;
  let sessionCorrect = 0;
  let sessionIncorrect = 0;
  let canvas = null;
  let ctx = null;

  const BOX_COLORS = ['#00e0c6', '#ffcc00', '#ff5da2', '#7c9cff', '#7CFC9A'];
  const $ = (id) => document.getElementById(id);

  function feedback(kind, msg) {
    if (typeof showFeedback === 'function') {
      showFeedback(kind, msg);
    } else {
      const el = $('val-fb');
      if (el) el.textContent = msg;
    }
  }

  // Remplace <img id="val-img"> par un canvas (image + boîtes au même endroit).
  function setupCanvas() {
    const img = $('val-img');
    if (!img || canvas) return;
    canvas = document.createElement('canvas');
    canvas.id = 'val-canvas';
    // Hérite du rendu de .val-img mais en "contain" (image entière, non rognée).
    canvas.style.width = '100%';
    canvas.style.height = 'auto';
    canvas.style.display = 'block';
    canvas.style.borderRadius = '4px';
    canvas.style.border = '1px solid var(--border)';
    canvas.style.background = '#050810';
    img.style.display = 'none';
    img.parentNode.insertBefore(canvas, img.nextSibling);
    ctx = canvas.getContext('2d');
  }

  function clearCanvas(message) {
    if (!ctx) return;
    canvas.width = 640;
    canvas.height = 360;
    ctx.fillStyle = '#050810';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (message) {
      ctx.fillStyle = '#3a4660';
      ctx.font = '28px Orbitron, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(message, canvas.width / 2, canvas.height / 2);
    }
  }

  // Dessine l'image + une boîte par détection (coords natives de l'image).
  function renderImageWithBoxes(item) {
    setupCanvas();
    const img = new Image();
    img.onload = function () {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      const lw = Math.max(2, Math.round(img.naturalWidth / 400));
      const fontSize = Math.max(14, Math.round(img.naturalWidth / 45));
      ctx.lineWidth = lw;
      ctx.font = `${fontSize}px 'Share Tech Mono', monospace`;
      ctx.textAlign = 'left';

      (item.detections || []).forEach(function (det, i) {
        const b = det.bbox_xyxy;
        if (!b) return;
        const color = BOX_COLORS[i % BOX_COLORS.length];
        const x = b[0], y = b[1], w = b[2] - b[0], h = b[3] - b[1];

        ctx.strokeStyle = color;
        ctx.strokeRect(x, y, w, h);

        const pct = det.confidence != null ? ' ' + Math.round(det.confidence * 100) + '%' : '';
        const label = (det.class_name || '?') + pct;
        const padX = 6, th = fontSize + 6;
        const tw = ctx.measureText(label).width + padX * 2;
        const ly = y - th >= 0 ? y - th : y; // évite de sortir en haut
        ctx.fillStyle = color;
        ctx.fillRect(x - lw / 2, ly, tw, th);
        ctx.fillStyle = '#04111a';
        ctx.fillText(label, x + padX - lw / 2, ly + fontSize);
      });
    };
    img.onerror = function () { clearCanvas('IMAGE ?'); };
    img.src = BASE_URL + '/api/review/image/' + encodeURIComponent(item.id) + '?t=' + Date.now();
  }

  // Charge le prochain élément à valider dans la page.
  async function loadNextReview() {
    try {
      const res = await fetch(BASE_URL + '/api/review/next', { cache: 'no-store' });

      if (res.status === 204) {
        currentReviewId = null;
        setupCanvas();
        clearCanvas('FILE VIDE');
        if ($('robot-class')) $('robot-class').textContent = 'FILE VIDE';
        return;
      }

      const item = await res.json();
      currentReviewId = item.id;
      renderImageWithBoxes(item);

      const cls = (item.predicted_class || 'INCONNU').toUpperCase();
      const conf = item.confidence != null ? ' (' + Math.round(item.confidence * 100) + '%)' : '';
      const n = (item.detections || []).length;
      const extra = n > 1 ? ` — ${n} objets` : '';
      if ($('robot-class')) $('robot-class').textContent = cls + conf + extra;
    } catch (err) {
      currentReviewId = null;
      feedback('err', 'Pont injoignable');
    }
  }

  // Envoie la décision puis enchaîne sur l'image suivante.
  // result : 'correct' | 'incorrect' | 'skip'
  async function sendValidation(result) {
    if (!currentReviewId) {
      feedback('skip', 'Aucune image à valider');
      return;
    }
    const id = currentReviewId;
    feedback('pend', 'Envoi en cours...');

    try {
      const res = await fetch(BASE_URL + '/api/review/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, decision: result }),
      });
      const data = await res.json();

      if (!res.ok || data.status !== 'ok') {
        feedback('err', 'Erreur : ' + (data.message || res.status));
        return;
      }

      if (result === 'correct') {
        sessionCorrect++;
        if ($('s-ok')) $('s-ok').textContent = sessionCorrect;
        feedback('ok', 'Ajouté au dataset YOLO');
      } else if (result === 'incorrect') {
        sessionIncorrect++;
        if ($('s-ko')) $('s-ko').textContent = sessionIncorrect;
        feedback('ok', 'Déplacé dans rejected/');
      } else {
        feedback('skip', 'Image passée (skipped/)');
      }

      await loadNextReview();
    } catch (err) {
      feedback('err', 'Raspberry Pi injoignable');
    }
  }

  // La caméra (page 1) continue d'utiliser current.jpg, mais on ne laisse plus
  // refreshCamera() écraser l'image de validation : on ne touche que cam-img.
  function refreshCameraOnly() {
    const src = BASE_URL + CAM_PATH + '?t=' + Date.now();
    const cam = $('cam-img');
    if (cam) cam.src = src;
    if ($('cam-ts')) $('cam-ts').textContent = new Date().toLocaleTimeString('fr-FR');
  }

  // Expose / override les fonctions globales appelées par le HTML et main.js.
  window.sendValidation = sendValidation;
  window.refreshCamera = refreshCameraOnly;

  document.addEventListener('DOMContentLoaded', function () {
    loadNextReview();
    // Récupère les nouvelles images quand la file était vide (sans écraser
    // une image déjà affichée et en attente de décision).
    setInterval(function () {
      if (currentReviewId === null) loadNextReview();
    }, 3000);
  });
})();
