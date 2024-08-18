import discord
import logging
from helpers import get_translation, get_author_name, add_modlog, add_check_to_messages, get_playername, add_emojis_to_messages, only_remove_buttons

class PermaBanButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, api_client, player_id, user_lang):
        super().__init__(style=discord.ButtonStyle.red, label=label, custom_id=custom_id)
        self.api_client = api_client
        self.player_id = player_id
        self.user_lang = user_lang

    async def callback(self, interaction: discord.Interaction):
        # ToDO: Replace with Select Reason
        #modal = PermaBanModal(get_translation(self.user_lang, "perma_ban_modal_title"), self.api_client, self.player_id, self.user_lang)
        #await interaction.response.send_modal(modal)
        pass