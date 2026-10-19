from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from storage import LEVELS

NEW_TEXT = "📖 New Text"
DICTIONARY = "📚 Словарь"
REVIEW = "🧠 Повторить слова"
VERBS = "📋 Глаголы"
VERB_QUIZ = "🎯 Тест глаголов"
HOMEWORK = "📝 Домашка"
SETTINGS = "⚙️ Настройки"


def menu() -> ReplyKeyboardMarkup:
    rows = [[NEW_TEXT, DICTIONARY], [REVIEW, HOMEWORK], [VERBS, VERB_QUIZ], [SETTINGS]]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows],
        resize_keyboard=True,
        input_field_placeholder="Пиши мне на английском или по-русски",
    )


def inline(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows]
    )


def after_text() -> InlineKeyboardMarkup:
    return inline([("➕ Слова из текста в словарь", "text:words")], [("📖 Ещё текст", "text:new")])


def candidates(words: list[dict]) -> InlineKeyboardMarkup:
    rows = [[(f"➕ {w['en']} — {w['ru']}"[:60], f"add:{i}")] for i, w in enumerate(words)]
    return inline(*rows, [("➕ Добавить все", "add:all")])


def dictionary() -> InlineKeyboardMarkup:
    return inline([("➕ Добавить слово", "dict:add"), ("🧠 Повторить", "quiz:next")])


def quiz_question(index: int) -> InlineKeyboardMarkup:
    return inline([("👀 Показать перевод", f"quiz:show:{index}")])


def quiz_answer(index: int) -> InlineKeyboardMarkup:
    return inline([("✅ Знаю", f"quiz:yes:{index}"), ("❌ Не знаю", f"quiz:no:{index}")], [("🗑 Удалить слово", f"quiz:del:{index}")])


def quiz_next() -> InlineKeyboardMarkup:
    return inline([("➡️ Следующее", "quiz:next")])


def verbs_pages(current: int, total: int) -> InlineKeyboardMarkup:
    row = []
    if current > 0:
        row.append(("⬅️", f"verbs:{current - 1}"))
    if current < total - 1:
        row.append(("➡️", f"verbs:{current + 1}"))
    return inline(row, [("🎯 Тест глаголов", "vq:next")])


def verb_quiz() -> InlineKeyboardMarkup:
    return inline([("🤷 Не помню", "vq:skip"), ("⏹ Хватит", "vq:stop")])


def verb_next() -> InlineKeyboardMarkup:
    return inline([("➡️ Ещё глагол", "vq:next"), ("⏹ Хватит", "vq:stop")])


def homework(done: bool) -> InlineKeyboardMarkup:
    if done:
        return inline([("🆕 Новое задание", "hw:new")])
    return inline([("📤 Сдать", "hw:submit")], [("🆕 Другое задание", "hw:new")])


def settings(enabled: bool) -> InlineKeyboardMarkup:
    return inline(
        [(lvl, f"level:{lvl}") for lvl in LEVELS],
        [("🔕 Выключить напоминание" if enabled else "🔔 Включить напоминание", "remind:toggle")],
    )


def reminder(homework_pending: bool) -> InlineKeyboardMarkup:
    first = [("📤 Сдать домашку", "hw:submit")] if homework_pending else [("📝 Домашка", "hw:show")]
    return inline(first, [("📖 New Text", "text:new"), ("🧠 Слова", "quiz:next")])
