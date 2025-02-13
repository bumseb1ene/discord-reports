import os
import json
from dotenv import load_dotenv

# Globale Variablen, in denen die Konfigurationsdaten gespeichert werden
languages = {}
prompts = {}
excluded_words = []
autorespond_trigger = {}

# Dictionary, um die letzte Änderungszeit (mtime) der Dateien zu speichern
config_mod_times = {}

def init_config_mod_times():
    """Initialisiert die mtime-Werte für alle Konfigurationsdateien."""
    global config_mod_times
    files = ['.env', 'languages.json', 'autorespond_trigger.json', 'exclude_words.json', 'prompts.json']
    for f in files:
        try:
            config_mod_times[f] = os.path.getmtime(f)
        except Exception as e:
            config_mod_times[f] = 0
            print(f"Fehler beim Initialisieren von {f}: {e}")

# Initiale mtime-Werte setzen
init_config_mod_times()

def reload_configs():
    """
    Prüft alle Konfigurationsdateien und lädt sie neu, wenn sie seit dem letzten Laden geändert wurden.
    Aktualisiert dabei auch .env-Variablen.
    """
    global config_mod_times, languages, prompts, excluded_words, autorespond_trigger

    # .env: Neu laden, falls geändert
    try:
        env_mtime = os.path.getmtime('.env')
        if env_mtime > config_mod_times.get('.env', 0):
            load_dotenv(override=True)
            config_mod_times['.env'] = env_mtime
            print("Neue .env-Daten geladen.")
    except Exception as e:
        print("Fehler beim Laden der .env:", e)

    # languages.json
    try:
        lang_mtime = os.path.getmtime('languages.json')
        if lang_mtime > config_mod_times.get('languages.json', 0):
            with open('languages.json', 'r', encoding='utf8') as file:
                languages = json.load(file)
            config_mod_times['languages.json'] = lang_mtime
            print("languages.json wurde neu geladen.")
    except Exception as e:
        print("Fehler beim Laden von languages.json:", e)

    # autorespond_trigger.json
    try:
        art_mtime = os.path.getmtime('autorespond_trigger.json')
        if art_mtime > config_mod_times.get('autorespond_trigger.json', 0):
            with open('autorespond_trigger.json', 'r', encoding='utf8') as file:
                autorespond_trigger = json.load(file)
            config_mod_times['autorespond_trigger.json'] = art_mtime
            print("autorespond_trigger.json wurde neu geladen.")
    except Exception as e:
        print("Fehler beim Laden von autorespond_trigger.json:", e)

    # exclude_words.json
    try:
        ew_mtime = os.path.getmtime('exclude_words.json')
        if ew_mtime > config_mod_times.get('exclude_words.json', 0):
            with open('exclude_words.json', 'r', encoding='utf8') as file:
                data = json.load(file)
                excluded_words = data.get("exclude", [])
            config_mod_times['exclude_words.json'] = ew_mtime
            print("exclude_words.json wurde neu geladen.")
    except Exception as e:
        print("Fehler beim Laden von exclude_words.json:", e)

    # prompts.json
    try:
        prompts_mtime = os.path.getmtime('prompts.json')
        if prompts_mtime > config_mod_times.get('prompts.json', 0):
            with open('prompts.json', 'r', encoding='utf8') as file:
                prompts = json.load(file)
            config_mod_times['prompts.json'] = prompts_mtime
            print("prompts.json wurde neu geladen.")
    except Exception as e:
        print("Fehler beim Laden von prompts.json:", e)
