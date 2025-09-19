import os
import telebot
from telebot import types
import sqlite3
import io
from flask import Flask, request

# Конфигурация через переменные окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8300658638:AAHUCZ7A3ci-SMEZK_s_fM-amD1vHjjnCkE')
ADMIN_IDS = list(map(int, os.environ.get('ADMIN_IDS', '1717331690,1410156253,6635207675').split(',')))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
user_data = {}
user_orders = {}


def init_db():
    connection = sqlite3.connect("mmm.db")
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Descript TEXT,
    Photo BLOB,
    Cena TEXT,
    Category TEXT DEFAULT '—' NOT NULL
    )
    ''')
    connection.commit()
    connection.close()


@app.route('/')
def index():
    return "Bot is running!"


@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Invalid content type', 403


@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Штаны👖", callback_data='shtn'))
    markup.add(types.InlineKeyboardButton("Ремни🧢", callback_data='remn'))
    markup.add(types.InlineKeyboardButton("Тишки👕", callback_data='tishk'))
    markup.add(types.InlineKeyboardButton("Обувь👟", callback_data='shuz'))
    markup.add(types.InlineKeyboardButton("Худи🧥", callback_data='hudi'))
    markup.add(types.InlineKeyboardButton("Другое💫", callback_data='drugoe'))
    markup.add(types.InlineKeyboardButton("Акции💯", callback_data='akcii'))
    bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}, "
                                      f"я твой Telegram бот для заказа одежды!\n\n Каталог:", reply_markup=markup)


def save_product(name, descript, photo_bytes=None, cena=None, category=None):
    conn = sqlite3.connect('mmm.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO Products (Name, Descript, Photo, Cena, Category)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, descript, photo_bytes, cena, category))
    conn.commit()
    conn.close()


@bot.message_handler(commands=['del'])
def del_message(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "Удалять данные может только админ")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Да", callback_data="confirmdel_all"),
        types.InlineKeyboardButton("❌ Нет", callback_data="canceldel_all")
    )

    bot.send_message(message.chat.id, "Вы уверены, что хотите удалить все товары из базы?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["confirmdel_all", "canceldel_all"])
def process_full_deletion(call):
    if call.data == "canceldel_all":
        bot.send_message(call.message.chat.id, "Удаление отменено.")
        bot.answer_callback_query(call.id)
        return

    conn = sqlite3.connect('mmm.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute("DELETE FROM Products")
    conn.commit()
    conn.close()

    order_text = "✅ Удаление всех товаров выполнено!"
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, order_text)

    bot.send_message(call.message.chat.id, order_text)
    bot.answer_callback_query(call.id, "Удалено всё из базы.")


@bot.message_handler(commands=['delkategory'])
def del_kategori(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "Удалять данные может только админ")
        return

    markup = types.InlineKeyboardMarkup()
    categories = ["Штаны", "Ремни", "Обувь", "Тишки", "Худи", "Другое", "Акции"]
    for cat in categories:
        markup.add(types.InlineKeyboardButton(cat, callback_data=f"choosecat_{cat}"))

    bot.send_message(message.chat.id, "Выберите категорию для удаления:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("choosecat_"))
def confirm_deletion(call):
    category = call.data.split("_", 1)[1]

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Да", callback_data=f"confirmdel_{category}"),
        types.InlineKeyboardButton("❌ Нет", callback_data="canceldel")
    )

    bot.send_message(call.message.chat.id, f"Вы уверены, что хотите удалить категорию '{category}'?",
                     reply_markup=markup)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirmdel_") or call.data == "canceldel")
def process_deletion(call):
    if call.data == "canceldel":
        bot.send_message(call.message.chat.id, "Удаление отменено.")
        bot.answer_callback_query(call.id)
        return

    category = call.data.split("_", 1)[1]

    conn = sqlite3.connect('mmm.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute("DELETE FROM Products WHERE Category = ?", (category,))
    conn.commit()
    conn.close()

    bot.send_message(call.message.chat.id, f"✅ Все товары из категории '{category}' удалены.")
    bot.answer_callback_query(call.id, f"Удалено: {category}")


@bot.message_handler(commands=['add'])
def start_add(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "Только админ может добавлять товары!")
        return

    user_data[message.chat.id] = {}
    markup = types.InlineKeyboardMarkup()
    categories = {
        "Штаны": "shtn",
        "Ремни": "remn",
        "Обувь": "shuz",
        "Тишки": "tishk",
        "Худи": "hudi",
        "Другое": "drugoe",
        "Акции": "akcii",
    }
    for name, callback in categories.items():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"cat_{callback}"))

    bot.send_message(message.chat.id, "Выберите категорию товара:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def hand_cate(call):
    category_map = {
        "cat_shtn": "Штаны",
        "cat_remn": "Ремни",
        "cat_tishk": "Тишки",
        "cat_shuz": "Обувь",
        "cat_hudi": "Худи",
        "cat_drugoe": "Другое",
        "cat_akcii": "Акции",
    }
    category = category_map.get(call.data)
    user_data[call.message.chat.id]['category'] = category

    if category == "Акции":
        bot.send_message(call.message.chat.id, "Введите текст акции")
        bot.register_next_step_handler(call.message, get_akcii_text)
    else:
        bot.send_message(call.message.chat.id, f"Вы выбрали категорию: {category}\nТеперь введите название товара:")
        bot.register_next_step_handler(call.message, get_name)


def get_akcii_text(message):
    user_data[message.chat.id]['descript'] = message.text
    data = user_data[message.chat.id]
    save_product(name="Акции", descript=data['descript'], photo_bytes=None, cena=None, category=data['category'])
    bot.send_message(message.chat.id, "✅ Акция добавлена успешно!")
    user_data.pop(message.chat.id)


def get_name(message):
    user_data[message.chat.id]['name'] = message.text
    bot.send_message(message.chat.id, "Введите описание:")
    bot.register_next_step_handler(message, get_descript)


def get_descript(message):
    user_data[message.chat.id]['descript'] = message.text
    bot.send_message(message.chat.id, "Отправьте фото:")
    bot.register_next_step_handler(message, get_photo)


def get_photo(message):
    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        user_data[message.chat.id]['photo'] = downloaded_file
        bot.send_message(message.chat.id, "Введите цену:")
        bot.register_next_step_handler(message, get_cena)
    else:
        bot.send_message(message.chat.id, "Это не фото. Попробуйте снова.")
        bot.register_next_step_handler(message, get_photo)


def get_cena(message):
    try:
        cena = str(message.text)
        data = user_data[message.chat.id]
        save_product(data['name'], data['descript'], data['photo'], cena, data['category'])
        bot.send_message(message.chat.id, "✅ Данные успешно сохранены!")
        user_data.pop(message.chat.id)
    except ValueError:
        bot.send_message(message.chat.id, "Цена должна быть числом. Попробуйте снова.")
        bot.register_next_step_handler(message, get_cena)


@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    try:
        if call.data in ['shtn', 'shuz', 'remn', 'tishk', 'hudi', 'drugoe', 'akcii', 'nazad']:
            handle_category_callback(call)
        elif call.data.startswith("buy_"):
            handle_buy(call)
        elif call.data.startswith("choosecat_"):
            confirm_deletion(call)
        elif call.data.startswith("confirmdel_") or call.data == "canceldel":
            process_deletion(call)
        elif call.data in ["confirmdel_all", "canceldel_all"]:
            process_full_deletion(call)
        elif call.data.startswith("cat_"):
            hand_cate(call)
    except Exception as e:
        print(f"Error in callback handler: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")


def handle_category_callback(call):
    if call.data == 'shtn':
        send_shtani(call.message)
    elif call.data == 'shuz':
        send_shuz(call.message)
    elif call.data == 'remn':
        send_remn(call.message)
    elif call.data == 'tishk':
        send_tishk(call.message)
    elif call.data == 'hudi':
        send_hudi(call.message)
    elif call.data == 'drugoe':
        send_drugoe(call.message)
    elif call.data == 'akcii':
        send_akcii(call.message)
    elif call.data == 'nazad':
        bot.answer_callback_query(call.id)
        start_message(call.message)


def send_akcii(message):
    conn = sqlite3.connect('mmm.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT id, Name, Descript, Photo, Cena FROM Products WHERE Category=?", ("Акции",))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "❌ Пока акций нет.")
        return

    for i, row in enumerate(rows):
        product_id, name, descript, photo_blob, cena = row
        caption = f"{descript}"

        markup = types.InlineKeyboardMarkup()
        if i == len(rows) - 1:
            markup.add(types.InlineKeyboardButton(text="Назад", callback_data="nazad"))

        if photo_blob:
            photo_stream = io.BytesIO(photo_blob)
            bot.send_photo(message.chat.id, photo_stream, caption=caption, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, caption, reply_markup=markup)


def send_drugoe(message):
    conn = sqlite3.connect('mmm.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT id, Name, Descript, Photo, Cena FROM Products Where category=?", ("Другое",))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "❌ Пока товаров нет.")
        return

    for i, row in enumerate(rows):
        product_id, name, descript, photo_blob, cena = row
        photo = io.BytesIO(photo_blob)
        photo.name = 'photo5.jpg'
        caption = f"👖 Название: {name}\n📝 Описание: {descript}\n💰 Цена: {cena}"

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{product_id}")
        markup.add(button)
        if i == len(rows) - 1:
            markup.add(types.InlineKeyboardButton(text="Назад", callback_data="nazad"))
        bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=markup)


def send_hudi(message):
    conn = sqlite3.connect('mmm.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT id, Name, Descript, Photo, Cena FROM Products Where category=?", ("Худи",))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "❌ Пока товаров нет.")
        return

    for i, row in enumerate(rows):
        product_id, name, descript, photo_blob, cena = row
        photo = io.BytesIO(photo_blob)
        photo.name = 'photo6.jpg'
        caption = f"👖 Название: {name}\n📝 Описание: {descript}\n💰 Цена: {cena}"

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{product_id}")
        markup.add(button)
        if i == len(rows) - 1:
            markup.add(types.InlineKeyboardButton(text="Назад", callback_data="nazad"))
        bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=markup)


def send_tishk(message):
    conn = sqlite3.connect('mmm.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT id, Name, Descript, Photo, Cena FROM Products Where category=?", ("Тишки",))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "❌ Пока товаров нет.")
        return

    for i, row in enumerate(rows):
        product_id, name, descript, photo_blob, cena = row
        photo = io.BytesIO(photo_blob)
        photo.name = 'photo4.jpg'
        caption = f"👖 Название: {name}\n📝 Описание: {descript}\n💰 Цена: {cena} "

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{product_id}")
        markup.add(button)
        if i == len(rows) - 1:
            markup.add(types.InlineKeyboardButton(text="Назад", callback_data="nazad"))
        bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=markup)


def send_shtani(message):
    conn = sqlite3.connect('mmm.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, Name, Descript, Photo, Cena FROM Products Where category=?", ("Штаны",))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "❌ Пока товаров нет.")
        return

    for i, row in enumerate(rows):
        product_id, name, descript, photo_blob, cena = row
        photo = io.BytesIO(photo_blob)
        photo.name = 'photo.jpg'
        caption = f"👖 Название: {name}\n📝 Описание: {descript}\n💰 Цена: {cena}"

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{product_id}")
        markup.add(button)
        if i == len(rows) - 1:
            markup.add(types.InlineKeyboardButton(text="Назад", callback_data="nazad"))
        bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=markup)


def send_shuz(message):
    conn = sqlite3.connect('mmm.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, Name, Descript, Photo, Cena FROM Products WHERE Category = ?", ("Обувь",))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "❌ Пока товаров нет.")
        return
    for i, row in enumerate(rows):
        product_id, name, descript, photo_blob, cena = row
        photo = io.BytesIO(photo_blob)
        photo.name = 'photo2.jpg'
        caption = f"👖 Название: {name}\n📝 Описание: {descript}\n💰 Цена: {cena}"

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{product_id}")
        markup.add(button)
        if i == len(rows) - 1:
            markup.add(types.InlineKeyboardButton(text="Назад", callback_data="nazad"))
        bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=markup)


def send_remn(message):
    conn = sqlite3.connect('mmm.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, Name, Descript, Photo, Cena FROM Products WHERE Category = ?", ("Ремни",))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        bot.send_message(message.chat.id, "❌ Пока товаров нет.")
        return
    for i, row in enumerate(rows):
        product_id, name, descript, photo_blob, cena = row
        photo = io.BytesIO(photo_blob)
        photo.name = 'photo3.jpg'
        caption = f"👖 Название: {name}\n📝 Описание: {descript}\n💰 Цена: {cena}"
        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{product_id}")
        markup.add(button)
        if i == len(rows) - 1:
            markup.add(types.InlineKeyboardButton(text="Назад", callback_data="nazad"))
        bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_buy(call):
    product_id = call.data.split("_")[1]

    conn = sqlite3.connect('mmm.db')
    cursor = conn.cursor()
    cursor.execute("SELECT Name, Descript, Cena FROM Products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()

    if product:
        name, descript, cena = product
        user_orders[call.from_user.id] = {
            "product": {
                "name": name,
                "descript": descript,
                "cena": cena
            }
        }
        bot.send_message(call.message.chat.id, "✍️ Введите ваше ФИО:")
        bot.register_next_step_handler(call.message, get_fio)
    else:
        bot.send_message(call.message.chat.id, "❌ Ошибка: товар не найден.")
    bot.answer_callback_query(call.id)


def get_fio(message):
    user_orders[message.from_user.id]["fio"] = message.text
    bot.send_message(message.chat.id, "🏙 Введите ваш город:")
    bot.register_next_step_handler(message, get_city)


def get_city(message):
    user_orders[message.from_user.id]["city"] = message.text
    bot.send_message(message.chat.id, "📍 Введите ваш адрес:")
    bot.register_next_step_handler(message, get_address)


def get_address(message):
    user_orders[message.from_user.id]["address"] = message.text
    bot.send_message(message.chat.id, "📞 Введите ваш номер телефона:")
    bot.register_next_step_handler(message, get_phone)


def get_phone(message):
    user_orders[message.from_user.id]["phone"] = message.text
    bot.send_message(message.chat.id, "📧 Введите ваш адрес почты:")
    bot.register_next_step_handler(message, confirm_order)


def confirm_order(message):
    user_orders[message.from_user.id]["email"] = message.text
    data = user_orders[message.from_user.id]
    product = data["product"]

    summary = (
        f"📦 Ваш заказ:\n\n"
        f"🛍 Товар: {product['name']}\n"
        f"📝 Описание: {product['descript']}\n"
        f"💰 Цена: {product['cena']} BYN\n\n"
        f"👤 ФИО: {data['fio']}\n"
        f"🏙 Город: {data['city']}\n"
        f"📍 Адрес: {data['address']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"📧 Почта: {data['email']}"
    )

    bot.send_message(message.chat.id, summary)
    bot.send_message(message.chat.id, "❓ Подтвердите заказ: напишите *Да* или *Нет*")
    bot.register_next_step_handler(message, handle_text_confirmation)


def handle_text_confirmation(message):
    user_id = message.from_user.id
    text = message.text.strip().lower()

    if text == "да":
        data = user_orders.get(user_id)
        if not data:
            bot.send_message(message.chat.id, "❌ Ошибка: данные заказа не найдены.")
            return

        product = data["product"]
        order_text = (
            f"📦 Новый заказ!\n\n"
            f"🛍 Товар: {product['name']}\n"
            f"📝 Описание: {product['descript']}\n"
            f"💰 Цена: {product['cena']} BYN\n\n"
            f"👤 ФИО: {data['fio']}\n"
            f"🏙 Город: {data['city']}\n"
            f"📍 Адрес: {data['address']}\n"
            f"📞 Телефон: {data['phone']}\n"
            f"📧 Почта: {data['email']}\n\n"
            f"🔗 Пользователь: @{message.from_user.username or message.from_user.first_name}\n"
            f"🆔 ID: {message.from_user.id}"
        )

        for admin_id in ADMIN_IDS:
            bot.send_message(admin_id, order_text)
        bot.send_message(message.chat.id, "✅ Ваш заказ подтверждён! Мы скоро свяжемся с вами.")
        user_orders.pop(user_id)

    elif text == "нет":
        user_orders.pop(user_id, None)
        bot.send_message(message.chat.id, "❌ Заказ отменён.")
    else:
        bot.send_message(message.chat.id, "⚠️ Пожалуйста, напишите *Да* или *Нет*.")
        bot.register_next_step_handler(message, handle_text_confirmation)


if __name__ == '__main__':
    init_db()

    # Удаляем предыдущие вебхуки
    bot.remove_webhook()

    # Проверяем режим запуска
    if WEBHOOK_URL and not os.environ.get('DEBUG'):
        # Режим вебхука для продакшена
        bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        print("Webhook установлен")
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        # Режим polling для разработки
        print("Starting bot in polling mode...")
        bot.polling(none_stop=True)
