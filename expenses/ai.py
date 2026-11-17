"""
AI helper — uses Google Gemini (free API) to automatically guess the category
of an expense from its description (title).

Design goal: this must NEVER crash the app. If there is no API key, no
internet, or any error, it safely falls back to the 'Other' category. So the
whole application works perfectly with or without AI.

Uses Python's built-in urllib, so no extra package needs to be installed.
"""
import json
import os
import urllib.request
import urllib.error

from django.conf import settings
from .models import Expense

# The exact category names the model is allowed to choose from.
VALID_CATEGORIES = [c[0] for c in Expense.CATEGORY_CHOICES]

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


def categorize_expense(title):
    """
    Return the best category for an expense title using Gemini.
    Falls back to 'Other' if AI is unavailable for any reason.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        # No key configured — skip AI gracefully.
        return 'Other'

    model = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
    prompt = (
        "You are an expense categorizer. Choose the single best category for "
        f"this expense from exactly this list: {', '.join(VALID_CATEGORIES)}.\n"
        f'Expense: "{title}"\n'
        "Reply with ONLY the category word, nothing else."
    )

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 10},
    }).encode("utf-8")

    url = GEMINI_URL.format(model=model) + f"?key={api_key}"
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # Pull the text out of Gemini's response structure.
        answer = (
            data["candidates"][0]["content"]["parts"][0]["text"].strip()
        )
    except Exception:
        # Any failure (no internet, bad key, rate limit, parsing) -> safe fallback.
        return 'Other'

    # Only accept an answer that matches one of our real categories.
    for category in VALID_CATEGORIES:
        if category.lower() in answer.lower():
            return category
    return 'Other'
