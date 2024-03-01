# Importing necessary libraries for the bot and API interaction
import os
import re
import discord
from discord.ext import commands
from discord.ui import View, Button

from dotenv import load_dotenv
from api_client import APIClient  # Assuming this is the same as provided earlier
from Levenshtein import distance as levenshtein_distance
from Levenshtein import jaro_winkler
from helpers import remove_markdown, remove_bracketed_content, find_player_names, get_translation


import logging

# Konfiguration des Loggings
logging.basicConfig(filename='bot_log.txt', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Loading environment variables
load_dotenv()

# Discord Bot configuration
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL')
API_TOKEN = os.getenv('API_TOKEN')
ALLOWED_CHANNEL_ID = int(os.getenv('ALLOWED_CHANNEL_ID'))  # Assuming channel ID is an integer
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
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
        self.api_client = APIClient(API_BASE_URL, API_TOKEN)
        self.author_name = ""  # Initialisieren des Attributs für den Autorennamen

    async def on_ready(self):
        print(get_translation(user_lang, "bot_logged_in").format(self.user))
        if await self.api_client.login(USERNAME, PASSWORD):
            print(get_translation(user_lang, "api_login_successful"))
        else:
            print(get_translation(user_lang, "api_login_failed"))

    async def on_message(self, message):
        trigger_words = ["able", "baker", "charlie", "commander", "kommandant", "dog", "easy", "fox", "george", "how", "item", "jig", "king", "love", "mike", "negat", "option", "prep", "queen", "roger", "sugar", "tare", "uncle", "victor", "william", "x-ray", "yoke", "zebra"]
        team = None  # Initialisierung von 'team'

        if message.author == self.user or message.channel.id != ALLOWED_CHANNEL_ID:
            return

        if message.embeds:
            embed = message.embeds[0]
            message_author = message.author.display_name if message.author else get_translation(user_lang, "unknown_sender")
            logging.info(get_translation(user_lang, "message_sent_by").format(message_author))

            # Aktualisiertes Regex-Muster
            updated_regex_pattern = r"(.+?)\s+\[(Axis|Allies)\](?:\[\w+\])?"

            if embed.author and embed.author.name:
                match = re.match(updated_regex_pattern, embed.author.name)
                if match:
                    self.author_name = match.group(1).strip()
                    team = match.group(2).strip()
                    logging.info(get_translation(user_lang, "embed_author_name").format(self.author_name))
                    logging.info(get_translation(user_lang, "detected_team").format(team))
                else:
                    logging.error(get_translation(user_lang, "author_team_extract_error"))

        if embed.description:
            clean_description = remove_markdown(embed.description)
            logging.info(f"Cleaned Embed Description: {clean_description}")
            command_parts = clean_description.split()

            if '!admin' in command_parts:
                logging.info(f"'!admin' command found in message: {message.content}")
                admin_index = command_parts.index('!admin')
                reported_parts = command_parts[admin_index + 1:]
                logging.info(f"Parts after '!admin': {reported_parts}")

                if reported_parts:
                    if any(word in reported_parts for word in trigger_words):
                        logging.info(get_translation(user_lang, "identified_unit_report"))
                        trigger_word_index = next(i for i, part in enumerate(reported_parts) if part in trigger_words)
                        unit_name = reported_parts[trigger_word_index]

                        # Accept 'commander' and 'kommandant' as trigger words
                        if "commander" in reported_parts or "kommandant" in reported_parts:
                            unit_name = "commmand"

                        roles = ["officer", "spotter", "tankcommander", "armycommander"]
                        logging.info(f"Unit name: {unit_name}, Roles: {roles}")

                        # Stellen Sie sicher, dass 'team' vor dem Aufruf von find_and_respond_unit gesetzt ist
                        if team:
                            await self.find_and_respond_unit(team, unit_name, roles, message)
                        else:
                            logging.error(get_translation(user_lang, "team_not_identified"))

                    else:
                        logging.info(get_translation(user_lang, "identified_player_report"))
                        reported_identifier = " ".join(reported_parts)
                        logging.info(get_translation(user_lang, "reported_identifier").format(reported_identifier))
                        await self.find_and_respond_player(message, reported_identifier)
                        logging.info(get_translation(user_lang, "find_respond_player_called"))


    async def find_and_respond_unit(self, team, unit_name, roles, message):
        # Abfragen der Spielerdaten von der API
        player_data = await self.api_client.get_detailed_players()

        # Sicherstellen, dass unit_name nicht None ist
        if unit_name is None:
            unit_name = ""

        # Suchen nach einem Spieler, der den Kriterien entspricht
        matching_players = []
        for player_id, player_info in player_data['result']['players'].items():
            # Verwenden von get() um None zu vermeiden und einen leeren String als Standardwert zu setzen
            player_unit_name = player_info.get('unit_name', "")
            if player_unit_name is None:
                player_unit_name = ""

            if player_info['team'].lower() == team.lower() and \
               player_unit_name.lower() == unit_name.lower() and \
               player_info['role'].lower() in [role.lower() for role in roles]:
                player_details = {
                    "name": player_info['name'],
                    "level": player_info['level'],
                    "kills": player_info['kills'],
                    "deaths": player_info['deaths'],
                    "steam_id_64": player_info['steam_id_64'],  # Steam-ID hinzufügen
                }
                matching_players.append(player_details)

        # Erstellen des Embeds
        if matching_players:
            embed_title = get_translation(user_lang, "players_in_unit").format(unit_name, ', '.join(roles), team)
            embed = discord.Embed(title=embed_title, color=0xd85f0e)
            view = View(timeout=None)
            for player in matching_players:
                # Abrufen des aktuellen Spielernamens
                current_player_name = await self.api_client.get_player_by_steam_id(player['steam_id_64'])

                # Abrufen der zusätzlichen Spielerdaten, einschließlich total_playtime_seconds
                player_additional_data = await self.api_client.get_player_by_id(player['steam_id_64'])
                total_playtime_seconds = player_additional_data.get('total_playtime_seconds', 0)
                total_playtime_hours = total_playtime_seconds / 3600

                # Erstellen eines Buttons
                button_label = get_translation(user_lang, "kick_player").format(current_player_name) if current_player_name else get_translation(user_lang, "kick_player_generic")
                button = Button(label=button_label, style=discord.ButtonStyle.red, custom_id=player['steam_id_64'])
                button.steam_id_64 = player['steam_id_64']  # Speichern der Steam-ID im Button
                button.player_name = current_player_name  # Speichern des Spielernamens im Button
                button.callback = self.button_click  # Verknüpfen des Callbacks
                view.add_item(button)

                # Erstellen des Buttons für unbegründeten Report
                unjustified_report_button = Button(label=get_translation(user_lang, "unjustified_report"), style=discord.ButtonStyle.grey, custom_id="unjustified_report")
                unjustified_report_button.callback = self.unjustified_report_click  # Verknüpfen des neuen Callbacks
                view.add_item(unjustified_report_button)

                no_action_button = Button(label=get_translation(user_lang, "wrong_player_reported"), style=discord.ButtonStyle.grey, custom_id="no_action")
                no_action_button.callback = self.no_action_click
                view.add_item(no_action_button)

                embed.add_field(name=get_translation(user_lang, "name"), value=player["name"], inline=True)
                embed.add_field(name=get_translation(user_lang, "level"), value=player["level"], inline=True)
                embed.add_field(name=get_translation(user_lang, "total_playtime"), value=f"{total_playtime_hours:.2f} " + get_translation(user_lang, "hours"), inline=True)
                embed.add_field(name=get_translation(user_lang, "kills"), value=player["kills"], inline=True)
                embed.add_field(name=get_translation(user_lang, "deaths"), value=player["deaths"], inline=True)
                embed.add_field(name=get_translation(user_lang, "steam_id"), value=player["steam_id_64"], inline=True)


            # Senden der Antwort als Reaktion auf die ursprüngliche Nachricht
            response_message = await message.reply(embed=embed, view=view)

            self.last_response_message_id = response_message.id  # Speichern der Nachrichten-ID
            await response_message.add_reaction('⏳')
        else:
            response = get_translation(user_lang, "no_players_found").format(unit_name, ', '.join(roles), team)
            await message.channel.send(response)

        await message.add_reaction('⏳')
        logging.info(get_translation(user_lang, "response_sent").format(unit_name, ', '.join(roles), team))

    async def find_and_respond_player(self, message, reported_identifier, max_levenshtein_distance=3, jaro_winkler_threshold=0.85):
        logging.info(get_translation(user_lang, "find_and_respond_player_called"))
        logging.info(get_translation(user_lang, "searching_for_player_report").format(reported_identifier))

        reported_identifier_cleaned = remove_bracketed_content(reported_identifier)
        potential_names = find_player_names(reported_identifier_cleaned)

        live_game_stats = await self.api_client.get_player_data()
        if not live_game_stats or 'result' not in live_game_stats or 'stats' not in live_game_stats['result']:
            logging.error("Failed to retrieve live game stats")
            return

        best_match = None
        best_player_data = None
        best_score = 0

        for player in live_game_stats['result']['stats']:
            player_name_words = player['player'].lower().split()
            for reported_word in potential_names:
                for player_word in player_name_words:
                    levenshtein_score = levenshtein_distance(reported_word.lower(), player_word)
                    jaro_score = jaro_winkler(reported_word.lower(), player_word)

                    # Kombinieren der Scores
                    if levenshtein_score < max_levenshtein_distance or jaro_score > jaro_winkler_threshold:
                        combined_score = levenshtein_score + (1 - jaro_score)  # Kombinierter Score
                        if combined_score > best_score:
                            best_score = combined_score
                            best_match = player['player']
                            best_player_data = player

        if best_match:
            logging.info(get_translation(user_lang, "best_match_found").format(best_match))
            player_additional_data = await self.api_client.get_player_by_id(best_player_data['steam_id_64'])
            total_playtime_seconds = player_additional_data.get('total_playtime_seconds', 0)
            total_playtime_hours = total_playtime_seconds / 3600
            embed_title = get_translation(user_lang, "report_for_player").format(best_match)
            embed = discord.Embed(title=embed_title, color=0xd85f0e)
            embed.add_field(name=get_translation(user_lang, "information"), value=get_translation(user_lang, "check_report_match"), inline=False)
            embed.add_field(name=get_translation(user_lang, "total_playtime"), value=f"{total_playtime_hours:.2f} " + get_translation(user_lang, "hours"), inline=True)
            embed.add_field(name="Steam-ID", value=best_player_data['steam_id_64'], inline=True)  # 'Steam-ID' kann gleich bleiben
            embed.add_field(name=get_translation(user_lang, "kills"), value=best_player_data['kills'], inline=True)
            embed.add_field(name=get_translation(user_lang, "kill_streak"), value=best_player_data['kills_streak'], inline=True)
            embed.add_field(name=get_translation(user_lang, "deaths"), value=best_player_data['deaths'], inline=True)
            embed.add_field(name=get_translation(user_lang, "teamkills"), value=best_player_data['teamkills'], inline=True)
            embed.add_field(name=get_translation(user_lang, "teamkill_streak"), value=best_player_data['teamkills_streak'], inline=True)

            # Erstellen und Hinzufügen der Buttons
            button_label = get_translation(user_lang, "kick_player").format(best_match)
            button = Button(label=button_label, style=discord.ButtonStyle.red, custom_id=best_player_data['steam_id_64'])
            button.callback = self.button_click
            view = View(timeout=None)
            view.add_item(button)

            unjustified_report_button = Button(label=get_translation(user_lang, "unjustified_report"), style=discord.ButtonStyle.grey, custom_id="unjustified_report")
            unjustified_report_button.callback = self.unjustified_report_click
            view.add_item(unjustified_report_button)

            no_action_button = Button(label=get_translation(user_lang, "wrong_player_reported"), style=discord.ButtonStyle.grey, custom_id="no_action")
            no_action_button.callback = self.no_action_click
            view.add_item(no_action_button)


            response_message = await message.reply(embed=embed, view=view)
            self.last_response_message_id = response_message.id  # Speichern der Nachrichten-ID
            await response_message.add_reaction('⏳')
        else:
            await message.channel.send(get_translation(user_lang, "no_matching_player_found"))


    async def button_click(self, interaction: discord.Interaction):
        steam_id_64 = interaction.data['custom_id']
        confirm_button_label = get_translation(user_lang, "confirm")
        confirm_message = get_translation(user_lang, "are_you_sure_kick")
        confirm_button = discord.ui.Button(label=confirm_button_label, style=discord.ButtonStyle.green, custom_id=f"confirm_{steam_id_64}")
        confirm_button.callback = self.confirm_kick
        view = discord.ui.View(timeout=None)
        view.add_item(confirm_button)
        await interaction.response.send_message(confirm_message, view=view, ephemeral=True)
        # Abrufen der ursprünglichen Nachricht, auf die reagiert werden soll
        original_message = await interaction.channel.fetch_message(self.last_response_message_id)
        # Führen Sie hier Aktionen mit original_message durch, z. B. Reaktionen hinzufügen/entfernen

    async def confirm_kick(self, interaction: discord.Interaction):
        steam_id_64 = interaction.data['custom_id'].split('_')[1]

        player_name = await self.api_client.get_player_by_steam_id(steam_id_64)
        if player_name:
            success = await self.api_client.do_kick(player_name, steam_id_64)
            if success:
                kicked_message = get_translation(user_lang, "player_kicked_successfully").format(player_name)
                await interaction.response.send_message(kicked_message, ephemeral=True)
                # Abrufen der Liste aller Spieler, um die Steam-ID des Autors zu finden
                players_data = await self.api_client.get_players_fast()
                if players_data and 'result' in players_data:
                    players_list = players_data['result']
                    author_player = next((p for p in players_list if p['name'].lower() == self.author_name.lower()), None)
                    if author_player:
                        # Senden einer Nachricht an den Autor
                        author_steam_id_64 = author_player['steam_id_64']
                        message_to_author = get_translation(user_lang, "message_to_author_kicked").format(player_name)
                        await self.api_client.do_message_player(self.author_name, author_steam_id_64, message_to_author)
                    else:
                        logging.error(get_translation(user_lang, "author_not_found"))
                else:
                    logging.error("Failed to retrieve players list or 'result' not in players_data.")
            else:
                await interaction.response.send_message(get_translation(user_lang, "error_kicking_player"), ephemeral=True)
        else:
            await interaction.response.send_message(get_translation(user_lang, "player_name_not_retrieved"), ephemeral=True)

        try:
            # Abrufen der ursprünglichen Nachricht, auf die reagiert werden soll
            original_message = await interaction.channel.fetch_message(self.last_response_message_id)
            # Hinzufügen des grünen Hakens und Deaktivieren des Buttons
            await original_message.clear_reaction('⏳')
            await original_message.add_reaction('✅')
            new_view = discord.ui.View(timeout=None)
            for item in original_message.components:
                if isinstance(item, discord.ui.Button):
                    new_button = discord.ui.Button(style=item.style, label=item.label, disabled=True)
                    new_view.add_item(new_button)
            await original_message.edit(view=new_view)
        except discord.NotFound:
            logging.error(get_translation(user_lang, "message_not_found_or_uneditable"))
        except Exception as e:
            logging.error(get_translation(user_lang, "unexpected_error").format(e))

    async def unjustified_report_click(self, interaction: discord.Interaction):
        print("Unjustified report click triggered")

        new_view = discord.ui.View(timeout=None)
        await interaction.message.edit(view=new_view)
        print("Kick buttons removed")

        await interaction.message.clear_reaction('⏳')
        await interaction.message.add_reaction('❌')
        print("Reactions updated")

        confirm_message = get_translation(user_lang, "unjustified_report_acknowledged")
        await interaction.response.send_message(confirm_message, ephemeral=True)
        print("Confirmation message sent")

        author_name = self.author_name
        print(f"Using extracted author name: {author_name}")

        players_data = await self.api_client.get_players_fast()
        if players_data and 'result' in players_data:
            players_list = players_data['result']
            player = next((p for p in players_list if p['name'].lower() == self.author_name.lower()), None)
            if player:
                steam_id_64 = player['steam_id_64']
                message_to_send = get_translation(user_lang, "report_not_granted")
                await self.api_client.do_message_player(self.author_name, steam_id_64, message_to_send)
            else:
                logging.error(f"Player {self.author_name} not found.")
        else:
            logging.error("Failed to retrieve players list or 'result' not in players_data.")

    async def no_action_click(self, interaction: discord.Interaction):
        # Entfernen aller Buttons aus der Nachricht
        new_view = discord.ui.View(timeout=None)
        await interaction.message.edit(view=new_view)

        # Hinzufügen des roten X als Reaktion
        await interaction.message.clear_reaction('⏳')
        await interaction.message.add_reaction('❌')

        # Optional: Senden einer Bestätigungsnachricht
        confirm_message = get_translation(user_lang, "no_action_performed")
        await interaction.response.send_message(confirm_message, ephemeral=True)



    async def on_close(self):
        if self.api_client.session:
            await self.api_client.close_session()

# Running the bot
bot = MyBot(intents)
bot.run(TOKEN)  # Uncomment these lines to run the bot
