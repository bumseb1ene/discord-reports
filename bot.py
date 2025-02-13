import os
import re
import discord
from discord.ext import commands
from discord.ui import View

from dotenv import load_dotenv
from api_client import APIClient
from Levenshtein import distance as levenshtein_distance
from Levenshtein import jaro_winkler
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

# Importiere die KI-Funktionen aus der Datei ai_functions.py
from ai_functions import (
    generate_warning_text,
    generate_tempban_text,
    generate_permaban_text,
    generate_kick_text,
    classify_report_text,
    classify_insult_severity,
    generate_positive_response_text
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
user_lang = os.getenv('USER_LANG', 'en')
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("true", "1")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

class MyBot(commands.Bot):
    def __init__(self, intents):
        super().__init__(command_prefix="!", intents=intents)
        self.api_client = APIClient(None, API_TOKEN)
        self.api_base_url = None
        self.excluded_words = load_excluded_words('exclude_words.json')
        self.autorespond_trigger = load_autorespond_tigger('autorespond_trigger.json')
        self.user_lang = os.getenv('USER_LANG', 'en')
        from openai import AsyncOpenAI
        self.ai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.dry_run = DRY_RUN
        # Dictionary to track warnings for Kick-Logik
        self.warning_counts = {}

    def extract_server_name(self, embed):
        if embed.footer:
            return embed.footer.text.strip()
        return None

    def get_api_base_url_from_server_name(self, extracted_server_name):
        for i in range(1, MAX_SERVERS + 1):
            server_name_env_var = f"SERVER_NAME_{i}"
            if os.getenv(server_name_env_var) == extracted_server_name:
                return os.getenv(f"API_BASE_URL_{i}")
        return None

    async def on_ready(self):
        print(f'{self.user} has logged in.')

    async def on_message(self, message):
        if not get_author_name():
            set_author_name(message.author.display_name)
        if message.author == self.user or message.channel.id != ALLOWED_CHANNEL_ID:
            return

        server_name = None
        api_base_url = None
        clean_description = None

        if message.embeds:
            embed = message.embeds[0]
            if embed.footer:
                server_name = self.extract_server_name(embed)
                if server_name:
                    api_base_url = self.get_api_base_url_from_server_name(server_name)
                    if api_base_url:
                        self.api_client.base_url = api_base_url
                        print(get_translation(user_lang, "api_login_successful").format(api_base_url))
                    else:
                        print(get_translation(user_lang, "no_api_base_url_found"))
                else:
                    print(get_translation(user_lang, "no_server_name_found"))
            if embed.description:
                clean_description = remove_markdown(embed.description)
            if embed.author and embed.author.name:
                updated_regex_pattern = r"(.+?)\s+\[(Axis|Allies)\](?:\[\w+\])?"
                match = re.match(updated_regex_pattern, embed.author.name)
                if match:
                    set_author_name(match.group(1).strip())
                    team = match.group(2).strip()
                    logging.info(f"Embed Author Name: {get_author_name()}")
                    logging.info(f"Detected team: {team}")
                else:
                    logging.error("Could not extract author name and team from the embed author. Falling back to message.author.display_name")
                    set_author_name(message.author.display_name)
            else:
                set_author_name(message.author.display_name)

        if not clean_description:
            return

        # Hole alle validierten Spielernamen über die API
        players_fast = await self.api_client.get_players()
        if players_fast and 'result' in players_fast:
            valid_player_names = [player['name'] for player in players_fast['result']]
        else:
            valid_player_names = []

        # Entferne alle Spielernamen aus dem Text, bevor er an die KI übergeben wird
        text_to_classify = remove_player_names(clean_description, valid_player_names)

        # --- Triggerwörter für Squad-Reports einfügen ---
        trigger_words = [
            "able", "baker", "charlie", "commander", "kommandant", "dog", "easy", "fox",
            "george", "how", "item", "jig", "king", "love", "mike", "negat", "option",
            "prep", "queen", "roger", "sugar", "tare", "uncle", "victor", "william",
            "x-ray", "yoke", "zebra"
        ]
        reported_parts = clean_description.split()
        if reported_parts and any(word in reported_parts for word in trigger_words):
            logging.info("Identified as unit report.")
            trigger_word_index = next(i for i, part in enumerate(reported_parts) if part in trigger_words)
            unit_name = reported_parts[trigger_word_index]
            if "commander" in reported_parts or "kommandant" in reported_parts:
                unit_name = "command"
            roles = ["officer", "spotter", "tankcommander", "armycommander"]
            logging.info(f"Unit name: {unit_name}, Roles: {roles}")
            if 'team' in locals() and team:
                await self.find_and_respond_unit(team, unit_name, roles, message)
            else:
                logging.error("Team not identified for unit report.")
            return
        # --- Ende Triggerwörter-Block ---

        # KI-basierte Klassifikation: Text klassifizieren und Begründung erhalten
        kategorie, begruendung = await classify_report_text(self.ai_client, text_to_classify, self.user_lang)
        logging.info(f"[KI-Klassifizierung]: {kategorie} - {begruendung}")

        # Fall "perma": Spieler permanent bannen
        if kategorie == "perma":
            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            if author_player_id:
                warning_text = await generate_warning_text(self.ai_client, author_name, begruendung, self.user_lang)
                ban_success = await self.api_client.do_perma_ban(author_name, author_player_id, warning_text)
                blacklist_success = await self.api_client.add_blacklist_record(author_player_id, begruendung)
                if ban_success and blacklist_success:
                    log_entry = f"Automatischer Perma-Bann durch KI: {begruendung}"
                    embed = discord.Embed(
                        title=get_translation(self.user_lang, "automatic_perma_ban_title") or "Automatischer Perma-Bann",
                        description=warning_text,
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Reporter (Melder)", value=author_name, inline=False)
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    embed.add_field(name=get_translation(self.user_lang, "logbook"), value=log_entry, inline=False)
                    await message.reply(embed=embed)
                else:
                    logging.error("Perma-Bann oder Blacklist-Eintrag konnte nicht ausgeführt werden.")
            else:
                logging.error("Kein passender Spieler für den Perma-Bann gefunden.")
            return

        # Fall "beleidigung": Schweregrad ermitteln und entsprechende Maßnahmen ergreifen
        if kategorie == "beleidigung":
            severity, severity_reason = await classify_insult_severity(self.ai_client, text_to_classify, self.user_lang)
            logging.info(f"Insult severity: {severity} - {severity_reason}")
            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            if severity == "warning":
                if author_player_id in self.warning_counts and self.warning_counts[author_player_id] >= 1:
                    kick_text = await generate_kick_text(self.ai_client, author_name, severity_reason, self.user_lang)
                    if not self.dry_run:
                        kick_success = await self.api_client.do_kick(author_name, author_player_id, kick_text)
                    else:
                        kick_success = True
                    if self.dry_run:
                        embed = discord.Embed(
                            title="DRY RUN: Kick",
                            description=f"DRY RUN: Kick für {author_name} – {severity_reason}",
                            color=discord.Color.blue()
                        )
                    else:
                        if kick_success:
                            embed = discord.Embed(
                                title="Kick",
                                description=kick_text,
                                color=discord.Color.blue()
                            )
                        else:
                            embed = discord.Embed(
                                title="Fehler",
                                description="Kick konnte nicht ausgeführt werden.",
                                color=discord.Color.blue()
                            )
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    embed.add_field(name="Begründung", value=severity_reason, inline=False)
                    if self.dry_run:
                        embed.set_footer(text="DRY RUN: Testmodus")
                    await message.reply(embed=embed)
                    self.warning_counts[author_player_id] = 0
                else:
                    warning_text = await generate_warning_text(self.ai_client, author_name, severity_reason, self.user_lang)
                    if author_player_id not in self.warning_counts:
                        self.warning_counts[author_player_id] = 0
                    self.warning_counts[author_player_id] += 1
                    embed = discord.Embed(
                        title="Verwarnung",
                        description=warning_text,
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    embed.add_field(name="Begründung", value=severity_reason, inline=False)
                    if self.dry_run:
                        embed.set_footer(text="DRY RUN: Testmodus")
                    else:
                        await self.api_client.do_message_player(author_name, author_player_id, warning_text)
                    await message.reply(embed=embed)
            elif severity == "temp_ban":
                warning_text = await generate_warning_text(self.ai_client, author_name, severity_reason, self.user_lang)
                if not self.dry_run:
                    ban_success = await self.api_client.do_temp_ban(author_name, author_player_id, 24, warning_text)
                if self.dry_run:
                    embed = discord.Embed(
                        title="DRY RUN: 24-Stunden-Bann",
                        description=f"DRY RUN: Temp-Bann (24h) für {author_name} – {warning_text}",
                        color=discord.Color.gold()
                    )
                else:
                    if ban_success:
                        embed = discord.Embed(
                            title="24-Stunden-Bann",
                            description=warning_text,
                            color=discord.Color.gold()
                        )
                    else:
                        embed = discord.Embed(
                            title="Fehler",
                            description="Temp-Bann konnte nicht ausgeführt werden.",
                            color=discord.Color.gold()
                        )
                embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                embed.add_field(name="Begründung", value=severity_reason, inline=False)
                if self.dry_run:
                    embed.set_footer(text="DRY RUN: Testmodus")
                await message.reply(embed=embed)
            elif severity == "perma":
                warning_text = await generate_warning_text(self.ai_client, author_name, severity_reason, self.user_lang)
                if not self.dry_run:
                    ban_success = await self.api_client.do_perma_ban(author_name, author_player_id, severity_reason)
                    blacklist_success = await self.api_client.add_blacklist_record(author_player_id, severity_reason)
                if self.dry_run:
                    embed = discord.Embed(
                        title="DRY RUN: Permanenter Bann",
                        description=f"DRY RUN: Perma-Bann für {author_name} – {warning_text}",
                        color=discord.Color.red()
                    )
                else:
                    if ban_success and blacklist_success:
                        embed = discord.Embed(
                            title="Permanenter Bann",
                            description=warning_text,
                            color=discord.Color.red()
                        )
                    else:
                        embed = discord.Embed(
                            title="Fehler",
                            description="Perma-Bann konnte nicht ausgeführt werden.",
                            color=discord.Color.red()
                        )
                embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                embed.add_field(name="Begründung", value=severity_reason, inline=False)
                if self.dry_run:
                    embed.set_footer(text="DRY RUN: Testmodus")
                await message.reply(embed=embed)
            return

        # Admin-Befehl prüfen – Nachricht beginnt mit "!admin"
        if clean_description.strip().lower().startswith("!admin"):
            admin_content = clean_description.strip()[len("!admin"):].strip()
            # Hole die Liste gültiger Spielernamen (in Kleinbuchstaben)
            players_fast = await self.api_client.get_players()
            valid_player_names = []
            if players_fast and 'result' in players_fast:
                valid_player_names = [player['name'].lower() for player in players_fast['result']]
            # Suche im gesamten admin_content nach einem gültigen Spielernamen
            found_candidate = None
            for valid_name in valid_player_names:
                if valid_name in admin_content.lower():
                    found_candidate = valid_name
                    break
            if found_candidate:
                logging.info(f"Admin report detected. Reported identifier extracted: {found_candidate}")
                await self.find_and_respond_player(message, found_candidate)
                return
            else:
                # Kein gültiger Spielername: Positive Nachricht auslösen
                author_name = get_author_name() or message.author.display_name
                author_player_id = await get_playerid_from_name(author_name, self.api_client)
                if author_player_id:
                    positive_text = await generate_positive_response_text(self.ai_client, author_name, admin_content, self.user_lang)
                    embed = discord.Embed(
                        title=get_translation(self.user_lang, "positive_response_title"),
                        description=positive_text,
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    await message.reply(embed=embed)
                    await self.api_client.do_message_player(author_name, author_player_id, positive_text)
                else:
                    logging.error("Kein passender Spieler für den positiven Report gefunden.")
                return

        # Falls kein Admin-Befehl vorliegt und die Klassifikation "legitim" ist
        if kategorie == "legitim":
            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            if author_player_id:
                positive_text = await generate_positive_response_text(self.ai_client, author_name, begruendung, self.user_lang)
                embed = discord.Embed(
                    title=get_translation(self.user_lang, "positive_response_title"),
                    description=positive_text,
                    color=discord.Color.green()
                )
                embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                await message.reply(embed=embed)
                positive_dm = await generate_positive_response_text(self.ai_client, author_name, begruendung, self.user_lang)
                await self.api_client.do_message_player(author_name, author_player_id, positive_dm)
            else:
                logging.error("Kein passender Spieler für den positiven Report gefunden.")
            return

        logging.info("Classification unknown: no action taken.")

    async def show_punish_reporter(self, message: discord.Message, reason: str):
        fallback_name = message.author.display_name if message.author else None
        author_name = get_author_name() or fallback_name
        logging.info(f"show_punish_reporter: get_author_name() returned: {get_author_name()}, fallback: {fallback_name}")
        if not author_name:
            logging.error("Could not retrieve author_name; skipping punish_reporter.")
            return

        author_player_id = await get_playerid_from_name(author_name, self.api_client)
        if not author_player_id:
            logging.error(f"No matching player found for author: {author_name}.")
            return

        embed = discord.Embed(
            title=get_translation(self.user_lang, "reporter_insult_title"),
            description=get_translation(self.user_lang, "reporter_insult_description").format(reason=reason),
            color=discord.Color.red()
        )
        embed.add_field(name="Reporter (Melder)", value=author_name, inline=False)
        embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)

        view = Reportview(self.api_client)
        await view.add_buttons(
            user_lang=self.user_lang,
            reported_player_name=author_name,
            player_id=author_player_id,
            self_report=True,
            player_found=True
        )
        await message.reply(embed=embed, view=view)

    async def find_and_respond_unit(self, team, unit_name, roles, message):
        player_data = await self.api_client.get_detailed_players()
        if player_data is None or 'result' not in player_data or 'players' not in player_data['result']:
            logging.error("Failed to retrieve player data or player data is incomplete.")
            return

        if unit_name is None:
            unit_name = ""

        matching_player = []
        for player_id, player_info in player_data['result']['players'].items():
            player_unit_name = player_info.get('unit_name', "") or ""
            if (
                player_info['team'] and player_info['team'].lower() == team.lower()
                and player_unit_name.lower() == unit_name.lower()
                and player_info['role'].lower() in [role.lower() for role in roles]
            ):
                player_details = {
                    "name": player_info['name'],
                    "level": player_info['level'],
                    "kills": player_info['kills'],
                    "deaths": player_info['deaths'],
                    "player_id": player_info['player_id'],
                }
                matching_player = player_details
                break

        if matching_player:
            player_additional_data = await self.api_client.get_player_by_id(matching_player['player_id'])
            embed = await unitreportembed(
                player_additional_data,
                user_lang,
                unit_name,
                roles,
                team,
                matching_player
            )
            view = Reportview(self.api_client)
            await view.add_buttons(
                user_lang,
                matching_player['name'],
                player_additional_data['player_id']
            )
            response_message = await message.reply(embed=embed, view=view)
            self.last_response_message_id = response_message.id
        else:
            await self.player_not_found(message)

        logging.info(get_translation(user_lang, "response_sent").format(unit_name=unit_name, roles=', '.join(roles), team=team))

    async def find_and_respond_player(self, message, reported_identifier,
                                      max_levenshtein_distance=3,
                                      jaro_winkler_threshold=0.85):
        logging.info("find_and_respond_player function called")
        logging.info(f"Searching for player report: {reported_identifier}")
        reported_identifier_cleaned = remove_bracketed_content(reported_identifier)
        potential_names = find_player_names(reported_identifier_cleaned, self.excluded_words)
        players_fast = await self.api_client.get_players()
        if not players_fast or 'result' not in players_fast:
            logging.error("Failed to retrieve players list")
            return
        max_combined_score_threshold = float(os.getenv('MAX_COMBINED_SCORE_THRESHOLD', 0.8))
        best_match = None
        best_player_data = None
        best_score = float('inf')
        for player in players_fast['result']:
            cleaned_player_name = remove_clantags(player['name'].lower())
            player_name_words = cleaned_player_name.split()
            for reported_word in potential_names:
                for player_word in player_name_words:
                    levenshtein_score = levenshtein_distance(reported_word.lower(), player_word)
                    jaro_score = jaro_winkler(reported_word.lower(), player_word)
                    if levenshtein_score <= max_combined_score_threshold or jaro_score >= jaro_winkler_threshold:
                        combined_score = levenshtein_score + (1 - jaro_score)
                        logging.info(
                            f"Scores for '{reported_word}' vs '{cleaned_player_name}': Levenshtein = {levenshtein_score}, Jaro = {jaro_score}, Combined = {combined_score}"
                        )
                        if combined_score < best_score and combined_score <= max_combined_score_threshold:
                            best_score = combined_score
                            best_match = player['name']
                            best_player_data = player
                            logging.info(f"New best match found: {best_match} with score {best_score}")
        if best_match:
            live_game_stats = await self.api_client.get_player_data(best_player_data['player_id'])
            if not live_game_stats or 'result' not in live_game_stats or 'stats' not in live_game_stats['result']:
                logging.error("Failed to retrieve live game stats for the best matching player")
                return
            player_stats = next(
                (item for item in live_game_stats['result']['stats']
                 if item['player_id'] == best_player_data['player_id']),
                None
            )
            if player_stats:
                logging.info(get_translation(user_lang, "best_match_found").format(best_match))
                player_additional_data = await self.api_client.get_player_by_id(best_player_data['player_id'])
                total_playtime_seconds = player_additional_data.get('total_playtime_seconds', 0)
                total_playtime_hours = total_playtime_seconds / 3600
                embed = await playerreportembed(
                    user_lang,
                    best_match,
                    player_stats,
                    total_playtime_hours,
                    best_player_data
                )
                response_message = await message.reply(embed=embed)
                self.last_response_message_id = response_message.id
                view = Reportview(self.api_client)
                await view.add_buttons(
                    user_lang,
                    best_match,
                    best_player_data['player_id']
                )
                await response_message.edit(view=view)
            else:
                await self.player_not_found(message)
        else:
            await self.player_not_found(message)

    async def player_not_found(self, message):
        author_name = get_author_name() or message.author.display_name
        author_player_id = await get_playerid_from_name(author_name, self.api_client)
        not_found_text = get_translation(self.user_lang, "player_not_found_auto_msg")
        if author_player_id:
            await self.api_client.do_message_player(author_name, author_player_id, not_found_text)
        embed = await player_not_found_embed(author_player_id, author_name, self.user_lang)
        view = Reportview(self.api_client)
        await view.add_buttons(
            user_lang=self.user_lang,
            reported_player_name=author_name,
            player_id=author_player_id,
            self_report=False,
            player_found=False
        )
        await message.reply(embed=embed, view=view)

    async def on_close(self):
        if self.api_client.session:
            await self.api_client.close_session()

bot = MyBot(intents)
bot.run(TOKEN)
