"""Run the drafting pipeline on a note without Telegram.

Usage:  python3 demo.py [path/to/note.txt]
Defaults to examples/batch14_note.txt and saves the result to examples/<name>_output.txt.
"""

import os
import sys

import bot

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(bot.HERE, "examples", "batch14_note.txt")
note = open(path).read().strip()

print("Drafting LinkedIn post (generate -> QA checks -> fact-check -> revise)...")
post, failures, warnings, revisions = bot.write_linkedin(note)
report = bot.qa_report(failures, warnings, revisions)
print("Drafting newsletter...")
newsletter = bot.gemini(bot.NEWSLETTER_PROMPT, [("user", "Meera's raw note:\n\n" + note)])

output = (f"RAW NOTE\n{'=' * 60}\n{note}\n\n"
          f"LINKEDIN POST ({len(post.split())} words)\n{'=' * 60}\n{post}\n\n"
          f"{report}\n\n"
          f"NEWSLETTER\n{'=' * 60}\n{newsletter}\n")
out_path = os.path.splitext(path)[0].replace("_note", "") + "_output.txt"
with open(out_path, "w") as f:
    f.write(output)
print(output)
print(f"Saved to {out_path}")
