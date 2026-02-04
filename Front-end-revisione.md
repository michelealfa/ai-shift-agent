# 📄 PRD: AI Shift & Traffic Intelligence System

## 1. VISIONE DEL PROGETTO
**Obiettivo:** Automatizzare la gestione dei turni lavorativi e l'assistenza al pendolarismo tramite un'applicazione web privata.
**Funzionalità Core:** 1. Estrazione turni da foto tramite Vision AI.
2. Sincronizzazione su Google Sheets con validazione umana.
3. Chatbot per query sui turni e calcolo traffico intelligente (Origgio -> Arese).

---

## 2. ARCHITETTURA TECNICA (FULL-STACK)
Il sistema è distribuito su container Docker per garantire portabilità e isolamento.



* **Frontend:** SPA Mobile-First (HTML5, Tailwind CSS, Vue/React).
* **Backend:** FastAPI (Python 3.10+).
* **Worker:** Celery + Redis (Task asincroni per AI).
* **AI Models:** Ollama (Llama 3.2 Vision) per OCR; Llama 3.1 per NLP e analisi traffico.
* **External APIs:** Google Sheets API v4 e Google Maps Distance Matrix API.

---

## 3. ANALISI FUNZIONALE DETTAGLIATA (FRONTEND)

### 3.1 Dashboard & Widget
L'interfaccia deve presentare i dati in modo modulare:
* **Carousel Turni:** Card dinamiche che mostrano i dati presenti su Google Sheets (Data, Giorno, Slot 1, Slot 2).
* **Traffic Insight Widget:** * **Origine:** Toggle rapido `[CASA (Origgio)]` | `[GPS]` | `[ALTRO]`.
    * **Destinazione:** Statica `"Il Centro, Arese"`.
    * **Display:** Tempo di percorrenza in tempo reale, colore semaforico (Verde/Giallo/Rosso) e orario di partenza consigliato per non tardare al turno.

### 3.2 Flusso OCR & Validazione (Human-in-the-loop)
1.  **Upload:** Input con `capture="camera"` per attivare la fotocamera mobile.
2.  **Attesa:** Spinner con log di stato ("Analisi riga 'VALENTINA' in corso...").
3.  **Griglia Editabile:** Post-analisi, i dati appaiono in una tabella con input `type="time"`. L'utente può modificare, aggiungere o eliminare slot prima del commit finale.

---

## 4. LOGICA DI BUSINESS (BACKEND)

### 4.1 Modulo Vision AI (OCR)
* **Prompt:** Deve estrarre i dati solo per il `TARGET_USER_NAME`.
* **Formato:** Deve restituire un JSON strutturato: `{"shifts": [{"date": "YYYY-MM-DD", "slots": ["08:00-14:00"]}]}`.
* **Enrichment:** Il backend converte i giorni della settimana (es. "Lunedì 2") in date assolute basandosi sulla settimana corrente.

### 4.2 Traffic Intelligence Engine
Il calcolo del traffico segue regole rigide:
1.  **Input:** Origine (scelta da front), Destinazione (Arese), Orario Turno (da Sheets).
2.  **API Maps:** Chiamata a `googlemaps.distance_matrix` con parametro `departure_time="now"` o `arrival_time`.
3.  **Logica di Allerta:** Se `tempo_percorrenza + 5min (margine) > ora_inizio_turno`, invia un'allerta rossa "Ritardo Probabile".

### 4.3 Sync Engine (Google Sheets)
* **Metodo:** Upsert (Update or Insert).
* **Chiave:** Data + Nome Utente.
* **Persistenza:** Una volta confermati i dati dal front, il backend aggiorna le colonne `Slot_1`, `Slot_2` e inserisce un timestamp di validazione.

---

## 5. SPECIFICHE TECNICHE API

| Endpoint | Metodo | Descrizione |
| :--- | :--- | :--- |
| `/api/upload` | `POST` | Riceve immagine + target_name. Restituisce `task_id`. |
| `/api/status/{id}`| `GET` | Polling per recuperare i turni estratti da Ollama. |
| `/api/confirm` | `POST` | Riceve JSON validato e scrive su Google Sheets. |
| `/api/traffic` | `GET` | Calcola traffico Origgio -> Arese (o GPS -> Arese). |
| `/api/query` | `POST` | NLP Chat per domande (es. "Quante ore ho fatto?"). |

---

## 6. CRITERI DI ACCETTAZIONE (AC)
* **AC1:** Il toggle "CASA" deve forzare l'origine a "Origgio" senza errori di geolocalizzazione.
* **AC2:** La tabella di revisione deve gestire turni spezzati (es. Mattina + Pomeriggio).
* **AC3:** Il sistema deve rispondere alle domande sul traffico entro 3 secondi.
* **AC4:** L'accesso al sistema deve essere limitato tramite `X-API-KEY` statica definita nel file `.env`.

---

## 7. CONFIGURAZIONE DEPLOYMENT (DOCKER-COMPOSE)
```yaml
services:
  frontend: (Nginx serving static files)
  backend: (FastAPI server)
  worker: (Celery worker for AI tasks)
  redis: (Task broker)
  ollama: (Local AI inference)