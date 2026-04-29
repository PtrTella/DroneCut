Ecco il **PRD (Product Requirements Document) focalizzato al 100% sull'Interfaccia Grafica (GUI)**. 

Questo documento è stato epurato da tutta la logica di intelligenza artificiale di backend (che verrà gestita altrove) e si concentra esclusivamente sull'architettura visiva, l'esperienza utente (UX) e il Micro-Player integrato. 

Copia questo testo e passalo al tuo agente specializzato nello sviluppo frontend/GUI.

***

# 📋 PRD Frontend: DroneCut GUI (CustomTkinter)

## 🎯 Obiettivo del Modulo
Sviluppare l'interfaccia utente desktop per **DroneCut**, un pre-processore video. L'app deve caricare progetti salvati (`.dcproj`), mostrare una galleria di clip video preselezionate e permettere all'utente di visualizzarle tramite un player integrato leggerissimo, selezionare le preferite ed esportarle.

## 🛠 Stack Tecnologico Frontend
* **Framework Principale:** `customtkinter` (Gestione finestre, bottoni, layout).
* **Tema:** Dark Mode forzata (`ctk.set_appearance_mode("dark")`).
* **Gestione Immagini/Video:** `Pillow` (PIL) e `opencv-python` (`cv2`). **Nota:** OpenCV è usato qui *solo* come motore di decodifica dei frame per il player integrato, non per l'analisi AI.
* **Concorrenza:** L'interfaccia non deve **mai** bloccarsi. Le chiamate ai video o agli script di esportazione devono usare il modulo `threading` o il metodo nativo `app.after()`.

---

## 📐 Layout Generale e Navigazione
L'applicazione consiste in una singola finestra (es. `1000x750` pixel, ridimensionabile).
Il routing tra le viste avviene distruggendo/nascondendo i `CTkFrame` attuali e renderizzando i nuovi.

### Vista 1: Home Screen (`HomeView`)
* **Componenti:**
    * Titolo App grande al centro.
    * Bottone Primario: **"✨ Nuovo Progetto AI"** -> Apre un `ctk.filedialog.askopenfilename` (solo `.mp4`, `.mov`).
    * Bottone Secondario: **"📂 Carica Progetto"** -> Apre un filedialog (solo `.dcproj`).
* **Azioni:** La selezione di un file innesca la transizione alla Vista 2 (se Nuovo) o alla Vista 3 (se Carica).

### Vista 2: Loading Screen (`LoadingView`)
* **Componenti:**
    * Etichetta di stato: `CTkLabel` (es. "Fase 2/4: Ricerca Semantica in corso...").
    * Barra di avanzamento: `CTkProgressBar` (modalità progressiva o circolare se supportata).
* **Azioni:** Questa vista resta in ascolto passivo dei segnali/eventi emessi dal thread del backend AI. Al completamento, transita automaticamente alla Vista 3.

### Vista 3: Review Gallery (`GalleryView`) - Il Core dell'App
* **Header (Alto):**
    * Nome del progetto (estratto dal JSON).
    * Bottone: "💾 Salva Modifiche" (Scrive lo stato dei checkbox nel `.dcproj`).
    * Bottone (Accento Visivo): **"🎬 Esporta Selezionate"**.
* **Area Principale (Centro):**
    * Un `CTkScrollableFrame` che occupa tutto lo spazio rimanente.
    * All'interno, una griglia o lista verticale che renderizza dinamicamente N componenti `ClipCard`.

---

## 🧩 Specifiche del Componente: `ClipCard`
La `ClipCard` è un frame riutilizzabile che rappresenta una singola scena proposta dall'AI.

**Struttura Visiva (`CTkFrame`):**
1.  **Video Display:** Un `CTkLabel` (dimensioni fisse, es. 320x180 px). Di default mostra l'immagine JPEG statica (la thumbnail).
2.  **Area Testo:** Un `CTkLabel` col titolo della clip (es. "Lago al tramonto") e un altro con la durata (es. "5.2 sec").
3.  **Controlli:**
    * Un `CTkButton` col testo "▶️ Play". Quando cliccato, il testo cambia in "⏹ Stop".
    * Un `CTkCheckBox` col testo "Esporta", selezionato di default. L'evento toggle di questo checkbox deve aggiornare la variabile booleana in memoria.

---

## 🎬 In-App Micro-Player (Logica di Riproduzione)
L'agente deve implementare il player video direttamente dentro la `ClipCard` usando OpenCV e Tkinter. 

**Flusso Operativo del Tasto "Play":**
1.  L'utente preme "▶️ Play".
2.  La classe istanzia `cap = cv2.VideoCapture(proxy_video_path)`.
3.  Esegue un salto temporale al punto di inizio della clip: `cap.set(cv2.CAP_PROP_POS_MSEC, start_ms)`.
4.  Avvia un metodo interno alla classe chiamato `_stream_frame()`.

**Il Loop `_stream_frame()` (CRITICO):**
* Legge il frame successivo (`cap.read()`).
* Controlla se il timestamp attuale `cap.get(cv2.CAP_PROP_POS_MSEC)` è maggiore di `end_ms`. Se sì, esegue l'operazione di Stop (vedi sotto).
* Converte il frame: `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)`, lo passa a `Image.fromarray`, crea un `CTkImage` e lo applica al `CTkLabel` del Video Display.
* Invece di usare un loop `while` o `time.sleep` (che bloccherebbero la GUI), il metodo richiama se stesso usando il loop degli eventi nativo di Tkinter: `self.after(33, self._stream_frame)` (33ms = ~30 FPS).

**Flusso Operativo dello "Stop":**
* Rilascia la risorsa video: `cap.release()`.
* Cancella l'istruzione `.after` in sospeso (per fermare il loop).
* Ripristina la `thumbnail` statica originaria sul `CTkLabel`.
* Riporta il testo del bottone a "▶️ Play".

---

## 🛡 Gestione degli Eventi e Connessioni (Mocks)
Visto che l'agente frontend non scriverà il backend, deve predisporre questi "vuoti" (funzioni fittizie o callback) da agganciare in seguito:

1.  `on_start_new_project(video_path)`: Scatena la transizione alla Vista 2.
2.  `on_export_requested(lista_clip_approvate)`: Quando premuto, cambia il cursore in "caricamento" e lancia una funzione in un thread separato (che in futuro chiamerà FFmpeg). Mostra un pop-up di successo al termine.
3.  **Controllo Player Esclusivo:** Assicurarsi che solo UNA `ClipCard` possa essere in riproduzione simultaneamente. Se l'utente preme Play sulla Clip 2, la Clip 1 deve arrestarsi automaticamente se era in riproduzione.