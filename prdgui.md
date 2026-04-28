Ecco il **PRD (Product Requirements Document) definitivo per la GUI di DroneCut**, strutturato appositamente per essere copiato e incollato al tuo agente AI (Cursor, Devin, ecc.). 

Questo documento si concentra esclusivamente sulla costruzione dell'interfaccia con **CustomTkinter**, garantendo un design moderno, scuro (Dark Mode nativa macOS) e una reattività perfetta (zero blocchi dell'interfaccia durante i calcoli pesanti).

***

# 📋 PRD: DroneCut App - Interfaccia Grafica (GUI)

## Contesto per l'Agente AI
Devi sviluppare l'interfaccia utente desktop per **DroneCut**, un'applicazione Python basata su intelligenza artificiale per il montaggio video automatizzato. L'elaborazione AI (backend) è pesante ed è già strutturata in una classe `DroneCutPipeline`.
Il tuo compito è costruire una GUI moderna e reattiva che permetta all'utente di selezionare il video, inserire istruzioni testuali, monitorare l'avanzamento e visualizzare i risultati.

**Stack Tecnologico e Regole Rigide:**
* **Framework GUI:** Esclusivamente `customtkinter` (Dark Mode predefinita).
* **Gestione Immagini:** `Pillow` (PIL) combinato con `ctk.CTkImage` per il rendering delle miniature.
* **Concorrenza (CRITICO):** La GUI **non deve mai bloccarsi** (niente *spinning beach ball* su macOS). Tutte le chiamate al backend (`DroneCutPipeline.run()`) devono essere eseguite all'interno di un `threading.Thread` separato. L'aggiornamento della GUI dal thread secondario deve avvenire tramite `app.after()` o callback sicure.

---

## 📐 Layout Strutturale (Design System)

L'interfaccia deve essere a finestra singola (`800x700` pixel, ridimensionabile), divisa verticalmente in 4 sezioni logiche:

1.  **Header:** Titolo dell'app ("DroneCut 🚁") e un sottotitolo descrittivo.
2.  **Input & Settings Section:**
    * Un grande pulsante `CTkButton` per selezionare il file video originale (apre il file dialog nativo di sistema).
    * Un campo testuale `CTkEntry` per la **Ricerca Tematica Opzionale** (es. *"Montaggio dinamico incentrato sul furgone"*). Questo input verrà passato al VLM nel backend.
3.  **Monitoring Section (Nascosta di default, visibile in elaborazione):**
    * Una label `CTkLabel` per mostrare lo stato attuale (es. *"Fase 3/6: Rilevamento Outlier Semantici..."*).
    * Una barra di avanzamento `CTkProgressBar` (modalità *determinate*).
4.  **Results Gallery (Nascosta di default, visibile a fine analisi):**
    * Un'area scorrevole `CTkScrollableFrame`.
    * All'interno, una griglia che popola dinamicamente le miniature (thumbnail) delle clip selezionate dall'AI, affiancate dalle loro descrizioni testuali.
    * Un pulsante "Esporta Selezionate" (FFmpeg Render) ancorato in basso.

---

## 🚀 Milestone di Sviluppo per l'Agente

### **Milestone 1: Scheletro e Layout di Base**
* **Azione:** Crea il file `gui.py`. Inizializza l'app CustomTkinter con tema scuro e colore di accento blu/teal.
* **Componenti:** Implementa tutte le 4 sezioni descritte nel Design System.
* **Logica Iniziale:** Implementa la funzione `seleziona_file()` che usa `customtkinter.filedialog` per far scegliere un file `.mp4` o `.mov` e aggiorna una label con il nome del file scelto.

### **Milestone 2: Integrazione Threading e Callback**
* **Azione:** Connetti il pulsante "Inizia Analisi" alla pipeline di backend.
* **Threading:** Quando l'utente clicca il pulsante, avvia un `threading.Thread(target=self.run_pipeline)`.
* **Callback:** Passa alla pipeline una funzione `progress_callback(status_text: str, progress_float: float)`. Assicurati di usare il metodo `.after()` di Tkinter se devi aggiornare i widget della GUI dal thread secondario, per evitare crash critici di macOS.
* **UI Update:** Durante l'esecuzione, disabilita il pulsante di avvio, mostra la Monitoring Section e fai avanzare la `CTkProgressBar`.

### **Milestone 3: Risultati e Galleria Dinamica**
* **Azione:** Gestisci il ritorno dei dati a fine elaborazione. Il backend restituirà una lista di dizionari: `[{"thumbnail_path": "...", "caption": "...", "start": 10.5, "end": 15.0}]`.
* **Rendering Thumbnail:** Itera sulla lista. Per ogni elemento, carica l'immagine con `PIL.Image`, ridimensionala (es. 200x120), trasformala in `CTkImage` e inseriscila nella `Results Gallery`.
* **Struttura Griglia:** Per ogni clip mostra l'immagine a sinistra e i metadati (caption e durata) a destra in modo pulito e allineato.

### **Milestone 4: Script di Packaging (PyInstaller)**
* **Azione:** Crea un file `build_mac.py` (o un `.spec`) per compilare la GUI in un'applicazione standalone `.app`.
* **Parametri PyInstaller:** * Usa la flag `--windowed` (o `--noconsole`) per nascondere il terminale.
    * Includi espressamente `customtkinter` come *hidden import* (è fondamentale perché PyInstaller spesso lo ignora).
    * Aggiungi l'istruzione `--add-data` per includere eventuali icone o asset grafici.

---

## 🛡️ Gestione Errori e UX (User Experience)
* **Filtro Estensioni:** Il selettore file deve permettere solo estensioni video (`.mp4`, `.mov`, `.mkv`).
* **Errori Backend:** Avvolgi la chiamata al thread in un blocco `try/except`. Se la pipeline AI fallisce, catcha l'eccezione e mostra un pop-up nativo o un messaggio d'errore rosso nell'interfaccia tramite un `CTkLabel` dedicato. Ripristina l'interfaccia allo stato iniziale per permettere un nuovo tentativo.
* **Cleanup Visivo:** Quando l'utente preme "Nuovo Progetto" o seleziona un nuovo video, svuota programmaticamente il `CTkScrollableFrame` distruggendo i vecchi widget delle miniature (`widget.destroy()`).