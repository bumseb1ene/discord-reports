# helpers.py
import re
import json
from datetime import datetime
import time
import logging
import tempfile

def remove_markdown(content):
    patterns = [r'\*\*', r'__', r'\*', r'~~', r'\`']
    for pattern in patterns:
        content = re.sub(pattern, '', content)
    return content.lower()

def remove_bracketed_content(text):
    return re.sub(r"\[.*?\]", "", text)

def remove_player_names(text, player_names):
    """
    Entfernt alle Vorkommen von Spielernamen aus dem Text.
    :param text: Der Originaltext.
    :param player_names: Liste der validierten Spielernamen.
    :return: Der Text ohne die Spielernamen.
    """
    for name in player_names:
        text = re.sub(r'\b' + re.escape(name) + r'\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def find_player_names(text, excluded_words):
    words = text.split()
    potential_names = []
    for i in range(len(words)):
        if words[i].lower() not in excluded_words:
            potential_names.append(words[i])
        if i < len(words) - 1:
            if words[i].lower() not in excluded_words and words[i + 1].lower() not in excluded_words:
                potential_names.append(words[i] + " " + words[i + 1])
    return potential_names

with open('languages.json', 'r', encoding="utf8") as file:
    languages = json.load(file)

def get_translation(lang, key):
    return languages.get(lang, {}).get(key, "")

author_name = None

def set_author_name(name):
    global author_name
    author_name = name

def get_author_name():
    return author_name if author_name else ""

def load_excluded_words(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data.get("exclude", [])

def load_autorespond_tigger(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def remove_clantags(name):
    name_without_clantags = re.sub(r"\[.{1,4}?\]|\|.{1,4}?\||i\|i", "", name)
    name_cleaned = re.sub(r"[^\w\s]", "", name_without_clantags, flags=re.UNICODE)
    return name_cleaned.strip()

async def add_modlog(interaction, logmessage, player_id, user_lang, api_client, original_message=False, delete_buttons=True, add_entry=False):
    now = datetime.now()
    date_time = now.strftime("%d.%m.%Y %H:%M:%S:")
    logging.info(date_time + logmessage)
    if player_id is not False:
        await api_client.post_player_comment(player_id, logmessage)
    actiontime = "<t:" + str(int(time.time())) + ":f>: "
    logmessage = actiontime + logmessage
    mesg_id = interaction.message.id
    if not original_message:
        original_message = await interaction.channel.fetch_message(interaction.message.id)
    new_embed = original_message.embeds[0]
    if not add_entry:
        new_embed.add_field(name=get_translation(user_lang, "logbook"), value=logmessage, inline=False)
    else:
        value = new_embed.fields[-1].value + "\n" + logmessage
        new_embed.set_field_at(index=-1, name=new_embed.fields[-1].name, value=value, inline=False)
    if delete_buttons:
        await original_message.edit(view=None, embed=new_embed)
    else:
        await original_message.edit(embed=new_embed)

async def only_remove_buttons(interaction):
    original_message = await interaction.channel.fetch_message(interaction.message.id)
    await original_message.edit(view=None)

async def add_check_to_messages(interaction, original_message=False):
    if not original_message:
        original_message = await interaction.channel.fetch_message(interaction.message.id)
    await original_message.add_reaction('✅')
    reportmessage = await original_message.channel.fetch_message(original_message.reference.message_id)
    await reportmessage.add_reaction('✅')

async def remove_emojis_to_messages(interaction, emoji='⚠️'):
    original_message = await interaction.channel.fetch_message(interaction.message.id)
    await original_message.clear_reaction(emoji)
    reportmessage = await interaction.channel.fetch_message(original_message.reference.message_id)
    await reportmessage.clear_reaction(emoji)

async def add_emojis_to_messages(interaction, emoji='⚠️'):
    original_message = await interaction.channel.fetch_message(interaction.message.id)
    await original_message.add_reaction(emoji)
    reportmessage = await interaction.channel.fetch_message(original_message.reference.message_id)
    await reportmessage.add_reaction(emoji)

async def get_playername(player_id, api_client):
    player_name = await api_client.get_player_by_steam_id(player_id)
    return player_name if player_name else player_id

async def get_logs(api_client, player_name):
    logs = await api_client.get_structured_logs(60, None, player_name)
    if logs and len(logs['result']['logs']) > 0:
        log_message = ""
        for log in logs['result']['logs']:
            timestamp = datetime.fromtimestamp(log['timestamp_ms'] / 1000)
            timestr = timestamp.strftime("%d.%m.%Y %H:%M:%S")
            log_messages = f"{timestr}: {log['action']} by {log['player_name_1']} - {log['message']}"
            log_message += log_messages + "\n"
        if log_message:
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as temp_log_file:
                temp_log_file.write(log_message)
                filename = temp_log_file.name
            return filename
    else:
       return False

async def get_playerid_from_name(name, api_client):
    players_data = await api_client.get_players()
    if players_data and 'result' in players_data:
        players_list = players_data['result']
        author_player = next((p for p in players_list if p['name'].lower() == name.lower()), None)
        if author_player:
            return author_player['player_id']
