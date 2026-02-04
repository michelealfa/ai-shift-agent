import os
import asyncio
import json
import logging
from celery import Celery
from telegram import Bot
from ..config.config import settings
from ..ai.gemini_client import GeminiClient
from ..ai.prompts import ShiftLogic
from ..storage.sheets_client import SheetsClient

logger = logging.getLogger(__name__)

celery_app = Celery(
    'shift_agent_tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Client instances are now created dynamically within tasks to support multi-tenancy

@celery_app.task(name="process_shift_image")
def process_shift_image_task(image_path: str, chat_id: int = None, user_id: int = None, target_user: str = None, web_mode: bool = False, user_settings: dict = None):
    """Processed shift image using Gemini Vision AI."""
    logger.info(f"Avvio elaborazione immagine Gemini: {image_path}. Web mode: {web_mode}")
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(process_image_logic(image_path, chat_id, target_user, web_mode, user_settings))

async def process_image_logic(image_path: str, chat_id: int, target_user: str, web_mode: bool, user_settings: dict = None):
    user_settings = user_settings or {}
    gemini_key = user_settings.get("gemini_api_key")
    
    # Initialize dynamic clients
    gemini = GeminiClient(api_key=gemini_key)
    
    bot = None
    if not web_mode and chat_id:
        try:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        except Exception as e:
            logger.error(f"Errore inizializzazione bot: {e}")

    target_user = target_user or settings.TARGET_USER_NAME
    settings.load_dynamic_settings()
    logger.info(f"Target User for extraction: {target_user}")
    try:
        # 1. Vision OCR con Gemini
        prompt = ShiftLogic.get_vision_prompt(target_user)
        logger.info(f"Sending prompt to Gemini: {prompt}")
        result = await gemini.analyze_image(image_path, prompt)
        
        # 2. Parsing dei dati
        raw_response = result.get("response", "{}")
        logger.info(f"Raw Gemini response: {raw_response}")
        
        # Pulizia robusta del JSON ritorno da Gemini (che spesso mette markdown)
        if "```json" in raw_response:
            raw_response = raw_response.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_response:
            raw_response = raw_response.split("```")[1].split("```")[0].strip()
        
        try:
            # Gemini a volte restituisce testo extra prima/dopo il JSON se il prompt non è perfetto
            # Cerchiamo di trovare l'inizio e la fine del JSON
            start_idx = raw_response.find('{')
            end_idx = raw_response.rfind('}')
            if start_idx != -1 and end_idx != -1:
                raw_response = raw_response[start_idx:end_idx+1]
                
            parsed_data = json.loads(raw_response)
        except Exception as e:
            logger.error(f"Parsing error: {e}. Raw input: {raw_response}")
            parsed_data = {"error": "JSON malformato", "raw": raw_response}

        if web_mode:
            return parsed_data
        
        if bot:
            await bot.send_message(chat_id=chat_id, text="✅ Analisi Gemini completata!")
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Task Gemini error: {e}")
        if bot:
            await bot.send_message(chat_id=chat_id, text=f"⚠️ Errore durante l'elaborazione Gemini: {str(e)}")
        return {"error": str(e)}
    finally:
        # Cleanup file temporaneo
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass
