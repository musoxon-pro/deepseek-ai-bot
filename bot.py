import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import asyncio

# Loglash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token va API kalitlari
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Flask ilovasi
flask_app = Flask(__name__)

# Telegram Application (global)
application = None

async def deepseek_response(user_message: str) -> str:
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
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
        return "Kechirasiz, hozir javob bera olmayman. Birozdan so‘ng urinib ko‘ring."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Assalomu alaykum! Men Deepseek AI botiman. Savolingizni yozing.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Xabar: {user_text}")
    await update.message.chat.send_action(action="typing")
    reply = await deepseek_response(user_text)
    await update.message.reply_text(reply)

def setup_application():
    global application
    if application is None:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return application

async def setup_webhook_async():
    """Webhook o‘rnatish (asinxron versiya)"""
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL')
    if not webhook_url:
        logger.warning("RENDER_EXTERNAL_URL topilmadi. Webhook o‘rnatilmadi.")
        return
    
    full_url = f"{webhook_url.rstrip('/')}/webhook"
    try:
        # Bot yaratish
        bot = Bot(token=TELEGRAM_TOKEN)
        
        # Mavjud webhookni tekshirish
        webhook_info = await bot.get_webhook_info()
        
        if webhook_info.url != full_url:
            await bot.set_webhook(url=full_url)
            logger.info(f"Webhook o‘rnatildi: {full_url}")
        else:
            logger.info("Webhook allaqachon to‘g‘ri o‘rnatilgan.")
    except Exception as e:
        logger.error(f"Webhook o‘rnatishda xatolik: {e}")

def setup_webhook_sync():
    """Webhook o‘rnatish (sinxron wrapper)"""
    try:
        # Yangi event loop yaratish
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_webhook_async())
        loop.close()
    except Exception as e:
        logger.error(f"Webhook o‘rnatishda xatolik (sync wrapper): {e}")

# Webhook o‘rnatish (sinxron wrapper orqali)
setup_webhook_sync()

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        # Application mavjudligini tekshirish
        app = setup_application()
        
        # Yangi event loop yaratish
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            update = Update.de_json(request.get_json(force=True), app.bot)
            loop.run_until_complete(app.process_update(update))
        except Exception as e:
            logger.error(f"Webhook processing xatosi: {e}")
        finally:
            loop.close()
            
        return 'OK', 200
    return 'OK', 200

@flask_app.route('/')
def index():
    return "Bot ishlayapti!", 200

# Gunicorn uchun WSGI entry point
app = flask_app

if __name__ == '__main__':
    setup_application()
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)
