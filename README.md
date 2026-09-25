# Skin content bot

A Telegram bot that turns a skincare founder's rough voice-note-style thoughts into finished LinkedIn posts and newsletters **in her own writing voice** — and checks every draft before she sees it.

Built for Meera, founder of Skinstinct (an Indian fragrance-free skincare brand). Her voice was extracted from 15 of her real pieces (4 LinkedIn posts, 11 newsletters).

## The problem

Meera has good ideas in rough form ("batch fourteen came back and the pH looked off...") but turning each into a post in her exact style takes time. Generic AI writing sounds nothing like her: it hypes, uses emojis, invents statistics and sells. Her voice is the opposite: precise, dry, admits mistakes, never sells, and always ends by telling the reader what question to ask a brand.

## How it works

```
Meera sends a rough note on Telegram
        │
        ▼
1. DRAFT       Gemini writes the post using her system prompt + 2 example posts
        │
        ▼
2. QA CHECKS   Code checks the draft against her checklist (below)
        │      └─ any failure → Gemini revises once with the exact list of problems
        ▼
3. FACT-CHECK  A second Gemini call compares the post to her note and lists any claim
        │      that isn't in the note, or is stronger than the note
        │      └─ any unsupported claim → Gemini revises; anything still flagged is deleted
        ▼
4. REPLY       Bot sends the post + a QA report back on Telegram
```

### QA checklist (enforced in code, `qa_linkedin()` in `bot.py`)

| Check | Rule |
|---|---|
| Length | 420–540 words, 6–8 paragraphs |
| Opening | Must not open with a question |
| Formatting | No bullets, bold, headers, hashtags, emojis, exclamation marks, em dashes |
| Banned words | game-changer, revolutionary, holy grail, skin-loving, thrilled, dive in, DM me… |
| Spelling | British (colour, moisturiser, oxidise…) |
| Invented numbers | Every number in the post must appear in Meera's note |
| Voice moves | Has a short 2–8 word verdict sentence and an "I'm not saying X. What I'm saying is Y." line |
| Call to action | Points the reader at "any brand", never a purchase |
| Facts | No claim beyond what the note says (LLM fact-check) |

## Commands (on Telegram)

| Send | Get |
|---|---|
| any note | LinkedIn post + QA report |
| `/newsletter <note>` | Newsletter email with 2 subject lines |
| `/both <note>` | Both |
| `/start` or `/help` | Instructions |

## Example

Input: [`examples/batch14_note.txt`](examples/batch14_note.txt)
Output (post, QA report, newsletter): [`examples/batch14_output.txt`](examples/batch14_output.txt)

## Setup

Needs Python 3.9+ and uses only the standard library, so there's nothing to install.

1. Create a bot with [@BotFather](https://t.me/BotFather) and get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).
2. Copy `.env.example` to `.env` and fill in both keys.
3. Run the bot:
   ```
   python3 bot.py
   ```
4. Or test the full pipeline without Telegram:
   ```
   python3 demo.py                      # uses examples/batch14_note.txt
   python3 demo.py path/to/your_note.txt
   ```

## Files

| File | Purpose |
|---|---|
| `bot.py` | Telegram bot, Gemini calls, QA checks, fact-check, revision loop |
| `demo.py` | Runs the same pipeline on a text file, saves the output |
| `prompts/linkedin_system_prompt.txt` | Meera's LinkedIn voice rules (structure, rhythm, banned words) |
| `prompts/linkedin_examples.txt` | Two example posts used as style references |
| `voice-skill.txt` | Full voice guide extracted from her 15 pieces (used for newsletters) |
| `examples/` | Sample input note and real output |
| `.env.example` | Template for the two API keys (the real `.env` is never committed) |

## Limitations

- The fact-check catches invented facts and numbers, but it's an LLM, so Meera should still read every post before publishing.
- The bot runs while `bot.py` is running on a machine. It doesn't host itself.
- Text messages only (no voice notes).
