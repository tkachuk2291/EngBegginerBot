import logging
import re
import time

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

log = logging.getLogger(__name__)

MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]
SKIP_MARKERS = ("image", "tts", "audio", "live", "embedding", "vision", "gemma", "learnlm", "aqa", "robotics", "computer-use")
RATE_PAUSE = 60
DAY_PAUSE = 3 * 60 * 60
GONE_PAUSE = 24 * 60 * 60
ERROR_PAUSE = 5 * 60

PLAIN = "Пиши обычным текстом без markdown: никаких звёздочек, решёток и обратных кавычек."

TUTOR = (
    "Ты — дружелюбный и терпеливый репетитор английского языка для русскоязычного ученика уровня {level}. "
    "Объясняй по-русски, просто и коротко, примеры давай на английском с переводом. "
    "Если ученик пишет по-английски — сначала мягко исправь ошибки и коротко объясни, потом ответь по сути. "
    "Можешь давать маленькие упражнения, объяснять грамматику, слова, произношение (транскрипцией), "
    "переводить и поддерживать разговор на английском, если ученик этого хочет. " + PLAIN
)


class TutorError(Exception):
    pass


class Story(BaseModel):
    title: str
    english: str
    russian: str


class Word(BaseModel):
    en: str
    ru: str


class Words(BaseModel):
    words: list[Word]


class Translation(BaseModel):
    ru: str


class Task(BaseModel):
    task: str


class Tutor:
    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.models = list(MODELS)
        self.paused: dict[str, float] = {}

    async def discover_models(self) -> None:
        try:
            found = []
            async for model in await self.client.aio.models.list():
                name = (model.name or "").removeprefix("models/")
                if (
                    "flash" in name
                    and "generateContent" in (model.supported_actions or [])
                    and not any(marker in name for marker in SKIP_MARKERS)
                    and name not in self.models
                ):
                    found.append(name)
        except Exception as exc:
            log.warning("Could not list Gemini models, using built-in list", extra={"error": str(exc)[:300]})
            return

        def version(name: str) -> float:
            match = re.search(r"(\d+(?:\.\d+)?)", name)
            return float(match.group(1)) if match else 0

        found.sort(key=lambda n: ("preview" in n or "exp" in n, -version(n)))
        self.models += found
        log.info("Gemini model chain", extra={"models": self.models})

    async def _ask(self, contents, system: str, schema: type[BaseModel] | None = None, temperature: float = 0.8):
        config = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
        if schema:
            config.response_mime_type = "application/json"
            config.response_schema = schema
        for model in self.models:
            if self.paused.get(model, 0) > time.monotonic():
                continue
            try:
                response = await self.client.aio.models.generate_content(model=model, contents=contents, config=config)
            except errors.APIError as exc:
                if exc.code == 429:
                    pause = DAY_PAUSE if "day" in str(exc).lower() else RATE_PAUSE
                elif exc.code in (403, 404):
                    pause = GONE_PAUSE
                else:
                    pause = ERROR_PAUSE
                self.paused[model] = time.monotonic() + pause
                log.warning("Gemini model failed", extra={"model": model, "code": exc.code, "error": str(exc)[:300]})
                continue
            except Exception as exc:
                log.warning("Gemini request failed", extra={"model": model, "error": f"{type(exc).__name__}: {exc}"[:300]})
                continue
            result = response.parsed if schema else (response.text or "").strip()
            if result:
                return result
            log.warning("Gemini returned empty answer", extra={"model": model})
        raise TutorError("No Gemini model answered")

    async def chat(self, history: list[tuple[str, str]], message: str, level: str) -> str:
        contents = [
            types.Content(role=role, parts=[types.Part.from_text(text=text)]) for role, text in history
        ]
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))
        return await self._ask(contents, TUTOR.format(level=level))

    async def story(self, level: str, topic: str) -> Story:
        about = f"на тему «{topic}»" if topic else "на любую живую бытовую или интересную тему"
        prompt = (
            f"Напиши короткий текст на английском {about} для ученика уровня {level}: 100–160 слов, "
            "естественный язык, полезная лексика, можно немного новых слов. "
            "title — короткий заголовок на английском, english — текст, russian — точный перевод на русский."
        )
        return await self._ask(prompt, TUTOR.format(level=level), Story, temperature=1.0)

    async def extract_words(self, text: str, level: str) -> list[Word]:
        prompt = (
            f"Выбери из текста 5–8 самых полезных для ученика уровня {level} слов или выражений "
            "(в начальной форме) и дай короткий перевод каждого на русский.\n\n" + text
        )
        return (await self._ask(prompt, TUTOR.format(level=level), Words, temperature=0.3)).words

    async def translate(self, word: str) -> str:
        prompt = f"Дай короткий перевод на русский (1–3 варианта через запятую) для: {word}"
        return (await self._ask(prompt, TUTOR.format(level="A2"), Translation, temperature=0.2)).ru

    async def homework(self, level: str, words: list[str]) -> str:
        vocab = f" Используй в задании слова из словаря ученика: {', '.join(words)}." if words else ""
        prompt = (
            f"Придумай домашнее задание по английскому для ученика уровня {level} на 15–20 минут, "
            "которое можно выполнить и сдать одним текстовым сообщением в Telegram: "
            "например, перевести предложения, вставить пропущенные слова, ответить на вопросы, "
            f"написать несколько предложений на тему.{vocab} Пронумеруй пункты, условия пиши по-русски."
        )
        return (await self._ask(prompt, TUTOR.format(level=level), Task, temperature=1.0)).task

    async def check_homework(self, level: str, task: str, answer: str) -> str:
        prompt = (
            f"Задание было такое:\n{task}\n\nОтвет ученика:\n{answer}\n\n"
            "Проверь по пунктам, исправь ошибки и коротко объясни их, похвали за удачное, "
            "в конце поставь оценку от 1 до 10 и дай один совет."
        )
        return await self._ask(prompt, TUTOR.format(level=level), temperature=0.4)
