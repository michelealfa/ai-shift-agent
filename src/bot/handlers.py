import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from ..config.config import settings
from ..tasks.worker import process_shift_image_task

# Configure logging
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started the bot.")
    if user_id not in settings.TELEGRAM_ALLOWED_USERS:
        logger.warning(f"Unauthorized user {user_id} tried to start the bot.")
        return
    await update.message.reply_text(
        f"Ciao {update.effective_user.first_name}! 👋\n\n"
        "Sono il tuo assistente per i turni.\n"
        "📸 Inviami la foto della tabella orari per aggiornare i tuoi dati.\n"
        "💬 Oppure chiedimi: 'Cosa faccio domani?' o 'Che turni ho sabato?'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in settings.TELEGRAM_ALLOWED_USERS:
        return
    
    # Gestione Immagini (OCR Process)
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        os.makedirs("temp", exist_ok=True)
        file_path = f"temp/{photo_file.file_id}.jpg"
        await photo_file.download_to_drive(file_path)
        
        await update.message.reply_text("📥 Immagine ricevuta! Sto analizzando la tabella... Ti avviserò appena finito (max 30s).")
        
        # Trigger Celery Task async
        process_shift_image_task.delay(file_path, update.effective_chat.id, user_id)
        return

    # Gestione Testo (NLP Query)
    if update.message.text:
        # Qui si chiamerebbe OllamaClient e poi SheetsClient per rispondere
        # Per ora simuliamo la ricezione
        await update.message.reply_text("💡 Sto consultando il tuo calendario... Un attimo.")
        # NLP logic integration point
        return

async def handle_webhook(data: dict):
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Aggiungi handler se non sono già stati aggiunti (in un'app reale questo si fa diversamente)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, handle_message))
    
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
