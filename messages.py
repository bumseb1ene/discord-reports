import discord
from discord.ext import commands
from discord.ui import View, Button
from helpers import remove_markdown, remove_bracketed_content, find_player_names, get_translation, get_author_name, set_author_name, load_excluded_words, remove_clantags
from modals import TempBanButton, MessagePlayerModal, MessagePlayerButton, MessageReportedPlayerModal, MessageReportedPlayerButton, KickReasonSelect  # Importieren Sie das neue Modal und den Button
from perma import PermaBanModal, PermaBanButton
import os


async def unitreportembed(player_additional_data, unit_name, roles, team, player, logbookmessage = False):
    user_lang = os.getenv('USER_LANG', 'en')
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
    embed.add_field(name=get_translation(user_lang, "steam_id"), value=player["steam_id_64"], inline=True)
    if logbookmessage != False:
        embed.add_field(name=get_translation(user_lang, "logbook"), value=logbookmessage)
    return embed

async def unitreportview(self, user_lang, unit_name, roles, team, player, player_additional_data):
    view = View(timeout=None)
    current_player_name = await self.api_client.get_player_by_steam_id(player['steam_id_64'])
    button_label = get_translation(user_lang, "kick_player").format(
        current_player_name) if current_player_name else get_translation(user_lang, "kick_player_generic")
    button = Button(label=button_label, style=discord.ButtonStyle.green, custom_id=player['steam_id_64'])
    button.steam_id_64 = player['steam_id_64']
    button.player_name = current_player_name
    button.callback = self.button_click
    view.add_item(button)
    message_reported_player_button_label = get_translation(user_lang, "message_reported_player").format(
        player['name'])
    message_reported_player_button = MessageReportedPlayerButton(label=message_reported_player_button_label,
                                                                 custom_id=f"message_reported_player_{player['steam_id_64']}",
                                                                 api_client=self.api_client,
                                                                 steam_id_64=player['steam_id_64'],
                                                                 user_lang=user_lang)
    view.add_item(message_reported_player_button)
    temp_ban_button_label = get_translation(user_lang, "temp_ban_player").format(player['name'])
    temp_ban_button = TempBanButton(label=temp_ban_button_label, custom_id=f"temp_ban_{player['steam_id_64']}",
                                    api_client=self.api_client, steam_id_64=player['steam_id_64'],
                                    user_lang=user_lang, report_type="unit", player_additional_data=player_additional_data)
    view.add_item(temp_ban_button)
    perma_ban_button_label = get_translation(user_lang, "perma_ban_button_label").format(player['name'])
    perma_ban_button = PermaBanButton(label=perma_ban_button_label, custom_id=f"perma_ban_{player['steam_id_64']}",
                                      api_client=self.api_client, steam_id_64=player['steam_id_64'],
                                      user_lang=user_lang)
    view.add_item(perma_ban_button)

    message_player_button_label = get_translation(user_lang, "message_player").format(player['name'])
    message_player_button = MessagePlayerButton(label=message_player_button_label,
                                                custom_id=f"message_player_{player['steam_id_64']}",
                                                api_client=self.api_client, steam_id_64=player['steam_id_64'],
                                                user_lang=user_lang)
    view.add_item(message_player_button)

    unjustified_report_button = Button(label=get_translation(user_lang, "unjustified_report"),
                                       style=discord.ButtonStyle.grey, custom_id="unjustified_report")
    unjustified_report_button.callback = self.unjustified_report_click
    view.add_item(unjustified_report_button)

    no_action_button = Button(label=get_translation(user_lang, "wrong_player_reported"),
                              style=discord.ButtonStyle.grey, custom_id="no_action")
    no_action_button.callback = self.no_action_click
    view.add_item(no_action_button)
    return view


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
    embed.add_field(name="Steam-ID", value=best_player_data['steam_id_64'], inline=True)
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

async def playerreportview(self, user_lang, best_match, best_player_data):
    view = View(timeout=None)
    button_label = get_translation(user_lang, "kick_player").format(best_match)
    button = Button(label=button_label, style=discord.ButtonStyle.green, custom_id=best_player_data['steam_id_64'])
    button.callback = self.button_click
    view.add_item(button)

    message_reported_player_button_label = get_translation(user_lang, "message_reported_player").format(best_match)
    message_reported_player_button = MessageReportedPlayerButton(label=message_reported_player_button_label,
                                                                 custom_id=f"message_reported_player_{best_player_data['steam_id_64']}",
                                                                 api_client=self.api_client,
                                                                 steam_id_64=best_player_data['steam_id_64'],
                                                                 user_lang=user_lang)
    view.add_item(message_reported_player_button)

    temp_ban_button_label = get_translation(user_lang, "temp_ban_player").format(best_match)
    temp_ban_button = TempBanButton(label=temp_ban_button_label,
                                    custom_id=f"temp_ban_{best_player_data['steam_id_64']}", api_client=self.api_client,
                                    steam_id_64=best_player_data['steam_id_64'], user_lang=user_lang, report_type="player", player_additional_data=False)
    view.add_item(temp_ban_button)

    perma_ban_button_label = get_translation(user_lang, "perma_ban_button_label").format(best_match)
    perma_ban_button = PermaBanButton(label=perma_ban_button_label,
                                      custom_id=f"perma_ban_{best_player_data['steam_id_64']}",
                                      api_client=self.api_client, steam_id_64=best_player_data['steam_id_64'],
                                      user_lang=user_lang)
    view.add_item(perma_ban_button)

    message_player_button_label = get_translation(user_lang, "message_player").format(best_match)
    message_player_button = MessagePlayerButton(label=message_player_button_label,
                                                custom_id=f"message_player_{best_player_data['steam_id_64']}",
                                                api_client=self.api_client, steam_id_64=best_player_data['steam_id_64'],
                                                user_lang=user_lang)
    view.add_item(message_player_button)

    unjustified_report_button = Button(label=get_translation(user_lang, "unjustified_report"),
                                       style=discord.ButtonStyle.grey, custom_id="unjustified_report")
    unjustified_report_button.callback = self.unjustified_report_click
    view.add_item(unjustified_report_button)

    no_action_button = Button(label=get_translation(user_lang, "wrong_player_reported"), style=discord.ButtonStyle.grey,
                              custom_id="no_action")
    no_action_button.callback = self.no_action_click
    view.add_item(no_action_button)
    return view