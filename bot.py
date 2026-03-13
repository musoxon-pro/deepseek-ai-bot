import os
import logging
from flask import Flask, request
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import asyncio

# Loglash sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token va kalitlar
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # Deepseek API endpoint

# Flask ilovasi (webhook uchun)
flask_app = Flask(__name__)

# Telegram Application obyekti (global)
application = None

async def deepseek_response(user_message: str) -> str:
    """Deepseek API dan javob olish"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",  # yoki boshqa model nomi
        "messages": [{"role": "user", "content": user_message}],
        "temperature": 0.7
    }
    try:
        response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"Deepseek API xatosi: {e}")
        return "Kechirasiz, hozir javob bera olmayapman. Birozdan so‘ng urinib ko‘ring."

async def start(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Assalomu alaykum! Men Deepseek AI botiman. Savolingizni yozing.")

async def handle_message(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Xabar: {user_text}")
    # Yozayotgan holatini ko‘rsatish
    await update.message.chat.send_action(action=telegram.constants.ChatAction.TYPING)
    # Deepseek API dan javob olish
    reply = await deepseek_response(user_text)
    await update.message.reply_text(reply)

def setup_application():
    """Telegram Application ni yaratish va handlerlarni ulash"""
    global application
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return application

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint"""
    if request.method == 'POST':
        update = telegram.Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run_coroutine_threadsafe(application.process_update(update), application.loop)
        return 'OK', 200
    return 'OK', 200

@flask_app.route('/')
def index():
    return "Bot ishlayapti!", 200

if __name__ == '__main__':
    # Application ni sozlash
    setup_application()
    # Webhook ni o‘rnatish (faqat bir marta bajariladi, lekin har safar ishga tushganda ham zarar qilmaydi)
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL')  # Render tomonidan avtomatik beriladi
    if webhook_url:
        webhook_full = f"{webhook_url.rstrip('/')}/webhook"
        application.bot.set_webhook(url=webhook_full)
        logger.info(f"Webhook o‘rnatildi: {webhook_full}")
    else:
        logger.warning("RENDER_EXTERNAL_URL topilmadi, webhook o‘rnatilmadi. Iltimos, o‘z qo‘lingiz bilan o‘rnating.")
    # Flask serverni ishga tushirish (Render 10000 portni kuzatadi)
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)
