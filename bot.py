"""Skin content bot: turns Meera's raw notes into LinkedIn posts and newsletters.

Run locally:  python3 bot.py   (polls Telegram; keys in .env next to this file)
On Vercel:    api/webhook.py receives messages from Telegram instead of polling.
Uses only the Python standard library.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def read(*parts):
    with open(os.path.join(HERE, *parts)) as f:
        return f.read()


# Keys come from .env locally, or from environment variables on Vercel.
ENV_PATH = os.path.join(HERE, ".env")
ENV = {**(load_env(ENV_PATH) if os.path.exists(ENV_PATH) else {}), **os.environ}
TG_TOKEN = ENV["TELEGRAM_BOT_TOKEN"]
GEMINI_KEY = ENV["GEMINI_API_KEY"]
GEMINI_MODEL = ENV.get("GEMINI_MODEL", "gemini-flash-latest")
TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"

LINKEDIN_PROMPT = read("prompts", "linkedin_system_prompt.txt") + "\n\n" + read("prompts", "linkedin_examples.txt")

NEWSLETTER_PROMPT = f"""You are the ghostwriter for Meera Pillai, founder of the Indian fragrance-free skincare
brand Skinstinct. She spent two years in pharmaceutical formulation, is not a dermatologist and
never gives medical advice. Write strictly in her voice, following this guide:

{read("voice-skill.txt")}

HARD RULES
- Use ONLY the facts in Meera's note. Never invent numbers, dates, names, test results,
  process changes or customer reactions. If a needed fact is missing, write around it.
- Never strengthen a claim. Keep her exact level of certainty: "isn't unsafe" must not
  become "completely safe".
- British spelling. Spaced hyphens ( - ) for dashes, never em dashes.
- Plain prose. No markdown, asterisks, bullets, emojis, hashtags or exclamation marks.

OUTPUT (plain text)
Two subject line options on the first two lines, each starting "Subject: ", plain and
conversational, one with a parenthetical aside. Then a blank line, then the email: "Hi," on
its own line, 250-450 words, speaks to customers, signs off with just "Meera".
"""

BANNED = ["game-changer", "game changer", "revolutionary", "holy grail", "skin-loving",
          "thrilled", "excited to share", "dive in", "here's the thing", "follow for more",
          "dm me", "link in comments", "buckle up", "shocking", "toxic"]
AMERICAN = {"color": "colour", "behavior": "behaviour", "moisturizer": "moisturiser",
            "oxidize": "oxidise", "oxidizes": "oxidises", "oxidized": "oxidised",
            "sensitization": "sensitisation", "sensitize": "sensitise",
            "organization": "organisation", "standardized": "standardised",
            "analyze": "analyse", "realize": "realise", "center": "centre",
            "flavor": "flavour", "favor": "favour", "stabilize": "stabilise",
            "stabilized": "stabilised", "optimize": "optimise", "recognize": "recognise"}

HELP_TEXT = """Hi Meera. Send me your raw notes and I'll draft them in your voice.

Just send the note -> LinkedIn post
/newsletter <note> -> newsletter email
/both <note> -> LinkedIn post + newsletter

Include every real fact and number you want used - I won't invent any. Each LinkedIn post comes with a QA report against your checklist."""


def log(msg):
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def http_post(url, payload, headers=None, timeout=120):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def tg(method, **params):
    return http_post(f"{TG_API}/{method}", params, timeout=params.get("timeout", 0) + 30)


def send_text(chat_id, text):
    # Telegram caps messages at 4096 characters; split on paragraph breaks.
    chunks, current = [], ""
    for para in text.split("\n\n"):
        if current and len(current) + len(para) + 2 > 3900:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    for chunk in chunks:
        tg("sendMessage", chat_id=chat_id, text=chunk[:4096])


def gemini(system, turns, json_mode=False):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": role, "parts": [{"text": text}]} for role, text in turns],
        "generationConfig": {"temperature": 0.2 if json_mode else 0.6},
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    result = http_post(url, payload, headers={"x-goog-api-key": GEMINI_KEY})
    parts = result["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()


NUMBER_WORDS = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty".split())}


def numbers_in(text):
    found = set(re.findall(r"\d+(?:\.\d+)?", text))
    found |= {NUMBER_WORDS[w] for w in re.findall(r"[a-z]+", text.lower()) if w in NUMBER_WORDS}
    return found


def qa_linkedin(post, note):
    """Run the QA checklist. Returns (failures, warnings) as lists of plain-English lines."""
    failures, warnings = [], []
    lower = post.lower()
    paragraphs = [p for p in re.split(r"\n\s*\n", post.strip()) if p.strip()]
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", post.replace("\n", " ")) if s.strip()]
    words = len(post.split())

    if not 420 <= words <= 540:
        failures.append(f"Length is {words} words; must be 420-540.")
    if not 6 <= len(paragraphs) <= 8:
        failures.append(f"Has {len(paragraphs)} paragraphs; must be 6-8.")
    if paragraphs and "?" in paragraphs[0]:
        failures.append("Opens with a question; must open cold on a scene, date or number.")
    if "!" in post:
        failures.append("Contains an exclamation mark.")
    if "#" in post:
        failures.append("Contains a hashtag.")
    if "**" in post or re.search(r"^\s*#{1,6}\s", post, re.M):
        failures.append("Contains bold or headers.")
    if re.search(r"^\s*([-*•]|\d+[.)])\s", post, re.M):
        failures.append("Contains bullets or a numbered list; lists must live inside prose.")
    if "—" in post or "–" in post:
        failures.append("Uses em/en dashes; use spaced hyphens ' - ' instead.")
    if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", post):
        failures.append("Contains an emoji.")
    for phrase in BANNED:
        if phrase in lower:
            failures.append(f'Uses banned phrase "{phrase}".')
    for us, uk in AMERICAN.items():
        if re.search(rf"\b{us}\b", lower):
            failures.append(f'American spelling "{us}"; use "{uk}".')
    invented = sorted(numbers_in(post) - numbers_in(note))
    if invented:
        failures.append("Uses numbers not in Meera's note (possibly invented): " + ", ".join(invented)
                        + ". Remove them or write around them.")

    if not any(2 <= len(s.split()) <= 8 for s in sentences):
        failures.append("No short 2-8 word verdict sentence.")
    if "not saying" not in lower and "not making a case" not in lower:
        failures.append('Missing the "I\'m not saying X. What I\'m saying is Y." guardrail.')
    if "any brand" not in lower:
        failures.append('Reader action must point at "any brand" (e.g. "Not us specifically - any brand.").')
    if "?" in post and not (paragraphs and "?" in paragraphs[0]):
        warnings.append("Contains a question mark - check it is a reported question, not one aimed at the reader.")
    if len(numbers_in(post)) < 4:
        warnings.append(f"Only {len(numbers_in(post))} distinct numbers (checklist wants 4+). "
                        "Send more real figures in your note if you have them.")
    if "useful information" in lower:
        warnings.append('Uses "that\'s useful information" - keep it to max 1 in every 3 posts.')
    return failures, warnings


FACT_CHECK_PROMPT = """You are a strict fact-checker for a skincare founder's LinkedIn post.
Compare the POST against the NOTE (the founder's only source of facts about her company).
List every statement in the post about Skinstinct, its batch, supplier, process, customers,
costs or the industry that is NOT supported by the note, or that is STRONGER than the note
(e.g. "often" -> "remarkable regularity", "isn't unsafe" -> "completely safe", or any
prediction about how brands or customers will respond).
General, well-established formulation science explanations are allowed and must NOT be listed.
Return JSON: {"unsupported": [{"quote": "<exact words from post>", "why": "<short reason>"}]}
Return an empty list if everything is supported."""


def fact_check(post, note):
    raw = gemini(FACT_CHECK_PROMPT, [("user", f"NOTE:\n{note}\n\nPOST:\n{post}")], json_mode=True)
    try:
        return [(c["quote"], c["why"]) for c in json.loads(raw).get("unsupported", [])]
    except (ValueError, KeyError, TypeError, AttributeError):
        return []


def remove_sentences(post, quotes):
    """Delete every sentence containing one of the quotes. Returns (post, removed, not_found)."""
    removed, found = [], set()
    paragraphs = []
    for para in re.split(r"\n\s*\n", post.strip()):
        kept = []
        for sentence in re.split(r"(?<=[.!?])\s+", para.strip()):
            hit = next((q for q in quotes if q.strip(" .").lower() in sentence.lower()), None)
            if hit:
                removed.append(sentence)
                found.add(hit)
            else:
                kept.append(sentence)
        if kept:
            paragraphs.append(" ".join(kept))
    return "\n\n".join(paragraphs), removed, [q for q in quotes if q not in found]


def revise(turns, post, issues):
    turns += [("model", post), ("user", "Revise the post to fix every issue below. Keep everything "
              "else the same. Where a claim is unsupported, delete it or soften it to exactly what "
              "the note says. Output only the post text.\n\n- " + "\n- ".join(issues))]
    return gemini(LINKEDIN_PROMPT, turns)


def write_linkedin(note):
    user_msg = ("Write a LinkedIn post from Meera's note below. Pick the best-fitting pillar "
                "(Ingredient Deep-Dive, Founder Story, India-Specific Context, Industry Transparency). "
                "Use only facts in the note.\n\nNOTE:\n" + note)
    turns = [("user", user_msg)]
    post = gemini(LINKEDIN_PROMPT, turns)
    revisions = 0
    failures, _ = qa_linkedin(post, note)
    if failures:
        post = revise(turns, post, failures)
        revisions += 1
    unsupported = fact_check(post, note)
    if unsupported:
        post = revise(turns, post, [f'Unsupported claim: "{q}" - {why}' for q, why in unsupported])
        revisions += 1
        unsupported = fact_check(post, note)
    # Last resort: delete any sentence the fact-checker still flags.
    post, removed, not_found = remove_sentences(post, [q for q, _ in unsupported])
    failures, warnings = qa_linkedin(post, note)
    warnings += [f'Removed unsupported sentence: "{r}"' for r in removed]
    failures += [f'Unsupported claim still in post: "{q}"' for q in not_found]
    return post, failures, warnings, revisions


def qa_report(failures, warnings, revisions):
    lines = ["QA REPORT" + (f" (after {revisions} automatic revision{'s' if revisions > 1 else ''})" if revisions else "")]
    if not failures:
        lines.append("All hard checks passed: length, paragraphs, formatting, banned words, "
                     "British spelling, no invented numbers, verdict line, guardrail, "
                     "any-brand CTA, fact-check against your note.")
    lines += ["FAIL: " + f for f in failures]
    lines += ["CHECK: " + w for w in warnings]
    lines.append("Always check yourself: no selling, no medical advice, every claim is true.")
    return "\n".join(lines)


def handle(message):
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    log(f"Received from {message.get('from', {}).get('first_name', 'user')}: {text[:60]!r}")
    if not text:
        send_text(chat_id, "I can only read text messages for now. Type or paste your note.")
        return

    command, _, rest = text.partition(" ")
    command = command.split("@")[0].lower()
    if command in ("/start", "/help"):
        send_text(chat_id, HELP_TEXT)
        return
    modes = {"/linkedin": ("linkedin",), "/newsletter": ("newsletter",), "/both": ("linkedin", "newsletter")}
    if command in modes:
        note, wanted = rest.strip(), modes[command]
    elif command.startswith("/"):
        send_text(chat_id, HELP_TEXT)
        return
    else:
        note, wanted = text, ("linkedin",)

    if len(note) < 20:
        send_text(chat_id, "Add your note after the command, e.g. /newsletter batch fourteen came back...")
        return

    send_text(chat_id, "Got it. Drafting and checking against your QA list - about 30-60 seconds.")
    try:
        if "linkedin" in wanted:
            tg("sendChatAction", chat_id=chat_id, action="typing")
            post, failures, warnings, revisions = write_linkedin(note)
            send_text(chat_id, post)
            send_text(chat_id, qa_report(failures, warnings, revisions))
            log(f"Sent LinkedIn post ({len(post.split())} words, {revisions} revisions, "
                f"{len(failures)} failures)")
        if "newsletter" in wanted:
            tg("sendChatAction", chat_id=chat_id, action="typing")
            send_text(chat_id, gemini(NEWSLETTER_PROMPT, [("user", "Meera's raw note:\n\n" + note)]))
            log("Sent newsletter")
    except urllib.error.HTTPError as e:
        print("Gemini error:", e.code, e.read()[:500])
        send_text(chat_id, f"Gemini returned an error ({e.code}). Try again in a minute.")
    except Exception as e:
        print("Error:", repr(e))
        send_text(chat_id, "Something went wrong while drafting. Try again in a minute.")


def main():
    me = tg("getMe")["result"]
    print(f"Running as @{me['username']} with {GEMINI_MODEL}. Press Ctrl+C to stop.")
    offset = None
    while True:
        try:
            params = {"timeout": 50, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset
            for update in tg("getUpdates", **params)["result"]:
                offset = update["update_id"] + 1
                if "message" in update:
                    handle(update["message"])
        except KeyboardInterrupt:
            print("Stopped.")
            return
        except Exception as e:
            log(f"Polling error, retrying in 5s: {e!r}")
            time.sleep(5)


if __name__ == "__main__":
    main()
