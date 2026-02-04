# 📄 PRD: AI Shift & Traffic Assistant (Ultimate Master Edition)

## 1. VISIONE DEL PROGETTO
Automatizzare l'estrazione dei turni lavorativi tramite Vision AI, centralizzare i dati su Google Sheets e fornire assistenza intelligente per il pendolarismo sulla tratta **Origgio -> Arese**, con gestione multi-utente e pannello di controllo centralizzato per l'amministratore.

---

## 2. ARCHITETTURA DI SISTEMA
L'ecosistema è progettato per essere scalabile e containerizzato, separando la logica di business dall'inferenza pesante dei modelli Vision.



* **Frontend:** SPA Mobile-First (HTML5, Tailwind CSS, Vue.js/React).
* **Backend:** FastAPI (Python) per gestione logica core, IAM dinamico e API proxy.
* **AI Engine:** Ollama (Llama 3.2 Vision) per OCR; Llama 3.1 per analisi dati e NLP.
* **Storage:** Google Sheets API v4 (Fogli: `Turni_Dati`, `Admin_Users`, `System_Config`).
* **External API:** Google Maps Distance Matrix per calcolo traffico in tempo reale.

---

## 3. IDENTITY & ACCESS MANAGEMENT (IAM)

### 3.1 Startup & User Selection
All'avvio, l'applicazione non permette l'accesso diretto ai dati senza identificazione.
1. **Chiamata Public:** Il frontend esegue `GET /api/public/users`.
2. **User Picker:** Viene mostrata una griglia con foto profilo e nomi.
3. **Persistenza:** Una volta selezionato l'utente, la `X-API-KEY` univoca viene salvata nel `localStorage`. Ogni chiamata successiva include l'header `Authorization: Bearer <KEY>`.

### ✅ CRITERI DI ACCETTAZIONE (CA) - IAM
* **CA.IAM.1:** La select deve caricare i dati in < 1 secondo dal database.
* **CA.IAM.2:** In assenza di `X-API-KEY` nel localStorage, l'utente deve essere sempre reindirizzato alla selezione profilo.
* **CA.IAM.3:** Se un utente viene disabilitato dal pannello Admin, la sua chiave deve smettere di funzionare istantaneamente (errore 401).

---

## 4. WORKFLOW UTENTE E UX (USER ACTIONS)

### 4.1 Flusso A: Ingestione Turni (OCR)
1. **Azione:** Clic su "📷 Carica Foto". Il sistema apre la fotocamera nativa.
2. **Stato:** Visualizzazione spinner di caricamento con log in tempo reale.
3. **Azione:** Revisione dei dati estratti in una tabella editabile (Review Table).
4. **Azione:** Clic su "Salva" per eseguire l'Upsert su Google Sheets.

### ✅ CRITERI DI ACCETTAZIONE (CA) - OCR
* **CA.OCR.1:** L'AI deve ignorare simboli grafici (🎵) e testo non inerente agli orari.
* **CA.OCR.2:** Se la cella contiene più turni, il primo deve finire in `slot_1`, i rimanenti concatenati in `slot_2`.
* **CA.OCR.3:** In caso di errore nel caricamento su Google Sheets, i dati devono rimanere editabili nel frontend per permettere un nuovo tentativo.

---

## 5. MODULO TRAFFIC INTELLIGENCE (ORIGGIO ↔ ARESE)

### 5.1 Calcolo Dinamico
Calcolo delle condizioni di viaggio per la destinazione fissa: **"Il Centro, Arese"**.

### ✅ CRITERI DI ACCETTAZIONE (CA) - TRAFFICO
* **CA.TRA.1:** Il widget deve mostrare il tempo di percorrenza esatto restituito dalle API di Maps.
* **CA.TRA.2:** Il colore del widget deve cambiare: **Verde** (<15m), **Giallo** (15-25m), **Rosso** (>25m).
* **CA.TRA.3:** Lo switch tra Origgio (Casa) e GPS deve aggiornare il calcolo in < 2 secondi.

---

## 6. STRUTTURA PANNELLO ADMIN
Accessibile tramite rotta protetta `/admin`, permette il controllo granulare del sistema.

### 6.1 Funzionalità Admin
* **Gestione Utenti:** Creazione profili, generazione `X-API-KEY` e gestione foto.
* **Log di Sistema:** Monitoraggio degli ultimi 100 log (Errori OCR, Sync, API).
* **Gestione Prompt:** Editor per modificare le istruzioni inviate a Ollama.

### ✅ CRITERI DI ACCETTAZIONE (CA) - ADMIN
* **CA.ADM.1:** La modifica del "System Prompt" deve avere effetto immediato sul caricamento successivo di un'immagine.
* **CA.ADM.2:** I log devono indicare chiaramente l'ID Utente associato ad ogni azione per permettere il debugging mirato.
* **CA.ADM.3:** L'Admin deve poter resettare la password/key di un utente senza cancellarne i dati storici.

---

## 7. CASI D'USO (CS) - SCENARI UTENTE

### CS 1: Inserimento Turni Settimanali
**Scenario:** Valentina riceve la tabella e la carica. L'AI estrae i dati per la sua riga specifica e lei conferma l'inserimento.
**Esito:** I turni appaiono nel foglio Google Sheets correttamente mappati per data.

### CS 2: Calcolo Partenza Pendolare
**Scenario:** Valentina vede che il turno inizia alle 10:00. Il widget segnala traffico intenso (28 min). 
**Esito:** Il sistema suggerisce di partire entro le 09:25.

---

## 8. PROMPT AI OTTIMIZZATO (FEW-SHOT)
```text
Analizza l'immagine per l'utente {target_user}. 
REGOLE: 
1. Estrai orari pulendo simboli grafici (es. 🎵). 
2. Primo orario in 'slot_1', altri in 'slot_2' separati da virgola. 
3. Se la cella è vuota, scrivi 'RIPOSO'.
Input esempio: "🎵 08:30-12:30, 13:30-15:30" 
Output JSON: {"slot_1": "08:30-12:30", "slot_2": "13:30-15:30"}