import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("OPENAI_API_MODEL", "gpt-3.5-turbo")  # Beispielhaft

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

async def analyze_text(ai_client, text: str, user_lang: str) -> dict:
    """
    Erkennt Sprache (ISO-Kürzel),
    ordnet den Text einer Kategorie zu: legit, insult, temp_ban, perma, unknown
    und ermittelt (falls beleidigend) den Schweregrad: warning, temp_ban, perma.
    Gibt zudem eine kurze Begründung (reason) zurück, möglichst in der erkannten Sprache.
    
    Zusätzliche Regel:
    - Persönliche Meinungen, Aussagen => 'legit'.
    - Persönliche Angriffe wie Motherfucker, Hurensohn => 'perma'.
    - Falls unsicher => 'legit'.
    - Sehr kurze Texte oder solche, die nur aus gängigen Internet-/Gaming-Abkürzungen bestehen (z. B. "haha", "lol", "gg"), sollen in der Standardsprache (user_lang) beantwortet werden.
    """
    if not text.strip():
        return {
            "lang": "en",
            "category": "unknown",
            "severity": None,
            "reason": ""
        }

    system_prompt = (
        f"You are a concise text analyzer. Your default output language must be the one specified by the bot's {user_lang} setting. "
        f"If the text is clearly written in a language other than {user_lang} (either English or German), then detect and indicate that language. "
        "However, if the text contains ambiguous words that could belong to either language, or if it is very short or consists solely of common internet abbreviations or gaming jargon (e.g. 'haha', 'lol', 'gg'), always respond in the language specified by user_lang. "
        f"For example, if user_lang is '{user_lang}', even ambiguous words must result in a {user_lang} response. "
        "Treat mild negative phrases like 'das ist doof' as 'legit' (not as an insult). For strong hate speech, severe insults, or discriminatory language, normally classify as 'insult' or 'perma'. "
        "However, if the text is a report of violations committed by other players (for example, insults, racism, anti-Semitism, or NS slogans in voice chat), always classify the text as 'legit'. "
        "Advertising for right-wing extremist parties such as the AfD should be classified as 'perma'. "
        "Note: Hell Let Loose uses the American military alphabet from World War II for squad names. Therefore, references such as 'love' (e.g. Officer Love of the Love Squad) must not be interpreted as insults. "
        "Output strictly in valid JSON with these keys: {\"lang\": \"...\", \"category\": \"...\", \"severity\": \"...\", \"reason\": \"...\"}"
    )



    user_prompt = f"""
1) Which ISO-639-1 language code best matches this text? (e.g. 'en', 'de')
2) Classify the text into one of: legit, insult, temp_ban, perma, or unknown.
3) If classified as insult, temp_ban, or perma, also determine severity: 'warning', 'temp_ban', or 'perma'.
4) Provide a brief reason (max 186 chars), in the same language as the text.
5) Allow expressions of opinion that do not offend anyone in 'legit'.

Output JSON exactly in this format (no extra keys):

{{
  "lang": "...",
  "category": "...",
  "severity": "...",
  "reason": "..."
}}

Text: {text}
"""

    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=150,
            temperature=0.0
        )
        raw_answer = response.choices[0].message.content.strip()
        logging.info("analyze_text: raw_answer => %s", raw_answer)
        parsed = {
            "lang": "en",
            "category": "unknown",
            "severity": None,
            "reason": ""
        }
        try:
            parsed_json = json.loads(raw_answer)
            parsed["lang"] = parsed_json.get("lang", "en")
            parsed["category"] = parsed_json.get("category", "unknown")
            parsed["severity"] = parsed_json.get("severity", None)
            parsed["reason"] = parsed_json.get("reason", "")
        except json.JSONDecodeError:
            logging.warning("analyze_text: Could not parse JSON, returning fallback.")
        return parsed
    except Exception as e:
        logging.error("Error in analyze_text: %s", e)
        return {
            "lang": "en",
            "category": "unknown",
            "severity": None,
            "reason": ""
        }

# Übersetzungsfunktion entfernt – alle Texte werden direkt in user_lang generiert

async def generate_warning_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    logging.info("generate_warning_text: %s, reason='%s'", author_name, reason)
    prompt = load_prompt_text("generate_warning_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=reason)

    system_prompt = f"You are an AI admin. Answer in {user_language}."

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
        logging.error("Error generating warning text: %s", e)
        return f"Warning, {author_name}: {reason} (Short)"

async def generate_tempban_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    logging.info("generate_tempban_text: %s, reason='%s'", author_name, reason)
    prompt = load_prompt_text("generate_tempban_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=reason)

    system_prompt = f"You are an AI admin. Answer in {user_language}."

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
        logging.error("Error generating temp ban text: %s", e)
        return f"24-hour ban, {author_name}: {reason}"

async def generate_permaban_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    logging.info("generate_permaban_text: %s, reason='%s'", author_name, reason)
    prompt = load_prompt_text("generate_permaban_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=reason)

    system_prompt = f"You are an AI admin. Answer in {user_language}."

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
        logging.error("Error generating perma ban text: %s", e)
        return f"Permanent ban, {author_name}: {reason}"

async def generate_kick_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    logging.info("generate_kick_text: %s, reason='%s'", author_name, reason)
    prompt = load_prompt_text("generate_kick_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=reason)

    system_prompt = f"You are an AI admin. Answer in {user_language}."

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
        logging.error("Error generating kick text: %s", e)
        return f"Kick, {author_name}: {reason}"

async def generate_positive_response_text(ai_client, author_name, context_text, user_language):
    """
    Für 'legit' oder positive Admin-Antworten.
    """
    logging.info("generate_positive_response_text: %s, context='%s'", author_name, context_text)
    prompt = load_prompt_text("generate_positive_response_text", user_language)
    user_content = prompt.format(author_name=author_name, reason=context_text)

    system_prompt = f"You are an AI admin. Answer in {user_language}."

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
        return text
    except Exception as e:
        logging.error("Error generating positive text: %s", e)
        return f"Hello {author_name}, thanks for your message!"
