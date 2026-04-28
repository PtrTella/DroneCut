# DroneCut V3: The Director 🚁🎬

**Obiettivo:** Trasformare gigabyte di girato drone in una timeline di montaggio professionale, utilizzando un'AI che agisce non solo come analista, ma come vero e proprio **Assistente di Regia**.

---

## 🛠 Architettura della Pipeline (7 Stadi)

### 1. Proxy Generation (FFmpeg)
*   Crea una versione ultra-leggera (480p, 1 FPS) per l'analisi.
*   **Performance:** Riduce drasticamente il carico su CPU/GPU.

### 2. Semantic Mapping (CLIP)
*   Genera "Visual Fingerprints" ogni secondo con `CLIP-ViT-B/32`.
*   Identifica i capitoli semantici del video.

### 3. Semantic Audit & Mapping (DBSCAN + PCA)
*   **Granularità:** Crea micro-cluster (Eps=0.12) per isolare inquadrature specifiche.
*   **Visualizzazione:** Genera una mappa 2D (`clustering_map.png`) per mostrare la struttura del video.
*   **Inclusività:** Non scarta nulla come rumore, ma cataloga tutto.

### 4. Surgical Stability Trimming (OpenCV)
*   Rifinitura millimetrica dei bordi (2s iniziali/finali) per eliminare scatti o vibrazioni.
*   **Regola Magica:** Scarta clip che, dopo il trimming, durano meno di **3.0 secondi**.

### 5. Aesthetic Scoring (CLIP Aesthetic)
*   Valuta la bellezza visiva (colore, composizione) su una scala 1-10.
*   Prepara il "Podio Estetico" per ogni cluster.

### 6. VLM Creative Selection (Moondream2 - The Director)
*   **Quality Audit:** Il VLM ispeziona il frame. Scarta inquadrature sbagliate, fuori fuoco o droni che puntano il nulla.
*   **Theme Search (Text-to-Edit):** Se l'utente inserisce un tema (es. "solo azione e furgone"), il VLM seleziona solo i cluster pertinenti.
*   **Podium Rule:** Esporta le **Top 3** clip migliori per ogni cluster approvato.

### 7. Timeline Render & Debug (FFmpeg)
*   **Output:** Genera la cartella `data/output/timeline/` pronta per il montaggio.
*   **Visual Debug:** Per ogni clip scartata, salva un frame JPG con il motivo del taglio in `data/debug/`.

---

## ⚙️ Parametri Core (`src/config.py`)

*   `MIN_SCENE_DURATION = 3.0`: Evita glitch visivi e tagli troppo frenetici.
*   `AESTHETIC_THRESHOLD = 6.0`: Solo materiale di qualità entra nel montaggio.
*   `DBSCAN_EPS = 0.12`: Massima specificità nei gruppi di inquadrature.
*   `THEME_PROMPT`: Permette di guidare l'AI tramite linguaggio naturale.

---

## 📂 Struttura Cartelle
*   `data/output/timeline/`: I tuoi "Daily" pronti per Premiere/CapCut.
*   `data/debug/`: Archivio visivo delle decisioni dell'AI (Mappa cluster e frame scartati).
*   `data/proxy/`: Cache dei proxy per velocizzare i run successivi.

---

## ⚡️ Ottimizzazioni Apple Silicon (M4 Pro)
*   **Backend:** Utilizzo nativo di `mps` (Metal Performance Shaders).
*   **Engine:** Moondream2 su `transformers` per massima stabilità.
*   **Memory:** Svuotamento aggressivo della VRAM (`empty_cache`) tra gli stadi pesanti.
