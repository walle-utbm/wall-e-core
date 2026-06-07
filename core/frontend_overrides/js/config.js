//  config.js — Paramètres globaux (OVERLAY wall-e-core)
//  Le front est servi par le pont (core/server.py), donc on utilise des URLs
//  RELATIVES : les appels repartent toujours vers la bonne origine, que tu
//  ouvres le dashboard en localhost ou via l'IP de la Pi.

const BASE_URL = "";    // servi par le pont -> relatif
const POLL_MS  = 500;   // Intervalle de polling des données (ms)
const CAM_MS   = 3000;  // Intervalle de rafraîchissement caméra (ms)

// Chemin de l'image caméra (page 1). La page de validation, elle, tire ses
// images de l'API du pont (/api/review/*) via review.js.
const CAM_PATH = "/images/current.jpg";

// Plage de température affichée sur le thermomètre (°C)
const TEMP_MIN = 35;
const TEMP_MAX = 45;
