import html
import logging
import re
from dataclasses import dataclass, field

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, ErrorEvent, Message

import keyboards as kb
import verbs
from ai import Tutor, TutorError
from config import parse_time
from storage import LEVELS, Storage

log = logging.getLogger(__name__)

HISTORY_LIMIT = 20
CHUNK = 4000
NEW_TEXT_RE = re.compile(r"^(new\s*text|новый\s+текст)\b\s*(.*)$", re.IGNORECASE | re.DOTALL)
WORD_RE = re.compile(r"^(.+?)\s*(?:—|–|\s-\s|=|:)\s*(.+)$")
BUSY = "Gemini сейчас недоступен, попробуй чуть позже 🙏"

HELP = (
    "Я твой репетитор английского 🇬🇧\n\n"
    "Просто пиши мне — по-английски или по-русски: исправлю ошибки, объясню грамматику, переведу, поболтаю.\n\n"
    "📖 New Text (или /text тема) — текст на английском с переводом\n"
    "📚 Словарь — твои слова; /add word - перевод, /del word\n"
    "🧠 Повторить слова — карточки из словаря\n"
    "📋 Глаголы — таблица неправильных глаголов; /verb go — найти глагол\n"
    "🎯 Тест глаголов — проверь себя на формах\n"
    "📝 Домашка — задание, сдаёшь ответом, я проверяю\n"
    "⚙️ Настройки — уровень, напоминание (/remind 19:00, /remind off)\n"
    "/reset — забыть историю разговора"
)


@dataclass
class Session:
    mode: str = ""
    verb: int = 0
    history: list[tuple[str, str]] = field(default_factory=list)


def chunks(text: str) -> list[str]:
    parts = []
    while len(text) > CHUNK:
        cut = text.rfind("\n", 0, CHUNK)
        cut = cut if cut > 0 else CHUNK
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts + [text] if text else parts


async def answer(message: Message, text: str, markup=None) -> None:
    parts = chunks(text)
    for i, part in enumerate(parts):
        await message.answer(part, reply_markup=markup if i == len(parts) - 1 else None)


async def progress(message: Message, text: str) -> Message:
    if message.from_user and not message.from_user.is_bot:
        return await message.reply(text)
    return await message.answer(text)


async def finish(status: Message, body: str, markup=None) -> None:
    if len(body) <= CHUNK:
        try:
            await status.edit_text(body, parse_mode="HTML", reply_markup=markup)
            return
        except TelegramBadRequest as e:
            log.warning("HTML edit failed", extra={"error": e.message})
    parts = chunks(html.unescape(re.sub(r"<[^>]+>", "", body)))
    await status.edit_text(parts[0], reply_markup=markup if len(parts) == 1 else None)
    for i, part in enumerate(parts[1:], 2):
        await status.answer(part, reply_markup=markup if i == len(parts) else None)


def homework_text(storage: Storage) -> str:
    hw = storage.homework
    status = "✅ сдано" if hw["done"] else "⏳ ждёт ответа"
    text = f"📝 <b>Домашнее задание от {hw['given']}</b> ({status})\n\n{html.escape(hw['task'])}"
    if hw["done"] and hw["feedback"]:
        text += f"\n\n✍️ <b>Проверка</b>\n<blockquote expandable>{html.escape(hw['feedback'])}</blockquote>"
    elif not hw["done"]:
        text += "\n\n<i>Когда будешь готов — нажми «Сдать» и пришли ответ одним сообщением.</i>"
    return text


def settings_text(storage: Storage) -> str:
    rem = storage.reminder
    state = f"каждый день в {rem['time']}" if rem["enabled"] else "выключено"
    return (
        f"⚙️ Уровень: {storage.level}\n🔔 Напоминание: {state}\n\n"
        "Время напоминания: /remind 19:00\nУровень можно выбрать кнопкой ниже."
    )


def build_router(admin_id: int) -> Router:
    router = Router()
    router.message.filter(F.from_user.id == admin_id)
    router.callback_query.filter(F.from_user.id == admin_id)

    async def new_text(message: Message, storage: Storage, tutor: Tutor, topic: str = "") -> None:
        status = await progress(message, "⏳ Пишу текст...")
        try:
            story = await tutor.story(storage.level, topic)
        except TutorError:
            await status.edit_text(BUSY)
            return
        storage.set_text(story.english)
        log.info("Story sent", extra={"topic": topic, "english_level": storage.level})
        await finish(
            status,
            f"📖 <b>{html.escape(story.title)}</b>\n\n{html.escape(story.english)}\n\n"
            f"🇷🇺 <b>Перевод</b>\n<blockquote expandable>{html.escape(story.russian)}</blockquote>",
            kb.after_text(),
        )

    async def show_dictionary(message: Message, storage: Storage) -> None:
        words = storage.sorted_words()
        if not words:
            await message.answer(
                "📚 Словарь пока пуст.\nДобавь слово: /add apple - яблоко (или просто /add apple — переведу сам).",
                reply_markup=kb.dictionary(),
            )
            return
        lines = [f"📚 Словарь ({len(words)}):", ""] + [f"• {w['en']} — {w['ru']}" for w in words]
        await answer(message, "\n".join(lines), kb.dictionary())

    async def add_word(message: Message, storage: Storage, tutor: Tutor, raw: str) -> None:
        match = WORD_RE.match(raw.strip())
        if match:
            en, ru = match.group(1), match.group(2)
        else:
            en = raw.strip()
            try:
                ru = await tutor.translate(en)
            except TutorError:
                await message.answer(BUSY + "\nИли укажи перевод сам: /add word - перевод")
                return
        created = storage.add_word(en, ru)
        log.info("Word saved", extra={"word": en, "new_word": created})
        await message.answer(f"{'➕ Добавил' if created else '✏️ Обновил'}: {en} — {ru}")

    async def ask_word(message: Message, storage: Storage) -> None:
        picked = storage.pick_word()
        if not picked:
            await message.answer("Словарь пуст — сначала добавь слова: /add word - перевод")
            return
        index, word = picked
        await message.answer(f"🧠 Как переводится?\n\n{word['en']}", reply_markup=kb.quiz_question(index))

    async def ask_verb(message: Message, session: Session) -> None:
        session.mode = "verb"
        session.verb = verbs.random_verb()
        verb = verbs.VERBS[session.verb]
        await message.answer(
            f"🎯 {verb[0]} ({verb[3]})\nНапиши вторую и третью формы через пробел, например: went gone",
            reply_markup=kb.verb_quiz(),
        )

    async def show_homework(message: Message, storage: Storage, tutor: Tutor, fresh: bool = False) -> None:
        if fresh or not storage.homework:
            status = await progress(message, "⏳ Составляю задание...")
            words = [w["en"] for w in storage.sorted_words()][-15:]
            try:
                task = await tutor.homework(storage.level, words)
            except TutorError:
                await status.edit_text(BUSY)
                return
            storage.set_homework(task)
            log.info("Homework given", extra={"english_level": storage.level})
        else:
            status = await progress(message, "📝")
        await finish(status, homework_text(storage), kb.homework(storage.homework["done"]))

    @router.message(CommandStart())
    @router.message(Command("help"))
    async def start(message: Message) -> None:
        await message.answer(HELP, reply_markup=kb.menu())

    @router.message(Command("text"))
    async def text_command(message: Message, command: CommandObject, storage: Storage, tutor: Tutor) -> None:
        await new_text(message, storage, tutor, command.args or "")

    @router.message(F.text == kb.NEW_TEXT)
    async def text_button(message: Message, storage: Storage, tutor: Tutor) -> None:
        await new_text(message, storage, tutor)

    @router.message(Command("words"))
    @router.message(F.text == kb.DICTIONARY)
    async def dictionary(message: Message, storage: Storage) -> None:
        await show_dictionary(message, storage)

    @router.message(Command("add"))
    async def add_command(message: Message, command: CommandObject, storage: Storage, tutor: Tutor, session: Session) -> None:
        if not command.args:
            session.mode = "add"
            await message.answer("Пришли слово и перевод, например: apple - яблоко")
            return
        await add_word(message, storage, tutor, command.args)

    @router.message(Command("del"))
    async def delete_command(message: Message, command: CommandObject, storage: Storage) -> None:
        if not command.args:
            await message.answer("Напиши так: /del apple")
            return
        deleted = storage.delete_word(command.args)
        await message.answer(f"🗑 Удалил: {command.args}" if deleted else "Такого слова нет в словаре.")

    @router.message(Command("quiz"))
    @router.message(F.text == kb.REVIEW)
    async def quiz(message: Message, storage: Storage) -> None:
        await ask_word(message, storage)

    @router.message(Command("verbs"))
    @router.message(F.text == kb.VERBS)
    async def verbs_table(message: Message) -> None:
        await message.answer(verbs.page(0), reply_markup=kb.verbs_pages(0, verbs.pages()))

    @router.message(Command("verb"))
    async def verb_search(message: Message, command: CommandObject) -> None:
        if not command.args:
            await message.answer("Напиши так: /verb go (можно по-русски: /verb идти)")
            return
        found = verbs.find(command.args)
        text = "\n".join(verbs.format_verb(v) for v in found) if found else "Не нашёл такого неправильного глагола."
        await message.answer(text)

    @router.message(Command("verbquiz"))
    @router.message(F.text == kb.VERB_QUIZ)
    async def verb_quiz(message: Message, session: Session) -> None:
        await ask_verb(message, session)

    @router.message(Command("homework"))
    @router.message(F.text == kb.HOMEWORK)
    async def homework(message: Message, storage: Storage, tutor: Tutor) -> None:
        await show_homework(message, storage, tutor)

    @router.message(Command("settings"))
    @router.message(F.text == kb.SETTINGS)
    async def settings(message: Message, storage: Storage) -> None:
        await message.answer(settings_text(storage), reply_markup=kb.settings(storage.reminder["enabled"]))

    @router.message(Command("remind"))
    async def remind(message: Message, command: CommandObject, storage: Storage) -> None:
        arg = (command.args or "").strip().lower()
        if arg in ("off", "выкл"):
            storage.update_reminder(enabled=False)
        elif arg in ("on", "вкл"):
            storage.update_reminder(enabled=True)
        elif parse_time(arg):
            storage.update_reminder(time=parse_time(arg), enabled=True, last="")
        elif arg:
            await message.answer("Не понял время. Пример: /remind 19:30, /remind off, /remind on")
            return
        log.info("Reminder changed", extra={"reminder": dict(storage.reminder)})
        await message.answer(settings_text(storage), reply_markup=kb.settings(storage.reminder["enabled"]))

    @router.message(Command("level"))
    async def level(message: Message, command: CommandObject, storage: Storage) -> None:
        value = (command.args or "").strip().upper()
        if value not in LEVELS:
            await message.answer(f"Уровни: {', '.join(LEVELS)}. Пример: /level B1")
            return
        storage.set_level(value)
        await message.answer(f"Уровень: {value}")

    @router.message(Command("reset"))
    async def reset(message: Message, session: Session) -> None:
        session.history.clear()
        session.mode = ""
        await message.answer("🧹 Начинаем разговор с чистого листа.")

    @router.message(F.text)
    async def text(message: Message, storage: Storage, tutor: Tutor, session: Session) -> None:
        mode, session.mode = session.mode, ""
        if mode == "add":
            await add_word(message, storage, tutor, message.text)
            return
        if mode == "verb":
            verb = verbs.VERBS[session.verb]
            if verbs.check(session.verb, message.text):
                await message.answer(f"✅ Верно! {verbs.format_verb(verb)}", reply_markup=kb.verb_next())
            else:
                await message.answer(f"❌ Правильно: {verbs.format_verb(verb)}", reply_markup=kb.verb_next())
            return
        if mode == "homework" and storage.homework:
            status = await progress(message, "⏳ Проверяю...")
            try:
                feedback = await tutor.check_homework(storage.level, storage.homework["task"], message.text)
            except TutorError:
                session.mode = "homework"
                await status.edit_text(BUSY + "\nПришли ответ ещё раз чуть позже.")
                return
            storage.finish_homework(feedback)
            log.info("Homework checked")
            await finish(status, f"✍️ <b>Проверка</b>\n\n{html.escape(feedback)}", kb.homework(True))
            return
        match = NEW_TEXT_RE.match(message.text.strip())
        if match:
            await new_text(message, storage, tutor, match.group(2).strip())
            return
        status = await progress(message, "⏳ Думаю...")
        try:
            reply = await tutor.chat(session.history, message.text, storage.level)
        except TutorError:
            await status.edit_text(BUSY)
            return
        session.history += [("user", message.text), ("model", reply)]
        del session.history[:-HISTORY_LIMIT]
        await finish(status, html.escape(reply))

    @router.message()
    async def other(message: Message) -> None:
        await message.answer("Я понимаю только текст 🙂", reply_markup=kb.menu())

    @router.callback_query(F.data == "text:new")
    async def cb_text(call: CallbackQuery, storage: Storage, tutor: Tutor) -> None:
        await call.answer()
        await new_text(call.message, storage, tutor)

    @router.callback_query(F.data == "text:words")
    async def cb_text_words(call: CallbackQuery, storage: Storage, tutor: Tutor) -> None:
        await call.answer("Выбираю слова…")
        if not storage.data["last_text"]:
            await call.message.answer("Сначала попроси новый текст.")
            return
        status = await progress(call.message, "⏳ Выбираю слова...")
        try:
            words = await tutor.extract_words(storage.data["last_text"], storage.level)
        except TutorError:
            await status.edit_text(BUSY)
            return
        storage.set_candidates([w.model_dump() for w in words])
        await status.edit_text("Какие слова добавить в словарь?", reply_markup=kb.candidates(storage.data["candidates"]))

    @router.callback_query(F.data.startswith("add:"))
    async def cb_add(call: CallbackQuery, storage: Storage) -> None:
        pool = storage.data["candidates"]
        key = call.data.split(":")[1]
        chosen = pool if key == "all" else [pool[int(key)]] if int(key) < len(pool) else []
        for word in chosen:
            storage.add_word(word["en"], word["ru"])
        await call.answer(f"Добавлено: {len(chosen)}")

    @router.callback_query(F.data == "dict:add")
    async def cb_dict_add(call: CallbackQuery, session: Session) -> None:
        session.mode = "add"
        await call.answer()
        await call.message.answer("Пришли слово и перевод, например: apple - яблоко (или только слово — переведу сам)")

    @router.callback_query(F.data.startswith("quiz:"))
    async def cb_quiz(call: CallbackQuery, storage: Storage) -> None:
        parts = call.data.split(":")
        action = parts[1]
        if action == "next":
            await call.answer()
            await ask_word(call.message, storage)
            return
        index = int(parts[2])
        if index >= len(storage.words):
            await call.answer("Слово уже не в словаре")
            return
        word = storage.words[index]
        if action == "show":
            await call.answer()
            await call.message.edit_text(f"🧠 {word['en']} — {word['ru']}", reply_markup=kb.quiz_answer(index))
        elif action == "del":
            storage.delete_word(word["en"])
            await call.answer("Удалено")
            await call.message.edit_text(f"🗑 {word['en']} удалено", reply_markup=kb.quiz_next())
        else:
            storage.mark_word(index, action == "yes")
            await call.answer("👍" if action == "yes" else "Повторим ещё")
            await call.message.edit_reply_markup(reply_markup=None)
            await ask_word(call.message, storage)

    @router.callback_query(F.data.startswith("verbs:"))
    async def cb_verbs(call: CallbackQuery) -> None:
        number = int(call.data.split(":")[1])
        await call.answer()
        await call.message.edit_text(verbs.page(number), reply_markup=kb.verbs_pages(number, verbs.pages()))

    @router.callback_query(F.data.startswith("vq:"))
    async def cb_verb_quiz(call: CallbackQuery, session: Session) -> None:
        action = call.data.split(":")[1]
        await call.answer()
        if action == "skip" and session.mode == "verb":
            session.mode = ""
            await call.message.answer(f"Запоминай: {verbs.format_verb(verbs.VERBS[session.verb])}", reply_markup=kb.verb_next())
        elif action == "stop":
            session.mode = ""
            await call.message.answer("Хорошо, на сегодня с глаголами всё 👌")
        elif action == "next":
            await ask_verb(call.message, session)

    @router.callback_query(F.data.startswith("hw:"))
    async def cb_homework(call: CallbackQuery, storage: Storage, tutor: Tutor, session: Session) -> None:
        action = call.data.split(":")[1]
        await call.answer()
        if action == "submit":
            if not storage.homework or storage.homework["done"]:
                await call.message.answer("Активного задания нет.", reply_markup=kb.homework(True))
                return
            session.mode = "homework"
            await call.message.answer("Жду твой ответ одним сообщением ✍️")
        else:
            await show_homework(call.message, storage, tutor, fresh=action == "new")

    @router.callback_query(F.data.startswith("level:"))
    async def cb_level(call: CallbackQuery, storage: Storage) -> None:
        storage.set_level(call.data.split(":")[1])
        await call.answer(f"Уровень {storage.level}")
        await call.message.edit_text(settings_text(storage), reply_markup=kb.settings(storage.reminder["enabled"]))

    @router.callback_query(F.data == "remind:toggle")
    async def cb_remind(call: CallbackQuery, storage: Storage) -> None:
        storage.update_reminder(enabled=not storage.reminder["enabled"])
        await call.answer()
        await call.message.edit_text(settings_text(storage), reply_markup=kb.settings(storage.reminder["enabled"]))

    @router.error()
    async def on_error(event: ErrorEvent) -> None:
        if isinstance(event.exception, TelegramNetworkError):
            log.warning("Telegram network error", extra={"error": str(event.exception)[:300]})
            return
        log.exception("Handler failed", exc_info=event.exception)

    return router
