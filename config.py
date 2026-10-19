import os
import re
from dataclasses import dataclass
from zoneinfo import ZoneInfo

TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, "").strip() or default


def _required(name: str) -> str:
    value = _env(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is not set (see .env.example)")
    return value


def parse_time(value: str) -> str | None:
    match = TIME_RE.match(value.strip())
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}"


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int
    gemini_api_key: str
    tz: ZoneInfo
    reminder_time: str


def load_config() -> Config:
    return Config(
        bot_token=_required("BOT_TOKEN"),
        admin_id=int(_required("ADMIN_ID")),
        gemini_api_key=_required("GEMINI_API_KEY"),
        tz=ZoneInfo(_env("TZ", "Europe/Kyiv")),
        reminder_time=parse_time(_env("REMINDER_TIME", "19:00")) or "19:00",
    )
