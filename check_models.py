"""Time one short answer from each Gemini model, to pick a fast one for the demo.

Run from the project folder:  python check_models.py
"""

import os
import time

os.environ.setdefault("GEMINI_TIMEOUT", "60")  # wait longer than the app does

from app import gemini  # noqa: E402  (app.config reads GEMINI_TIMEOUT on import)

MODELS = ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite"]

print("Testing 3 models, up to 1 minute each...\n")
client = gemini.make_client()
for model in MODELS:
    start = time.time()
    try:
        gemini.GeminiChat(client, model).generate_content("Réponds en une phrase : bonjour !")
        print(f"{model:24} {time.time() - start:5.1f} s   OK")
    except Exception as exc:
        print(f"{model:24} {time.time() - start:5.1f} s   ERROR {str(exc)[:90]}")
