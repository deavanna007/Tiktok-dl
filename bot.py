import json
import os
import requests
import telebot
from telebot import types

# --- កំណត់ព័ត៌មានបឋម ---
API_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'  # ⚠️ ដាក់ Token របស់អ្នកនៅទីនេះ
ADMIN_ID = 6953887858  # Telegram Admin ID
DB_FILE = 'users.json'

bot = telebot.TeleBot(API_TOKEN)

# ឃ្លាំងផ្ទុក Link បណ្ដោះអាសន្ន
media_cache = {}


# --- មុខងាររក្សាទុក ID អ្នកប្រើប្រាស់ ---
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
  bot.reply_to(
      message,
      '👋 សួស្តី! ខ្ញុំជា Bot ទាញយកវីដេអូ និងរូបថត (Photo Slides) ពី TikTok'
      ' គ្មាន Watermark។\n\nសូមផ្ញើ Link TikTok មកខ្ញុំឥឡូវនេះ!',
  )


# --- មុខងារ Admin: មើលចំនួនអ្នកប្រើប្រាស់ ---
@bot.message_handler(commands=['stats'])
def show_stats(message):
  if message.chat.id == ADMIN_ID:
    if os.path.exists(DB_FILE):
      with open(DB_FILE, 'r', encoding='utf-8') as f:
        users = json.load(f)
      bot.reply_to(
          message, f'📊 **ស្ថិតិ៖**\nអ្នកប្រើប្រាស់សរុប: `{len(users)}` នាក់'
      )
    else:
      bot.reply_to(message, '📊 មិនទាន់មានទិន្នន័យអ្នកប្រើប្រាស់នៅឡើយទេ!')


# --- មុខងារ Admin: Broadcast สារ ---
@bot.message_handler(commands=['broadcast'])
def broadcast_msg(message):
  if message.chat.id == ADMIN_ID:
    msg_text = message.text.replace('/broadcast', '').strip()
    if not msg_text:
      bot.reply_to(
          message,
          'សូមវាយសារដែលអ្នកចង់ផ្ញើ! ឧទាហរណ៍៖ `/broadcast សួស្តីអ្នកទាំងអស់គ្នា`',
      )
      return

    if not os.path.exists(DB_FILE):
      bot.reply_to(message, '❌ គ្មានអ្នកប្រើប្រាស់នៅក្នុង Database!')
      return

    with open(DB_FILE, 'r', encoding='utf-8') as f:
      users = json.load(f)

    count = 0
    bot.send_message(ADMIN_ID, '🚀 កំពុងចាប់ផ្តើមផ្ញើសារ...')

    for user_id in users:
      try:
        bot.send_message(user_id, f'📢 **ដំណឹងពី Admin:**\n\n{msg_text}')
        count += 1
      except Exception:
        continue

    bot.send_message(
        ADMIN_ID, f'✅ បានផ្ញើទៅកាន់អ្នកប្រើប្រាស់ `{count}` នាក់រួចរាល់!'
    )


# --- មុខងារ Handle TikTok Link (Video & Photo Slides) ---
@bot.message_handler(func=lambda message: "tiktok.com" in message.text)
def handle_tiktok(message):
  save_user(message.chat.id)
  url = message.text.strip()
  status_msg = bot.reply_to(
      message, '🔎 កំពុងទាញយកទិន្នន័យ សូមរង់ចាំមួយភ្លែត...'
  )

  try:
    api_url = f'https://www.tikwm.com/api/?url={url}'
    res = requests.get(api_url).json()

    if res.get('code') == 0:
      data = res['data']
      v_id = data['id']
      title = data.get('title', 'TikTok Content')

      # ករណីទី ១៖ ប្រសិនបើជា Photo Slides (មានប្រភពជារូបថតច្រើន)
      if 'images' in data and data['images']:
        images = data['images']
        bot.edit_message_text(
            f'🖼️ រកឃើញរូបថតចំនួន {len(images)} សន្លឹក! កំពុងផ្ញើជូន...',
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
        )

        # បំបែកផ្ញើជារៀងរាល់ 10 រូបក្នុង 1 Album (ព្រោះ Telegram អនុញ្ញាតអតិបរមា 10 media ក្នុង 1 album)
        media_group = []
        for index, img_url in enumerate(images):
          media_group.append(types.InputMediaPhoto(media=img_url))

          # ពេលគ្រប់ 10 រូប ឬដល់រូបចុងក្រោយ ផ្ញើចេញម្តង
          if len(media_group) == 10 or index == len(images) - 1:
            bot.send_media_group(message.chat.id, media_group)
            media_group = []

        # ផ្ញើចម្រៀង (MP3) ដែលអមជាមួយ Photo Slide នោះ (បើមាន)
        if 'music' in data:
          bot.send_audio(
              message.chat.id,
              data['music'],
              caption=f'🎵 ចម្រៀងអមរូបថត៖ {title}',
          )

        bot.delete_message(message.chat.id, status_msg.message_id)

      # ករណីទី ២៖ ប្រសិនបើជា Video ធម្មតា
      else:
        media_cache[v_id] = {
            'video': data['play'],
            'music': data['music'],
            'title': title,
        }

        markup = types.InlineKeyboardMarkup()
        btn_v = types.InlineKeyboardButton(
            '🎬 Video (HD)', callback_data=f'vid_{v_id}'
        )
        btn_a = types.InlineKeyboardButton(
            '🎵 Audio (MP3)', callback_data=f'aud_{v_id}'
        )
        markup.add(btn_v, btn_a)

        bot.edit_message_text(
            f'✨ **{title}**\n\nសូមជ្រើសរើសប្រភេទឯកសារដែលអ្នកចង់បាន៖',
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            reply_markup=markup,
        )

    else:
      bot.edit_message_text(
          '❌ មិនអាចទាញយកបានទេ! សូមពិនិត្យ Link ឡើងវិញ។',
          chat_id=message.chat.id,
          message_id=status_msg.message_id,
      )
  except Exception as e:
    bot.edit_message_text(
        '⚠️ មានបញ្ហាក្នុងការភ្ជាប់ទៅកាន់ Server!',
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
    )


# --- មុខងារឆ្លើយតបពេលគេចុច Button សម្រាប់ Video / MP3 ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
  try:
    action, v_id = call.data.split('_')

    if v_id not in media_cache:
      bot.answer_callback_query(
          call.id,
          '⚠️ ទិន្នន័យនេះបានផុតកំណត់ហើយ សូមផ្ញើ Link សារជាថ្មី!',
          show_alert=True,
      )
      return

    media_info = media_cache[v_id]
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id, 'កំពុងផ្ញើឯកសារ...')

    if action == 'vid':
      bot.send_video(
          chat_id, media_info['video'], caption=f"🎬 {media_info['title']}"
      )
    elif action == 'aud':
      bot.send_audio(
          chat_id, media_info['music'], caption=f"🎵 {media_info['title']}"
      )

    bot.delete_message(chat_id, call.message.message_id)

  except Exception as e:
    bot.send_message(call.message.chat.id, '❌ មានបញ្ហាក្នុងការផ្ញើឯកសារ!')


print('🤖 Bot is running successfully...')
bot.infinity_polling()