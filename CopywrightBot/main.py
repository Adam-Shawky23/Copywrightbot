from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import os
import json
import time
import re

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables for bot state
is_running = False
job_task = None
telethon_client = None
SENT_MESSAGES_FILE = 'sent_messages.json'
ACTIVE_CHAT_IDS_FILE = 'active_chat_ids.json'

# Credentials (replace with your new bot's credentials)
API_ID = '24300542'
API_HASH = '3879413077a541b3fd3b3786e17baa90'
BOT_TOKEN = '8049998764:AAGPjxFfFCw89ignSnfK1usY5V6uMG3RAYI'  # Fill in
BOT_CHAT_ID = ''  # Optional, for admin/debug

# Target channels and keywords (replace with your new bot's list)
CHANNELS = [
    '@sova_freelance', '@TRemoters', '@GetClient', '@freelance_chat_birzha', '@Freelaceworkchat', '@distantworkchat', '@pragmaticachat', '@freelance_chatik0', '@freelance_rabota_chat', '@pixeldischat', '@jobsrobot_chat', '@dizayneri_chat', '@pomogator1', '@freelance7', '@freelancce', '@workk_onchat', '@jobsikfree_bot', '@vakansii', '@novobranez','@kopirayter_kopirayting', '@self_ma', '@Work4writers', '@edit_zp', '@copywriter_vacancies', '@copy_go', '@rabota_udalennaya1', '@work_editor', '@textodromo', '@freelanceeboom'
]

KEYWORDS = [
    '#копирайтер',
    '#рерайтер',
    'Нужен копирайтер',
    'Ищу копирайтера',
    'Нужен рерайтер',
    'Ищу рерайтера',
    'Нужен текстовик',
    'Ищу текстовика',
    'Нужен редактор',
    'Ищу редактора',
    'Ищем копирайтера'
]

def load_sent_messages():
    try:
        if os.path.exists(SENT_MESSAGES_FILE):
            with open(SENT_MESSAGES_FILE, 'r') as f:
                return set(json.load(f))
    except Exception as e:
        logger.error(f"Error loading sent messages: {e}")
    return set()

def save_sent_messages(sent_messages):
    try:
        with open(SENT_MESSAGES_FILE, 'w') as f:
            json.dump(list(sent_messages), f)
    except Exception as e:
        logger.error(f"Error saving sent messages: {e}")

def clear_sent_messages():
    try:
        if os.path.exists(SENT_MESSAGES_FILE):
            os.remove(SENT_MESSAGES_FILE)
            logger.info("Cleared sent_messages.json")
    except Exception as e:
        logger.error(f"Error clearing sent messages: {e}")

def load_active_chat_ids():
    try:
        if os.path.exists(ACTIVE_CHAT_IDS_FILE):
            with open(ACTIVE_CHAT_IDS_FILE, 'r') as f:
                return set(json.load(f))
    except Exception as e:
        logger.error(f"Error loading active chat ids: {e}")
    return set()

def save_active_chat_ids(chat_ids):
    try:
        with open(ACTIVE_CHAT_IDS_FILE, 'w') as f:
            json.dump(list(chat_ids), f)
    except Exception as e:
        logger.error(f"Error saving active chat ids: {e}")

def has_exact_keyword(text, keywords):
    text_lower = text.lower()
    words = set(re.findall(r'#?\w+(?:-\w+)*', text_lower))
    return any(keyword.lower() in words for keyword in keywords)

async def setup_client():
    global telethon_client
    if not telethon_client:
        session_name = 'bot_user_session'
        from telethon.sessions import StringSession
        from telethon.errors import SessionPasswordNeededError
        telethon_client = TelegramClient(session_name, API_ID, API_HASH)
        if not os.path.exists(session_name + '.session'):
            print('No Telethon session found. Please log in with your user account.')
            await telethon_client.start()
            print('Telethon user session created and saved.')
        else:
            await telethon_client.start()

async def cleanup_client():
    global telethon_client
    if telethon_client:
        await telethon_client.disconnect()
        telethon_client = None

async def search_jobs(context: ContextTypes.DEFAULT_TYPE):
    global is_running, telethon_client
    if not telethon_client or not is_running:
        return
    sent_messages = load_sent_messages()
    active_chat_ids = load_active_chat_ids()
    for channel in CHANNELS:
        if not is_running:
            break
        try:
            entity = await telethon_client.get_entity(channel)
            history = await telethon_client(GetHistoryRequest(
                peer=entity,
                limit=50,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            for message in history.messages:
                if not is_running:
                    break
                if hasattr(message, 'message') and message.message:
                    logger.info(f"Fetched message from {channel}: {message.message}")
                    message_id = f"{channel}_{message.id}"
                    # Only send if message contains a Telegram username
                    if (message_id not in sent_messages and 
                        has_exact_keyword(message.message, KEYWORDS) and 
                        '#помогу' not in message.message.lower() and
                        re.search(r'@\w{5,}', message.message)):
                        for chat_id in active_chat_ids:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"{message.message}"
                            )
                        sent_messages.add(message_id)
                        save_sent_messages(sent_messages)
        except Exception as e:
            logger.error(f"Error processing channel {channel}: {str(e)}")
            continue

async def run_job_search(context: ContextTypes.DEFAULT_TYPE):
    global is_running
    while is_running:
        try:
            await search_jobs(context)
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in job search: {str(e)}")
            await asyncio.sleep(60)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global is_running, job_task
    chat_id = update.effective_chat.id
    active_chat_ids = load_active_chat_ids()
    active_chat_ids.add(chat_id)
    save_active_chat_ids(active_chat_ids)
    if is_running:
        await update.message.reply_text('Bot is already running! You will now receive job posts.')
        return
    await setup_client()
    is_running = True
    job_task = asyncio.create_task(run_job_search(context))
    await update.message.reply_text('Bot started! You will now receive job posts.')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global is_running, job_task, telethon_client
    chat_id = update.effective_chat.id
    active_chat_ids = load_active_chat_ids()
    if chat_id in active_chat_ids:
        active_chat_ids.remove(chat_id)
        save_active_chat_ids(active_chat_ids)
        await update.message.reply_text('You will no longer receive job posts.')
    else:
        await update.message.reply_text('You were not receiving job posts.')
    if not active_chat_ids and is_running:
        is_running = False
        if job_task:
            job_task.cancel()
            try:
                await job_task
            except asyncio.CancelledError:
                pass
            job_task = None
        await cleanup_client()
        await update.message.reply_text('Bot stopped!')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    active_chat_ids = load_active_chat_ids()
    if chat_id in active_chat_ids:
        status_msg = 'You are currently receiving job posts.'
    else:
        status_msg = 'You are not receiving job posts. Use /start to subscribe.'
    await update.message.reply_text(status_msg)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

def main() -> None:
    global is_running, telethon_client
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_error_handler(error_handler)
    print("Starting bot... Use Ctrl+C to stop")
    application.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    finally:
        is_running = False
        if telethon_client:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(cleanup_client())
                loop.close()
            except Exception as e:
                print(f"Error during cleanup: {e}")
        print("Bot cleanup completed")
