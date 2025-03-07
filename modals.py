import discord
from discord.ui import Select, Button
from helpers import (
    get_translation, get_author_name, add_modlog, add_check_to_messages,
    add_emojis_to_messages, only_remove_buttons, get_logs, remove_emojis_to_messages,
    get_playername
)
from datetime import datetime, timedelta

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
        view = ReasonSelect(
            user_lang=self.user_lang,
            api_client=self.api_client,
            player_id=self.player_id,
            action="Message",
            author_player_id=self.author_player_id,
            author_name=self.author_name,
            original_report_message=interaction.message,
            self_report=self.self_report
        )
        await view.initialize_view()
        await interaction.followup.send(
            get_translation(self.user_lang, "message_placeholder"),
            view=view,
            ephemeral=True
        )

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
        view = ReasonSelect(
            user_lang=self.user_lang,
            api_client=self.api_client,
            player_id=self.player_id,
            action="Punish",
            author_player_id=self.author_player_id,
            author_name=get_author_name(),
            original_report_message=interaction.message,
            self_report=self.self_report
        )
        await view.initialize_view()
        await interaction.followup.send(
            get_translation(self.user_lang, "select_reason"),
            view=view,
            ephemeral=True
        )

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
        view = ReasonSelect(
            user_lang=self.user_lang,
            api_client=self.api_client,
            player_id=self.player_id,
            action="Kick",
            author_player_id=self.author_player_id,
            author_name=self.author_name,
            original_report_message=interaction.message,
            self_report=self.self_report
        )
        await view.initialize_view()
        await interaction.followup.send(
            get_translation(self.user_lang, "select_kick_reason"),
            view=view,
            ephemeral=True
        )

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
        view = ReasonSelect(
            user_lang=self.user_lang,
            api_client=self.api_client,
            player_id=self.player_id,
            action="Temp-Ban",
            author_player_id=self.author_player_id,
            author_name=get_author_name(),
            original_report_message=interaction.message,
            self_report=self.self_report
        )
        await view.initialize_view()
        await interaction.followup.send(
            get_translation(self.user_lang, "select_reason"),
            view=view,
            ephemeral=True
        )

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
        view = ReasonSelect(
            user_lang=self.user_lang,
            api_client=self.api_client,
            player_id=self.player_id,
            action="Perma-Ban",
            author_player_id=self.author_player_id,
            author_name=get_author_name(),
            original_report_message=interaction.message,
            self_report=self.self_report
        )
        await view.initialize_view()
        await interaction.followup.send(
            get_translation(self.user_lang, "select_reason"),
            view=view,
            ephemeral=True
        )

class MessagePlayerModal(discord.ui.Modal):
    """
    Modal zum direkten Schreiben an einen Spieler
    (wird über den MessagePlayerButton aufgerufen).
    """
    def __init__(self, title: str, api_client, player_id, user_lang, author_name, self_report):
        super().__init__(title=get_translation(user_lang, "message_player_modal_title").format(author_name))
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.author_name = author_name
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
        players_data = await self.api_client.get_players()
        if players_data and 'result' in players_data:
            players_list = players_data['result']
            # author_name => aus self.author_name
            author_player = next((p for p in players_list if p['name'].lower() == self.author_name.lower()), None)
            if author_player:
                # Player ID des Autors
                player_id = author_player['player_id']
                success = await self.api_client.do_message_player(self.author_name, player_id, message_content)

                if success:
                    confirmation_message = get_translation(self.user_lang, "message_sent_successfully").format(
                        self.author_name, message_content
                    )
                else:
                    confirmation_message = get_translation(self.user_lang, "error_sending_message")

                await interaction.response.send_message(confirmation_message, ephemeral=True)
                modlog = get_translation(self.user_lang, "log_message").format(
                    interaction.user.display_name, self.author_name, message_content
                )
                await add_modlog(interaction, modlog, player_id, self.user_lang, self.api_client)
                await add_check_to_messages(interaction)
            else:
                await interaction.response.send_message(
                    get_translation(self.user_lang, "author_name_not_found"),
                    ephemeral=True
                )
                await add_emojis_to_messages(interaction)
                await only_remove_buttons(interaction)
        else:
            await interaction.response.send_message(
                get_translation(self.user_lang, "error_retrieving_players"),
                ephemeral=True
            )
            await add_emojis_to_messages(interaction)
            await only_remove_buttons(interaction)

class MessagePlayerButton(discord.ui.Button):
    """Button, der direkt ein Modal öffnet, um eine Nachricht an den Spieler zu schreiben."""
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang, self_report):
        super().__init__(style=discord.ButtonStyle.grey, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang
        self.self_report = self_report

    async def callback(self, interaction: discord.Interaction):
        author_name = get_author_name()
        modal = MessagePlayerModal(
            get_translation(self.user_lang, "message_player_modal_title"),
            self.api_client,
            self.player_id,
            self.user_lang,
            author_name,
            self.self_report
        )
        await interaction.response.send_modal(modal)

class Unjustified_Report(discord.ui.Button):
    def __init__(self, author_name, author_id, user_lang, api_client):
        super().__init__(
            style=discord.ButtonStyle.grey,
            label=get_translation(user_lang, "unjustified_report"),
            custom_id="unjustified_report"
        )
        self.author_name = author_name
        self.author_id = author_id
        self.user_lang = user_lang
        self.api_client = api_client

    async def callback(self, interaction: discord.Interaction):
        new_view = discord.ui.View(timeout=None)
        await interaction.message.edit(view=new_view)
        await add_emojis_to_messages(interaction, '❌')
        confirm_message = get_translation(self.user_lang, "unjustified_report_acknowledged")
        await interaction.response.send_message(confirm_message, ephemeral=True)

        if self.author_id:
            message_to_send = get_translation(self.user_lang, "report_not_granted")
            await self.api_client.do_message_player(self.author_name, self.author_id, message_to_send)
            modlog = get_translation(self.user_lang, "log_unjustified").format(interaction.user.display_name)
            await add_modlog(interaction, modlog, False, self.user_lang, self.api_client)

class No_Action_Button(discord.ui.Button):
    def __init__(self, user_lang, api_client):
        super().__init__(
            label=get_translation(user_lang, "wrong_player_reported"),
            style=discord.ButtonStyle.grey,
            custom_id="no_action"
        )
        self.user_lang = user_lang
        self.api_client = api_client

    async def callback(self, interaction: discord.Interaction):
        await only_remove_buttons(interaction)
        modlog = get_translation(self.user_lang, "log_no-action").format(interaction.user.display_name)
        await add_modlog(interaction, modlog, False, self.user_lang, self.api_client)
        confirm_message = get_translation(self.user_lang, "no_action_performed")
        await interaction.response.send_message(confirm_message, ephemeral=True)
        await add_emojis_to_messages(interaction, '🗑')

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
                get_translation(self.user_lang, "no_logs_found").format(self.player_name)
            )
        else:
            msg = get_translation(self.user_lang, "logs_for").format(self.player_name)
            await interaction.followup.send(msg, file=discord.File(temp_log_file_path))
        self.disabled = True
        emb = interaction.message.embeds[0]
        await interaction.message.edit(embed=emb, view=self.msg_view)

class Manual_process(discord.ui.Button):
    def __init__(self, user_lang, api_client):
        super().__init__(
            label=get_translation(user_lang, "button_manual_process"),
            style=discord.ButtonStyle.grey,
            custom_id="manual_process"
        )
        self.user_lang = user_lang
        self.api_client = api_client

    async def callback(self, interaction: discord.Interaction):
        view = Finish_Report_Button(user_lang=self.user_lang, api_client=self.api_client)
        modlog = get_translation(self.user_lang, "log_manual").format(interaction.user.display_name)
        await interaction.message.edit(view=view)
        await add_modlog(interaction, modlog, False, self.user_lang, self.api_client, delete_buttons=False)
        confirm_message = get_translation(self.user_lang, "manual_process_respond")
        await interaction.response.send_message(confirm_message, ephemeral=True)
        await add_emojis_to_messages(interaction, '👀')

class Finish_Report_Button(discord.ui.View):
    def __init__(self, user_lang, api_client):
        super().__init__(timeout=3600)
        self.user_lang = user_lang
        self.api_client = api_client
        self.message = None
        self.add_buttons()

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message:
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
        await add_modlog(
            interaction,
            logmessage,
            player_id=False,
            user_lang=self.user_lang,
            api_client=self.api_client,
            add_entry=True
        )

class ReasonSelect(discord.ui.View):
    """
    Zeigt ein Select-Menü an. Entscheidet je nach self.action, ob wir "MESSAGE" oder "REASON" verwenden.
    Anschließend öffnet sich ein Modal zum Bestätigen/Anpassen des Textes.
    """
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
        # 1) Templates vom neuen Endpunkt holen
        templates = await self.api_client.get_all_message_templates()
        # 2) Je nach Aktion entweder "MESSAGE" oder "REASON" wählen
        if self.action == "Message":
            all_entries = templates.get("MESSAGE", [])
        else:
            # Für Kick, Temp-Ban, Perma-Ban, Punish => REASON
            all_entries = templates.get("REASON", [])
        self.reasons = all_entries
        self.player_name = await get_playername(self.player_id, self.api_client)
        selectinst = Select(placeholder=select_label)
        selectinst.min_values = 1
        selectinst.max_values = 1
        options = []
        # Option für "eigene Reason" oder "eigene Nachricht"
        options.append(discord.SelectOption(
            label=get_translation(self.user_lang, "own_reason"),
            value="empty"
        ))
        entries = 0
        # Aus den Objekten "title" auslesen, als Label fürs Select
        for x, obj in enumerate(self.reasons):
            title = obj.get("title", "NoTitle")
            if len(title) > 100:
                title = title[:100]
            if title and entries < 24:  # max 25 total
                options.append(discord.SelectOption(label=title, value=str(x)))
                entries += 1
        selectinst.options = options
        selectinst.callback = self.callback
        self.add_item(selectinst)

    async def callback(self, interaction):
        value = interaction.data["values"][0]
        if value != "empty":
            value_index = int(value)
            reason_obj = self.reasons[value_index]
            reason_text = reason_obj.get("content", "")
        else:
            reason_text = "empty"
        # Passenden Titel je nach Aktion
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
        else:
            title = "Reason Input"
        await interaction.response.send_modal(
            ReasonInput(
                reason_text,
                self.action,
                self.player_id,
                self.user_lang,
                self.api_client,
                self.player_name,
                self.author_player_id,
                self.author_name,
                self.original_report_message,
                self.self_report,
                title=title
            )
        )

class ReasonInput(discord.ui.Modal):
    """
    Zeigt ein Textfeld mit dem vorgeschlagenen content an.
    Bei Temp-Ban zusätzlich ein Feld für die Dauer.
    """
    def __init__(
        self, reason_text, action, player_id, user_lang, api_client, player_name, author_player_id,
        author_name, original_report_message, self_report, *args, **kwargs
    ) -> None:
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

        # TextInput für den Grund / die Nachricht
        if reason_text != "empty":
            self.add_item(discord.ui.TextInput(
                label=get_translation(self.user_lang, "input_reason"),
                style=discord.TextStyle.long,
                default=reason_text,
                max_length=300
            ))
        else:
            self.add_item(discord.ui.TextInput(
                label=get_translation(self.user_lang, "input_reason"),
                style=discord.TextStyle.long,
                default="_",
                max_length=300
            ))
        # Falls "Temp-Ban", ein weiteres Feld für die Dauer
        if action == "Temp-Ban":
            self.add_item(discord.ui.TextInput(
                label=get_translation(user_lang, "temp_ban_duration_label"),
                placeholder=get_translation(user_lang, "temp_ban_duration_placeholder"),
                style=discord.TextStyle.short,
                max_length=5
            ))

    async def on_submit(self, interaction: discord.Interaction):
        self.reason = self.children[0].value
        duration = 0

        if self.action == "Temp-Ban":
            duration = self.children[1].value

        description = (
            get_translation(self.user_lang, "player_name").format(self.player_name) + "\n" +
            get_translation(self.user_lang, "steam_id") + f": `{self.player_id}`\n" +
            get_translation(self.user_lang, "action").format(self.action) + "\n"
        )
        if self.action == "Temp-Ban":
            description += (
                get_translation(self.user_lang, "temp_ban_duration_label") +
                f": `{duration}`\n"
            )
        description += (
            get_translation(self.user_lang, "reason") + f": `{self.reason}`\n\n" +
            get_translation(self.user_lang, "discard_hint")
        )

        embed = discord.Embed(
            title=get_translation(self.user_lang, "confirm_action"),
            description=description,
            color=discord.Colour.red()
        )

        # Temp-Ban > 72h => Bestätigung
        if self.action == "Temp-Ban" and int(duration) > 72:
            await interaction.response.send_message(
                embeds=[embed],
                ephemeral=True,
                view=Confirm_Action_Button(
                    self.user_lang,
                    self.api_client,
                    self.player_id,
                    self.player_name,
                    self.action,
                    self.reason,
                    self.author_player_id,
                    self.author_name,
                    self.original_report_message,
                    self.self_report,
                    duration
                )
            )
        elif self.action == "Temp-Ban" and int(duration) <= 72:
            await interaction.response.defer(ephemeral=False)
            await perform_action(
                self.action,
                self.reason,
                self.player_name,
                self.player_id,
                self.author_name,
                self.author_player_id,
                self.original_report_message,
                self.user_lang,
                self.api_client,
                interaction,
                self.self_report,
                duration
            )
        elif self.action == "Perma-Ban":
            await interaction.response.send_message(
                embeds=[embed],
                ephemeral=True,
                view=Confirm_Action_Button(
                    self.user_lang,
                    self.api_client,
                    self.player_id,
                    self.player_name,
                    self.action,
                    self.reason,
                    self.author_player_id,
                    self.author_name,
                    self.original_report_message,
                    self.self_report
                )
            )
        else:
            # Andere Aktionen direkt
            await interaction.response.defer(ephemeral=False)
            await perform_action(
                self.action,
                self.reason,
                self.player_name,
                self.player_id,
                self.author_name,
                self.author_player_id,
                self.original_report_message,
                self.user_lang,
                self.api_client,
                interaction,
                self.self_report
            )

class Confirm_Action_Button(discord.ui.View):
    """Button, um Temp-Ban >72h oder Perma-Ban endgültig zu bestätigen."""
    def __init__(
        self, user_lang, api_client, player_id, player_name, action, reason,
        author_player_id, author_name, original_report_message, self_report, duration=0
    ):
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
        for item in self.children:
            item.disabled = True
        if hasattr(self, 'message') and self.message:
            await self.message.edit(view=self)

    def add_buttons(self):
        button_label = get_translation(self.user_lang, "confirm")
        button = Button(label=button_label, style=discord.ButtonStyle.green, custom_id="confirm_action")
        button.callback = self.button_callback
        self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await interaction.edit_original_response(view=None)
        await perform_action(
            self.action,
            self.reason,
            self.player_name,
            self.player_id,
            self.author_name,
            self.author_player_id,
            self.original_report_message,
            self.user_lang,
            self.api_client,
            interaction,
            self.self_report,
            self.duration
        )

async def perform_action(
    action, reason, player_name, player_id, author_name, author_player_id,
    original_report_message, user_lang, api_client, interaction, self_report, duration=0
):
    good_result = True

    if action == "Message":
        message_content = reason
        if player_name:
            success = await api_client.do_message_player(player_name, player_id, message_content)
            if success:
                modlog = get_translation(user_lang, "log_message").format(
                    interaction.user.display_name, player_name, message_content,
                    original_message=original_report_message
                )
                confirmation_message = get_translation(user_lang, "message_sent_successfully").format(
                    player_name, message_content
                )
            else:
                good_result = False
                confirmation_message = get_translation(user_lang, "error_sending_message")

    elif action == "Punish":
        success = await api_client.do_punish(player_id, player_name, reason)
        if success:
            modlog = get_translation(user_lang, "log_punish").format(
                interaction.user.display_name, player_name, reason,
                original_message=original_report_message
            )
            confirmation_message = get_translation(user_lang, "punish_confirmed")
        else:
            confirmation_message = get_translation(user_lang, "error_action")
            good_result = False

    elif action == "Kick":
        if player_name:
            success = await api_client.do_kick(player_name, player_id, reason)
            if success:
                confirmation_message = get_translation(user_lang, "player_kicked_successfully").format(player_name)
                modlog = get_translation(user_lang, "log_kick").format(
                    interaction.user.display_name,
                    await get_playername(player_id, api_client),
                    reason
                )
                if self_report is False:
                    message_to_author = get_translation(user_lang, "message_to_author_kicked").format(player_name)
                    await api_client.do_message_player(author_name, author_player_id, message_to_author)
            else:
                good_result = False
                confirmation_message = get_translation(user_lang, "error_kicking_player")
        else:
            good_result = False
            confirmation_message = get_translation(user_lang, "player_name_not_retrieved")

    elif action == "Temp-Ban":
        expire_time = datetime.utcnow() + timedelta(hours=int(duration))
        expires_at = expire_time.strftime("%Y-%m-%dT%H:%M")
        success = await api_client.add_blacklist_record(player_id, reason, expires_at)
        if success:
            confirmation_message = get_translation(user_lang, "player_temp_banned_successfully").format(
                player_name, duration, reason
            )
            if author_player_id and self_report is False:
                message_to_author = get_translation(user_lang, "message_to_author_temp_banned").format(player_name)
                await api_client.do_message_player(author_name, author_player_id, message_to_author)
        else:
            good_result = False
            confirmation_message = get_translation(user_lang, "error_temp_banning_player")

        modlog = get_translation(user_lang, "log_tempban").format(
            interaction.user.display_name, player_name, duration, reason
        )

    elif action == "Perma-Ban":
        success = await api_client.add_blacklist_record(player_id, reason)
        if success:
            confirmation_message = get_translation(user_lang, "player_perma_banned_successfully").format(player_name, reason)
            modlog = get_translation(user_lang, "log_perma").format(
                interaction.user.display_name,
                await get_playername(player_id, api_client),
                reason
            )
            if author_player_id and self_report is False:
                message_to_author = get_translation(user_lang, "message_to_author_perma_banned").format(player_name)
                await api_client.do_message_player(author_name, author_player_id, message_to_author)
            
            # Zusätzliche Embed mit den Spielerinformationen als Code-Block:
            # Die Labels für Grund und Beweise werden aus den Translations bezogen.
            reason_label = get_translation(user_lang, "reason")
            evidence_label = get_translation(user_lang, "evidence")
            code_block = f"```\
Name: {player_name}\n\
ID: {player_id}\n\
{reason_label}: {reason}\n\
{evidence_label}:\n\
```"
            note = get_translation(user_lang, "hack_let_loose_note")
            extra_embed = discord.Embed(
                title=get_translation(user_lang, "banned_player_data_title"),
                description=f"{code_block}\n{note}",
                color=discord.Colour.blue()
            )
            await interaction.followup.send(embed=extra_embed)
        else:
            good_result = False
            confirmation_message = get_translation(user_lang, "error_perma_banning_player")

    if not good_result:
        await interaction.followup.send(confirmation_message, ephemeral=True)
        await add_emojis_to_messages(interaction, original_report_message)
        await only_remove_buttons(interaction)
    else:
        await interaction.followup.send(confirmation_message, ephemeral=True)
        if 'modlog' in locals():
            await add_modlog(
                interaction, modlog, player_id, user_lang, api_client,
                original_message=original_report_message
            )
        await add_check_to_messages(interaction, original_report_message)
