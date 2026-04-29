# 📋 DroneCut Pipeline Technical Specification (v4.1)
**Architecture**: The Chronological Scalpel (Surgical Sliding Window Edition)

Questa pipeline è progettata per trasformare girato drone grezzo in una timeline di clip stabili, esteticamente superiori e pronte per il montaggio manuale, eliminando colli di bottiglia AI e logiche di clustering non deterministiche.

---

## 🛠️ Stadio 1: Chronological Scene Detection
- **Engine**: OpenAI CLIP (`vit-base-patch32`).
- **Logica**: Analisi sequenziale del video (Proxy 1 FPS).
- **Meccanismo**: Calcola la Cosine Similarity tra frame consecutivi.
- **Soglia**: `SEMANTIC_CUT_THRESHOLD = 0.85`. Se la similarità scende sotto questa soglia, viene generato un taglio netto (hard cut).
- **Risultato**: Una lista cronologica di "Raw Chapters".

---

## 🛠️ Stadio 2: Surgical Stability Audit (Sliding Window)
- **Engine**: OpenCV Farneback Optical Flow.
- **Processo**: 
    1. **Full Scan**: Analisi integrale di ogni Raw Chapter (Downsample 240p per massime performance).
    2. **Metriche Anti-Caos**: 
       - **Peak Flow (90° percentile)**: Individua movimenti bruschi improvvisi.
       - **Motion Jitter (Std Dev)**: Misura la fluidità del movimento (cinematico vs caotico).
    3. **Sliding Window**: L'algoritmo identifica la **finestra contigua più lunga** di frame stabili.
- **The Gate**: Se la finestra stabile trovata è `< 2.0s` (`MIN_SCENE_DURATION`), la clip viene scartata.
- **Risultato**: Estrazione chirurgica della "Golden Window" stabile da ogni capitolo.

---

## 🛠️ Stadio 3: Multi-Frame Aesthetic Scoring
- **Engine**: CLIP-Aesthetic Predictor.
- **Logica**: Nessuna ghigliottina automatica. Ogni clip sopravvissuta viene valutata.
- **Campionamento**: Media pesata su 3 campioni (al 25%, 50% e 75% della durata della clip) per evitare errori di valutazione su singoli frame.
- **Risultato**: Ogni clip riceve un `aesthetic_score` (1.0 - 10.0) salvato nei metadati.

---

## 🛠️ Stadio 4: Serialization & Manifest
- **Azione**: 
    1. Generazione di titoli sequenziali (`Scena_01`, `Scena_02`, ...).
    2. Estrazione di thumbnail (JPG) dal centro della finestra stabile.
    3. Creazione del manifest `.dcproj` (JSON) contenente:
       - `id`, `title`, `start_sec`, `end_sec`, `duration`, `aesthetic_score`.
       - `video_clip`: Path assoluto al segmento MP4 esportato.
       - `thumbnail`: Path all'anteprima immagine.

---

## 🛠️ Stadio 5: Rendering (Lossless Export)
- **Engine**: FFmpeg.
- **Metodo**: Stream Copy (`-c copy`). Nessuna ricompressione, nessuna perdita di qualità, velocità istantanea.
- **Output**: Cartella `data/output/timeline/` contenente i singoli file MP4 numerati.

---

## 🎛️ Parametri di Configurazione Correnti (`config.py`)
| Parametro | Valore | Descrizione |
| :--- | :--- | :--- |
| `SEMANTIC_CUT_THRESHOLD` | 0.85 | Sensibilità ai cambi di scena semantici. |
| `MIN_SCENE_DURATION` | 2.0s | Durata minima accettabile per una clip stabile. |
| `MAX_CHAOS_MAGNITUDE` | 12.0 | Tolleranza massima ai picchi di movimento (shaky). |
| `MAX_JITTER_THRESHOLD` | 3.0 | Tolleranza massima alla discontinuità del movimento. |
| `PROXY_FPS` | 1 | Frequenza di campionamento per lo Stadio 1. |
