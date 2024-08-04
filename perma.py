import discord
import logging
from helpers import get_translation, get_author_name, add_modlog, add_check_to_messages, get_playername, add_warning_to_messages, only_remove_buttons

class PermaBanModal(discord.ui.Modal):
    def __init__(self, title: str, api_client, steam_id_64, user_lang):
        super().__init__(title=get_translation(user_lang, "perma_ban_modal_title"))
        self.api_client = api_client
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang

        self.reason = discord.ui.TextInput(
            label=get_translation(user_lang, "perma_ban_reason_label"),
            placeholder=get_translation(user_lang, "perma_ban_reason_placeholder"),
            style=discord.TextStyle.long,
            required=True,
            max_length=300
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason.value
        by = interaction.user.name
        
        player_name = await self.api_client.get_player_by_steam_id(self.steam_id_64)
        if player_name:
            success = await self.api_client.do_perma_ban(player_name, self.steam_id_64, reason, by)
            await self.api_client.add_blacklist_record(self.steam_id_64, reason, by)
            if success:
                confirmation_message = get_translation(self.user_lang, "player_perma_banned_successfully").format(player_name, reason)
                players_data = await self.api_client.get_players()
                if players_data and 'result' in players_data:
                    players_list = players_data['result']
                    author_name = get_author_name()
                    author_player = next((p for p in players_list if p['name'].lower() == author_name.lower()), None)
                    if author_player:
                        steam_id_64 = author_player['steam_id_64']  # Korrekte Zuweisung der Steam-ID
                        message_to_author = get_translation(self.user_lang, "message_to_author_perma_banned").format(player_name)
                        await self.api_client.do_message_player(author_name, steam_id_64, message_to_author)
            else:
                confirmation_message = get_translation(self.user_lang, "error_perma_banning_player")
                await interaction.response.send_message(confirmation_message, ephemeral=True)
                await add_warning_to_messages(interaction)
                await only_remove_buttons(interaction)
                return

            await interaction.response.send_message(confirmation_message, ephemeral=True)

            # Update the original message to disable buttons
            try:
                modlog = get_translation(self.user_lang, "log_perma").format(interaction.user.display_name,
                                                                            get_playername(self), reason)
                await add_modlog(interaction, modlog, self.steam_id_64, self.user_lang, self.api_client)
                await add_check_to_messages(interaction)
            except discord.NotFound:
                logging.error("Original message not found or uneditable.")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")

        else:
            await interaction.response.send_message(get_translation(self.user_lang, "player_name_not_retrieved"), ephemeral=True)
            await add_warning_to_messages(interaction)
            await only_remove_buttons(interaction)

class PermaBanButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, steam_id_64, user_lang):
        super().__init__(style=discord.ButtonStyle.red, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.steam_id_64 = steam_id_64
        self.user_lang = user_lang

    async def callback(self, interaction: discord.Interaction):
        modal = PermaBanModal(get_translation(self.user_lang, "perma_ban_modal_title"), self.api_client, self.steam_id_64, self.user_lang)
        await interaction.response.send_modal(modal)
