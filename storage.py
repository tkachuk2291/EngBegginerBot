import json
import logging
import os
import random
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

LEVELS = ("A1", "A2", "B1", "B2", "C1")
TEXTS_LIMIT = 100


class Storage:
    def __init__(self, path: Path, reminder_time: str) -> None:
        self.path = path
        self.data = {
            "level": "A2",
            "words": [],
            "homework": None,
            "last_text": "",
            "texts": [],
            "candidates": [],
            "reminder": {"time": reminder_time, "enabled": True, "last": ""},
        }
        if path.exists():
            try:
                self.data.update(json.loads(path.read_text("utf-8")))
            except (OSError, ValueError):
                log.exception("State file is broken, starting fresh", extra={"path": str(path)})
                path.rename(path.with_suffix(".broken"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), "utf-8")
        os.replace(tmp, self.path)

    @property
    def level(self) -> str:
        return self.data["level"]

    def set_level(self, level: str) -> None:
        self.data["level"] = level
        self.save()

    @property
    def words(self) -> list[dict]:
        return self.data["words"]

    def sorted_words(self) -> list[dict]:
        return sorted(self.words, key=lambda w: w["en"].casefold())

    def find_word(self, en: str) -> dict | None:
        key = en.strip().casefold()
        return next((w for w in self.words if w["en"].casefold() == key), None)

    def add_word(self, en: str, ru: str) -> bool:
        existing = self.find_word(en)
        if existing:
            existing["ru"] = ru
            self.save()
            return False
        self.words.append({"en": en.strip(), "ru": ru.strip(), "added": date.today().isoformat(), "known": 0, "missed": 0})
        self.save()
        return True

    def delete_word(self, en: str) -> bool:
        word = self.find_word(en)
        if not word:
            return False
        self.words.remove(word)
        self.save()
        return True

    def pick_word(self) -> tuple[int, dict] | None:
        if not self.words:
            return None
        weights = [(1 + w["missed"]) / (1 + w["known"]) for w in self.words]
        index = random.choices(range(len(self.words)), weights=weights)[0]
        return index, self.words[index]

    def mark_word(self, index: int, known: bool) -> None:
        self.words[index]["known" if known else "missed"] += 1
        self.save()

    @property
    def homework(self) -> dict | None:
        return self.data["homework"]

    def set_homework(self, task: str) -> None:
        self.data["homework"] = {"task": task, "given": date.today().isoformat(), "done": False, "feedback": ""}
        self.save()

    def finish_homework(self, feedback: str) -> None:
        self.data["homework"].update(done=True, feedback=feedback)
        self.save()

    @property
    def reminder(self) -> dict:
        return self.data["reminder"]

    def update_reminder(self, **values) -> None:
        self.reminder.update(values)
        self.save()

    @property
    def texts(self) -> list[dict]:
        return self.data["texts"]

    def add_text(self, title: str, english: str, russian: str) -> int:
        self.texts.append({"title": title, "english": english, "russian": russian})
        del self.texts[:-TEXTS_LIMIT]
        self.data["last_text"] = english
        self.data["candidates"] = []
        self.save()
        return len(self.texts) - 1

    def set_candidates(self, words: list[dict]) -> None:
        self.data["candidates"] = words
        self.save()
