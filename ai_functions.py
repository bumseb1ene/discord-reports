import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL", "gpt-4o-mini-2024-07-18")

# Lade die Prompts aus der JSON-Datei
with open("prompts.json", "r", encoding="utf8") as f:
    prompts = json.load(f)

def get_prompt(prompt_key: str, lang: str, **kwargs) -> str:
    template = prompts.get(prompt_key, {}).get(lang)
    if template:
        return template.format(**kwargs)
    return ""

async def generate_warning_text(ai_client, author_name: str, reason: str, lang: str) -> str:
    prompt = get_prompt("generate_warning_text", lang, author_name=author_name, reason=reason)
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 200:
            text = text[:200].rstrip() + "…"
        return text
    except Exception as e:
        logging.error(f"Error generating warning text: {e}")
        return f"Hey {author_name}, änder dein Verhalten, sonst gibt's Ärger!"

async def generate_tempban_text(ai_client, author_name: str, reason: str, lang: str) -> str:
    prompt = get_prompt("generate_tempban_text", lang, author_name=author_name, reason=reason)
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 240:
            text = text[:240].rstrip() + "…"
        return text
    except Exception as e:
        logging.error(f"Error generating temp ban text: {e}")
        return f"Hey {author_name}, du bekommst 24h Bann – ändere sofort dein Verhalten!"

async def generate_permaban_text(ai_client, author_name: str, reason: str, lang: str) -> str:
    prompt = get_prompt("generate_permaban_text", lang, author_name=author_name, reason=reason)
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 240:
            text = text[:240].rstrip() + "…"
        return text
    except Exception as e:
        logging.error(f"Error generating perma ban text: {e}")
        return f"Hey {author_name}, dein Verhalten ist untragbar – du bist dauerhaft aus Hell Let Loose ausgeschlossen!"

async def generate_kick_text(ai_client, author_name: str, reason: str, lang: str) -> str:
    prompt = get_prompt("generate_kick_text", lang, author_name=author_name, reason=reason)
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 240:
            text = text[:240].rstrip() + "…"
        return text
    except Exception as e:
        logging.error(f"Error generating kick text: {e}")
        return f"Hey {author_name}, du wirst jetzt gekickt, weil dein Verhalten nicht akzeptabel ist!"

async def classify_report_text(ai_client, text: str, lang: str) -> tuple[str, str]:
    prompt = get_prompt("classify_report_text", lang, text=text)
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.8
        )
        full_answer = response.choices[0].message.content.strip()
        kategorie = "unbekannt"
        begruendung = ""
        for ln in full_answer.splitlines():
            ln = ln.strip()
            if ln.lower().startswith("kategorie:"):
                val = ln[10:].strip().lower()
                if "legitim" in val:
                    kategorie = "legitim"
                elif "beleidigung" in val:
                    kategorie = "beleidigung"
                elif "perma" in val:
                    kategorie = "perma"
                else:
                    kategorie = "unbekannt"
            elif ln.lower().startswith("begründung:") or ln.lower().startswith("begruendung:"):
                begruendung = ln.split(":", 1)[1].strip()
        return (kategorie, begruendung)
    except Exception as e:
        logging.error(f"[KI-Fehler] {e}")
        return ("unbekannt", "")

async def classify_insult_severity(ai_client, text: str, lang: str) -> tuple[str, str]:
    prompt = get_prompt("classify_insult_severity", lang, text=text)
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.0
        )
        full_answer = response.choices[0].message.content.strip()
        severity = "warning"
        reason = ""
        for ln in full_answer.splitlines():
            ln = ln.strip()
            if ln.lower().startswith("schweregrad:"):
                severity = ln.split(":", 1)[1].strip().lower()
            elif ln.lower().startswith("begründung:") or ln.lower().startswith("begruendung:"):
                reason = ln.split(":", 1)[1].strip()
        return (severity, reason)
    except Exception as e:
        logging.error(f"[KI-Schweregrad-Fehler] {e}")
        return ("warning", "Fehler bei der Schweregradbestimmung, Standard: Verwarnung")

async def generate_positive_response_text(ai_client, author_name, context_text, user_lang):
    prompt = get_prompt("generate_positive_response_text", user_lang, author_name=author_name, reason=context_text)
    response = await ai_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0.8
    )
    generated_text = response.choices[0].message.content.strip()
    return generated_text


