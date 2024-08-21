# Importing necessary libraries for the bot and API interaction
import os
import re
import discord
from discord.ext import commands
from discord.ui import View

from dotenv import load_dotenv
from api_client import APIClient  # Assuming this is the same as provided earlier
from Levenshtein import distance as levenshtein_distance
from Levenshtein import jaro_winkler
from helpers import remove_markdown, remove_bracketed_content, find_player_names, get_translation, get_author_name, \
    set_author_name, load_excluded_words, remove_clantags, add_modlog, add_emojis_to_messages, get_logs, \
    only_remove_buttons, get_playerid_from_name, load_autorespond_tigger
from modals import MessagePlayerButton, Finish_Report_Button, ReasonSelect  # Importieren Sie das neue Modal und den Button
import logging
from messages import unitreportembed, playerreportembed, player_not_found_embed, Reportview

# Konfiguration des Loggings
logging.basicConfig(filename='bot_log.txt', level=logging.DEBUG,  # Level auf DEBUG gesetzt
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Loading environment variables
load_dotenv()

# Discord Bot configuration
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_TOKEN = os.getenv('RCON_API_TOKEN')
ALLOWED_CHANNEL_ID = int(os.getenv('ALLOWED_CHANNEL_ID'))  # Assuming channel ID is an integer
USERNAME = os.getenv('RCON_USERNAME')
PASSWORD = os.getenv('RCON_PASSWORD')
MAX_SERVERS = int(os.getenv('MAX_SERVERS'))
user_lang = os.getenv('USER_LANG', 'en')  # Standardwert auf 'en' gesetzt

# Setting up Discord client
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

class MyBot(commands.Bot):
    def __init__(self, intents):
        super().__init__(command_prefix="!", intents=intents)
        self.api_client = APIClient(None, API_TOKEN)  # Initialisieren ohne API_BASE_URL
        self.api_base_url = None
        self.api_logged_in = False
        self.excluded_words = load_excluded_words('exclude_words.json')
        self.autorespond_trigger = load_autorespond_tigger('autorespond_trigger.json')

    async def login_to_api(self, api_base_url):
        if not self.api_logged_in or self.api_base_url != api_base_url:
            self.api_base_url = api_base_url
            self.api_client.base_url = api_base_url
            self.api_logged_in = await self.api_client.login(USERNAME, PASSWORD)
            if self.api_logged_in:
                print(get_translation(user_lang, "api_login_successful").format(api_base_url))
            else:
                print(get_translation(user_lang, "api_login_failed").format(api_base_url))

    def extract_server_name(self, embed):
        if embed.footer:
            return embed.footer.text.strip()
        return None

    def get_api_base_url_from_server_name(self, extracted_server_name):
        # Durchsuchen Sie alle möglichen SERVER_NAME_X und finden Sie die übereinstimmende API_BASE_URL_X
        for i in range(1, MAX_SERVERS + 1):
            server_name_env_var = f"SERVER_NAME_{i}"
            if os.getenv(server_name_env_var) == extracted_server_name:
                return os.getenv(f"API_BASE_URL_{i}")
        return None  # Keine passende API-Basis-URL gefunden

    async def on_ready(self):
        print(f'{self.user} has logged in.')

    async def on_message(self, message):
        # Prüfen Sie zuerst, ob die Nachricht von Ihrem Bot oder von einem unerlaubten Kanal kommt.
        if message.author == self.user or message.channel.id != ALLOWED_CHANNEL_ID:
            return

        server_name = None
        api_base_url = None

        if message.embeds:
            embed = message.embeds[0]
            if embed.footer:
                server_name = self.extract_server_name(embed)
                if server_name:
                    api_base_url = self.get_api_base_url_from_server_name(server_name)
                    if api_base_url:
                        self.api_client.base_url = api_base_url
                        await self.login_to_api(api_base_url)
                    else:
                        print(get_translation(user_lang, "no_api_base_url_found"))
                else:
                    print(get_translation(user_lang, "no_server_name_found"))

        if server_name is not None:
            api_base_url = self.get_api_base_url_from_server_name(server_name)

        # Überprüfen Sie, ob eine gültige URL gefunden wurde, bevor Sie fortfahren
        if api_base_url:
            self.api_client.base_url = api_base_url
            await self.login_to_api(api_base_url)

        trigger_words = ["able", "baker", "charlie", "commander", "kommandant", "dog", "easy", "fox", "george", "how", "item", "jig", "king", "love", "mike", "negat", "option", "prep", "queen", "roger", "sugar", "tare", "uncle", "victor", "william", "x-ray", "yoke", "zebra"]
        team = None  # Initialisierung von 'team'

        if message.embeds:
            embed = message.embeds[0]
            message_author = message.author.display_name if message.author else "Unbekannter Sender"
            logging.info(f"Message send from Author: {message_author}")

            # Aktualisiertes Regex-Muster
            updated_regex_pattern = r"(.+?)\s+\[(Axis|Allies)\](?:\[\w+\])?"

            if embed.author and embed.author.name:
                match = re.match(updated_regex_pattern, embed.author.name)
                if match:
                    set_author_name(match.group(1).strip())
                    team = match.group(2).strip()
                    logging.info(f"Embed Author Name: {get_author_name()}")
                    logging.info(f"Detected team: {team}")
                else:
                    logging.error("Could not extract author name and team from the embed author.")

            if embed.description:
                clean_description = remove_markdown(embed.description)
                logging.info(f"Cleaned Embed Description: {clean_description}")
                command_parts = clean_description.split()

            if not "clean_description" in locals():
                return

            if clean_description.lower() in self.autorespond_trigger:
                author_name = get_author_name()
                playerid = await get_playerid_from_name(get_author_name(), api_client=self.api_client)
                message_content = get_translation(user_lang, "no_reason_or_player")
                success = await self.api_client.do_message_player(author_name, playerid, message_content)
                if success:
                    await message.add_reaction("✅")
                    await message.add_reaction("📨")
                return


            if "watched on:" not in clean_description: # Don't react on watchlist messages
                reported_parts = command_parts

                if reported_parts:
                    if any(word in reported_parts for word in trigger_words):
                        logging.info("Identified as unit report.")
                        trigger_word_index = next(i for i, part in enumerate(reported_parts) if part in trigger_words)
                        unit_name = reported_parts[trigger_word_index]

                        # Accept 'commander' and 'kommandant' as trigger words
                        if "commander" in reported_parts or "kommandant" in reported_parts:
                            unit_name = "command"

                        roles = ["officer", "spotter", "tankcommander", "armycommander"]
                        logging.info(f"Unit name: {unit_name}, Roles: {roles}")

                        # Stellen Sie sicher, dass 'team' vor dem Aufruf von find_and_respond_unit gesetzt ist
                        if team:
                            await self.find_and_respond_unit(team, unit_name, roles, message)
                        else:
                            logging.error("Team not identified for unit report.")

                    else:
                        logging.info("Identified as player report.")
                        reported_identifier = " ".join(reported_parts)
                        logging.info(f"Reported identifier: {reported_identifier}")
                        await self.find_and_respond_player(message, reported_identifier)
                        logging.info("find_and_respond_player called.")


    async def find_and_respond_unit(self, team, unit_name, roles, message):
        player_data = await self.api_client.get_detailed_players()

        if player_data is None or 'result' not in player_data or 'players' not in player_data['result']:
            logging.error("Failed to retrieve player data or player data is incomplete.")
            return

        if unit_name is None:
            unit_name = ""

        matching_player = []
        for player_id, player_info in player_data['result']['players'].items():
            player_unit_name = player_info.get('unit_name', "")
            if player_unit_name is None:
                player_unit_name = ""

            if player_info['team'] and player_info['team'].lower() == team.lower() and \
            player_unit_name.lower() == unit_name.lower() and \
            player_info['role'].lower() in [role.lower() for role in roles]:
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
            player_additional_data= await self.api_client.get_player_by_id(matching_player['player_id'])
            embed = await unitreportembed(player_additional_data, user_lang, unit_name, roles, team, matching_player)
            view = Reportview(self.api_client)
            await view.add_buttons(user_lang, matching_player['name'], player_additional_data['player_id'], self.unjustified_report_click, self.no_action_click, self.manual_process)
            response_message = await message.reply(embed=embed, view=view)
            self.last_response_message_id = response_message.id
        else:
            # Verwenden des vorhandenen MessagePlayerButton, um dem Absender zu antworten
            author_name = get_author_name()
            await self.player_not_found(message, get_translation(user_lang, "no_players_found").format(unit_name, ', '.join(roles), team))
        logging.info(get_translation(user_lang, "response_sent").format(unit_name, ', '.join(roles), team))

    async def find_and_respond_player(self, message, reported_identifier, max_levenshtein_distance=3, jaro_winkler_threshold=0.85):
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
                        logging.info(f"Scores for '{reported_word}' vs '{cleaned_player_name}': Levenshtein = {levenshtein_score}, Jaro = {jaro_score}, Combined = {combined_score}")

                        if combined_score < best_score and combined_score <= max_combined_score_threshold:
                            best_score = combined_score
                            best_match = player['name']
                            best_player_data = player
                            logging.info(f"New best match found: {best_match} with score {best_score}")

        if best_match:
            live_game_stats = await self.api_client.get_player_data(best_player_data['player_id'])
            player_stats = next((item for item in live_game_stats['result']['stats'] if
                                 item['player_id'] == best_player_data['player_id']), None)
            if not live_game_stats or 'result' not in live_game_stats or 'stats' not in live_game_stats['result']:
                logging.error("Failed to retrieve live game stats for the best matching player")
                return

            if player_stats:
                logging.info(get_translation(user_lang, "best_match_found").format(best_match))
                player_additional_data = await self.api_client.get_player_by_id(best_player_data['player_id'])
                total_playtime_seconds = player_additional_data.get('total_playtime_seconds', 0)
                total_playtime_hours = total_playtime_seconds / 3600
                embed = await playerreportembed(user_lang, best_match, player_stats, total_playtime_hours, best_player_data)

                response_message = await message.reply(embed=embed)
                self.last_response_message_id = response_message.id
                view = Reportview(self.api_client)
                await view.add_buttons(user_lang, best_match, best_player_data['player_id'], self.unjustified_report_click, self.no_action_click, self.manual_process)
                await response_message.edit(view=view)
            else:
                await self.player_not_found(message)
        else:
            await self.player_not_found(message)

    async def player_not_found(self, message):
        author_name = get_author_name()
        view = View(timeout=None)
        view = Reportview(self.api_client)
        name = get_author_name()
        player_id = await get_playerid_from_name(name, self.api_client)
        await view.add_buttons(user_lang, get_author_name(), player_id, self.unjustified_report_click, self.no_action_click,
                               self.manual_process, self_report=True)
        embed = await player_not_found_embed(player_id, author_name, user_lang)
        await message.reply(embed=embed, view=view)


    async def unjustified_report_click(self, interaction: discord.Interaction):
        print("Unjustified report click triggered")

        new_view = discord.ui.View(timeout=None)
        await interaction.message.edit(view=new_view)
        print("Kick buttons removed")

        await add_emojis_to_messages(interaction, '❌')
        print("Reactions updated")

        confirm_message = get_translation(user_lang, "unjustified_report_acknowledged")
        await interaction.response.send_message(confirm_message, ephemeral=True)
        print("Confirmation message sent")

        author_name = get_author_name()
        print(f"Using extracted author name: {author_name}")

        players_data = await self.api_client.get_players()
        if players_data and 'result' in players_data:
            players_list = players_data['result']
            player = next((p for p in players_list if p['name'].lower() == author_name.lower()), None)
            if player:
                player_id = player['player_id']
                message_to_send = get_translation(user_lang, "report_not_granted")
                await self.api_client.do_message_player(author_name, player_id, message_to_send)
                modlog = get_translation(user_lang, "log_unjustified").format(interaction.user.display_name)
                await add_modlog(interaction, modlog, False, user_lang, self.api_client)
            else:
                logging.error(f"Player {author_name} not found.")
        else:
            logging.error("Failed to retrieve players list or 'result' not in players_data.")



    async def no_action_click(self, interaction: discord.Interaction):
        # Entfernen aller Buttons aus der Nachricht
        await only_remove_buttons(interaction)
        modlog = get_translation(user_lang, "log_no-action").format(interaction.user.display_name)
        await add_modlog(interaction, modlog, False, user_lang, self.api_client)
        # Optional: Senden einer Bestätigungsnachricht
        confirm_message = get_translation(user_lang, "no_action_performed")
        await interaction.response.send_message(confirm_message, ephemeral=True)
        # Hinzufügen des Mülleimers als Reaktion
        await add_emojis_to_messages(interaction, '🗑')

    async def manual_process(self, interaction: discord.Interaction):
        view = Finish_Report_Button(user_lang=user_lang, api_client=self.api_client)
        modlog = get_translation(user_lang, "log_manual").format(interaction.user.display_name)
        await interaction.message.edit(view=view)
        await add_modlog(interaction, modlog, False, user_lang, self.api_client, delete_buttons=False)
        # Optional: Senden einer Bestätigungsnachricht
        confirm_message = get_translation(user_lang, "manual_process_respond")
        await interaction.response.send_message(confirm_message, ephemeral=True)
        await add_emojis_to_messages(interaction, '👀')



    async def on_close(self):
        if self.api_client.session:
            await self.api_client.close_session()

# Running the bot
bot = MyBot(intents)
bot.run(TOKEN)
