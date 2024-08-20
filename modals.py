import discord
from discord.ui import Select, Button  # Import der Select Klasse
from helpers import get_translation, get_author_name, set_author_name, add_modlog, add_check_to_messages, \
    get_playername, add_emojis_to_messages, only_remove_buttons, get_logs, remove_emojis_to_messages, get_playername
import logging
import os

class PunishButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang, author_player_id, self_report):
        super().__init__(style=discord.ButtonStyle.blurple, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.author_player_id = author_player_id
        self.self_report = self_report

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = ReasonSelect(self.user_lang, self.api_client, self.player_id, "Punish", self.author_player_id, get_author_name(), interaction.message, self.self_report)
        await view.initialize_view()
        await interaction.followup.send(get_translation(self.user_lang, "select_reason"), view=view, ephemeral=True)

class KickButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang, author_player_id, author_name, self_report):
        super().__init__(style=discord.ButtonStyle.green, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.author_player_id = author_player_id
        self.author_name = author_name
        self.self_report = self_report

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = ReasonSelect(self.user_lang, self.api_client, self.player_id, "Kick", self.author_player_id, self.author_name, interaction.message, self.self_report)
        await view.initialize_view()
        await interaction.followup.send(get_translation(self.user_lang, "select_kick_reason"), view=view, ephemeral=True)

class TempBanButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang, author_player_id, self_report):
        super().__init__(style=discord.ButtonStyle.green, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.author_player_id = author_player_id
        self.self_report = self_report

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = ReasonSelect(self.user_lang, self.api_client, self.player_id, "Temp-Ban", self.author_player_id, get_author_name(), interaction.message, self.self_report)
        await view.initialize_view()
        await interaction.followup.send(get_translation(self.user_lang, "select_reason"), view=view, ephemeral=True)

class PermaBanButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang, author_player_id, self_report):
        super().__init__(style=discord.ButtonStyle.red, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.author_player_id = author_player_id
        self.self_report = self_report

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = ReasonSelect(self.user_lang, self.api_client, self.player_id, "Perma-Ban", self.author_player_id,
                            get_author_name(), interaction.message, self.self_report)
        await view.initialize_view()
        await interaction.followup.send(get_translation(self.user_lang, "select_reason"), view=view,
                                                ephemeral=True)


class MessagePlayerModal(discord.ui.Modal):
    def __init__(self, title: str, api_client, player_id, user_lang, author_name, self_report):
        super().__init__(title=get_translation(user_lang, "message_player_modal_title").format(author_name))
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.author_name = author_name  # Hinzufügen des author_name
        self.self_report = self_report

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
                modlog = get_translation(self.user_lang, "log_message").format(interaction.user.display_name,
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
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang, self_report):
        super().__init__(style=discord.ButtonStyle.grey, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.self_report = self_report

    async def callback(self, interaction: discord.Interaction):
        author_name = get_author_name()  # Hier holen wir den author_name
        modal = MessagePlayerModal(
            get_translation(self.user_lang, "message_player_modal_title"),
            self.api_client,
            self.player_id,
            self.user_lang,
            author_name, self.self_report  # Den author_name an das Modal übergeben
        )
        await interaction.response.send_modal(modal)


class MessageReportedPlayerButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang, author_player_id, author_name, self_report):
        super().__init__(style=discord.ButtonStyle.grey, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.author_player_id = author_player_id
        self.author_name = author_name
        self.self_report = self_report

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = ReasonSelect(self.user_lang, self.api_client, self.player_id, "Message", self.author_player_id, self.author_name, interaction.message, self.self_report)
        await view.initialize_view()
        await interaction.followup.send(get_translation(self.user_lang, "message_placeholder"), view=view,
                                                ephemeral=True)


class Show_logs_button(discord.ui.Button):
    def __init__(self, view, player_name, custom_id, user_lang):
        super().__init__(style=discord.ButtonStyle.grey, label="Logs", emoji="📄", custom_id=custom_id)
        self.api_client = view.api_client
        self.player_name = player_name
        self.msg_view = view
        self.user_lang = user_lang

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        temp_log_file_path = await get_logs(self.api_client, self.player_name)
        if temp_log_file_path is False:
            await interaction.response.send_message(
                get_translation(self.user_lang, "no_logs_found").format(self.player_name))
        else:
            msg = get_translation(self.user_lang, "logs_for").format(self.player_name)
            await interaction.followup.send(msg, file=discord.File(temp_log_file_path))
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

    def __init__(self, user_lang, api_client, player_id, action, author_player_id, author_name, original_report_message,
                 self_report):
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
        self.original_report_message = original_report_message
        self.self_report = self_report

    async def initialize_view(self):
        select_label = get_translation(self.user_lang, "select_reason")
        reasons = await self.api_client.get_all_standard_message_config()
        self.reasons = reasons
        self.player_name = await get_playername(self.player_id, self.api_client)
        selectinst = Select(placeholder=select_label)
        selectinst.min_values = 1
        selectinst.max_values = 1
        options = []
        options.append(discord.SelectOption(label=get_translation(self.user_lang, "own_reason"), value="empty"))
        if len(reasons) != 0:
            for x, reason in enumerate(reasons):
                if len(reason) > 100:
                    reason = reason[:100]
                options.append(discord.SelectOption(label=reason, value=str(x)))
        selectinst.options = options
        selectinst.callback = self.callback
        self.add_item(selectinst)

    async def callback(self, interaction):
        value = interaction.data["values"][0]
        if value != "empty":
            value = int(value)
            reason = self.reasons[value]
        else:
            reason = value
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
                        self.author_player_id, self.author_name, self.original_report_message, self.self_report, title=title))


class ReasonInput(discord.ui.Modal):
    def __init__(self, reason, action, player_id, user_lang, api_client, player_name, author_player_id, author_name, original_report_message,
                 self_report, *args, **kwargs) -> None:
        super().__init__(timeout=600, custom_id="reason_input", *args, **kwargs)
        self.user_lang = user_lang
        self.api_client = api_client
        self.player_id = player_id
        self.player_name = player_name
        self.action = action
        self.author_player_id = author_player_id
        self.author_name = author_name
        self.original_report_message = original_report_message
        self.self_report = self_report
        if reason != "empty":
            self.add_item(discord.ui.TextInput(label=get_translation(self.user_lang, "input_reason"),
                                               style=discord.TextStyle.long, default=reason, max_length=300))
        else:
            self.add_item(discord.ui.TextInput(label=get_translation(self.user_lang, "input_reason"),
                                               style=discord.TextStyle.long, default="_", max_length=300))
        if action == "Temp-Ban":
            self.add_item(discord.ui.TextInput(
            label=get_translation(user_lang, "temp_ban_duration_label"),
            placeholder=get_translation(user_lang, "temp_ban_duration_placeholder"),
            style=discord.TextStyle.short,
            max_length=5
            ))


    async def on_submit(self, interaction: discord.Interaction):
        self.reason = self.children[0].value
        if self.action == "Temp-Ban":
            duration = self.children[1].value
        description = get_translation(self.user_lang, "player_name").format(self.player_name) + "\n"
        description = description + get_translation(self.user_lang, "steam_id") + ": `" + self.player_id + "`\n"
        description = description + get_translation(self.user_lang, "action").format(self.action) + "\n"
        if self.action == "Temp-Ban":
            description = description + get_translation(self.user_lang,
                                                        "temp_ban_duration_label") + ": `" + duration + "`\n"
        description = description + get_translation(self.user_lang, "reason") + ": `" + self.reason + "`\n\n"
        description = description + get_translation(self.user_lang, "discard_hint")
        embed = discord.Embed(
            title=get_translation(self.user_lang, "confirm_action"),
            description=description,
            color=discord.Colour.red(),  # Pycord provides a class with default colors you can choose from
        )

        if self.action ==  "Temp-Ban" and int(duration) > 72:
            await interaction.response.send_message(embeds=[embed], ephemeral=True,
                                                    view=Confirm_Action_Button(self.user_lang, self.api_client,
                                                                               self.player_id, self.player_name,
                                                                               self.action, self.reason,
                                                                               self.author_player_id,
                                                                               self.author_name,
                                                                               self.original_report_message, self.self_report,
                                                                               duration))
        elif self.action == "Temp-Ban" and int(duration) < 72:
            await interaction.response.defer(ephemeral=False)
            await perform_action(self.action, self.reason, self.player_name, self.player_id, self.author_name, self.author_player_id, self.original_report_message, self.user_lang, self.api_client, interaction, self.self_report, duration)
        elif self.action == "Perma-Ban":
            await interaction.response.send_message(embeds=[embed], ephemeral=True,
                                                view=Confirm_Action_Button(self.user_lang, self.api_client,
                                                                           self.player_id, self.player_name,
                                                                           self.action, self.reason,
                                                                           self.author_player_id, self.author_name, self.original_report_message, self.self_report))
        else:
            await interaction.response.defer(ephemeral=False)
            await perform_action(self.action, self.reason, self.player_name, self.player_id, self.author_name,
                                 self.author_player_id, self.original_report_message, self.user_lang, self.api_client,
                                 interaction, self.self_report)

class Confirm_Action_Button(discord.ui.View):  # Create a class called MyView that subclasses discord.ui.View
    def __init__(self, user_lang, api_client, player_id, player_name, action, reason, author_player_id, author_name, original_report_message, self_report,
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
        self.self_report = self_report
        self.original_report_message = original_report_message
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
        await interaction.response.defer(ephemeral=False)
        await interaction.edit_original_response(view=None)
        await perform_action(self.action, self.reason, self.player_name, self.player_id, self.author_name, self.author_player_id, self.original_report_message, self.user_lang, self.api_client, interaction, self.self_report, self.duration)

async def perform_action(action, reason, player_name, player_id, author_name, author_player_id, original_report_message, user_lang, api_client, interaction, self_report, duration = 0):
    good_result = True
    if action == "Message":
        message_content = reason
        by = interaction.user.name
        if player_name:
            success = await api_client.do_message_player(player_name, player_id, message_content)
            if success:
                modlog = get_translation(user_lang, "log_message").format(
                    interaction.user.display_name,
                    player_name,
                    message_content, original_message=original_report_message)
                confirmation_message = get_translation(user_lang, "message_sent_successfully").format(
                    player_name,
                    message_content)
            else:
                good_result = False
                confirmation_message = get_translation(user_lang, "error_sending_message")
    elif action == "Punish":
        success = await api_client.do_punish(player_id, player_name, reason)
        if success:
            modlog = get_translation(user_lang, "log_punish").format(interaction.user.display_name,
                                                                          player_name, reason,
                                                                          original_message=original_report_message)
            confirmation_message = get_translation(user_lang, "punish_confirmed")
        else:
            confirmation_message = get_translation(user_lang, "error_action")
            good_result = False
    elif action == "Kick":
        if player_name:
            success = await api_client.do_kick(player_name, player_id, reason)
            if success:
                confirmation_message = get_translation(user_lang, "player_kicked_successfully").format(
                    player_name)
                modlog = get_translation(user_lang, "log_kick").format(interaction.user.display_name,
                                                                            await get_playername(player_id, api_client),
                                                                            reason)
                if self_report == False:
                    message_to_author = get_translation(user_lang, "message_to_author_kicked").format(
                        player_name)
                    await api_client.do_message_player(author_name, author_player_id, message_to_author)
            else:
                good_result = False
                confirmation_message = get_translation(user_lang, "error_kicking_player")
        else:
            good_result = False
            confirmation_message = get_translation(user_lang, "player_name_not_retrieved")
    elif action == "Temp-Ban":
        success = await api_client.do_temp_ban(player_name, player_id, duration, reason)

        if success:
            confirmation_message = get_translation(user_lang, "player_temp_banned_successfully").format(
                player_name, duration, reason)
            if author_player_id and self_report == False:
                message_to_author = get_translation(user_lang, "message_to_author_temp_banned").format(
                    player_name)
                await api_client.do_message_player(author_name, author_player_id, message_to_author)
        else:
            good_result = False
            confirmation_message = get_translation(user_lang, "error_temp_banning_player")

        modlog = get_translation(user_lang, "log_tempban").format(interaction.user.display_name,
                                                                       player_name,
                                                                       duration, reason)

    elif action == "Perma-Ban":
        await api_client.do_perma_ban(player_name, player_id, reason)
        success = await api_client.add_blacklist_record(player_id, reason)
        if success:
            confirmation_message = get_translation(user_lang, "player_perma_banned_successfully").format(
                player_name, reason)
            modlog = get_translation(user_lang, "log_perma").format(interaction.user.display_name,
                                                                         await get_playername(player_id, api_client), reason)
            if author_player_id and self_report == False:
                message_to_author = get_translation(user_lang, "message_to_author_perma_banned").format(
                    player_name)
                await api_client.do_message_player(author_name, author_player_id, message_to_author)
        else:
            good_result = False
            confirmation_message = get_translation(user_lang, "error_perma_banning_player")

    if good_result == True:
        await interaction.followup.send(confirmation_message, ephemeral=True)
        await add_modlog(interaction, modlog, player_id, user_lang, api_client,
                         original_message=original_report_message)
        await add_check_to_messages(interaction, original_report_message)
    else:
        await interaction.followup.send(confirmation_message, ephemeral=True)
        await add_emojis_to_messages(interaction)
        await only_remove_buttons(interaction)
