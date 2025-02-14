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
    detect_language,
    translate_text,
    classify_report_text,
    classify_insult_severity,
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
user_lang = os.getenv('USER_LANG', 'en')  # Embed-/Systemsprache
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
        self.user_lang = user_lang
        from openai import AsyncOpenAI
        self.ai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.dry_run = DRY_RUN
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
                        print(get_translation(self.user_lang, "api_login_successful").format(api_base_url))
                    else:
                        print(get_translation(self.user_lang, "no_api_base_url_found"))
                else:
                    print(get_translation(self.user_lang, "no_server_name_found"))
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
                    logging.error("Could not extract author name and team from embed author. Falling back to message.author.display_name")
                    set_author_name(message.author.display_name)
            else:
                set_author_name(message.author.display_name)

        if not clean_description:
            return

        players_fast = await self.api_client.get_players()
        if players_fast and 'result' in players_fast:
            valid_player_names = [player['name'] for player in players_fast['result']]
        else:
            valid_player_names = []

        text_to_classify = remove_player_names(clean_description, valid_player_names)

        trigger_words = [
            "able", "baker", "charlie", "commander", "dog", "easy", "fox",
            "george", "how", "item", "jig", "king", "love", "mike", "negat", "option",
            "prep", "queen", "roger", "sugar", "tare", "uncle", "victor", "william",
            "x-ray", "yoke", "zebra"
        ]
        reported_parts = clean_description.split()
        if reported_parts and any(word in reported_parts for word in trigger_words):
            logging.info("Identified as unit report.")
            trigger_word_index = next(i for i, part in enumerate(reported_parts) if part in trigger_words)
            unit_name = reported_parts[trigger_word_index]
            if "commander" in reported_parts:
                unit_name = "command"
            roles = ["officer", "spotter", "tankcommander", "armycommander"]
            if 'team' in locals() and team:
                await self.find_and_respond_unit(team, unit_name, roles, message)
            else:
                logging.error("Team not identified for unit report.")
            return

        detected_lang = await detect_language(self.ai_client, text_to_classify)
        logging.info(f"[Language Detection] {detected_lang}")

        # Spielertext -> user_lang
        if detected_lang != self.user_lang:
            text_for_embed = await translate_text(self.ai_client, text_to_classify, detected_lang, self.user_lang)
        else:
            text_for_embed = text_to_classify

        # Grund-Embed
        # Wir lassen es standardmäßig "blurple", überschreiben aber später je nach Fall.
        embed_response = discord.Embed(color=discord.Color.blurple())
        embed_response.add_field(
            name=get_translation(self.user_lang, "player_text"),
            value=text_for_embed,
            inline=False
        )

        category, justification_playerlang = await classify_report_text(self.ai_client, text_to_classify, detected_lang)
        logging.info(f"[AI Classification]: {category} - {justification_playerlang}")
        justification_embedlang = await translate_text(self.ai_client, justification_playerlang, detected_lang, self.user_lang)

        def add_justification_field(embed_obj, text_justification):
            embed_obj.add_field(
                name=get_translation(self.user_lang, "justification"),
                value=text_justification,
                inline=False
            )
            return embed_obj

        if category == "perma":
            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            if author_player_id:
                permaban_playerlang = await generate_permaban_text(self.ai_client, author_name, justification_playerlang, detected_lang)
                permaban_embedlang = await translate_text(self.ai_client, permaban_playerlang, detected_lang, self.user_lang)

                if not self.dry_run:
                    ban_success = await self.api_client.do_perma_ban(author_name, author_player_id, permaban_playerlang)
                    blacklist_success = await self.api_client.add_blacklist_record(author_player_id, justification_playerlang)
                else:
                    ban_success = True
                    blacklist_success = True

                if ban_success and blacklist_success:
                    embed_response.title = get_translation(self.user_lang, "permanent_ban")
                    embed_response.description = permaban_embedlang
                    embed_response.color = discord.Color.red()  # Rot für Perma-Bann
                    add_justification_field(embed_response, justification_embedlang)
                    embed_response.add_field(
                        name=get_translation(self.user_lang, "reporter"),
                        value=author_name,
                        inline=False
                    )
                    embed_response.add_field(
                        name=get_translation(self.user_lang, "steam_id"),
                        value=str(author_player_id),
                        inline=False
                    )
                    await message.reply(embed=embed_response)
                else:
                    logging.error("Permanent ban or blacklist entry could not be executed.")
            else:
                logging.error("No matching player found for permanent ban.")
            return

        elif category == "insult" or category == "temp_ban":
            severity, severity_reason_playerlang = await classify_insult_severity(self.ai_client, text_to_classify, detected_lang)
            logging.info(f"Insult severity: {severity} - {severity_reason_playerlang}")
            severity_reason_embedlang = await translate_text(self.ai_client, severity_reason_playerlang, detected_lang, self.user_lang)

            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)

            if severity == "warning":
                if author_player_id in self.warning_counts and self.warning_counts[author_player_id] >= 1:
                    kick_playerlang = await generate_kick_text(self.ai_client, author_name, severity_reason_playerlang, detected_lang)
                    kick_embedlang = await translate_text(self.ai_client, kick_playerlang, detected_lang, self.user_lang)

                    if not self.dry_run:
                        kick_success = await self.api_client.do_kick(author_name, author_player_id, kick_playerlang)
                    else:
                        kick_success = True

                    embed_response.title = get_translation(self.user_lang, "kick")
                    embed_response.description = kick_embedlang
                    embed_response.color = discord.Color.blue()  # Blau für Kick
                    add_justification_field(embed_response, severity_reason_embedlang)
                    embed_response.add_field(
                        name=get_translation(self.user_lang, "steam_id"),
                        value=str(author_player_id),
                        inline=False
                    )
                    if self.dry_run:
                        embed_response.set_footer(text="DRY RUN: Test mode")
                    elif not kick_success:
                        embed_response.add_field(
                            name=get_translation(self.user_lang, "error"),
                            value="Kick could not be executed.",
                            inline=False
                        )
                    await message.reply(embed=embed_response)
                    self.warning_counts[author_player_id] = 0

                else:
                    # => Warning
                    warning_playerlang = await generate_warning_text(self.ai_client, author_name, severity_reason_playerlang, detected_lang)
                    warning_embedlang = await translate_text(self.ai_client, warning_playerlang, detected_lang, self.user_lang)

                    embed_response.title = get_translation(self.user_lang, "warning")
                    embed_response.description = warning_embedlang
                    embed_response.color = discord.Color.orange()  # Orange für Warning
                    add_justification_field(embed_response, severity_reason_embedlang)
                    embed_response.add_field(
                        name=get_translation(self.user_lang, "steam_id"),
                        value=str(author_player_id),
                        inline=False
                    )
                    if self.dry_run:
                        embed_response.set_footer(text="DRY RUN: Test mode")
                    else:
                        await self.api_client.do_message_player(author_name, author_player_id, warning_playerlang)

                    self.warning_counts.setdefault(author_player_id, 0)
                    self.warning_counts[author_player_id] += 1

                    await message.reply(embed=embed_response)

            elif severity == "temp_ban":
                bantext_playerlang = await generate_tempban_text(self.ai_client, author_name, severity_reason_playerlang, detected_lang)
                bantext_embedlang = await translate_text(self.ai_client, bantext_playerlang, detected_lang, self.user_lang)

                if not self.dry_run:
                    ban_success = await self.api_client.do_temp_ban(author_name, author_player_id, 24, bantext_playerlang)
                else:
                    ban_success = True

                embed_response.title = get_translation(self.user_lang, "24_hour_ban")
                embed_response.description = bantext_embedlang
                embed_response.color = discord.Color.gold()  # Gold für 24h-Bann
                add_justification_field(embed_response, severity_reason_embedlang)
                embed_response.add_field(
                    name=get_translation(self.user_lang, "steam_id"),
                    value=str(author_player_id),
                    inline=False
                )
                if not ban_success:
                    embed_response.add_field(
                        name=get_translation(self.user_lang, "error"),
                        value="Temp ban could not be executed.",
                        inline=False
                    )
                if self.dry_run:
                    embed_response.set_footer(text="DRY RUN: Test mode")
                await message.reply(embed=embed_response)

            elif severity == "perma":
                perma_playerlang = await generate_permaban_text(self.ai_client, author_name, severity_reason_playerlang, detected_lang)
                perma_embedlang = await translate_text(self.ai_client, perma_playerlang, detected_lang, self.user_lang)

                if not self.dry_run:
                    ban_success = await self.api_client.do_perma_ban(author_name, author_player_id, perma_playerlang)
                    blacklist_success = await self.api_client.add_blacklist_record(author_player_id, severity_reason_playerlang)
                else:
                    ban_success, blacklist_success = True, True

                embed_response.title = get_translation(self.user_lang, "permanent_ban")
                embed_response.description = perma_embedlang
                embed_response.color = discord.Color.red()  # Rot für Perma-Bann
                add_justification_field(embed_response, severity_reason_embedlang)
                embed_response.add_field(
                    name=get_translation(self.user_lang, "steam_id"),
                    value=str(author_player_id),
                    inline=False
                )
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

        # => !admin ...
        if clean_description.strip().lower().startswith("!admin"):
            admin_content = clean_description.strip()[len("!admin"):].strip()
            players_fast = await self.api_client.get_players()
            valid_player_names = []
            if players_fast and 'result' in players_fast:
                valid_player_names = [p['name'].lower() for p in players_fast['result']]
            found_candidate = None
            for valid_name in valid_player_names:
                if valid_name in admin_content.lower():
                    found_candidate = valid_name
                    break
            if found_candidate:
                logging.info(f"Admin report detected. Extracted identifier: {found_candidate}")
                await self.find_and_respond_player(message, found_candidate)
                return
            else:
                # => Positive Meldung
                author_name = get_author_name() or message.author.display_name
                author_player_id = await get_playerid_from_name(author_name, self.api_client)
                if author_player_id:
                    pos_playerlang = await generate_positive_response_text(self.ai_client, author_name, admin_content, detected_lang)
                    pos_embedlang = await translate_text(self.ai_client, pos_playerlang, detected_lang, self.user_lang)

                    embed_response.title = get_translation(self.user_lang, "positive_response_title")
                    embed_response.description = pos_embedlang
                    embed_response.color = discord.Color.green()  # Grün für positive Meldung
                    embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)

                    await message.reply(embed=embed_response)
                    await self.api_client.do_message_player(author_name, author_player_id, pos_playerlang)
                else:
                    logging.error("No matching player found for positive report.")
                return

        # => legit
        if category == "legit":
            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            if author_player_id:
                pos_playerlang = await generate_positive_response_text(self.ai_client, author_name, justification_playerlang, detected_lang)
                pos_embedlang = await translate_text(self.ai_client, pos_playerlang, detected_lang, self.user_lang)

                embed_response.title = get_translation(self.user_lang, "positive_response_title")
                embed_response.description = pos_embedlang
                embed_response.color = discord.Color.green()  # Grün für positives Feedback
                embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)

                await message.reply(embed=embed_response)
                # DM
                await self.api_client.do_message_player(author_name, author_player_id, pos_playerlang)
            else:
                logging.error("No matching player found for positive report.")
            return

        logging.info("Classification unknown: no action taken.")

    async def show_punish_reporter(self, message: discord.Message, reason: str):
        """
        Falls der Reporter-Text selbst beleidigend ist, etc.
        """
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
        embed.add_field(name=get_translation(self.user_lang, "reporter"), value=author_name, inline=False)
        embed.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)

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
            logging.error("Failed to retrieve detailed player data.")
            return

        if unit_name is None:
            unit_name = ""

        matching_player = []
        for player_id, player_info in player_data['result']['players'].items():
            player_unit_name = player_info.get('unit_name', "") or ""
            if (
                player_info['team'] and player_info['team'].lower() == team.lower() and
                player_unit_name.lower() == unit_name.lower() and
                player_info['role'].lower() in [r.lower() for r in roles]
            ):
                matching_player = {
                    "name": player_info['name'],
                    "level": player_info['level'],
                    "kills": player_info['kills'],
                    "deaths": player_info['deaths'],
                    "player_id": player_info['player_id'],
                }
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
            self.last_response_message_id = response_message.id
        else:
            await self.player_not_found(message)

        logging.info(get_translation(self.user_lang, "response_sent").format(unit_name=unit_name, roles=', '.join(roles), team=team))

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
                            f"Scores for '{reported_word}' vs '{cleaned_player_name}': "
                            f"Levenshtein = {levenshtein_score}, Jaro = {jaro_score}, Combined = {combined_score}"
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
                logging.info(get_translation(self.user_lang, "best_match_found").format(best_match))
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
