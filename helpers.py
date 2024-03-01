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

def find_player_names(text):
    """ Identifiziert potenzielle Spielernamen im Text. """
    words = text.split()
    potential_names = []
    for i in range(len(words)):
        potential_names.append(words[i])  # Einzelne Wörter als potenzielle Namen
        if i < len(words) - 1:
            potential_names.append(words[i] + " " + words[i + 1])  # Kombination von zwei Wörtern
    return potential_names

# Load the language file
with open('languages.json', 'r') as file:
    languages = json.load(file)

def get_translation(lang, key):
    '''Fetches the translation for a specific key and language.'''
    return languages.get(lang, {}).get(key, "")
