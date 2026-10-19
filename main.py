import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
from aiogram.types import BotCommand

import keyboards as kb
from ai import Tutor
from config import Config, load_config
from handlers import Session, build_router
from logsetup import aiogram_middleware, set_context, setup_logging, watch_loop
from storage import Storage

log = logging.getLogger("main")

DATA_PATH = Path("/app/data/state.json")
CHECK_EVERY = 30
REMIND_WINDOW = timedelta(hours=2)

COMMANDS = [
    BotCommand(command="text", description="Новый текст с переводом (можно указать тему)"),
    BotCommand(command="words", description="Мой словарь"),
    BotCommand(command="add", description="Добавить слово: /add word - перевод"),
    BotCommand(command="quiz", description="Повторить слова"),
    BotCommand(command="verbs", description="Таблица неправильных глаголов"),
    BotCommand(command="verbquiz", description="Тест на неправильные глаголы"),
    BotCommand(command="homework", description="Домашнее задание"),
    BotCommand(command="settings", description="Уровень и напоминание"),
    BotCommand(command="reset", description="Забыть историю разговора"),
    BotCommand(command="help", description="Что я умею"),
]


def reminder_text(storage: Storage) -> str:
    text = "⏰ Время позаниматься английским! Даже 15 минут в день дают результат 💪"
    hw = storage.homework
    if hw and not hw["done"]:
        text += f"\n\nКак там домашнее задание от {hw['given']}? Сделал? Присылай — проверю."
    else:
        text += "\n\nМожем взять новый текст, повторить слова или получить свежую домашку."
    return text


async def reminders(bot: Bot, config: Config, storage: Storage) -> None:
    while True:
        try:
            rem = storage.reminder
            now = datetime.now(config.tz)
            hour, minute = map(int, rem["time"].split(":"))
            due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            today = now.date().isoformat()
            if rem["enabled"] and rem["last"] != today and due <= now < due + REMIND_WINDOW:
                hw = storage.homework
                await bot.send_message(
                    config.admin_id,
                    reminder_text(storage),
                    reply_markup=kb.reminder(bool(hw and not hw["done"])),
                )
                storage.update_reminder(last=today)
                log.info("Reminder sent", extra={"date": today})
        except TelegramNetworkError as exc:
            log.warning("Reminder not sent, network error", extra={"error": str(exc)[:300]})
        except TelegramAPIError as exc:
            log.warning("Reminder not sent, Telegram error", extra={"error": str(exc)[:300]})
        except Exception:
            log.exception("Reminder loop failed")
        await asyncio.sleep(CHECK_EVERY)


async def main() -> None:
    setup_logging("eng-begginer-bot")
    watch_loop()
    config = load_config()
    set_context(admin_id=config.admin_id)
    storage = Storage(DATA_PATH, config.reminder_time)
    tutor = Tutor(config.gemini_api_key)
    await tutor.discover_models()

    bot = Bot(config.bot_token)
    dp = Dispatcher()
    dp["storage"] = storage
    dp["tutor"] = tutor
    dp["session"] = Session()
    dp.update.outer_middleware(aiogram_middleware())
    dp.include_router(build_router(config.admin_id))

    try:
        await bot.set_my_commands(COMMANDS)
    except (TelegramNetworkError, TelegramAPIError) as exc:
        log.warning("Could not set bot commands", extra={"error": str(exc)[:300]})

    task = asyncio.create_task(reminders(bot, config, storage))
    log.info("Bot started", extra={"english_level": storage.level, "reminder": storage.reminder, "words": len(storage.words)})
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
