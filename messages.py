import discord
from discord.ui import View, Button
from helpers import get_translation, get_author_name
from modals import TempBanButton, MessagePlayerButton,  MessageReportedPlayerButton, Show_logs_button
from perma import PermaBanButton
import random


async def unitreportembed(player_additional_data, user_lang, unit_name, roles, team, player):
    embed_title = get_translation(user_lang, "players_in_unit").format(unit_name, ', '.join(roles), team)
    embed = discord.Embed(title=embed_title, color=0xd85f0e)
    total_playtime_seconds = player_additional_data.get('total_playtime_seconds', 0)
    total_playtime_hours = total_playtime_seconds / 3600
    embed.add_field(name=get_translation(user_lang, "name"), value=player["name"], inline=True)
    embed.add_field(name=get_translation(user_lang, "level"), value=player["level"], inline=True)
    embed.add_field(name=get_translation(user_lang, "total_playtime"),
                    value=f"{total_playtime_hours:.2f} " + get_translation(user_lang, "hours"), inline=True)
    embed.add_field(name=get_translation(user_lang, "kills"), value=player["kills"], inline=True)
    embed.add_field(name=get_translation(user_lang, "deaths"), value=player["deaths"], inline=True)
    embed.add_field(name=get_translation(user_lang, "steam_id"), value=player["player_id"], inline=True)
    return embed

async def player_not_found_embed(title):
    embed = discord.Embed(title=title, color=discord.Colour.magenta())
    return embed

class Unitreportview(discord.ui.View):
    def __init__(self, api_client):
        super().__init__(timeout=3600)
        self.api_client = api_client

    async def on_timeout(self) -> None:
        # Step 2
        for item in self.children:
            item.disabled = True

        # Step 3
        await self.message.edit(view=self)

    async def add_buttons(self, user_lang, player, player_additional_data, kick_button_callback, unjustified_report_click, no_action_click, manual_process):
        current_player_name = await self.api_client.get_player_by_steam_id(player['player_id'])
        button_label = get_translation(user_lang, "kick_player").format(
            current_player_name) if current_player_name else get_translation(user_lang, "kick_player_generic")
        button = Button(label=button_label, style=discord.ButtonStyle.green, custom_id=player['player_id'])
        button.player_id = player['player_id']
        button.player_name = current_player_name
        button.callback = kick_button_callback
        self.add_item(button)
        message_reported_player_button_label = get_translation(user_lang, "message_reported_player").format(
            player['name'])
        message_reported_player_button = MessageReportedPlayerButton(label=message_reported_player_button_label,
                                                                     custom_id=f"message_reported_player_{player['player_id']}",
                                                                     api_client=self.api_client,
                                                                     player_id=player['player_id'],
                                                                     user_lang=user_lang)
        self.add_item(message_reported_player_button)
        temp_ban_button_label = get_translation(user_lang, "temp_ban_player").format(player['name'])
        temp_ban_button = TempBanButton(label=temp_ban_button_label, custom_id=f"temp_ban_{player['player_id']}",
                                        api_client=self.api_client, player_id=player['player_id'],
                                        user_lang=user_lang, report_type="unit",
                                        player_additional_data=player_additional_data)
        self.add_item(temp_ban_button)
        perma_ban_button_label = get_translation(user_lang, "perma_ban_button_label").format(player['name'])
        perma_ban_button = PermaBanButton(label=perma_ban_button_label, custom_id=f"perma_ban_{player['player_id']}",
                                          api_client=self.api_client, player_id=player['player_id'],
                                          user_lang=user_lang)
        self.add_item(perma_ban_button)

        message_player_button_label = get_translation(user_lang, "message_player").format(player['name'])
        message_player_button = MessagePlayerButton(label=message_player_button_label,
                                                    custom_id=f"message_player_{player['player_id']}",
                                                    api_client=self.api_client, player_id=player['player_id'],
                                                    user_lang=user_lang)
        self.add_item(message_player_button)

        unjustified_report_button = Button(label=get_translation(user_lang, "unjustified_report"),
                                           style=discord.ButtonStyle.grey, custom_id="unjustified_report")
        unjustified_report_button.callback = unjustified_report_click
        self.add_item(unjustified_report_button)

        no_action_button = Button(label=get_translation(user_lang, "wrong_player_reported"),
                                  style=discord.ButtonStyle.grey, custom_id="no_action")
        no_action_button.callback = no_action_click
        self.add_item(no_action_button)
        show_logs_buttonobj = Show_logs_button(self, player['name'], f"show_logs_{player['player_id']}", user_lang)
        self.add_item(show_logs_buttonobj)
        manual_process_button = Button(label=get_translation(user_lang, "button_manual_process"),
                                  style=discord.ButtonStyle.grey,
                                  custom_id="manual_process")
        manual_process_button.callback = manual_process
        self.add_item(manual_process_button)


async def playerreportembed(user_lang, best_match, player_stats, total_playtime_hours, best_player_data):
    embed_title = get_translation(user_lang, "report_for_player").format(best_match)
    embed = discord.Embed(title=embed_title, color=0xd85f0e)

    realname = None
    if player_stats.get('steaminfo') and player_stats['steaminfo'].get('profile'):
        realname = player_stats['steaminfo']['profile'].get('realname')

    if realname:
        embed.add_field(name=get_translation(user_lang, "realname"), value=realname, inline=True)
    embed.add_field(name=get_translation(user_lang, "information"),
                    value=get_translation(user_lang, "check_report_match"), inline=False)
    embed.add_field(name=get_translation(user_lang, "total_playtime"),
                    value=f"{total_playtime_hours:.2f} " + get_translation(user_lang, "hours"), inline=True)
    embed.add_field(name="Steam-ID", value=best_player_data['player_id'], inline=True)
    embed.add_field(name=get_translation(user_lang, "kills"), value=player_stats['kills'], inline=True)
    embed.add_field(name=get_translation(user_lang, "kill_streak"), value=player_stats['kills_streak'], inline=True)
    embed.add_field(name=get_translation(user_lang, "kill_death_ratio"), value=player_stats['kill_death_ratio'],
                    inline=True)
    embed.add_field(name=get_translation(user_lang, "kills_per_minute"), value=player_stats['kills_per_minute'],
                    inline=True)
    embed.add_field(name=get_translation(user_lang, "deaths"), value=player_stats['deaths'], inline=True)
    embed.add_field(name=get_translation(user_lang, "teamkills"), value=player_stats['teamkills'], inline=True)
    embed.add_field(name=get_translation(user_lang, "teamkill_streak"), value=player_stats['teamkills_streak'],
                    inline=True)
    return embed

class Playerreportview(discord.ui.View):
    def __init__(self, api_client):
        super().__init__(timeout=3600)
        self.api_client = api_client

    async def on_timeout(self) -> None:
        # Step 2
        for item in self.children:
            item.disabled = True

        # Step 3
        await self.message.edit(view=self)

    async def add_buttons(self, user_lang, best_match, best_player_data, kick_button_callback, unjustified_report_click, no_action_click, manual_process):
        button_label = get_translation(user_lang, "kick_player").format(best_match)
        button = Button(label=button_label, style=discord.ButtonStyle.green, custom_id=best_player_data['player_id'])
        button.callback = kick_button_callback
        self.add_item(button)

        message_reported_player_button_label = get_translation(user_lang, "message_reported_player").format(best_match)
        message_reported_player_button = MessageReportedPlayerButton(label=message_reported_player_button_label,
                                                                     custom_id=f"message_reported_player_{best_player_data['player_id']}",
                                                                     api_client=self.api_client,
                                                                     player_id=best_player_data['player_id'],
                                                                     user_lang=user_lang)
        self.add_item(message_reported_player_button)

        temp_ban_button_label = get_translation(user_lang, "temp_ban_player").format(best_match)
        temp_ban_button = TempBanButton(label=temp_ban_button_label,
                                        custom_id=f"temp_ban_{best_player_data['player_id']}",
                                        api_client=self.api_client,
                                        player_id=best_player_data['player_id'], user_lang=user_lang,
                                        report_type="player", player_additional_data=False)
        self.add_item(temp_ban_button)

        perma_ban_button_label = get_translation(user_lang, "perma_ban_button_label").format(best_match)
        perma_ban_button = PermaBanButton(label=perma_ban_button_label,
                                          custom_id=f"perma_ban_{best_player_data['player_id']}",
                                          api_client=self.api_client, player_id=best_player_data['player_id'],
                                          user_lang=user_lang)
        self.add_item(perma_ban_button)

        message_player_button_label = get_translation(user_lang, "message_player").format(best_match)
        message_player_button = MessagePlayerButton(label=message_player_button_label,
                                                    custom_id=f"message_player_{best_player_data['player_id']}",
                                                    api_client=self.api_client, player_id=best_player_data['player_id'],
                                                    user_lang=user_lang)
        self.add_item(message_player_button)

        unjustified_report_button = Button(label=get_translation(user_lang, "unjustified_report"),
                                           style=discord.ButtonStyle.grey, custom_id="unjustified_report")
        unjustified_report_button.callback = unjustified_report_click
        self.add_item(unjustified_report_button)

        no_action_button = Button(label=get_translation(user_lang, "wrong_player_reported"),
                                  style=discord.ButtonStyle.grey,
                                  custom_id="no_action")
        no_action_button.callback = no_action_click
        self.add_item(no_action_button)
        show_logs_buttonobj = Show_logs_button(self, best_match, custom_id="logs", user_lang=user_lang)
        self.add_item(show_logs_buttonobj)
        manual_process_button = Button(label=get_translation(user_lang, "button_manual_process"),
                                  style=discord.ButtonStyle.grey,
                                  custom_id="manual_process")
        manual_process_button.callback = manual_process
        self.add_item(manual_process_button)
