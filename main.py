import json
import os
import threading
import requests
import telebot
from telebot import types
from flask import Flask

# --- បង្កើត Web Server តូចមួយសម្រាប់ Render / UptimeRobot Ping ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live!", 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- កំណត់ព័ត៌មានបឋម ---
API_TOKEN = '8793230190:AAG16cBXtVAm8tSFSC9zE6CNBgnIq5qEO8U'
ADMIN_ID = 6953887858
DB_FILE = 'users.json'
DEVELOPER_NAME = '[Dea Vanna](https://t.me/deavanna1)'

bot = telebot.TeleBot(API_TOKEN)
media_cache = {}

def save_user(user_id):
    users = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except json.JSONDecodeError:
            users = []

    if user_id not in users:
        users.append(user_id)
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    save_user(message.chat.id)
    welcome_text = (
        f"👋 *សួស្តី!* ខ្ញុំជា Bot ទាញយកវីដេអូ និងរូបថត (Photo Slides) ពី TikTok គ្មាន Watermark。\n\n"
        f"👨‍💻 *អភិវឌ្ឍន៍ដោយ:* {DEVELOPER_NAME}\n\n"
        f"👉 *សូមផ្ញើ Link TikTok មកខ្ញុំឥឡូវនេះ!*"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.chat.id == ADMIN_ID:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
            bot.reply_to(
                message,
                f"📊 *ស្ថិតិប្រព័ន្ធ៖*\nអ្នកប្រើប្រាស់សរុប: {len(users)} នាក់",
                parse_mode='Markdown'
            )
        else:
            bot.reply_to(message, "📊 មិនទាន់មានទិន្នន័យអ្នកប្រើប្រាស់នៅឡើយទេ!")

@bot.message_handler(commands=['broadcast'])
def broadcast_msg(message):
    if message.chat.id == ADMIN_ID:
        msg_text = message.text.replace('/broadcast', '').strip()
        if not msg_text:
            bot.reply_to(message, "⚠️ សូមវាយសារដែលអ្នកចង់ផ្ញើ!", parse_mode='Markdown')
            return

        if not os.path.exists(DB_FILE):
            bot.reply_to(message, "❌ គ្មានអ្នកប្រើប្រាស់នៅក្នុង Database!")
            return

        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except Exception as e:
            bot.reply_to(message, f"❌ បរាជ័យក្នុងការអាន Database: {e}")
            return

        count = 0
        bot.send_message(ADMIN_ID, "🚀 *កំពុងចាប់ផ្តើមផ្ញើសារ...*", parse_mode='Markdown')

        for user_id in users:
            try:
                # បំលែង user_id ទៅជា int និងមិនប្រើ parse_mode ដើម្បីការពារ Error សញ្ញា _ ឬ Link
                bot.send_message(
                    int(user_id),
                    f"📢 ដំណឹងពី Admin:\n\n{msg_text}"
                )
                count += 1
            except Exception as e:
                print(f"Failed to send to {user_id}: {e}")
                continue

        bot.send_message(ADMIN_ID, f"✅ បានផ្ញើទៅកាន់អ្នកប្រើប្រាស់ `{count}` នាក់រួចរាល់!", parse_mode='Markdown')

@bot.message_handler(func=lambda message: "tiktok.com" in message.text)
def handle_tiktok(message):
    save_user(message.chat.id)
    
    # 1. សម្អាត Link កាត់ Parameter ?is_from_webapp... ចោល
    raw_url = message.text.strip()
    clean_url = raw_url.split('?')[0]
    
    status_msg = bot.reply_to(message, "🔎 *កំពុងទាញយកទិន្នន័យ សូមរង់ចាំមួយភ្លែត...*", parse_mode='Markdown')

    res_data = None
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # 2. ព្យាយាមទាញតាម TikWM (Primary API)
    try:
        api_url = f"https://www.tikwm.com/api/?url={clean_url}"
        response = requests.get(api_url, headers=headers, timeout=12)
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get('code') == 0:
                res_data = res_json['data']
    except Exception as e:
        print(f"TikWM API failed: {e}")

    # 3. ប្រសិនបើ TikWM បរាជ័យ ប្រើ TikWM ជាមួយ Raw URL ម្ដងទៀត
    if not res_data:
        try:
            api_url = f"https://www.tikwm.com/api/?url={raw_url}"
            response = requests.get(api_url, headers=headers, timeout=12)
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get('code') == 0:
                    res_data = res_json['data']
        except Exception as e:
            print(f"TikWM Raw URL failed: {e}")

    # 4. ប្រសិនបើទាញបានទិន្នន័យ ដំណើរការផ្ញើឯកសារ
    if res_data:
        try:
            v_id = res_data.get('id', 'media')
            title = res_data.get('title', 'TikTok Content')

            # ករណីជារូបថត (Photo Slides)
            if 'images' in res_data and res_data['images']:
                images = res_data['images']
                try:
                    bot.edit_message_text(
                        f"🖼️ *រកឃើញរូបថតចំនួន {len(images)} សន្លឹក!* កំពុងផ្ញើជូន...",
                        chat_id=message.chat.id,
                        message_id=status_msg.message_id,
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass

                media_group = []
                for index, img_url in enumerate(images):
                    if len(media_group) == 0:
                        caption = f"🖼️ *{title}*\n\n👤 *By:* {DEVELOPER_NAME}"
                        media_group.append(types.InputMediaPhoto(media=img_url, caption=caption, parse_mode='Markdown'))
                    else:
                        media_group.append(types.InputMediaPhoto(media=img_url))

                    if len(media_group) == 10 or index == len(images) - 1:
                        bot.send_media_group(message.chat.id, media_group)
                        media_group = []

                if 'music' in res_data and res_data['music']:
                    bot.send_audio(
                        message.chat.id,
                        res_data['music'],
                        title=title,
                        performer='Dea Vanna',
                        caption=f"🎵 *ចម្រៀងអមរូបថត៖* {title}\n👤 *By:* {DEVELOPER_NAME}",
                        parse_mode='Markdown'
                    )

                try:
                    bot.delete_message(message.chat.id, status_msg.message_id)
                except Exception:
                    pass

            # ករណីជា Video
            else:
                media_cache[v_id] = {
                    'video': res_data.get('play'),
                    'music': res_data.get('music'),
                    'title': title,
                }

                markup = types.InlineKeyboardMarkup()
                btn_v = types.InlineKeyboardButton('🎬 Video (HD)', callback_data=f'vid_{v_id}')
                btn_a = types.InlineKeyboardButton('🎵 Audio (MP3)', callback_data=f'aud_{v_id}')
                markup.add(btn_v, btn_a)

                try:
                    bot.edit_message_text(
                        f"✨ *{title}*\n\nសូមជ្រើសរើសប្រភេទឯកសារដែលអ្នកចង់បាន៖\n👨‍💻 *Bot by:* {DEVELOPER_NAME}",
                        chat_id=message.chat.id,
                        message_id=status_msg.message_id,
                        reply_markup=markup,
                        parse_mode='Markdown'
                    )
                except Exception:
                    bot.send_message(
                        message.chat.id,
                        f"✨ *{title}*\n\nសូមជ្រើសរើសប្រភេទឯកសារដែលអ្នកចង់បាន៖\n👨‍💻 *Bot by:* {DEVELOPER_NAME}",
                        reply_markup=markup,
                        parse_mode='Markdown'
                    )
        except Exception as err:
            print(f"Error processing media: {err}")
            try:
                bot.edit_message_text("⚠️ *មានបញ្ហាក្នុងការរៀបចំឯកសារ!*", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='Markdown')
            except Exception:
                bot.send_message(message.chat.id, "⚠️ *មានបញ្ហាក្នុងការរៀបចំឯកសារ!*", parse_mode='Markdown')

    else:
        try:
            bot.edit_message_text("❌ *មិនអាចទាញយកបានទេ!* API TikWM អាចនឹងរវល់ ឬ Link មិនត្រឹមត្រូវ។", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode='Markdown')
        except Exception:
            bot.send_message(message.chat.id, "❌ *មិនអាចទាញយកបានទេ!* API TikWM អាចនឹងរវល់ ឬ Link មិនត្រឹមត្រូវ។", parse_mode='Markdown')
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        action, v_id = call.data.split('_')

        if v_id not in media_cache:
            bot.answer_callback_query(call.id, '⚠️ ទិន្នន័យនេះបានផុតកំណត់ហើយ សូមផ្ញើ Link សារជាថ្មី!', show_alert=True)
            return

        media_info = media_cache[v_id]
        chat_id = call.message.chat.id

        bot.answer_callback_query(call.id, 'កំពុងផ្ញើឯកសារ...')

        if action == 'vid':
            caption = f"🎬 *{media_info['title']}*\n\n⚡ *Downloaded via Bot by:* {DEVELOPER_NAME}"
            bot.send_video(chat_id, media_info['video'], caption=caption, parse_mode='Markdown')
        elif action == 'aud':
            caption = f"🎵 *{media_info['title']}*\n\n🎧 *Audio Extracted by:* {DEVELOPER_NAME}"
            bot.send_audio(chat_id, media_info['music'], title=media_info['title'], performer=DEVELOPER_NAME, caption=caption, parse_mode='Markdown')

        bot.delete_message(chat_id, call.message.message_id)

    except Exception as e:
        bot.send_message(call.message.chat.id, "❌ *មានបញ្ហាក្នុងការផ្ញើឯកសារ!*", parse_mode='Markdown')

if __name__ == "__main__":
    # រ៉ាន់ Web Server លើ Background Thread សម្រាប់ Render Ping
    threading.Thread(target=run_web_server, daemon=True).start()
    print('🤖 Bot is running successfully...')
    bot.infinity_polling()
