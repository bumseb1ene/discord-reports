import discord
from discord.ui import Select, Button  # Import der Select Klasse
from helpers import get_translation, get_author_name, set_author_name, add_modlog, add_check_to_messages, \
    get_playername, add_emojis_to_messages, only_remove_buttons, get_logs, remove_emojis_to_messages, get_playername
import logging
import os


class TempBanButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang, report_type,
                 player_additional_data=False):
        super().__init__(style=discord.ButtonStyle.blurple, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.report_type = report_type
        self.player_additional_data = player_additional_data

    async def callback(self, interaction: discord.Interaction):
        # ToDo: Relace with SelectReasonView
        pass


class MessagePlayerModal(discord.ui.Modal):
    def __init__(self, title: str, api_client, player_id, user_lang, author_name):
        super().__init__(title=get_translation(user_lang, "message_player_modal_title"))
        self.api_client = api_client
        self.player_id = player_id
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
                player_id = author_player['player_id']
                success = await self.api_client.do_message_player(author_name, player_id, message_content)

                if success:
                    confirmation_message = get_translation(self.user_lang, "message_sent_successfully").format(
                        author_name, message_content)
                else:
                    confirmation_message = get_translation(self.user_lang, "error_sending_message")

                await interaction.response.send_message(confirmation_message, ephemeral=True)
                modlog = get_translation(self.user_lang, "log_message_reporter").format(interaction.user.display_name,
                                                                                        author_name,
                                                                                        message_content)
                await add_modlog(interaction, modlog, player_id, self.user_lang, self.api_client)
                await add_check_to_messages(interaction)
            else:
                await interaction.response.send_message(get_translation(self.user_lang, "author_name_not_found"),
                                                        ephemeral=True)
                await add_emojis_to_messages(interaction)
                await only_remove_buttons(interaction)
        else:
            await interaction.response.send_message(get_translation(self.user_lang, "error_retrieving_players"),
                                                    ephemeral=True)
            await add_emojis_to_messages(interaction)
            await only_remove_buttons(interaction)


class MessagePlayerButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang):
        super().__init__(style=discord.ButtonStyle.grey, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang

    async def callback(self, interaction: discord.Interaction):
        author_name = get_author_name()  # Hier holen wir den author_name
        modal = MessagePlayerModal(
            get_translation(self.user_lang, "message_player_modal_title"),
            self.api_client,
            self.player_id,
            self.user_lang,
            author_name  # Den author_name an das Modal übergeben
        )
        await interaction.response.send_modal(modal)


class MessageReportedPlayerButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang, author_player_id, author_name):
        super().__init__(style=discord.ButtonStyle.grey, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.author_player_id = author_player_id
        self.author_name = author_name

    async def callback(self, interaction: discord.Interaction):
        view = ReasonSelect(self.user_lang, self.api_client, self.player_id, "Message", self.author_player_id, self.author_name)
        await view.initialize_view()
        await interaction.response.send_message(get_translation(self.user_lang, "message_placeholder"), view=view,
                                                ephemeral=True)


class Show_logs_button(discord.ui.Button):
    def __init__(self, view, player_name, custom_id, user_lang):
        super().__init__(style=discord.ButtonStyle.grey, label="Logs", emoji="📄", custom_id=custom_id)
        self.api_client = view.api_client
        self.player_name = player_name
        self.msg_view = view
        self.user_lang = user_lang

    async def callback(self, interaction: discord.Interaction):
        temp_log_file_path = await get_logs(self.api_client, self.player_name)
        if temp_log_file_path is False:
            await interaction.response.send_message(
                get_translation(self.user_lang, "no_logs_found").format(self.player_name))
        else:
            msg = get_translation(self.user_lang, "logs_for").format(self.player_name)
            await interaction.response.send_message(msg, file=discord.File(temp_log_file_path))
        self.disabled = True
        emb = interaction.message.embeds[0]
        await interaction.message.edit(embed=emb, view=self.msg_view)


class Finish_Report_Button(discord.ui.View):  # Create a class called MyView that subclasses discord.ui.View
    def __init__(self, user_lang, api_client):
        super().__init__(timeout=3600)
        self.user_lang = user_lang
        self.api_client = api_client
        self.add_buttons()

    async def on_timeout(self) -> None:
        # Step 2
        for item in self.children:
            item.disabled = True

        # Step 3
        await self.message.edit(view=self)

    def add_buttons(self):
        button_label = get_translation(self.user_lang, "report_finished")
        button = Button(label=button_label, style=discord.ButtonStyle.green, custom_id="finished_processing")
        button.callback = self.button_callback
        self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        await add_check_to_messages(interaction)
        await only_remove_buttons(interaction)
        await remove_emojis_to_messages(interaction, "👀")
        logmessage = get_translation(self.user_lang, "has_finished_report").format(interaction.user.display_name)
        await add_modlog(interaction, logmessage, player_id=False, user_lang=self.user_lang, api_client=self.api_client,
                         add_entry=True)


class ReasonSelect(discord.ui.View):

    def __init__(self, user_lang, api_client, player_id, action, author_player_id, author_name):
        super().__init__(timeout=600)
        self.user_lang = user_lang
        self.api_client = api_client
        self.player_id = player_id
        self.reasons = []
        self.action = action
        self.author_player_id = author_player_id
        self.author_name = author_name
        self.player_name = ""
        self.reason = ""

    async def initialize_view(self):
        select_label = get_translation(self.user_lang, "select_reason")
        reasons = await self.api_client.get_all_standard_message_config()
        self.reasons = reasons
        self.player_name = await get_playername(self)
        selectinst = Select(placeholder=select_label)
        selectinst.min_values = 1
        selectinst.max_values = 1
        options = []
        for x, reason in enumerate(reasons):
            if len(reason) > 100:
                reason = reason[:100]
            options.append(discord.SelectOption(label=reason, value=str(x)))
        selectinst.options = options
        selectinst.callback = self.callback
        self.add_item(selectinst)
        pass

    async def callback(self, interaction):
        data = int(interaction.data["values"][0])
        reason = self.reasons[data]
        if self.action == "Message":
            title = get_translation(self.user_lang, "message_player_modal_title").format(self.player_name)
        elif self.action == "Punish":
            title = get_translation(self.user_lang, "punish_name_player").format(self.player_name)
        elif self.action == "Kick":
            title = get_translation(self.user_lang, "kick_name_player").format(self.player_name)
        elif self.action == "Temp-Ban":
            title = get_translation(self.user_lang, "tempban_name_player").format(self.player_name)
        elif self.action == "Perma-Ban":
            title = get_translation(self.user_lang, "perma_name_player").format(self.player_name)
        await interaction.response.send_modal(
            ReasonInput(reason, self.action, self.player_id, self.user_lang, self.api_client, self.player_name,
                        self.author_player_id, self.author_name, title=title))


class ReasonInput(discord.ui.Modal):
    def __init__(self, reason, action, player_id, user_lang, api_client, player_name, author_player_id, author_name,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_lang = user_lang
        self.api_client = api_client
        self.player_id = player_id
        self.player_name = player_name
        self.reason = []
        self.action = action
        self.author_player_id = author_player_id
        self.author_name = author_name
        self.add_item(discord.ui.TextInput(label=get_translation(self.user_lang, "input_reason"),
                                           style=discord.TextStyle.long, default=self.player_name))
        self.duration = discord.ui.TextInput(
            label=get_translation(user_lang, "temp_ban_duration_label"),
            placeholder=get_translation(user_lang, "temp_ban_duration_placeholder"),
            style=discord.TextStyle.short
        )

    async def callback(self, interaction: discord.Interaction):
        self.reason = self.children[0].value
        duration = self.children[1].value
        description = get_translation(self.user_lang, "player_name") + "`" + self.player_name + "`\n"
        description = description + get_translation(self.user_lang, "steam_id") + ": `" + self.player_id + "`\n"
        description = description + get_translation(self.user_lang, "action") + "`" + self.action + "`"
        if self.action == "Temp-Ban":
            description = description + get_translation(self.user_lang,
                                                        "temp_ban_duration_label") + ": `" + self.duration + "`\n"
        description = description + get_translation(self.user_lang, "reason") + ": `" + self.reason + "`"
        embed = discord.Embed(
            title=get_translation(self.user_lang, "confirm_action"),
            description=description,
            color=discord.Colour.blurple(),  # Pycord provides a class with default colors you can choose from
        )
        await interaction.response.send_message(embeds=[embed],
                                                view=Confirm_Action_Button(self.user_lang, self.api_client,
                                                                           self.player_id, self.player_name,
                                                                           self.action, self.reason,
                                                                           self.author_player_id, self.author_name,
                                                                           duration))


class Confirm_Action_Button(discord.ui.View):  # Create a class called MyView that subclasses discord.ui.View
    def __init__(self, user_lang, api_client, player_id, player_name, action, reason, author_player_id, author_name,
                 duration=0):
        super().__init__(timeout=3600)
        self.user_lang = user_lang
        self.api_client = api_client
        self.player_id = player_id
        self.player_name = player_name
        self.action = action
        self.reason = reason
        self.author_player_id = author_player_id
        self.author_name = author_name
        self.duration = duration
        self.add_buttons()

    async def on_timeout(self) -> None:
        # Step 2
        for item in self.children:
            item.disabled = True

        # Step 3
        await self.message.edit(view=self)

    def add_buttons(self):
        button_label = get_translation(self.user_lang, "confirm")
        button = Button(label=button_label, style=discord.ButtonStyle.green, custom_id="confirm_action")
        button.callback = self.button_callback
        self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        good_result = True
        if self.action == "Message":
            message_content = self.reason
            by = interaction.user.name
            player_name = await self.player_name
            if player_name:
                success = await self.api_client.do_message_player(player_name, self.player_id, message_content)
                if success:
                    modlog = get_translation(self.user_lang, "log_message_reported").format(
                        interaction.user.display_name,
                        self.player_name,
                        message_content)
                    confirmation_message = get_translation(self.user_lang, "message_sent_successfully").format(
                        player_name,
                        message_content)
                else:
                    good_result = False
                    confirmation_message = get_translation(self.user_lang, "error_sending_message")
        elif self.action == "Punish":
            success = await self.api_client.do_punish(self.player_id, self.player_name, self.reason)
            if success:
                modlog = get_translation(self.user_lang, "log_punish").format(interaction.user.display_name,
                                                                              self.player_name, self.reason)
                confirmation_message = get_translation(self.user_lang, "punish_confirmed")
            else:
                confirmation_message = get_translation(self.user_lang, "error_action")
                good_result = False
        elif self.action == "Kick":
            if self.player_name:
                success = await self.api_client.do_kick(self.player_name, self.player_id, self.reason)
                if success:
                    confirmation_message = get_translation(self.user_lang, "player_kicked_successfully").format(
                        self.player_name)
                    modlog = get_translation(self.user_lang, "log_kick").format(interaction.user.display_name,
                                                                                await get_playername(self),
                                                                                self.reason)
                    await add_modlog(interaction, modlog, self.player_id, self.user_lang, self.api_client)
                    await add_check_to_messages(interaction)
                    message_to_author = get_translation(self.user_lang, "message_to_author_kicked").format(
                        self.player_name)
                    await self.api_client.do_message_player(self.author_name, self.author_player_id, message_to_author)
                else:
                    good_result = False
                    confirmation_message = get_translation(self.user_lang, "error_kicking_player")
            else:
                good_result = False
                confirmation_message = get_translation(self.user_lang, "player_name_not_retrieved")
        elif self.action == "Temp-Ban":
            success = await self.api_client.do_temp_ban(self.player_name, self.player_id, self.duration, self.reason)

            if success:
                confirmation_message = get_translation(self.user_lang, "player_temp_banned_successfully").format(
                    self.player_name, self.duration, self.reason)
                if self.author_player_id:
                    message_to_author = get_translation(self.user_lang, "message_to_author_temp_banned").format(
                        self.player_name)
                    await self.api_client.do_message_player(self.author_name, self.author_player_id, message_to_author)
            else:
                good_result = False
                confirmation_message = get_translation(self.user_lang, "error_temp_banning_player")
            await interaction.response.send_message(confirmation_message, ephemeral=True)

            modlog = get_translation(self.user_lang, "log_tempban").format(interaction.user.display_name,
                                                                               self.player_name,
                                                                               self.duration, self.reason)

        elif self.action == "Perma-Ban":
            await self.api_client.do_perma_ban(self.player_name, self.player_id, self.reason)
            success = await self.api_client.add_blacklist_record(self.player_id, self.reason)
            if success:
                confirmation_message = get_translation(self.user_lang, "player_perma_banned_successfully").format(
                    self.player_name, self.reason)
                modlog = get_translation(self.user_lang, "log_perma").format(interaction.user.display_name,
                                                                            await get_playername(self), self.reason)
                if self.author_player_id:
                    message_to_author = get_translation(self.user_lang, "message_to_author_perma_banned").format(
                        self.player_name)
                    await self.api_client.do_message_player(self.author_name, self.author_player_id, message_to_author)
            else:
                good_result = False
                confirmation_message = get_translation(self.user_lang, "error_perma_banning_player")

        if good_result == True:
            await interaction.response.send_message(confirmation_message, ephemeral=True)
            await add_modlog(interaction, modlog, self.player_id, self.user_lang, self.api_client)
            await add_check_to_messages(interaction)
        else:
            await interaction.response.send_message(confirmation_message, ephemeral=True)
            await add_emojis_to_messages(interaction)
            await only_remove_buttons(interaction)
