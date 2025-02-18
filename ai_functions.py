import os
import logging
from dotenv import load_dotenv
from prompt_manager import PromptManager

load_dotenv()

MODEL = os.getenv("OPENAI_API_MODEL", "gpt-3.5-turbo")

prompt_manager = PromptManager(prompts_dir=".", default_lang="en")

#
# 1) Klassifikation
#
async def classify_comprehensive(ai_client, text: str, user_language: str) -> tuple[str, str, str, str]:
    """
    OUTPUT: 4 lines
    CATEGORY: <legit, insult, temp_ban, perma, unknown>
    SEVERITY: <warning, temp_ban, perma, none>
    REASON: ...
    EXPLANATION: ...
    """
    if not text.strip():
        return ("legit", "none", "No content", "Empty input")

    # Zusätzliche Regeln:
    # - legit: Anfragen, Hinweise, harmlose Aussagen
    # - insult: Beleidigungen, aber nicht extrem (z.B. "Idiot"). Severity "warning" oder "temp_ban"
    # - temp_ban: Sehr harte Beleidigungen/Aggression, Rassismus light
    # - perma: Extrem, Nazi, Rassismus hart, "heil hitler" etc.
    # - unknown: falls unklar
    # Bsp:
    extra_rules = f"""
Definition der Kategorien:
- legit: Normale Hinweise, Fragen, harmlose Aussagen ohne offensichtliche Beleidigung.
- insult: Mäßige Beleidigung oder Beschimpfung. Kann Severity=warning oder temp_ban sein (z.B. 'Du Idiot').
- temp_ban: Schwere, aggressive Beleidigung, aber noch kein Extremismus.
- perma: Extremistische/rassistische/hassvolle Inhalte (Nazi-Bezug, 'heil hitler', 'judensau', etc.).
- unknown: Falls du es nicht zuordnen kannst.

Definition Severity:
- warning: Leichte Beleidigung (z.B. 'Dummkopf').
- temp_ban: Massiv beleidigend, 'Arschloch', 'fick dich', Drohungen etc.
- perma: Rassismus, Extremismus, 'heil hitler', harte menschenverachtende Aussagen.
- none: Falls legit.
"""

    system_prompt = (
        f"You are a classification assistant. Always respond in {user_language}.\n"
        f"{extra_rules}\n"
        "Output exactly four lines:\n"
        "CATEGORY: <one of [legit, insult, temp_ban, perma, unknown]>\n"
        "SEVERITY: <one of [warning, temp_ban, perma, none]>\n"
        "REASON: <short text>\n"
        "EXPLANATION: <short explanation>\n"
        "No extra lines!"
    )

    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            max_tokens=200,
            temperature=0.0
        )
        full_answer = response.choices[0].message.content.strip()

        category, severity, reason, explanation = "unknown", "none", "", ""
        for line in full_answer.splitlines():
            line_lower = line.strip().lower()
            if line_lower.startswith("category:"):
                category = line.split(":", 1)[1].strip().lower()
            elif line_lower.startswith("severity:"):
                severity = line.split(":", 1)[1].strip().lower()
            elif line_lower.startswith("reason:"):
                reason = line.split(":", 1)[1].strip()
            elif line_lower.startswith("explanation:"):
                explanation = line.split(":", 1)[1].strip()

        return (category, severity, reason, explanation)

    except Exception as e:
        logging.error("[AI Error in classify_comprehensive] %s", e)
        return ("unknown", "none", "", "")

#
# 2) Generate-Aktions-Texte
#
async def generate_warning_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    template = prompt_manager.get_nested_prompt("prompts.actions.warning.templates.template", user_language)
    if not template:
        template = "Achtung, {author_name}! Grund: {reason}"
    user_content = template.format(author_name=author_name, reason=reason)

    system_prompt = f"Respond strictly in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.0
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 200:
            text = text[:200] + "..."
        return text
    except Exception as e:
        logging.error("Error generating warning text: %s", e)
        return f"Achtung, {author_name}! Grund: {reason}"

async def generate_tempban_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    template = prompt_manager.get_nested_prompt("prompts.actions.tempban.templates.template", user_language)
    if not template:
        template = "Du erhältst einen 24h-Bann, {author_name}. Grund: {reason}"
    user_content = template.format(author_name=author_name, reason=reason)

    system_prompt = f"Respond strictly in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.0
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 240:
            text = text[:240] + "..."
        return text
    except Exception as e:
        logging.error("Error generating temp ban text: %s", e)
        return f"{author_name}, du erhältst einen 24h-Bann! Grund: {reason}"

async def generate_permaban_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    template = prompt_manager.get_nested_prompt("prompts.actions.perma.templates.template", user_language)
    if not template:
        template = "Du wirst permanent gebannt, {author_name}. Grund: {reason}"
    user_content = template.format(author_name=author_name, reason=reason)

    system_prompt = f"Respond in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.0
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 240:
            text = text[:240] + "..."
        return text
    except Exception as e:
        logging.error("Error generating perma ban text: %s", e)
        return f"{author_name}, du wirst permanent gebannt! Grund: {reason}"

async def generate_kick_text(ai_client, author_name: str, reason: str, user_language: str) -> str:
    template = prompt_manager.get_nested_prompt("prompts.actions.kick.templates.template", user_language)
    if not template:
        template = "Du wirst vom Server gekickt, {author_name}. Grund: {reason}"
    user_content = template.format(author_name=author_name, reason=reason)

    system_prompt = f"Respond in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.0
        )
        text = response.choices[0].message.content.strip()
        if len(text) > 240:
            text = text[:240] + "..."
        return text
    except Exception as e:
        logging.error("Error generating kick text: %s", e)
        return f"{author_name}, du wirst gekickt! Grund: {reason}"

async def generate_positive_response_text(ai_client, author_name, context_text, user_language):
    template = prompt_manager.get_nested_prompt("prompts.actions.positive.templates.template", user_language)
    if not template:
        template = "Danke dir, {author_name}, für deine Meldung: {reason}"
    user_content = template.format(author_name=author_name, reason=context_text)

    system_prompt = f"Respond in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=120,
            temperature=0.0
        )
        text = response.choices[0].message.content.strip()
        return text
    except Exception as e:
        logging.error("Error generating positive text: %s", e)
        return f"Danke dir, {author_name}!"

async def generate_player_not_found_text(ai_client, author_name: str, user_language: str) -> str:
    key_path = "prompts.actions.player_not_found.templates.template"
    prompt_template = prompt_manager.get_nested_prompt(key_path, user_language)
    if not prompt_template:
        prompt_template = "Entschuldigung, {author_name}, wir konnten keinen passenden Spieler finden."
    user_content = prompt_template.format(author_name=author_name)

    system_prompt = f"Respond in {user_language}."
    try:
        response = await ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=100,
            temperature=0.0
        )
        text = response.choices[0].message.content.strip()
        return text
    except Exception as e:
        logging.error("Error generating player not found text: %s", e)
        return f"Entschuldigung, {author_name}, kein passender Spieler gefunden."
