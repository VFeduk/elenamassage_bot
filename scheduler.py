from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from telegram import Bot
import database
import config

bot = Bot(token=config.BOT_TOKEN)

def schedule_notifications(appointment_time_str, user_id, service):
    appointment_time = datetime.strptime(appointment_time_str, "%Y-%m-%d %H:%M")

    # За 24 часа
    notify_24h = appointment_time - timedelta(hours=24)
    if notify_24h > datetime.now():
        scheduler.add_job(
            send_notification,
            'date',
            run_date=notify_24h,
            args=[user_id, f"⏰ Напоминаем! Завтра в {appointment_time.strftime('%H:%M')} у вас сеанс массажа у {config.MASTER_NAME}"]
        )

    # За 1.5 часа
    notify_1_5h = appointment_time - timedelta(minutes=90)
    if notify_1_5h > datetime.now():
        scheduler.add_job(
            send_notification,
            'date',
            run_date=notify_1_5h,
            args=[user_id, f"⏳ Через полтора часа у вас массаж. Не забудьте явиться!"]
        )

def send_notification(chat_id, message):
    bot.send_message(chat_id=chat_id, text=message)

def start_scheduler():
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()
