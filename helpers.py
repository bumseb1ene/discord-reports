# In helpers.py
import re
import json
from datetime import datetime
import time
import logging
import tempfile

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


# Ads Modlog and Clears Buttons
async def add_modlog(interaction, logmessage, player_id, user_lang, api_client, original_message = False):
    now = datetime.now()  # current date and time
    date_time = now.strftime("%d.%m.%Y %H:%M:%S:")
    logging.info(date_time + logmessage) # Log in File
    if player_id is not False:
        await api_client.post_player_comment(player_id, logmessage)
    mesg_id = interaction.message.id
    if original_message == False:
        original_message = await interaction.channel.fetch_message(interaction.message.id)
    actiontime = "<t:" + str(int(time.time())) + ":f>: "
    logmessage = actiontime + logmessage
    new_embed = original_message.embeds[0]
    new_embed.add_field(name=get_translation(user_lang, "logbook"),value=logmessage)
    await original_message.edit(view=None, embed=new_embed)


async def only_remove_buttons(interaction):
    original_message = await interaction.channel.fetch_message(interaction.message.id)
    await original_message.edit(view=None)


async def add_check_to_messages(interaction, original_message = False):
    if original_message == False:
        original_message = await interaction.channel.fetch_message(interaction.message.id)
    await original_message.add_reaction('✅')
    reportmessage = await original_message.channel.fetch_message(original_message.reference.message_id)
    await reportmessage.add_reaction('✅')


async def add_emojis_to_messages(interaction, emoji = '⚠️'):
    original_message = await interaction.channel.fetch_message(interaction.message.id)
    await original_message.add_reaction(emoji)
    reportmessage = await original_message.channel.fetch_message(original_message.reference.message_id)
    await reportmessage.add_reaction(emoji)

async def get_playername(self):
    player_name = await self.api_client.get_player_by_steam_id(self.player_id)
    if player_name:
        name = player_name
    else:
        name = self.player_id
    return name

async def get_logs(api_client, player_name):
    logs = await api_client.get_structured_logs(60, None, None)  # Fetching logs without filtering by name
    if logs and 'logs' in logs['result']:
        log_message = ""
        for log in logs['result']['logs']:
            if log['player_name_1'] == player_name or log.get('player_name_2') == player_name:
                timestamp = datetime.fromtimestamp(log['timestamp_ms']/1000)
                timestr = timestamp.strftime("%d.%m.%Y %H:%M:%S")
                log_messages = f"{timestr}: {log['action']} by {log['player_name_1']} - {log['message']}"
                log_message = log_message + log_messages + "\n"
        if log_message:
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as temp_log_file:
                temp_log_file.write(log_message)
                filename = temp_log_file.name
            return filename
    else:
       logging.debug("No logs found or error fetching logs")