import discord
from helpers import get_translation, get_author_name, set_author_name

class TempBanModal(discord.ui.Modal):
    def __init__(self, title: str, api_client, steam_id_64, user_lang):
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
                confirmation_message = get_translation(self.user_lang, "player_temp_banned_successfully").format(player_name, duration_hours, reason)
                players_data = await self.api_client.get_players_fast()
                if players_data and 'result' in players_data:
                    players_list = players_data['result']
                    author_name = get_author_name()
                    author_player = next((p for p in players_list if p['name'].lower() == author_name.lower()), None)
                    if author_player:
                        steam_id_64 = author_player['steam_id_64']
                        message_to_author = get_translation(self.user_lang, "message_to_author_temp_banned").format(player_name)
                        await self.api_client.do_message_player(author_name, steam_id_64, message_to_author)
            else:
                confirmation_message = get_translation(self.user_lang, "error_temp_banning_player")

            await interaction.response.send_message(confirmation_message, ephemeral=True)

            # Update the original message to disable buttons
            try:
                original_message = await interaction.channel.fetch_message(interaction.message.id)
                await original_message.clear_reaction('⏳')
                await original_message.add_reaction('✅')
                new_view = discord.ui.View(timeout=None)
                for item in original_message.components:
                    if isinstance(item, discord.ui.Button):
                        new_button = discord.ui.Button(style=item.style, label=item.label, disabled=True)
                        new_view.add_item(new_button)
                await original_message.edit(view=new_view)
            except discord.NotFound:
                logging.error("Original message not found or uneditable.")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
        else:
            await interaction.response.send_message(get_translation(self.user_lang, "player_name_not_retrieved"), ephemeral=True)

class TempBanButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, steam_id_64, user_lang):
        super().__init__(style=discord.ButtonStyle.blurple, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang

    async def callback(self, interaction: discord.Interaction):
        modal = TempBanModal(get_translation(self.user_lang, "temp_ban_modal_title"), self.api_client, self.steam_id_64, self.user_lang)
        await interaction.response.send_modal(modal)
