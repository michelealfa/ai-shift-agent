# PRD: AI Shift Manager (Web-Front Edition)

## 1. Executive Summary
**Obiettivo:** Trasformare l'assistente turni da un bot Telegram a una Web Application proprietaria. 
**Finalità:** Consentire l'upload diretto della foto dei turni, l'anteprima dei dati estratti dall'AI (Llama 3.2 Vision) e una fase di validazione manuale (Human-in-the-loop) prima del salvataggio definitivo su Google Sheets.

---

## 2. Architettura del Sistema
Il sistema adotta un'architettura **Client-Server** containerizzata su VPS.



### 2.1 Componenti Tecnologici
* **Frontend:** Single Page Application (SPA) in HTML5/JS (o React/Vue) per la gestione dell'interfaccia utente.
* **Backend API (FastAPI):** Orchestratore delle richieste, gestione degli endpoint REST e dei task asincroni.
* **Task Queue (Celery + Redis):** Gestione dei carichi di lavoro pesanti (inferenza Vision AI) per garantire la reattività del frontend.
* **AI Engine (Ollama):** Modelli Open Source (Llama 3.2 Vision per OCR; Llama 3.1 per NLP).
* **Database:** Google Sheets API tramite service account.

---

## 3. Analisi Funzionale e Flussi Logici

### 3.1 Flusso di Lavoro: "Upload, Review & Commit"
Il processo è strutturato per massimizzare la precisione eliminando gli errori di "allucinazione" dell'AI:

1.  **Upload & Ingestione:** L'utente carica l'immagine e specifica il `Target_User` nel frontend.
2.  **Processing Asincrono:** Il backend salva il file e accoda un task Celery. Il frontend riceve un `task_id` e mostra uno stato di caricamento.
3.  **Anteprima Dati (Revisione):** Una volta completata l'analisi di Ollama, il frontend riceve un JSON e popola una **Griglia Editabile**.
4.  **Validazione Umana:** L'utente controlla gli orari estratti e corregge eventuali refusi o errori di lettura.
5.  **Commit Finale:** Al click su "Sal