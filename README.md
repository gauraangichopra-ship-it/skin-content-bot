# Skin content bot

Telegram bot that turns Meera's (Skinstinct) raw notes into LinkedIn posts and newsletters in her voice, using Gemini. Every LinkedIn draft is checked against a QA list (length, formatting, banned words, British spelling, no invented numbers) and fact-checked against the note.

## Setup

Create a `.env` file next to `bot.py`:

```
TELEGRAM_BOT_TOKEN=<from BotFather>
GEMINI_API_KEY=<from Google AI Studio>
GEMINI_MODEL=gemini-flash-latest
```

Run with Python 3 (standard library only, nothing to install):

```
python3 bot.py
```

## Usage

- Send a note -> LinkedIn post + QA report
- `/newsletter <note>` -> newsletter email
- `/both <note>` -> both

Prompts live in `prompts/`; the voice guide is `voice-skill.txt`.
