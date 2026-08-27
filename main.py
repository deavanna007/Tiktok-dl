import telebot
from telebot import types
import requests
import os
from flask import Flask
import threading

# កំណត់ Token និងព័ត៌មាន Bot
TOKEN = os.getenv('BOT_TOKEN') or "8793230190:AAG16cBXtVAm8tSFSC9zE6CNBgnIq5qEO8U"
DEVELOPER_NAME = "@deavanna1"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

# Storage បណ្ដោះអាសន្ន
media_cache = {}

def save_user(user_id):
    pass

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 ជម្រាបសួរ! សូមផ្ញើ Link TikTok ដើម្បីទាញយក Video ឬ MP3។")

@bot.message_handler(func=lambda message: "tiktok.com" in message.text)
def handle_tiktok(message):
    save_user(message.chat.id)
    
    raw_url = message.text.strip()
    clean_url = raw_url.split('?')[0]
    
    status_msg = bot.reply_to(message, "🔎 *កំពុងទាញយកទិន្នន័យ...*", parse_mode='Markdown')

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }

    # ប្រើ API ជំនួស Cobalt API
    payload = {"url": clean_url}
    video_url = None
    title = "TikTok Video"

    try:
        # API Backup ទី ១: Tikwm Rapid fallback
        req = requests.get(f"https://api.tiklydown.eu.org/api/download?url={clean_url}", timeout=10)
        if req.status_code == 200:
            res = req.json()
            video_url = res.get('video', {}).get('noWatermark') or res.get('url')
            title = res.get('title', 'TikTok Content')
    except Exception:
        pass

    # API Backup ទី ២ (ករណីទី ១ ដើរមិនរួច)
    if not video_url:
        try:
            req = requests.get(f"https://www.tikwm.com/api/?url={clean_url}", timeout=10)
            if req.status_code == 200 and req.json().get('code') == 0:
                data = req.json()['data']
                video_url = data.get('play')
                title = data.get('title', 'TikTok Content')
        except Exception:
            pass

    if video_url:
        try:
            bot.delete_message(message.chat.id, status_msg.message_id)
        except Exception:
            pass
        
        bot.send_video(
            message.chat.id,
            video_url,
            caption=f"🎬 *{title}*\n\n👨‍💻 *Bot by:* {DEVELOPER_NAME}",
            parse_mode='Markdown'
        )
    else:
        try:
            bot.edit_message_text(
                "❌ *មិនអាចទាញយកបានទេ!* អាសយដ្ឋាន Link នេះអាចនឹងមានបញ្ហា ឬ API ត្រូវគេកំណត់ដែនកំណត់។",
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                parse_mode='Markdown'
            )
        except Exception:
            bot.send_message(message.chat.id, "❌ *មិនអាចទាញយកបានទេ!* សូមព្យាយាមម្ដងទៀត។", parse_mode='Markdown')

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.infinity_polling(skip_pending_updates=True)
