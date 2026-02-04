from datetime import datetime
import json
import os

DYNAMIC_SETTINGS_PATH = "config/dynamic_settings.json"

from ..storage.settings_storage import settings_storage

class ShiftLogic:
    @staticmethod
    def get_vision_prompt(target_user: str):
        # 1. Try to get from database
        db_prompt = settings_storage.get_setting("VISION_PROMPT")
        
        # Get current year for replacement
        reference_year = str(datetime.now().year)
        
        if db_prompt:
            prompt = db_prompt
            if "{{ target_user }}" in prompt:
                prompt = prompt.replace("{{ target_user }}", target_user)
            if "{{ reference_year }}" in prompt:
                prompt = prompt.replace("{{ reference_year }}", reference_year)
            
            # Fallback if target_user was not a placeholder but we need to pass it
            if "{{ target_user }}" not in db_prompt and target_user not in prompt:
                prompt = f"User: {target_user}\nReference Year: {reference_year}\n{prompt}"
                
            return prompt
             
        # 2. Hardcoded Fallback (Updated with User Version)
        return f"""
        ANALISI TURNI - PRECISIONE MILLIMETRICA RICHIESTA (OCR MODE)

        OBIETTIVO:
        Estrarre informazioni dai turni presenti nell’immagine.
        L’estrazione deve basarsi sui dati visibili; sono consentite
        SOLO le inferenze esplicitamente autorizzate.

        UTENTE SPECIFICO DA ESTRARRE: {target_user}

        PARAMETRO ESTERNO (NON DA INFERIRE):
        ANNO_DI_RIFERIMENTO = {reference_year}

        REGOLE ASSOLUTE:
        - L’ANNO DI RIFERIMENTO è ESATTAMENTE {reference_year}.
        - NON calcolare, verificare o correggere l’anno.
        - NON usare il calendario per validare i giorni della settimana.
        - NON usare calendari esterni per coerenza logica.
        - L’anno NON è un’informazione visiva: è un parametro fisso.

        SVOLGI IL COMPITO:
        1. Identifica mese e giorno visibili.
        2. Combinali con ANNO_DI_RIFERIMENTO senza verifiche.
        3. Estrai i turni SOLO per '{target_user}'.

        GESTIONE ERRORE:
        - Se '{target_user}' non è presente:
          restituisci SOLO:
          {{ "errore": "Utente non trovato nella tabella dei turni" }}

        FORMATO JSON (OBBLIGATORIO):
        {{
          "anno_riferimento": {reference_year},
          "turni": [
            {{
              "data": "{reference_year}-MM-DD",
              "giorno": "Lunedì",
              "slot_1": "HH:MM-HH:MM",
              "slot_2": "HH:MM-HH:MM"
            }}
          ]
        }}
        """.strip()

    @staticmethod
    def get_nlp_prompt(user_query: str, current_shifts_context: str):
        # 1. Try to get from database
        db_prompt = settings_storage.get_setting("NLP_PROMPT")
        
        base = db_prompt or "Sei un assistente per i turni di lavoro. Rispondi alla domanda: {user_query} usando questo contesto: {context}"
        
        try:
            return base.format(
                current_date=datetime.now().strftime('%Y-%m-%d'),
                context=current_shifts_context,
                user_query=user_query
            )
        except Exception:
            # Fallback if format tokens mismatch
            return f"{base}\n\nContesto: {current_shifts_context}\nDomanda: {user_query}"

    @staticmethod
    def parse_dates_from_header(header_str: str):
        return [datetime.now().strftime('%Y-%m-%d')]
