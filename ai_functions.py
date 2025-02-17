import os
import logging
from dotenv import load_dotenv
from prompt_manager import PromptManager

load_dotenv()

MODEL = os.getenv("OPENAI_API_MODEL", "gpt-4o-mini")
prompt_manager = PromptManager(prompts_dir=".", default_lang="en")

async def detect_language(ai_client, text: str) -> str:
    if not text.strip():
        logging.info("detect_language: Empty text => defaulting to 'en'.")
        return "en"
    system_prompt = (
        "You are a language detection model. "
        "Return ONLY the ISO-639-1 code of the text (e.g. 'en', 'de', 'fr', 'es'). "
        "No explanations, no extra text."
    )
    user_prompt = f"{text}\n"
    logging.info("detect_language: Sending text to AI for language detection...")
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
        logging.info("detect_language: Raw AI response => '%s'", detected)
        if detected.startswith("de"):
            return "de"
        elif detected.startswith("fr"):
            return "fr"
        elif detected.startswith("es"):
            return "es"
        elif detected.startswith("en"):
            return "en"
        if len(detected) >= 2:
            return detected[:2]
        return "en"
    except Exception as e:
        logging.error("Error detecting language: %s", e)
        return "en"

async def translate_text(ai_client, original_text: str, from_lang: str, to_lang: str) -> str:
    logging.info("translate_text: from_lang=%s, to_lang=%s", from_lang, to_lang)
    if not original_text.strip():
        logging.info("translate_text: No text => returning as is.")
        return original_text
    if from_lang == to_lang:
        logging.info("translate_text: Same language => returning original text.")
        return original_text

    system_prompt = (
        f"You are a translation model. Translate the following from {from_lang} to {to_lang}. "
        "Return only the translated text, nothing else."
    )
    user_prompt = original_text
    logging.info("translate_text: Sending text to AI for translation...")
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
        translated = response.choices[0].message.content.strip()
        logging.info("translate_text: Translation result => '%s'", translated)
        return translated
    except Exception as e:
        logging.error("Error translating text: %s", e)
        return original_text

async def classify_report_text(ai_client, text: str, user_language: str) -> tuple[str, str]:
    logging.info("classify_report_text: Classifying text => '%s'", text)
    base_prompt = prompt_manager.get_nested_prompt("prompts.classification.report.templates.instructions", user_language)
    max_length = prompt_manager.get_nested_prompt("prompts.classification.report.metadata.max_length", user_language)
    user_content = base_prompt.format(
        text=text,
        legit="legit",
        insult="insult",
        temp_ban="temp_ban",
        perma="perma",
        unknown="unknown",
        category="CATEGORY",
        reason="REASON",
        max_length=max_length
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
        logging.info("classify_report_text: Raw classification response => '%s'", full_answer)
        category = "unknown"
        reason_text = ""
        for ln in full_answer.splitlines():
            ln_stripped = ln.strip()
            ln_lower = ln_stripped.lower()
            if ln_lower.startswith("category:"):
                val = ln_stripped.split(":", 1)[1].strip().lower()
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
            elif ln_lower.startswith("reason:"):
                reason_text = ln_stripped.split(":", 1)[1].strip()
        logging.info("classify_report_text: category='%s', reason='%s'", category, reason_text)
        return (category, reason_text)
    except Exception as e:
        logging.error("[AI Error in classify_report_text] %s", e)
        return ("unknown", "")

async def classify_insult_severity(ai_client, text: str, user_language: str) -> tuple[str, str]:
    logging.info("classify_insult_severity: Checking insult severity for text => '%s'", text)

    # Holen wir den Prompt für die Schweregradklassifizierung ohne den 'levels' Platzhalter
    base_prompt = prompt_manager.get_nested_prompt("prompts.classification.insult.templates.instructions", user_language)

    # Die Schweregrade direkt festlegen
    severity_levels = prompt_manager.get_nested_prompt("prompts.classification.insult.metadata.levels", user_language)
    warning_val = severity_levels.get("warning", "warning") if isinstance(severity_levels, dict) else "warning"
    temp_ban_val = severity_levels.get("temp_ban", "temp_ban") if isinstance(severity_levels, dict) else "temp_ban"
    perma_val = severity_levels.get("perma", "perma") if isinstance(severity_levels, dict) else "perma"
    
    # Prompt mit den expliziten Werten für warning, temp_ban und perma formatieren
    user_content = base_prompt.format(
        text=text,
        warning=warning_val,
        temp_ban=temp_ban_val,
        perma=perma_val,
        category="CATEGORY",
        reason="REASON"
    )

    system_prompt = f"You are a helpful assistant. The user speaks {user_language}. Always answer in {user_language}."

    try:
        # Sende den Request an die API
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
        logging.info("classify_insult_severity: Raw severity response => '%s'", full_answer)
        
        severity = "warning"  # Defaultwert
        reason = ""
        
        # Verarbeite die Antwort
        for ln in full_answer.splitlines():
            ln_stripped = ln.strip()
            ln_lower = ln_stripped.lower()

            # Extrahiere den Schweregrad
            if ln_lower.startswith("severity:"):
                severity_val = ln_stripped.split(":", 1)[1].strip().lower()
                if severity_val in ("warning", "temp_ban", "perma"):
                    severity = severity_val
                else:
                    severity = "warning"

            # Extrahiere den Grund
            elif ln_lower.startswith("reason:"):
                reason = ln_stripped.split(":", 1)[1].strip()

        logging.info("classify_insult_severity: severity='%s', reason='%s'", severity, reason)
        return (severity, reason)
    
    except Exception as e:
        logging.error("[AI Severity Error] %s", e)
        return ("warning", "Error determining severity; defaulting to warning")

async def generate_warning_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    logging.info("generate_warning_text: Generating warning text for '%s', reason='%s'", author_name, reason)
    template = prompt_manager.get_nested_prompt("prompts.actions.warning.templates.template", user_language)
    max_length = prompt_manager.get_nested_prompt("prompts.actions.warning.metadata.max_length", user_language)
    user_content = template.format(author_name=author_name, reason=reason, max_length=max_length)
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
        logging.info("generate_warning_text: AI response => '%s'", text)
        if len(text) > 200:
            text = text[:200].rstrip() + "…"
        return text
    except Exception as e:
        logging.error("Error generating warning text: %s", e)
        return f"Hey {author_name}, change your behavior or there will be consequences!"

async def generate_tempban_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    logging.info("generate_tempban_text: Generating 24h ban text for '%s', reason='%s'", author_name, reason)
    template = prompt_manager.get_nested_prompt("prompts.actions.tempban.templates.template", user_language)
    max_length = prompt_manager.get_nested_prompt("prompts.actions.tempban.metadata.max_length", user_language)
    user_content = template.format(author_name=author_name, reason=reason, max_length=max_length)
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
        logging.info("generate_tempban_text: AI response => '%s'", text)
        if len(text) > 240:
            text = text[:240].rstrip() + "…"
        return text
    except Exception as e:
        logging.error("Error generating temp ban text: %s", e)
        return f"Hey {author_name}, you will receive a 24-hour ban – change your behavior immediately!"

async def generate_permaban_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    logging.info("generate_permaban_text: Generating permanent ban text for '%s', reason='%s'", author_name, reason)
    template = prompt_manager.get_nested_prompt("prompts.actions.perma.templates.template", user_language)
    max_length = prompt_manager.get_nested_prompt("prompts.actions.perma.metadata.max_length", user_language)
    user_content = template.format(author_name=author_name, reason=reason, max_length=max_length)
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
        logging.info("generate_permaban_text: AI response => '%s'", text)
        if len(text) > 240:
            text = text[:240].rstrip() + "…"
        return text
    except Exception as e:
        logging.error("Error generating perma ban text: %s", e)
        return f"Hey {author_name}, your behavior is unacceptable – you are permanently banned!"

async def generate_kick_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    logging.info("generate_kick_text: Generating kick text for '%s', reason='%s'", author_name, reason)
    template = prompt_manager.get_nested_prompt("prompts.actions.kick.templates.template", user_language)
    max_length = prompt_manager.get_nested_prompt("prompts.actions.kick.metadata.max_length", user_language)
    user_content = template.format(author_name=author_name, reason=reason, max_length=max_length)
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
        logging.info("generate_kick_text: AI response => '%s'", text)
        if len(text) > 240:
            text = text[:240].rstrip() + "…"
        return text
    except Exception as e:
        logging.error("Error generating kick text: %s", e)
        return f"Hey {author_name}, you are being kicked because your behavior is not acceptable!"

async def generate_positive_response_text(ai_client, author_name, context_text, user_language):
    logging.info("generate_positive_response_text: Generating positive response for '%s', context='%s'", author_name, context_text)
    template = prompt_manager.get_nested_prompt("prompts.actions.positive.templates.template", user_language)
    user_content = template.format(author_name=author_name, reason=context_text)
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
        logging.info("generate_positive_response_text: AI response => '%s'", text)
        return text
    except Exception as e:
        logging.error("Error generating positive text: %s", e)
        return "I'm glad you appreciate it!"

async def generate_player_not_found_text(ai_client, author_name: str, user_language: str) -> str:
    key_path = "prompts.actions.player_not_found.templates.template"
    prompt_template = prompt_manager.get_nested_prompt(key_path, user_language)
    if not prompt_template:
        prompt_template = "Sorry {author_name}, we couldn't find a matching player."
    user_content = prompt_template.format(author_name=author_name)
    system_prompt = f"The user (player) speaks {user_language}. Always respond in {user_language}."
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
        text = response.choices[0].message.content.strip()
        return text
    except Exception as e:
        logging.error("Error generating player not found text: %s", e)
        return f"Sorry {author_name}, we couldn't find a matching player."
