import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
import database
import scheduler
import config
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Услуги и их длительность в минутах
SERVICES = {
    "Общий массаж — 60 мин (2000р)": 60,
    "Массаж головы — 30 мин (1000р)": 30,
    "Шейно-воротниковая зона — 45 мин (1000р)": 45,
    "Антицеллюлитный массаж — 2ч (5000р)": 120
}

# Получение рабочих дней
def get_available_days():
    days = []
    today = datetime.today()
    for i in range(7):
        day = today + timedelta(days=i)
        if day.strftime("%a").lower() in config.WORKING_HOURS['weekdays']:
            days.append(day.strftime("%Y-%m-%d"))
    return days

# Приветствие
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    utm_source = context.args[0] if context.args else "organic"

    reply_keyboard = [['ЗАПИСАТЬСЯ']]
    markup = ReplyKeyboardMarkup([KeyboardButton(text) for text in reply_keyboard], one_time_keyboard=False)
    
    update.message.reply_text(
        f'Здравствуйте! Вас приветствует электронной помощник массажиста Елены Крыловой! Приглашаю Вас посетить один из видов массажа!',
        reply_markup=markup
    )

# Обработка кнопки "Записаться"
def handle_signup(update: Update, context: CallbackContext) -> None:
    buttons = [[KeyboardButton(service)] for service in SERVICES.keys()]
    buttons.append([KeyboardButton("Назад")])
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=False)
    update.message.reply_text("Выберите тип массажа:", reply_markup=markup)

# Обработка выбора услуги
def handle_service_choice(update: Update, context: CallbackContext) -> None:
    selected_service = update.message.text
    if selected_service not in SERVICES:
        return

    context.user_data['service'] = selected_service
    days = get_available_days()

    buttons = []
    for day in days:
        date_obj = datetime.strptime(day, "%Y-%m-%d")
        day_name = date_obj.strftime("%A")
        full_day_name = {
            "Monday": "Понедельник",
            "Tuesday": "Вторник",
            "Wednesday": "Среда",
            "Thursday": "Четверг",
            "Friday": "Пятница",
            "Saturday": "Суббота"
        }.get(day_name, day_name)

        appointments = database.get_appointments_by_date(day)
        occupied = [time for _, time in appointments]
        duration = SERVICES[selected_service]

        total_minutes = (config.WORKING_HOURS['end'] - config.WORKING_HOURS['start']) * 60
        slots = []

        current_time = datetime.strptime(f"{day} {config.WORKING_HOURS['start']:02}:00", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(f"{day} {config.WORKING_HOURS['end']:02}:00", "%Y-%m-%d %H:%M")

        while current_time + timedelta(minutes=duration) <= end_time:
            slot_time = current_time.strftime("%H:%M")
            next_slot = current_time + timedelta(minutes=duration + config.BREAK_AFTER_SERVICE)
            if all(slot_time != occ[1] for occ in appointments):
                slots.append(slot_time)
            current_time = next_slot

        status = "занято" if not slots else f"есть слоты: {', '.join(slots)}"
        buttons.append([KeyboardButton(f"{full_day_name} ({status})")])

    buttons.append([KeyboardButton("Назад")])
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=False)
    update.message.reply_text("Выберите день:", reply_markup=markup)

# Обработка выбора дня
def handle_day_choice(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    day_match = text.split(" ")[0].lower()
    days_map = {
        "понедельник": "mon",
        "вторник": "tue",
        "среда": "wed",
        "четверг": "thu",
        "пятница": "fri",
        "суббота": "sat"
    }

    if day_match not in days_map.values():
        return

    selected_date = None
    today = datetime.today()
    for i in range(7):
        check_day = today + timedelta(days=i)
        if check_day.strftime("%a").lower() == day_match:
            selected_date = check_day.strftime("%Y-%m-%d")
            break

    if not selected_date:
        update.message.reply_text("Ошибка: дата не найдена.")
        return

    context.user_data['date'] = selected_date
    selected_service = context.user_data.get('service')

    if not selected_service:
        return

    duration = SERVICES[selected_service]
    appointments = database.get_appointments_by_date(selected_date)

    current_time = datetime.strptime(f"{selected_date} {config.WORKING_HOURS['start']:02}:00", "%Y-%m-%d %H:%M")
    end_time = datetime.strptime(f"{selected_date} {config.WORKING_HOURS['end']:02}:00", "%Y-%m-%d %H:%M")

    buttons = []
    while current_time + timedelta(minutes=duration) <= end_time:
        slot_time = current_time.strftime("%H:%M")
        next_slot = current_time + timedelta(minutes=duration + config.BREAK_AFTER_SERVICE)
        if all(slot_time != occ[1] for occ in appointments):
            buttons.append([KeyboardButton(slot_time)])
        current_time = next_slot

    buttons.append([KeyboardButton("Назад")])
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=False)
    update.message.reply_text("Выберите время:", reply_markup=markup)

# Обработка выбора времени
def handle_time_choice(update: Update, context: CallbackContext) -> None:
    time_str = update.message.text
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        return

    user = update.effective_user
    service = context.user_data.get("service")
    date = context.user_data.get("date")

    if not service or not date:
        return

    database.add_appointment(user.id, user.full_name, service, date, time_str, "manual")

    full_datetime = f"{date} {time_str}"
    scheduler.schedule_notifications(full_datetime, user.id, service)

    bot.send_message(
        chat_id=user.id,
        text=f"✅ Вы успешно записались:\n\nУслуга: {service}\nДата: {date}, {time_str}\n\n❗ Через 1 час вы получите напоминание. Пожалуйста, включите уведомления."
    )

    bot.send_message(
        chat_id=user.id,
        text=f"✅ Вы были добавлены в наш Telegram-канал: {config.CHANNEL_USERNAME}\nТам вы будете получать полезную информацию о массаже и новых услугах!"
    )

# Админ-панель
def admin_panel(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        update.message.reply_text("Доступ запрещён.")
        return

    buttons = [
        [KeyboardButton("Посмотреть записи")],
        [KeyboardButton("Статистика UTM")],
        [KeyboardButton("Очистить старые записи")],
        [KeyboardButton("Назад")]
    ]
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=False)
    update.message.reply_text("Админ-панель:", reply_markup=markup)

# Команды админа
def handle_admin_action(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    user_id = update.effective_user.id

    if user_id not in config.ADMIN_IDS:
        return

    if text == "Посмотреть записи":
        records = database.get_all_appointments()
        if not records:
            update.message.reply_text("Нет записей.")
            return

        for user_id, name, service, date, time in records:
            update.message.reply_text(f"🧑‍🦰 Имя: {name}\n🕒 Дата: {date}, {time}\n💆 Услуга: {service}")

    elif text == "Статистика UTM":
        stats = database.get_stats()
        msg = "📊 Статистика источников:\n"
        for source, count in stats:
            msg += f"- {source}: {count}\n"
        update.message.reply_text(msg)

    elif text == "Очистить старые записи":
        database.clear_old_appointments()
        update.message.reply_text("✅ Старые записи удалены.")

# Запуск бота
def main():
    database.init_db()
    scheduler.start_scheduler()

    updater = Updater(config.BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("admin", admin_panel))
    dispatcher.add_handler(MessageHandler(Filters.regex("ЗАПИСАТЬСЯ"), handle_signup))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda u, c: {
        "service": handle_service_choice,
        "date": handle_day_choice,
        "time": handle_time_choice,
        "admin": handle_admin_action
    }.get(next(iter(c.user_data.keys()), None), lambda u, c: None)(u, c)))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
