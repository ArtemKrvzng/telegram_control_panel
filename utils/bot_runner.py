import re
import sys
import logging
import telebot
from openai import OpenAI
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from utils.database import Database

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
api_key_gpt = "sk-4BrpT6qFsQ8mOwZ5qdJ4tpEScuTthzBtAOcyX5bvrZUUnu9nGFhGTqItkhrX5QfNB0nPXdRAaFA8igdBKBaclA"
db = Database()

# Проверка аргументов
if len(sys.argv) != 3:
    print("Использование: bot_runner.py <token> <user_id>")
    sys.exit(1)

TOKEN = sys.argv[1]
USER_ID = int(sys.argv[2])

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Последние активные сообщения от /start
last_start_messages = {}

# Команда /start
@bot.message_handler(commands=['start'])
def start_command(message: Message):
    chat_id = str(message.chat.id)
    user_id = USER_ID

    # Удаляем активное предыдущее сообщение /start
    if chat_id in last_start_messages and last_start_messages[chat_id]["active"]:
        try:
            bot.delete_message(chat_id, last_start_messages[chat_id]["message_id"])
        except Exception as e:
            logging.warning(f"Не удалось удалить предыдущее сообщение /start: {e}")

    logging.info(f"/start от chat_id={chat_id} → user_id={user_id}")

    if not user_id:
        bot.send_message(chat_id, "⚠️ Ошибка: пользователь не найден. Обратитесь в поддержку.")
        return

    try:
        subscribers = db.get_subscribers_by_user(user_id)
        is_subscribed = any(str(sub.telegram_chat_id) == chat_id for sub in subscribers)

        if is_subscribed:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🚫 Отписаться", callback_data="unsubscribe"))
            sent = bot.send_message(chat_id, "🔔 Вы уже подписаны на рассылку.\nХотите отписаться?", reply_markup=keyboard)
        else:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ Да", callback_data="subscribe_yes"),
                InlineKeyboardButton("❌ Нет", callback_data="subscribe_no")
            )
            sent = bot.send_message(chat_id, "📩 Привет! Хочешь подписаться на рассылку?\nУзнать другие команды /help", reply_markup=keyboard)

        # Сохраняем ID и активность сообщения
        last_start_messages[chat_id] = {"message_id": sent.message_id, "active": True}

    except Exception as e:
        logging.error(f"Ошибка обработки /start: {e}")
        bot.send_message(chat_id, "⚠️ Внутренняя ошибка. Попробуйте позже.")

# Callback обработка кнопок
@bot.callback_query_handler(func=lambda call: call.data in ["subscribe_yes", "subscribe_no", "unsubscribe"])
def handle_subscription_decision(call: CallbackQuery):
    chat_id = str(call.message.chat.id)
    user_id = USER_ID
    data = call.data

    logging.info(f"Callback от chat_id={chat_id}, data={data}")

    try:
        subscribers = db.get_subscribers_by_user(user_id)
        is_subscribed = any(str(sub.telegram_chat_id) == chat_id for sub in subscribers)

        if data == "subscribe_yes":
            if is_subscribed:
                bot.edit_message_text("🔔 Вы уже подписаны.",
                                      chat_id=call.message.chat.id,
                                      message_id=call.message.message_id)
                logging.info(f"Подписка уже существует: user_id={user_id}, chat_id={chat_id}")
            else:
                db.insert_subscriber(user_id=user_id, chat_id=chat_id)
                bot.edit_message_text("🎉 Вы успешно подписаны на рассылку!",
                                      chat_id=call.message.chat.id,
                                      message_id=call.message.message_id)
                logging.info(f"✅ Подписан: user_id={user_id}, chat_id={chat_id}")

        elif data == "subscribe_no":
            bot.edit_message_text("❌ Подписка отменена.",
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id)
            logging.info(f"🚫 Отказ от подписки: chat_id={chat_id}")

        elif data == "unsubscribe":
            if not is_subscribed:
                bot.edit_message_text("⚠️ Вы не были подписаны.",
                                      chat_id=call.message.chat.id,
                                      message_id=call.message.message_id)
                logging.info(f"⚠️ Попытка отписки без подписки: chat_id={chat_id}")
            else:
                db.remove_subscriber(user_id=user_id, chat_id=chat_id)
                bot.edit_message_text("🗑️ Вы отписались от рассылки.",
                                      chat_id=call.message.chat.id,
                                      message_id=call.message.message_id)
                logging.info(f"❌ Отписан: user_id={user_id}, chat_id={chat_id}")

        # Деактивируем сообщение
        if chat_id in last_start_messages:
            last_start_messages[chat_id]["active"] = False

    except Exception as e:
        logging.error(f"Ошибка при обработке callback: {e}")
        bot.edit_message_text("⚠️ Ошибка при обработке действия. Попробуйте позже.",
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id)

# GPT
@bot.message_handler(commands=['ask'])
def ask_chatgpt(message: Message):
    user_prompt = message.text.replace('/ask', '').strip()

    if not user_prompt:
        bot.reply_to(message, "✏️ Пожалуйста, введите вопрос после команды /ask.")
        return

    try:
        client = OpenAI(
            base_url="https://api.langdock.com/openai/eu/v1",  # можно заменить на другой OpenAI-совместимый адрес
            api_key=api_key_gpt
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # или другую модель, которую поддерживает ваш провайдер
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        reply_text = response.choices[0].message.content.strip()
        bot.reply_to(message, reply_text)

    except Exception as e:
        logging.error(f"Ошибка при запросе к GPT: {e}")
        bot.reply_to(message, "⚠️ Не удалось получить ответ от ChatGPT. Попробуй позже.")

# Приветствие
@bot.message_handler(func=lambda msg: msg.text and re.search(r'\b(привет|hello)\b', msg.text.lower()))
def greet_handler(message: Message):
    chat_id = message.chat.id
    try:
        bot.send_message(
            chat_id,
            "Привет! 👋 Если хочешь подписаться на рассылку, напиши /start 📬. Если хочешь узнать ответ на свой вопрос от Chat-GPT напиши /ask"
        )
    except Exception as e:
        logging.error(f"Ошибка при обработке приветствия: {e}")

# Ответ на неизвестный текст
@bot.message_handler(func=lambda msg: msg.text and not msg.text.startswith('/') and not re.search(r'\b(привет|hello)\b', msg.text.lower()))
def unknown_text_handler(message: Message):
    chat_id = message.chat.id
    try:
        bot.send_message(
            chat_id,
            "🤖 Я тебя понял, но не уверен, что именно ты хочешь.\nНапиши <b>/help</b>, чтобы узнать доступные команды.",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка при обработке произвольного текста: {e}")

# Команда /help
@bot.message_handler(commands=['help'])
def help_command(message: Message):
    bot.send_message(message.chat.id, "🤖 Команды:\n/start — Подписка / отписка\n/ask — Спросить Chat-GPT\n/help — Помощь")

# Старт
if __name__ == "__main__":
    logging.info(f"🚀 Запуск бота с token={TOKEN[:5]}..., user_id={USER_ID}")
    try:
        bot.infinity_polling()
    except Exception as e:
        logging.error(f"❌ Критическая ошибка запуска: {e}")
