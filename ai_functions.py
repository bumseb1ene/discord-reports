import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("OPENAI_API_MODEL", "gpt-4o-mini")

# Lade Prompts
with open("prompts.json", "r", encoding="utf8") as f:
    prompts = json.load(f)

def load_prompt_text(prompt_key: str, lang: str) -> str:
    """
    Lädt den Prompttext aus prompts.json.
    Fallback: Falls lang nicht in (en, de) ist => englisches Prompt.
    """
    if lang not in ("en", "de"):
        base_lang = "en"
    else:
        base_lang = lang
    prompt_data = prompts.get(prompt_key, {})
    return prompt_data.get(base_lang, "")

async def detect_language(ai_client, text: str) -> str:
    """
    Erkennt die Sprache (ISO-Kürzel, z.B. 'en', 'de', 'fr', 'es').
    Bei Fehler => 'en'.
    """
    if not text.strip():
        return "en"
    system_prompt = (
        "You are a language detection model. "
        "Return ONLY the ISO-639-1 code of the text (e.g. 'en', 'de', 'fr', 'es'). "
        "No explanations, no extra text."
    )
    user_prompt = f"{text}\n"

    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=5,
            temperature=0.0
        )
        detected = response.choices[0].message.content.strip().lower()
        # Bekannte Sprachen kurz prüfen:
        if detected.startswith("de"):
            return "de"
        elif detected.startswith("fr"):
            return "fr"
        elif detected.startswith("es"):
            return "es"
        elif detected.startswith("en"):
            return "en"
        # Falls z.B. "pt" etc. => nimm das
        if len(detected) >= 2:
            return detected[:2]
        return "en"
    except Exception as e:
        logging.error(f"Error detecting language: {e}")
        return "en"

async def translate_text(ai_client, original_text: str, from_lang: str, to_lang: str) -> str:
    """
    Übersetzt original_text von from_lang nach to_lang mithilfe eines OpenAI-Systemprompts.
    Falls from_lang == to_lang, gib original_text unverändert zurück.
    """
    if not original_text.strip():
        return original_text
    if from_lang == to_lang:
        return original_text  # Keine Übersetzung nötig

    # System-Prompt, der nur den übersetzten Text zurückgibt.
    system_prompt = (
        f"You are a translation model. Translate the following from {from_lang} to {to_lang}. "
        "Return only the translated text, nothing else."
    )
    user_prompt = original_text

    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error translating text: {e}")
        return original_text

# --- Klassifizierung (erzeugt reason_text in Spieler-Sprache) ---
async def classify_report_text(ai_client, text: str, user_language: str) -> tuple[str, str]:
    """
    Weist den Text einer Kategorie zu: legit, insult, temp_ban, perma, unknown.
    => Prompt-Template basierend auf (en/de).
    => System-Prompt erzwingt Antwort in user_language.
    => reason_text kommt in user_language zurück.
    """
    base_prompt = load_prompt_text("classify_report_text", user_language)
    user_content = base_prompt.format(
        text=text,
        legit="legit",
        insult="insult",
        temp_ban="temp_ban",
        perma="perma",
        unknown="unknown",
        category="CATEGORY",
        reason="REASON"
    )
    system_prompt = f"You are a helpful assistant. The user speaks {user_language}. Always answer in {user_language}."

    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=150,
            temperature=0.7
        )
        full_answer = response.choices[0].message.content.strip()
        category = "unknown"
        reason_text = ""
        for ln in full_answer.splitlines():
            ln = ln.strip()
            if ln.lower().startswith("category:"):
                val = ln[9:].strip().lower()
                if "legit" in val:
                    category = "legit"
                elif "insult" in val:
                    category = "insult"
                elif "temp_ban" in val:
                    category = "temp_ban"
                elif "perma" in val:
                    category = "perma"
                else:
                    category = "unknown"
            elif ln.lower().startswith("reason:"):
                reason_text = ln.split(":", 1)[1].strip()
        return (category, reason_text)
    except Exception as e:
        logging.error(f"[AI Error in classify_report_text] {e}")
        return ("unknown", "")

async def classify_insult_severity(ai_client, text: str, user_language: str) -> tuple[str, str]:
    """
    Ermittelt Schweregrad: warning / temp_ban / perma
    => reason kommt in user_language raus.
    """
    base_prompt = load_prompt_text("classify_insult_severity", user_language)
    user_content = base_prompt.format(
        text=text,
        warning="warning",
        temp_ban="temp_ban",
        perma="perma",
        category="CATEGORY",
        reason="REASON"
    )
    system_prompt = f"You are a helpful assistant. The user speaks {user_language}. Always answer in {user_language}."

    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=100,
            temperature=0.7
        )
        full_answer = response.choices[0].message.content.strip()
        severity = "warning"
        reason = ""
        for ln in full_answer.splitlines():
            ln = ln.strip()
            if ln.lower().startswith("severity:"):
                severity = ln.split(":", 1)[1].strip().lower()
            elif ln.lower().startswith("reason:"):
                reason = ln.split(":", 1)[1].strip()
        return (severity, reason)
    except Exception as e:
        logging.error(f"[AI Severity Error] {e}")
        return ("warning", "Error determining severity; defaulting to warning")

# --- Generierung von Text an den Spieler (Warn, Kick, TempBan, PermaBan, Positive) ---

async def generate_warning_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    prompt = load_prompt_text("generate_warning_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=reason)
    system_prompt = f"The user (player) speaks {user_language}. Always respond in {user_language}."

    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 200:
            text = text[:200].rstrip() + "…"
        return text
    except Exception as e:
        logging.error(f"Error generating warning text: {e}")
        return f"Hey {author_name}, change your behavior or there will be consequences!"

async def generate_tempban_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    prompt = load_prompt_text("generate_tempban_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=reason)
    system_prompt = f"The user (player) speaks {user_language}. Always respond in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 240:
            text = text[:240].rstrip() + "…"
        return text
    except Exception as e:
        logging.error(f"Error generating temp ban text: {e}")
        return f"Hey {author_name}, you will receive a 24-hour ban – change your behavior immediately!"

async def generate_permaban_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    prompt = load_prompt_text("generate_permaban_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=reason)
    system_prompt = f"The user (player) speaks {user_language}. Always respond in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 240:
            text = text[:240].rstrip() + "…"
        return text
    except Exception as e:
        logging.error(f"Error generating perma ban text: {e}")
        return f"Hey {author_name}, your behavior is unacceptable – you are permanently banned!"

async def generate_kick_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    prompt = load_prompt_text("generate_kick_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=reason)
    system_prompt = f"The user (player) speaks {user_language}. Always respond in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 240:
            text = text[:240].rstrip() + "…"
        return text
    except Exception as e:
        logging.error(f"Error generating kick text: {e}")
        return f"Hey {author_name}, you are being kicked because your behavior is not acceptable!"

async def generate_positive_response_text(ai_client, author_name, context_text, user_language):
    """
    Für 'legit' oder positive Admin-Antworten.
    """
    prompt = load_prompt_text("generate_positive_response_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=context_text)
    system_prompt = f"The user (player) speaks {user_language}. Always respond in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error generating positive text: {e}")
        return "I'm glad you appreciate it!"
