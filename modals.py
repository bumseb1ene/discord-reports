import discord
from discord.ui import Select  # Import der Select Klasse
from helpers import get_translation, get_author_name, set_author_name, add_modlog, add_check_to_messages, \
    get_playername, add_warning_to_messages, only_remove_buttons
import logging


class TempBanModal(discord.ui.Modal):
    def __init__(self, api_client, steam_id_64, user_lang):
        super().__init__(title=get_translation(user_lang, "temp_ban_modal_title"))
        self.api_client = api_client
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang

        self.duration = discord.ui.TextInput(
            label=get_translation(user_lang, "temp_ban_duration_label"),
            placeholder=get_translation(user_lang, "temp_ban_duration_placeholder"),
            style=discord.TextStyle.short
        )
        self.add_item(self.duration)

        self.reason = discord.ui.TextInput(
            label=get_translation(user_lang, "temp_ban_reason_label"),
            placeholder=get_translation(user_lang, "temp_ban_reason_placeholder"),
            style=discord.TextStyle.long,
            required=True,
            max_length=300
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        duration_hours = self.duration.value
        reason = self.reason.value
        by = interaction.user.name

        player_name = await self.api_client.get_player_by_steam_id(self.steam_id_64)
        if player_name:
            success = await self.api_client.do_temp_ban(player_name, self.steam_id_64, duration_hours, reason, by)

            if success:
                confirmation_message = get_translation(self.user_lang, "player_temp_banned_successfully").format(
                    player_name, duration_hours, reason)
                players_data = await self.api_client.get_players()
                if players_data and 'result' in players_data:
                    players_list = players_data['result']
                    author_name = get_author_name()
                    author_player = next((p for p in players_list if p['name'].lower() == author_name.lower()), None)
                    if author_player:
                        steam_id_64 = author_player['steam_id_64']
                        message_to_author = get_translation(self.user_lang, "message_to_author_temp_banned").format(
                            player_name)
                        await self.api_client.do_message_player(author_name, steam_id_64, message_to_author)
            else:
                confirmation_message = get_translation(self.user_lang, "error_temp_banning_player")
            await interaction.response.send_message(confirmation_message, ephemeral=True)

            # Update the original message to disable buttons
            try:
                modlog = get_translation(self.user_lang, "log_tempban").format(interaction.user.display_name,
                                                                               await get_playername(self),
                                                                               duration_hours, reason)
                await add_modlog(interaction, modlog, self.steam_id_64, self.user_lang, self.api_client)
                await add_check_to_messages(interaction)
            except discord.NotFound:
                logging.error("Original message not found or uneditable.")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
        else:
            await interaction.response.send_message(get_translation(self.user_lang, "player_name_not_retrieved"),
                                                    ephemeral=True)
            await add_warning_to_messages(interaction)
            await only_remove_buttons(interaction)


class TempBanButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, steam_id_64, user_lang, report_type,
                 player_additional_data=False):
        super().__init__(style=discord.ButtonStyle.blurple, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang
        self.report_type = report_type
        self.player_additional_data = player_additional_data

    async def callback(self, interaction: discord.Interaction):
        modal = TempBanModal(self.api_client, self.steam_id_64, self.user_lang)
        await interaction.response.send_modal(modal)


class MessagePlayerModal(discord.ui.Modal):
    def __init__(self, title: str, api_client, steam_id_64, user_lang, author_name):
        super().__init__(title=get_translation(user_lang, "message_player_modal_title"))
        self.api_client = api_client
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang
        self.author_name = author_name  # Hinzufügen des author_name

        self.message = discord.ui.TextInput(
            label=get_translation(user_lang, "message_label"),
            placeholder=get_translation(user_lang, "message_placeholder"),
            style=discord.TextStyle.long,
            required=True,
            max_length=300
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        message_content = self.message.value
        by = interaction.user.name

        author_name = self.author_name  # Verwenden des übergebenen author_name
        players_data = await self.api_client.get_players()
        if players_data and 'result' in players_data:
            players_list = players_data['result']
            author_player = next((p for p in players_list if p['name'].lower() == author_name.lower()), None)
            if author_player:
                steam_id_64 = author_player['steam_id_64']
                success = await self.api_client.do_message_player(author_name, steam_id_64, message_content)

                if success:
                    confirmation_message = get_translation(self.user_lang, "message_sent_successfully").format(
                        author_name, message_content)
                else:
                    confirmation_message = get_translation(self.user_lang, "error_sending_message")

                await interaction.response.send_message(confirmation_message, ephemeral=True)
                modlog = get_translation(self.user_lang, "log_message_reporter").format(interaction.user.display_name,
                                                                                        await get_playername(self),
                                                                                        message_content)
                await add_modlog(interaction, modlog, steam_id_64, self.user_lang, self.api_client)
                await add_check_to_messages(interaction)
            else:
                await interaction.response.send_message(get_translation(self.user_lang, "author_name_not_found"),
                                                        ephemeral=True)
                await add_warning_to_messages(interaction)
                await only_remove_buttons(interaction)
        else:
            await interaction.response.send_message(get_translation(self.user_lang, "error_retrieving_players"),
                                                    ephemeral=True)
            await add_warning_to_messages(interaction)
            await only_remove_buttons(interaction)


class MessagePlayerButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, steam_id_64, user_lang):
        super().__init__(style=discord.ButtonStyle.grey, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang

    async def callback(self, interaction: discord.Interaction):
        author_name = get_author_name()  # Hier holen wir den author_name
        modal = MessagePlayerModal(
            get_translation(self.user_lang, "message_player_modal_title"),
            self.api_client,
            self.steam_id_64,
            self.user_lang,
            author_name  # Den author_name an das Modal übergeben
        )
        await interaction.response.send_modal(modal)


class MessageReportedPlayerModal(discord.ui.Modal):
    def __init__(self, title: str, api_client, steam_id_64, user_lang):
        super().__init__(title=get_translation(user_lang, "message_reported_player_modal_title"))
        self.api_client = api_client
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang

        self.message = discord.ui.TextInput(
            label=get_translation(user_lang, "message_label"),
            placeholder=get_translation(user_lang, "message_placeholder"),
            style=discord.TextStyle.long,
            required=True,
            max_length=300
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        message_content = self.message.value
        by = interaction.user.name
        player_name = await self.api_client.get_player_by_steam_id(self.steam_id_64)
        if player_name:
            success = await self.api_client.do_message_player(player_name, self.steam_id_64, message_content)
            if success:
                modlog = get_translation(self.user_lang, "log_message_reported").format(interaction.user.display_name,
                                                                                        await get_playername(self),
                                                                                        message_content)
                await add_modlog(interaction, modlog, self.steam_id_64, self.user_lang, self.api_client)
                await add_check_to_messages(interaction)
                confirmation_message = get_translation(self.user_lang, "message_sent_successfully").format(player_name,
                                                                                                           message_content)
            else:
                await add_warning_to_messages(interaction)
                await only_remove_buttons(interaction)
                confirmation_message = get_translation(self.user_lang, "error_sending_message")

            await interaction.response.send_message(confirmation_message, ephemeral=True)


class MessageReportedPlayerButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, steam_id_64, user_lang):
        super().__init__(style=discord.ButtonStyle.grey, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang

    async def callback(self, interaction: discord.Interaction):
        modal = MessageReportedPlayerModal(get_translation(self.user_lang, "message_reported_player_modal_title"),
                                           self.api_client, self.steam_id_64, self.user_lang)
        await interaction.response.send_modal(modal)


class KickReasonSelect(Select):
    def __init__(self, steam_id_64, user_lang, original_message, api_client):
        options = [
            discord.SelectOption(label=get_translation(user_lang, "no_communication_voice_chat"),
                                 value=get_translation(user_lang, "no_communication_voice_chat")),
            discord.SelectOption(label=get_translation(user_lang, "solo_squads_not_allowed"),
                                 value=get_translation(user_lang, "solo_squads_not_allowed")),
            discord.SelectOption(label=get_translation(user_lang, "teamkills_not_tolerated"),
                                 value=get_translation(user_lang, "teamkills_not_tolerated")),
            discord.SelectOption(label=get_translation(user_lang, "trolls_not_tolerated"),
                                 value=get_translation(user_lang, "trolls_not_tolerated")),
            discord.SelectOption(label=get_translation(user_lang, "insults_not_tolerated"),
                                 value=get_translation(user_lang, "insults_not_tolerated")),
            discord.SelectOption(label=get_translation(user_lang, "cheating"),
                                 value=get_translation(user_lang, "cheating")),
            discord.SelectOption(label=get_translation(user_lang, "spamming"),
                                 value=get_translation(user_lang, "spamming")),
        ]
        super().__init__(placeholder=get_translation(user_lang, "select_kick_reason"), min_values=1, max_values=1,
                         options=options)
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang
        self.original_message = original_message
        self.api_client = api_client

    async def callback(self, interaction: discord.Interaction):
        selected_reason = self.values[0]

        await interaction.response.send_message(f"Gewählter Grund: {selected_reason}", ephemeral=True)
        modlog = get_translation(self.user_lang, "log_kick").format(interaction.user.display_name, await get_playername(self),
                                                                    selected_reason)
        await add_modlog(interaction, modlog, self.steam_id_64, self.user_lang, self.api_client)
        await add_check_to_messages(interaction)
        # Bestätige den Kick
        await self.view.bot.confirm_kick(interaction, self.steam_id_64, selected_reason)
