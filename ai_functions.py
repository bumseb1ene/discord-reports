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

async def classify_report_text(ai_client, text: str, user_language: str) -> tuple[str, str, str]:
    """
    Classifies the report text and returns a tuple:
    (category, subcategory, reason)
    If no subcategory is detected, subcategory will be "none".
    """
    logging.info("classify_report_text: Classifying text => '%s'", text)
    base_prompt = prompt_manager.get_nested_prompt("prompts.classification.report.templates.instructions", user_language)
    logging.info("base_prompt Inhalt: %s", base_prompt)
    max_length = prompt_manager.get_nested_prompt("prompts.classification.report.metadata.max_length", user_language)
    
    user_content = base_prompt.format(
        text=text,
        max_length=max_length,
        legit="legit",
        insult="insult",
        temp_ban="temp_ban",
        perma="perma",
        unknown="unknown"
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
        subcategory = "none"
        reason_text = ""
        found_category = False

        # Versuche, Zeile für Zeile das erwartete Format zu parsen
        for ln in full_answer.splitlines():
            ln_stripped = ln.strip()
            ln_lower = ln_stripped.lower()
            if ln_lower.startswith("category:"):
                found_category = True
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
        
        # Fallback: Suche im gesamten Text, falls kein "CATEGORY:" gefunden wurde
        if not found_category:
            lower_response = full_answer.lower()
            if "insult" in lower_response:
                category = "insult"
            elif "legit" in lower_response:
                category = "legit"
            elif "temp_ban" in lower_response:
                category = "temp_ban"
            elif "perma" in lower_response:
                category = "perma"
        
        # Zusätzliche Erkennung von Subkategorien anhand von Stichworten
        lower_response = full_answer.lower()
        if category == "legit":
            technical_keywords = ["technical", "bug", "server", "faulty", "map data", "disconnect", "crash", "texture", "lag"]
            communication_keywords = ["communication", "team", "chat", "instructions", "coordination", "understanding"]
            general_keywords = ["general", "uncertain", "vague", "suspicious", "concern", "indirect"]
            if any(word in lower_response for word in technical_keywords):
                subcategory = "technical"
            elif any(word in lower_response for word in communication_keywords):
                subcategory = "communication"
            elif any(word in lower_response for word in general_keywords):
                subcategory = "general"
        elif category == "insult":
            mild_keywords = ["dummy", "fool", "silly", "stupid", "doof"]
            strong_keywords = ["asshole", "bastard", "goddamn idiot", "loser", "scumbag", "insufferable"]
            personal_keywords = ["ugly", "hideous", "incompetent", "failure", "pitiful"]
            if any(word in lower_response for word in mild_keywords):
                subcategory = "mild"
            elif any(word in lower_response for word in strong_keywords):
                subcategory = "strong"
            elif any(word in lower_response for word in personal_keywords):
                subcategory = "personal"
        elif category == "temp_ban":
            very_strong_keywords = ["damned", "incorrigible", "fucking", "shithead", "detestable"]
            provocative_keywords = ["provocateur", "troublemaker", "imposition", "invite trouble", "aggressive"]
            unacceptable_keywords = ["unacceptable", "goes too far", "not acceptable", "unbearable"]
            if any(word in lower_response for word in very_strong_keywords):
                subcategory = "very_strong"
            elif any(word in lower_response for word in provocative_keywords):
                subcategory = "provocative"
            elif any(word in lower_response for word in unacceptable_keywords):
                subcategory = "unacceptable"
        elif category == "perma":
            racism_keywords = ["nazi", "judensau", "n-word", "gypsy", "inferior", "racist"]
            extremism_keywords = ["genocide", "cleanse", "extremist", "warmonger", "fanatic"]
            hate_speech_keywords = ["go hang yourself", "disgusting bastard", "hate speech", "i hate you"]
            advert_keywords = ["people's party", "join us", "vote for", "alternative for the people"]
            if any(word in lower_response for word in racism_keywords):
                subcategory = "racism"
            elif any(word in lower_response for word in extremism_keywords):
                subcategory = "extremism"
            elif any(word in lower_response for word in hate_speech_keywords):
                subcategory = "hate_speech"
            elif any(word in lower_response for word in advert_keywords):
                subcategory = "advert_extremist_parties"
        
        logging.info("classify_report_text: category='%s', subcategory='%s', reason='%s'", category, subcategory, reason_text)
        return (category, subcategory, reason_text)
    
    except Exception as e:
        logging.error("[AI Error in classify_report_text] %s", e)
        return ("unknown", "none", "")

async def classify_insult_severity(ai_client, text: str, user_language: str) -> tuple[str, str]:
    logging.info("classify_insult_severity: Checking insult severity for text => '%s'", text)
    base_prompt = prompt_manager.get_nested_prompt("prompts.classification.insult.templates.instructions", user_language)
    if not isinstance(base_prompt, str):
        logging.error("Error: base_prompt is not a string! Found: %s", base_prompt)
        return ("warning", "Error determining severity; defaulting to warning")
    
    severity_levels = prompt_manager.get_nested_prompt("prompts.classification.insult.metadata.levels", user_language)
    logging.info("severity_levels: %s", severity_levels)
    if not isinstance(severity_levels, dict):
        logging.error("Error: severity_levels is not a dictionary! Found: %s", severity_levels)
        severity_levels = {"warning": "warning", "temp_ban": "temp_ban", "perma": "perma"}
    
    warning_val = severity_levels.get("warning", "warning")
    temp_ban_val = severity_levels.get("temp_ban", "temp_ban")
    perma_val = severity_levels.get("perma", "perma")
    
    # Format-Parameter vorbereiten
    format_params = {
        "text": text,
        "warning": warning_val,
        "temp_ban": temp_ban_val,
        "perma": perma_val,
        "levels": f"{warning_val} / {temp_ban_val} / {perma_val}",
        "category": "CATEGORY",
        "reason": "REASON"
    }
    expected_keys = ["text", "warning", "temp_ban", "perma", "levels", "category", "reason"]
    missing_keys = [key for key in expected_keys if f"{{{key}}}" in base_prompt and key not in format_params]
    if missing_keys:
        logging.error("Error: base_prompt is missing required keys: %s", missing_keys)
        return ("warning", "Error formatting prompt; defaulting to warning")
    
    try:
        user_content = base_prompt.format(**format_params)
    except KeyError as e:
        logging.error("Error formatting base_prompt: Missing key %s", e)
        return ("warning", "Error formatting prompt; defaulting to warning")
    
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
        logging.info("classify_insult_severity: Raw severity response => '%s'", full_answer)
        
        severity = "warning"  # Standardwert
        reason = ""
        for ln in full_answer.splitlines():
            ln_stripped = ln.strip()
            ln_lower = ln_stripped.lower()
            if ln_lower.startswith("severity:") or ln_lower.startswith("severity level:"):
                severity_val = ln_stripped.split(":", 1)[1].strip().lower()
                found = False
                for key in severity_levels.values():
                    if key in severity_val:
                        severity = key
                        found = True
                        break
                if not found:
                    logging.warning("Unexpected severity level: '%s'. Defaulting to 'warning'", severity_val)
                    severity = "warning"
            elif ln_lower.startswith("reason:"):
                reason = ln_stripped.split(":", 1)[1].strip()
        
        logging.info("classify_insult_severity: severity='%s', reason='%s'", severity, reason)
        return (severity, reason)
    
    except Exception as e:
        logging.error("[AI Severity Error] %s", e)
        return ("warning", "Error determining severity; defaulting to warning")

async def classify_comprehensive(ai_client, text: str, user_language: str) -> tuple[str, str, str, str]:
    """
    Führt eine umfassende Klassifikation des Report-Textes durch.
    Gibt ein Tuple zurück: (category, severity, reason, explanation)
    """
    logging.info("classify_comprehensive: Classifying text comprehensively => '%s'", text)
    base_prompt = prompt_manager.get_nested_prompt("prompts.classification.comprehensive.templates.instructions", user_language)
    max_length = prompt_manager.get_nested_prompt("prompts.classification.comprehensive.metadata.max_length", user_language)
    
    user_content = base_prompt.format(
        text=text,
        max_length=max_length,
        legit="legit",
        insult="insult",
        temp_ban="temp_ban",
        perma="perma",
        unknown="unknown"
    )
    system_prompt = f"You are a helpful assistant. The user speaks {user_language}. Always answer in {user_language}."
    
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=200,
            temperature=0.7
        )
        full_answer = response.choices[0].message.content.strip()
        logging.info("classify_comprehensive: Raw response => '%s'", full_answer)
        
        category, severity, reason, explanation = "unknown", "none", "", ""
        for ln in full_answer.splitlines():
            ln_stripped = ln.strip()
            ln_lower = ln_stripped.lower()
            if ln_lower.startswith("category:"):
                category = ln_stripped.split(":", 1)[1].strip().lower()
            elif ln_lower.startswith("severity:"):
                severity = ln_stripped.split(":", 1)[1].strip().lower()
            elif ln_lower.startswith("reason:"):
                reason = ln_stripped.split(":", 1)[1].strip()
            elif ln_lower.startswith("explanation:"):
                explanation = ln_stripped.split(":", 1)[1].strip()
        
        return (category, severity, reason, explanation)
    
    except Exception as e:
        logging.error("[AI Error in classify_comprehensive] %s", e)
        return ("unknown", "none", "", "")

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
    user_content = prompt_template.format(author_name=author_name, reason="")
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
