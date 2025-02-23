import sqlite3
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from main import AvitoParse
import logging
from logging.handlers import TimedRotatingFileHandler
import os

bot = AsyncTeleBot('TOKEN')
user_data = {}
tracking_tasks = {}
handler = TimedRotatingFileHandler(
    filename="bot.log",  # РРјСЏ С„Р°Р№Р»Р° РґР»СЏ Р»РѕРіРѕРІ
    when="midnight",  # РћС‡РёСЃС‚РєР° РІ РїРѕР»РЅРѕС‡СЊ
    interval=1,  # РРЅС‚РµСЂРІР°Р» РІ РґРЅСЏС…
    backupCount=0  # РќРµ СЃРѕС…СЂР°РЅСЏС‚СЊ СЃС‚Р°СЂС‹Рµ Р»РѕРіРё
)

# РќР°СЃС‚СЂР°РёРІР°РµРј С„РѕСЂРјР°С‚ Р»РѕРіРѕРІ
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)

# РќР°СЃС‚СЂР°РёРІР°РµРј РѕСЃРЅРѕРІРЅРѕР№ РєРѕРЅС„РёРі РґР»СЏ Р»РѕРіРѕРІ
logging.basicConfig(
    level=logging.INFO,  # РЈСЂРѕРІРµРЅСЊ Р»РѕРіРёСЂРѕРІР°РЅРёСЏ
    handlers=[handler]  # РСЃРїРѕР»СЊР·СѓРµРј РѕР±СЂР°Р±РѕС‚С‡РёРє СЃ Р°РІС‚РѕРѕС‡РёСЃС‚РєРѕР№
)


async def monitor_tracking(user_id, product_name, check_frequency, object_id):
    avito = AvitoParse(
        product_name_search=product_name
    )

    while object_id in tracking_tasks:
        try:
            avito.parse()
            updated_data = avito.updates_product()
            logging.info(f'РРЅС„РѕСЂРјР°С†РёСЏ РІ С‚РµР»РµРіСЂР°РјРј РґР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ {user_id}: {updated_data}')
            if updated_data:
                for ad_id, ad_data in updated_data.items():
                    title = ad_data[0]  # РќР°Р·РІР°РЅРёРµ
                    price = ad_data[1]  # Р¦РµРЅР°
                    description = ad_data[2]  # РћРїРёСЃР°РЅРёРµ
                    link = ad_data[3]  # РЎСЃС‹Р»РєР°
                    images = ad_data[4]  # РљРѕСЂС‚РµР¶ СЃСЃС‹Р»РѕРє РЅР° РёР·РѕР±СЂР°Р¶РµРЅРёСЏ

                    # Р¤РѕСЂРјРёСЂСѓРµРј С‚РµРєСЃС‚ РґР»СЏ СЃРѕРѕР±С‰РµРЅРёСЏ
                    message_text = (
                        f"рџ”” РќР°Р№РґРµРЅРѕ РЅРѕРІРѕРµ РѕР±СЉСЏРІР»РµРЅРёРµ РґР»СЏ *{product_name}*:\n\n"
                        f"*РќР°Р·РІР°РЅРёРµ:* {title}\n"
                        f"рџ’µ *Р¦РµРЅР°:* {price} СЂСѓР±.\n\n"
                        f"*РћРїРёСЃР°РЅРёРµ:* {description}\n"
                        f"рџ”— [РЎСЃС‹Р»РєР° РЅР° РѕР±СЉСЏРІР»РµРЅРёРµ]({link})"
                    )

                    # Р¤РѕСЂРјРёСЂСѓРµРј РїРµСЂРІСѓСЋ С„РѕС‚РѕРіСЂР°С„РёСЋ СЃ С‚РµРєСЃС‚РѕРј
                    media_group = [types.InputMediaPhoto(images[0], caption=message_text, parse_mode='Markdown')]

                    # Р”РѕР±Р°РІР»СЏРµРј РѕСЃС‚Р°Р»СЊРЅС‹Рµ С„РѕС‚РѕРіСЂР°С„РёРё Р±РµР· С‚РµРєСЃС‚Р°
                    media_group.extend([types.InputMediaPhoto(image_url) for image_url in images[1:]])

                    # РћС‚РїСЂР°РІР»СЏРµРј РіСЂСѓРїРїСѓ С„РѕС‚РѕРіСЂР°С„РёР№ СЃ С‚РµРєСЃС‚РѕРј
                    await bot.send_media_group(user_id, media_group)
        except Exception as e:
            logging.error(f"РћС€РёР±РєР° РїСЂРё СЃР»РµР¶РєРµ Р·Р° '{product_name}': {e}")
        await asyncio.sleep(check_frequency * 60)


async def start_tracking():
    conn = sqlite3.connect('tracking.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('SELECT id, user_id, product_name, check_frequency FROM tracking_product')
    tracking_items = cursor.fetchall()
    cursor.close()
    conn.close()

    for item in tracking_items:
        object_id, user_id, product_name, check_frequency = item

        if object_id not in tracking_tasks:
            task = asyncio.create_task(
                monitor_tracking(user_id, product_name, check_frequency, object_id)
            )
            tracking_tasks[object_id] = task


async def stop_tracking(object_id):
    if object_id in tracking_tasks:
        task = tracking_tasks.pop(object_id)
        task.cancel()


@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message):
    conn = sqlite3.connect('tracking.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tracking_product (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_name TEXT,
        check_frequency INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')

    user_id = message.chat.id
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Р”РѕР±Р°РІРёС‚СЊ СЃР»РµР¶РєСѓ")
    markup.add("РЈРґР°Р»РёС‚СЊ СЃР»РµР¶РєСѓ")
    await bot.send_message(user_id, "Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ!рџ™€\nР’С‹Р±РµСЂРёС‚Рµ РґРµР№СЃС‚РІРёРµ:", reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == "РЈРґР°Р»РёС‚СЊ СЃР»РµР¶РєСѓ")
async def delete_tracking(message):
    user_id = message.chat.id
    conn = sqlite3.connect('tracking.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('SELECT id, product_name FROM tracking_product WHERE user_id = ?', (user_id,))
    user_trackings = cursor.fetchall()

    if not user_trackings:
        await bot.send_message(user_id, "РЈ РІР°СЃ РЅРµС‚ Р°РєС‚РёРІРЅС‹С… РѕР±СЉРµРєС‚РѕРІ СЃР»РµР¶РєРё.")
        cursor.close()
        conn.close()
        return

    markup = types.InlineKeyboardMarkup()
    for tracking_id, product_name in user_trackings:
        markup.add(types.InlineKeyboardButton(text=product_name, callback_data=f"delete_{tracking_id}"))
    await bot.send_message(user_id, "Р’С‹Р±РµСЂРёС‚Рµ СЃР»РµР¶РєСѓ РґР»СЏ СѓРґР°Р»РµРЅРёСЏ:", reply_markup=markup)

    cursor.close()
    conn.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
async def confirm_deletion(call):
    tracking_id = int(call.data.split("_")[1])
    conn = sqlite3.connect('tracking.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM tracking_product WHERE id = ?', (tracking_id,))
    conn.commit()

    if tracking_id in tracking_tasks:
        await stop_tracking(tracking_id)

    cursor.close()
    conn.close()

    await bot.send_message(call.message.chat.id, "РЎР»РµР¶РєР° СѓСЃРїРµС€РЅРѕ СѓРґР°Р»РµРЅР°.")


@bot.message_handler(func=lambda msg: msg.text == "Р”РѕР±Р°РІРёС‚СЊ СЃР»РµР¶РєСѓ")
async def add_tracking(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    await bot.send_message(user_id, "РЈРєР°Р¶РёС‚Рµ, С‡С‚Рѕ Р±СѓРґРµРј РёСЃРєР°С‚СЊ Рё РјРѕРЅРёС‚РѕСЂРёС‚СЊ (РЅР°Р·РІР°РЅРёРµ РїСЂРѕРґСѓРєС†РёРё/СѓСЃР»СѓРіРё):")
    user_data[user_id]['state'] = 'waiting_for_product_name'


@bot.message_handler(func=lambda msg: msg.chat.id in user_data and user_data[msg.chat.id].get('state') == 'waiting_for_product_name')
async def get_product_name(message):
    user_id = message.chat.id
    user_data[user_id]['product_name'] = message.text
    await bot.send_message(user_id, "РљР°Рє С‡Р°СЃС‚Рѕ РїСЂРѕРІРµСЂСЏС‚СЊ РЅРѕРІС‹Рµ РѕР±СЉСЏРІР»РµРЅРёСЏ (РІ РјРёРЅСѓС‚Р°С…):")
    user_data[user_id]['state'] = 'waiting_for_check_frequency'


@bot.message_handler(func=lambda msg: msg.chat.id in user_data and user_data[msg.chat.id].get('state') == 'waiting_for_check_frequency')
async def get_check_frequency(message):
    user_id = message.chat.id
    try:
        check_frequency = int(message.text)
        user_data[user_id]['check_frequency'] = check_frequency

        conn = sqlite3.connect('tracking.db', check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(''' 
        INSERT INTO tracking_product (user_id, product_name, check_frequency)
        VALUES (?, ?, ?)
        ''', (user_id, user_data[user_id]['product_name'], check_frequency))
        conn.commit()
        cursor.close()
        conn.close()

        await bot.send_message(user_id, f"РЎР»РµР¶РєР° Р·Р° '{user_data[user_id]['product_name']}' СѓСЃРїРµС€РЅРѕ РґРѕР±Р°РІР»РµРЅР°!")
        user_data.pop(user_id, None)  # РЈРґР°Р»СЏРµРј РІСЂРµРјРµРЅРЅС‹Рµ РґР°РЅРЅС‹Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
        await start_tracking()
    except ValueError:
        await bot.send_message(user_id, "Р’РІРµРґРёС‚Рµ РєРѕСЂСЂРµРєС‚РЅРѕРµ С‡РёСЃР»Рѕ РјРёРЅСѓС‚.")


async def main():
    if os.path.exists('tracking.db'):
        await start_tracking()
    await bot.polling(none_stop=True)


if __name__ == "__main__":
    asyncio.run(main())
