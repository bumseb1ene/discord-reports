import os
import re
import discord
from discord.ext import commands
from discord.ui import View

from dotenv import load_dotenv
from api_client import APIClient
from Levenshtein import distance as levenshtein_distance, jaro_winkler
from helpers import (
    remove_markdown,
    remove_bracketed_content,
    remove_player_names,
    find_player_names,
    get_translation,
    get_author_name,
    set_author_name,
    load_excluded_words,
    remove_clantags,
    add_modlog,
    add_emojis_to_messages,
    only_remove_buttons,
    get_playerid_from_name,
    load_autorespond_tigger
)
import logging
from messages import unitreportembed, playerreportembed, player_not_found_embed, Reportview

# AI functions
from ai_functions import (
    analyze_text,
    generate_positive_response_text,
    generate_warning_text,
    generate_tempban_text,
    generate_permaban_text,
    generate_kick_text
)

logging.basicConfig(
    filename='bot_log.txt',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_TOKEN = os.getenv('RCON_API_TOKEN')
ALLOWED_CHANNEL_ID = int(os.getenv('ALLOWED_CHANNEL_ID', '0'))
MAX_SERVERS = int(os.getenv('MAX_SERVERS', '1'))

# Wichtig: Für Deutsch stell hier "de" ein
user_lang = os.getenv('USER_LANG', 'en')  # Embed-/Systemsprache

DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("true", "1")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

# Neue Hilfsfunktion zur fuzzy Suche
def fuzzy_match(word: str, candidates: list[str], max_distance: int = 2) -> str | None:
    """
    Sucht in `candidates` nach dem ersten Eintrag, dessen Levenshtein-Distanz
    zu `word` <= max_distance ist. Gibt den passenden String zurück oder None,
    falls kein Match gefunden wurde.
    """
    word_lower = word.lower()
    for candidate in candidates:
        dist = levenshtein_distance(word_lower, candidate.lower())
        if dist <= max_distance:
            return candidate
    return None

class MyBot(commands.Bot):
    def __init__(self, intents):
        super().__init__(command_prefix="!", intents=intents)
        self.api_client = APIClient(None, API_TOKEN)
        self.api_base_url = None
        self.excluded_words = load_excluded_words('exclude_words.json')
        self.autorespond_trigger = load_autorespond_tigger('autorespond_trigger.json')
        self.user_lang = user_lang
        from openai import AsyncOpenAI
        self.ai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.dry_run = DRY_RUN
        self.warning_counts = {}
        logging.info("MyBot instance created. DRY_RUN=%s, user_lang=%s", self.dry_run, self.user_lang)

    def extract_server_name(self, embed):
        if embed.footer:
            server_name = embed.footer.text.strip()
            logging.info("extract_server_name: Found server name in footer: '%s'", server_name)
            return server_name
        logging.info("extract_server_name: No footer found in embed. Returning None.")
        return None

    def get_api_base_url_from_server_name(self, extracted_server_name):
        """
        Durchsucht die SERVER_NAME_ Umgebungsvariablen, um die passende API_BASE_URL zu finden.
        """
        if not extracted_server_name:
            logging.info("get_api_base_url_from_server_name: No server name provided.")
            return None

        logging.info("get_api_base_url_from_server_name: Searching for server '%s'", extracted_server_name)
        for i in range(1, MAX_SERVERS + 1):
            server_name_env_var = f"SERVER_NAME_{i}"
            if os.getenv(server_name_env_var) == extracted_server_name:
                base_url = os.getenv(f"API_BASE_URL_{i}")
                logging.info("get_api_base_url_from_server_name: Match found. Using base URL '%s'.", base_url)
                return base_url
        logging.info("get_api_base_url_from_server_name: No match found for '%s'.", extracted_server_name)
        return None

    async def on_ready(self):
        logging.info("Bot successfully logged in as: %s (id: %s)", self.user, self.user.id)
        print(f'{self.user} has logged in.')

    async def on_message(self, message):
        """
        Verarbeitet eingehende Nachrichten im erlaubten Kanal. Erkennt Meldungen und führt je nach Klassifizierung
        entsprechende Aktionen (Warnung, Kick, Ban, usw.) aus.
        """
        logging.info("on_message: Received message from '%s' in channel %s: %s",
                     message.author, message.channel.id, message.content)

        # Sicherstellen, dass der Author-Name in helpers.py gesetzt ist
        if not get_author_name():
            set_author_name(message.author.display_name)
            logging.info("on_message: Set author name to '%s'", message.author.display_name)

        # Prüfen, ob es vom Bot selbst kommt oder ob es im falschen Kanal ist
        if message.author == self.user:
            logging.info("on_message: Ignoring own message.")
            return
        if message.channel.id != ALLOWED_CHANNEL_ID:
            logging.info("on_message: Ignoring message from disallowed channel %s.", message.channel.id)
            return

        server_name = None
        api_base_url = None
        clean_description = None

        # --- Handling von Embeds ---
        if message.embeds:
            logging.info("on_message: Message contains an embed.")
            embed = message.embeds[0]

            # Server Name & API Base URL
            if embed.footer:
                server_name = self.extract_server_name(embed)
                if server_name:
                    api_base_url = self.get_api_base_url_from_server_name(server_name)
                    if api_base_url:
                        self.api_client.base_url = api_base_url
                        logging.info("on_message: API-Client base_url set to: %s", api_base_url)
                        print(get_translation(self.user_lang, "api_login_successful").format(api_base_url))
                    else:
                        logging.info("on_message: No matching API base URL found for server_name: %s", server_name)
                        print(get_translation(self.user_lang, "no_api_base_url_found"))
                else:
                    logging.info("on_message: Could not extract server name from embed footer.")
                    print(get_translation(self.user_lang, "no_server_name_found"))
            else:
                logging.info("on_message: Embed has no footer => cannot extract server name.")

            if embed.description:
                clean_description = remove_markdown(embed.description)
                logging.info("on_message: Cleaned embed description: '%s'", clean_description)

            if embed.author and embed.author.name:
                updated_regex_pattern = r"(.+?)\s+\[(Axis|Allies)\](?:\[\w+\])?"
                match = re.match(updated_regex_pattern, embed.author.name)
                if match:
                    set_author_name(match.group(1).strip())
                    team = match.group(2).strip()
                    logging.info("on_message: Extracted author name: '%s', Team: '%s'", get_author_name(), team)
                else:
                    logging.error("Could not extract author name and team from embed author: '%s'. Falling back to message.author.display_name", embed.author.name)
                    set_author_name(message.author.display_name)
            else:
                logging.info("on_message: No embed.author => falling back to message.author.display_name = '%s'", message.author.display_name)
                set_author_name(message.author.display_name)
        else:
            logging.info("on_message: No embeds found in the message.")

        if not clean_description:
            logging.info("on_message: No description to process => returning.")
            return

        # --- Admin-Befehl-Check (vor Unit-Report) ---
        if clean_description.strip().lower().startswith("admin") or clean_description.strip().lower().startswith("!admin"):
            logging.info("on_message: Admin-Befehl erkannt => Bearbeite Admin-Inhalt.")
            if clean_description.strip().lower().startswith("admin"):
                admin_content = clean_description.strip()[len("admin"):].strip()
            else:
                admin_content = clean_description.strip()[len("!admin"):].strip()
            
            # Zuerst den Inhalt analysieren, um zu prüfen, ob er als legit klassifiziert wird:
            admin_analysis = await analyze_text(self.ai_client, admin_content, self.user_lang)
            logging.info("on_message: Admin-Analyse-Ergebnis: Kategorie=%s", admin_analysis["category"])
            if admin_analysis["category"] != "legit":
                logging.info("on_message: Admin-Inhalt wird als '%s' klassifiziert – Admin-Workflow überspringen.", admin_analysis["category"])
            else:
                players_fast = await self.api_client.get_players()
                valid_player_names = []
                if players_fast and 'result' in players_fast:
                    valid_player_names = [p['name'].lower() for p in players_fast['result']]
    
                found_candidate = None
                admin_words = admin_content.lower().split()
                # Zuerst Fuzzy-Matching gegen gültige Spielernamen:
                for valid_name in valid_player_names:
                    for word in admin_words:
                        if fuzzy_match(word, [valid_name], max_distance=2):
                            found_candidate = valid_name
                            logging.info("on_message: Fuzzy match found for admin content: '%s'", found_candidate)
                            break
                    if found_candidate:
                        break
    
                # Wenn ein Kandidat gefunden wurde, versuchen wir den Spieler-Workflow.
                if found_candidate:
                    logging.info("on_message: Admin report detected => calling find_and_respond_player with '%s'.", found_candidate)
                    response_sent = await self.find_and_respond_player(message, found_candidate)
                    if response_sent:
                        return
                else:
                    # Falls kein Spieler gefunden wurde, versuchen wir den Squad-Workflow.
                    trigger_words = [
                        "able", "baker", "charlie", "commander", "dog", "easy", "fox",
                        "george", "how", "item", "jig", "king", "love", "mike", "negat", "option",
                        "prep", "queen", "roger", "sugar", "tare", "uncle", "victor", "william",
                        "x-ray", "yoke", "zebra"
                    ]
                    potential_unit = None
                    for word in admin_words:
                        unit_match = fuzzy_match(word, trigger_words, max_distance=2)
                        if unit_match:
                            potential_unit = unit_match
                            logging.info("on_message: Detected potential unit in admin content: '%s'", potential_unit)
                            break
                    if potential_unit and 'team' in locals() and team:
                        response_sent = await self.find_and_respond_unit(team, potential_unit, ["officer", "spotter", "tankcommander", "armycommander"], message)
                        if response_sent:
                            return
                    # Falls weder Spieler noch Squad zugeordnet werden konnten, wird der Fallback in on_message ausgeführt.
                    logging.info("on_message: Kein direkter Treffer gefunden im Admin-Workflow. Führe Fallback aus.")
                    fallback_identifier = admin_content
                    response_sent = await self.fallback_response(message, fallback_identifier)
                    if response_sent:
                        return

        # --- Normaler Workflow: Spieler-Daten holen und Text zum Klassifizieren vorbereiten ---
        logging.info("on_message: Attempting to retrieve current players from API.")
        players_fast = await self.api_client.get_players()
        if players_fast and 'result' in players_fast:
            valid_player_names = [player['name'] for player in players_fast['result']]
            logging.info("on_message: Retrieved %d player names.", len(valid_player_names))
        else:
            valid_player_names = []
            logging.error("on_message: Failed to retrieve valid player names.")

        # Entfernen echter Spieler-Namen vor KI-Klassifizierung
        text_to_classify = remove_player_names(clean_description, valid_player_names)
        logging.info("on_message: text_to_classify (with names removed): '%s'", text_to_classify)

        # --- KI-Analyse (Sprache, Kategorie, Schweregrad) ---
        analysis = await analyze_text(self.ai_client, text_to_classify, self.user_lang)
        detected_lang = analysis["lang"] or "en"
        category = analysis["category"] or "unknown"
        justification_playerlang = analysis["reason"] or ""
        severity = analysis["severity"]

        logging.info("on_message: AI analyze result => lang=%s, category=%s, severity=%s, reason=%s",
                     detected_lang, category, severity, justification_playerlang)

        # Keine Übersetzung: Texte werden direkt in der eingestellten Sprache (user_lang) verwendet.
        text_for_embed = text_to_classify
        justification_embedlang = justification_playerlang

        # Workflow für "perma", "insult" oder "temp_ban":
        if category == "perma":
            logging.info("on_message: Category is 'perma' -> Attempting permanent ban workflow.")
            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            if author_player_id:
                permaban_text = await generate_permaban_text(self.ai_client, author_name, justification_playerlang, self.user_lang)
                if not self.dry_run:
                    ban_success = await self.api_client.do_perma_ban(author_name, author_player_id, permaban_text)
                    blacklist_success = await self.api_client.add_blacklist_record(author_player_id, justification_playerlang)
                else:
                    logging.info("on_message: DRY_RUN active => skipping real ban/blacklist calls.")
                    ban_success = True
                    blacklist_success = True

                embed_response = discord.Embed(color=discord.Color.red())
                embed_response.title = get_translation(self.user_lang, "permanent_ban")
                embed_response.description = permaban_text
                embed_response = self.add_justification_field(embed_response, justification_embedlang)
                # Beide Felder hinzufügen: Reporter und Steam-ID
                embed_response.add_field(name=get_translation(self.user_lang, "reporter"), value=author_name, inline=False)
                embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                await message.reply(embed=embed_response)
            else:
                logging.error("on_message: No matching player found for permanent ban => aborting.")
            return

        elif category == "insult" or category == "temp_ban":
            logging.info("on_message: Category is '%s' => Checking severity: %s", category, severity)
            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            if not author_player_id:
                logging.error("on_message: No matching player found => skipping insult/kick/ban.")
                return

            if severity == "warning":
                if author_player_id in self.warning_counts and self.warning_counts[author_player_id] >= 1:
                    kick_text = await generate_kick_text(self.ai_client, author_name, justification_playerlang, self.user_lang)
                    if not self.dry_run:
                        kick_success = await self.api_client.do_kick(author_name, author_player_id, kick_text)
                    else:
                        kick_success = True

                    embed_response = discord.Embed(color=discord.Color.blue())
                    embed_response.title = get_translation(self.user_lang, "kick")
                    embed_response.description = kick_text
                    embed_response = self.add_justification_field(embed_response, justification_embedlang)
                    embed_response.add_field(name=get_translation(self.user_lang, "reporter"), value=author_name, inline=False)
                    embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                    if self.dry_run:
                        embed_response.set_footer(text="DRY RUN: Test mode")
                    await message.reply(embed=embed_response)
                    self.warning_counts[author_player_id] = 0
                else:
                    warning_text = await generate_warning_text(self.ai_client, author_name, justification_playerlang, self.user_lang)
                    embed_response = discord.Embed(color=discord.Color.orange())
                    embed_response.title = get_translation(self.user_lang, "warning")
                    embed_response.description = warning_text
                    embed_response = self.add_justification_field(embed_response, justification_embedlang)
                    embed_response.add_field(name=get_translation(self.user_lang, "reporter"), value=author_name, inline=False)
                    embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                    if self.dry_run:
                        embed_response.set_footer(text="DRY RUN: Test mode")
                    else:
                        await self.api_client.do_message_player(author_name, author_player_id, warning_text)
                    self.warning_counts.setdefault(author_player_id, 0)
                    self.warning_counts[author_player_id] += 1
                    await message.reply(embed=embed_response)

            elif severity == "temp_ban":
                ban_text = await generate_tempban_text(self.ai_client, author_name, justification_playerlang, self.user_lang)
                if not self.dry_run:
                    ban_success = await self.api_client.do_temp_ban(author_name, author_player_id, 24, ban_text)
                else:
                    ban_success = True

                embed_response = discord.Embed(color=discord.Color.gold())
                embed_response.title = get_translation(self.user_lang, "24_hour_ban")
                embed_response.description = ban_text
                embed_response = self.add_justification_field(embed_response, justification_embedlang)
                embed_response.add_field(name=get_translation(self.user_lang, "reporter"), value=author_name, inline=False)
                embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                if self.dry_run:
                    embed_response.set_footer(text="DRY RUN: Test mode")
                await message.reply(embed=embed_response)

            elif severity == "perma":
                perma_text = await generate_permaban_text(self.ai_client, author_name, justification_playerlang, self.user_lang)
                if not self.dry_run:
                    ban_success = await self.api_client.do_perma_ban(author_name, author_player_id, perma_text)
                    blacklist_success = await self.api_client.add_blacklist_record(author_player_id, justification_playerlang)
                else:
                    ban_success, blacklist_success = True, True

                embed_response = discord.Embed(color=discord.Color.red())
                embed_response.title = get_translation(self.user_lang, "permanent_ban")
                embed_response.description = perma_text
                embed_response = self.add_justification_field(embed_response, justification_embedlang)
                embed_response.add_field(name=get_translation(self.user_lang, "reporter"), value=author_name, inline=False)
                embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                if not (ban_success and blacklist_success):
                    embed_response.add_field(
                        name=get_translation(self.user_lang, "error"),
                        value="Permanent ban could not be executed.",
                        inline=False
                    )
                if self.dry_run:
                    embed_response.set_footer(text="DRY RUN: Test mode")
                await message.reply(embed=embed_response)
            return

        # Falls die Kategorie "legit" ist, führen wir den normalen (positiven) Workflow aus.
        if category == "legit":
            logging.info("on_message: Category='legit' => Positive / Neutral Meldung.")
            # Optional: Versuch, ob find_and_respond_player einen Treffer erzielt.
            author_name = get_author_name() or message.author.display_name
            response_sent = await self.find_and_respond_player(message, text_to_classify)
            if response_sent:
                return

            # Fallback, falls keine Zuordnung erfolgte:
            pos_text = await generate_positive_response_text(self.ai_client, author_name, justification_playerlang, self.user_lang)
            embed_response = discord.Embed(color=discord.Color.green())
            embed_response.title = get_translation(self.user_lang, "positive_response_title")
            embed_response.description = pos_text
            # Beide Felder hinzufügen: Reporter und Steam-ID (falls vorhanden)
            embed_response.add_field(name=get_translation(self.user_lang, "reporter"), value=author_name, inline=False)
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            steam_id_value = str(author_player_id) if author_player_id else "N/A"
            embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=steam_id_value, inline=False)
            await message.reply(embed=embed_response)
            if author_player_id and not self.dry_run:
                await self.api_client.do_message_player(author_name, author_player_id, pos_text)
            return

        logging.info("on_message: Classification unknown => No specific action performed.")

    # Helper: fügt ein Justification-Feld zum Embed hinzu
    def add_justification_field(self, embed_obj, text_justification):
        embed_obj.add_field(
            name=get_translation(self.user_lang, "justification"),
            value=text_justification,
            inline=False
        )
        return embed_obj

    # Fallback-Antwort, wenn weder Spieler noch Squad zugeordnet werden konnten
    async def fallback_response(self, message, identifier) -> bool:
        author_name = get_author_name() or message.author.display_name
        pos_text = await generate_positive_response_text(self.ai_client, author_name, identifier, self.user_lang)
        embed = discord.Embed(
            title=get_translation(self.user_lang, "positive_response_title"),
            description=pos_text,
            color=discord.Color.green()
        )
        embed.add_field(name=get_translation(self.user_lang, "reporter"), value=author_name, inline=False)
        author_player_id = await get_playerid_from_name(author_name, self.api_client)
        steam_id_value = str(author_player_id) if author_player_id else "N/A"
        embed.add_field(name=get_translation(self.user_lang, "steam_id"), value=steam_id_value, inline=False)
        await message.reply(embed=embed)
        if author_player_id and not self.dry_run:
            await self.api_client.do_message_player(author_name, author_player_id, pos_text)
        return True

    # Funktion zur Spielerzuordnung – gibt True zurück, falls bereits eine Antwort gesendet wurde
    async def find_and_respond_player(self, message, reported_identifier, max_levenshtein_distance=2) -> bool:
        logging.info("find_and_respond_player: Called with reported_identifier='%s'.", reported_identifier)
        reported_identifier_cleaned = remove_bracketed_content(reported_identifier)
        potential_names = find_player_names(reported_identifier_cleaned, self.excluded_words)
        logging.info("find_and_respond_player: Potential names after cleaning: %s", potential_names)

        players_fast = await self.api_client.get_players()
        if not players_fast or 'result' not in players_fast:
            logging.error("find_and_respond_player: Failed to retrieve players list.")
            return False

        best_match = None
        best_player_data = None
        best_score = float('inf')

        for player in players_fast['result']:
            cleaned_player_name = remove_clantags(player['name'].lower())
            player_name_words = cleaned_player_name.split()

            for reported_word in potential_names:
                for player_word in player_name_words:
                    dist = levenshtein_distance(reported_word.lower(), player_word.lower())
                    if dist <= max_levenshtein_distance and dist < best_score:
                        best_score = dist
                        best_match = player['name']
                        best_player_data = player
                        logging.info("find_and_respond_player: New best match '%s' (dist=%d)", best_match, best_score)

        if best_match:
            logging.info("find_and_respond_player: Best match = '%s' => retrieving live game stats.", best_match)
            live_game_stats = await self.api_client.get_player_data(best_player_data['player_id'])
            if live_game_stats and 'result' in live_game_stats and 'stats' in live_game_stats['result']:
                player_stats = next(
                    (item for item in live_game_stats['result']['stats'] if item['player_id'] == best_player_data['player_id']),
                    None
                )
                if player_stats:
                    logging.info("find_and_respond_player: Found player_stats for '%s'.", best_match)
                    player_additional_data = await self.api_client.get_player_by_id(best_player_data['player_id'])
                    total_playtime_seconds = player_additional_data.get('total_playtime_seconds', 0)
                    total_playtime_hours = total_playtime_seconds / 3600

                    embed = await playerreportembed(
                        self.user_lang,
                        best_match,
                        player_stats,
                        total_playtime_hours,
                        best_player_data
                    )
                    response_message = await message.reply(embed=embed)
                    self.last_response_message_id = response_message.id

                    view = Reportview(self.api_client)
                    await view.add_buttons(
                        self.user_lang,
                        best_match,
                        best_player_data['player_id']
                    )
                    await response_message.edit(view=view)
                    logging.info("find_and_respond_player: Sent player report embed for '%s' (ID=%s).", best_match, best_player_data['player_id'])
                    return True
        return False

    # Funktion zur Squad-Zuordnung – gibt True zurück, falls bereits eine Antwort gesendet wurde
    async def find_and_respond_unit(self, team, unit_name, roles, message) -> bool:
        logging.info("find_and_respond_unit: Called with team=%s, unit_name=%s, roles=%s", team, unit_name, roles)
        player_data = await self.api_client.get_detailed_players()
        if player_data is None or 'result' not in player_data or 'players' not in player_data['result']:
            logging.error("find_and_respond_unit: Failed to retrieve detailed player data.")
            return False

        trigger_words = [
            "able", "baker", "charlie", "dog", "easy", "fox",
            "george", "how", "item", "jig", "king", "love", "mike", "negat", "option",
            "prep", "queen", "roger", "sugar", "tare", "uncle", "victor", "william", "x-ray",
            "yoke", "zebra"
        ]

        if fuzzy_match(unit_name, ["commander"], max_distance=2) is not None:
            unit_name = "command"
        else:
            match = fuzzy_match(unit_name, trigger_words, max_distance=2)
            if match:
                unit_name = match

        logging.info("find_and_respond_unit: Using fuzzy-matched unit_name='%s'", unit_name)

        matching_player = None
        for player_id, player_info in player_data['result']['players'].items():
            player_unit_name = player_info.get('unit_name', "") or ""
            if (player_info['team'] and player_info['team'].lower() == team.lower() and
                player_unit_name.lower() == unit_name.lower() and
                player_info['role'].lower() in [r.lower() for r in roles]):
                matching_player = {
                    "name": player_info['name'],
                    "level": player_info['level'],
                    "kills": player_info['kills'],
                    "deaths": player_info['deaths'],
                    "player_id": player_info['player_id'],
                }
                logging.info("find_and_respond_unit: Found matching player: %s", matching_player)
                break

        if matching_player:
            player_additional_data = await self.api_client.get_player_by_id(matching_player['player_id'])
            embed = await unitreportembed(
                player_additional_data,
                self.user_lang,
                unit_name,
                roles,
                team,
                matching_player
            )
            view = Reportview(self.api_client)
            await view.add_buttons(
                self.user_lang,
                matching_player['name'],
                player_additional_data['player_id']
            )
            response_message = await message.reply(embed=embed, view=view)
            logging.info("find_and_respond_unit: Successfully sent unit report embed for player '%s'.", matching_player['name'])
            return True
        return False

    async def on_close(self):
        logging.info("Bot is shutting down -> closing API client session.")
        if self.api_client.session:
            await self.api_client.close_session()

bot = MyBot(intents)
bot.run(TOKEN)
