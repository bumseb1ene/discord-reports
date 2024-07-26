# In helpers.py
import re
import json

def remove_markdown(content):
    # Entfernt Discord Markdown-Formatierung (fett, kursiv, unterstrichen, durchgestrichen, Inline-Code)
    patterns = [r'\*\*', r'__', r'\*', r'~~', r'\`']
    for pattern in patterns:
        content = re.sub(pattern, '', content)
    return content.lower()

def remove_bracketed_content(text):
    """ Entfernt alle Inhalte in eckigen Klammern aus dem Text. """
    return re.sub(r"\[.*?\]", "", text)

def find_player_names(text, excluded_words):
    """ Identifiziert potenzielle Spielernamen im Text, schließt bestimmte Wörter aus. """
    words = text.split()
    potential_names = []
    for i in range(len(words)):
        # Einzelne Wörter als potenzielle Namen, sofern sie nicht ausgeschlossen sind
        if words[i].lower() not in excluded_words:
            potential_names.append(words[i])

        # Kombination von zwei Wörtern, sofern beide nicht ausgeschlossen sind
        if i < len(words) - 1:
            if words[i].lower() not in excluded_words and words[i + 1].lower() not in excluded_words:
                potential_names.append(words[i] + " " + words[i + 1])
    return potential_names

# Load the language file
with open('languages.json', 'r', encoding="utf8") as file:
    languages = json.load(file)

def get_translation(lang, key):
    '''Fetches the translation for a specific key and language.'''
    return languages.get(lang, {}).get(key, "")

author_name = None

def set_author_name(name):
    global author_name
    author_name = name

def get_author_name():
    return author_name

# Laden der Liste der auszuschließenden Wörter
def load_excluded_words(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data.get("exclude", [])

def remove_clantags(name):
    # Entfernen von Clantags mit bis zu 4 Zeichen in eckigen Klammern oder zwischen | |
    # sowie der spezifischen Kombination i|i
    name_without_clantags = re.sub(r"\[.{1,4}?\]|\|.{1,4}?\||i\|i", "", name)
    # Entfernen von Sonderzeichen und Emojis
    name_cleaned = re.sub(r"[^\w\s]", "", name_without_clantags, flags=re.UNICODE)
    return name_cleaned.strip()


