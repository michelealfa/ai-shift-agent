# AI Shift Agent 🚀

Sistema intelligente per la gestione dei turni lavorativi tramite AI (Google Gemini) e PostgreSQL.

## ✨ Caratteristiche Principali

- **📸 Vision OCR**: Estrazione automatica dei turni da immagini (foto di tabelle turni) con Google Gemini 2.0 Flash.
- **💬 AI Assistant**: Chatbot integrato per interrogare i propri turni ("Quando lavoro domani?", "Quante ore ho fatto questa settimana?").
- **📊 Admin Dashboard**: Pannello di controllo per la gestione utenti, reset chiavi API, personalizzazione dei prompt AI e monitoraggio log.
- **🚗 Traffic Matrix**: Calcolo del tempo di percorrenza verso il luogo di lavoro (Arese) integrato con Google Maps Distance Matrix.
- **📱 Mobile First**: Interfaccia web ottimizzata per smartphone con carosello turni a 3 settimane (passato, corrente, futuro).
- **🔄 Google Sheets Sync**: Sincronizzazione opzionale con fogli Google per ogni utente.

## 🚀 Deploy su Render

Il progetto è configurato per il deploy immediato su **Render** tramite il file `render.yaml` (Blueprint).

### Passaggi per il Rilascio:
1. Collega il tuo repository GitHub a Render.
2. Crea una nuova **Blueprint Instance**.
3. Configura le seguenti variabili d'ambiente nel gruppo `shift-agent-secrets`:
   - `GEMINI_API_KEY`: La tua chiave per Google AI Studio.
   - `TELEGRAM_BOT_TOKEN`: Il token del tuo bot Telegram.
   - `TELEGRAM_WEBHOOK_URL`: URL del tuo web service su Render + `/webhook`.
   - `GOOGLE_MAPS_API_KEY`: Chiave Google Cloud con Distance Matrix abilitata.
   - `X_API_KEY`: Una chiave statica a tua scelta per proteggere l'API.

## 🛠️ Stack Tecnologico
- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **AI**: Google Gemini Pro/Flash
- **Infrastruttura**: Docker & Render Blueprint

---
Sviluppato con ❤️ per ottimizzare la gestione dei turni.
