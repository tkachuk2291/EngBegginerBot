# EngBegginerBot

Personal English tutor Telegram bot (@eng_begginer_bot) powered by Gemini.

- Free chat with the tutor: corrections, grammar, translations, conversation practice
- "New Text": short English text + Russian translation, words can be added to the dictionary
- Personal dictionary with flashcard review
- Irregular verbs table, search and quiz
- Homework: Gemini gives a task, checks the answer and grades it
- Daily reminder to study (asks about homework)

## Run

```
cp .env.example .env   # fill BOT_TOKEN, ADMIN_ID, GEMINI_API_KEY
docker compose up -d --build
```

State is stored in the `eng-data` volume (`/app/data/state.json`).
