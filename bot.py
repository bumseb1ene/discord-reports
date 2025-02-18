import os
import re
import discord
from discord.ext import commands
from discord.ui import View

from dotenv import load_dotenv
from api_client import APIClient
from Levenshtein import distance as levenshtein_distance, jaro_winkler
from helpers import (
    remove_markdown,
    remove_bracketed_content,
    remove_player_names,
    find_player_names,
    get_translation,
    get_author_name,
    set_author_name,
    load_excluded_words,
    remove_clantags,
    add_modlog,
    add_emojis_to_messages,
    only_remove_buttons,
    get_playerid_from_name,
    load_autorespond_tigger
)
import logging
from messages import unitreportembed, playerreportembed, player_not_found_embed, Reportview

# KI-Funktionen
from ai_functions import (
    classify_comprehensive,
    generate_positive_response_text,
    generate_warning_text,
    generate_tempban_text,
    generate_permaban_text,
    generate_kick_text,
    generate_player_not_found_text
)

# -------------------------------------------------
# Logging-Konfiguration: Datei + Konsole
# -------------------------------------------------
logging.basicConfig(
    filename='bot_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

# -------------------------------------------------
# Env laden + Bot-Settings
# -------------------------------------------------
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_TOKEN = os.getenv('RCON_API_TOKEN')
ALLOWED_CHANNEL_ID = int(os.getenv('ALLOWED_CHANNEL_ID', '0'))
MAX_SERVERS = int(os.getenv('MAX_SERVERS', '1'))
user_lang = os.getenv('USER_LANG', 'en')  # Systemsprache / KI-Sprache
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("true", "1")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

# Bekannte Squad-/Unit-Namen
UNIT_KEYWORDS = [
    "able", "baker", "charlie", "commander", "dog", "easy", "fox",
    "george", "how", "item", "jig", "king", "love", "mike", "negat", "option",
    "prep", "queen", "roger", "sugar", "tare", "uncle", "victor", "william",
    "x-ray", "yoke", "zebra"
]


def combined_fuzzy_score(cand: str, target: str) -> float:
    """
    Kombinierter Wert aus Jaro-Winkler und Levenshtein:
    Score = (1 - jaroWinkler) * 2 + levenshtein
    => Je KLEINER score, desto ÄHNLICHER.
    """
    jw = jaro_winkler(cand, target)
    lv = levenshtein_distance(cand, target)
    score = (1 - jw)*2 + lv
    return score


class MyBot(commands.Bot):
    def __init__(self, intents):
        super().__init__(command_prefix="!", intents=intents)
        self.api_client = APIClient(None, API_TOKEN)
        self.api_base_url = None

        self.excluded_words = load_excluded_words('exclude_words.json')
        self.autorespond_trigger = load_autorespond_tigger('autorespond_trigger.json')
        self.user_lang = user_lang

        from openai import AsyncOpenAI
        self.ai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.dry_run = DRY_RUN
        self.warning_counts = {}
        logging.info("MyBot instance created. DRY_RUN=%s, user_lang=%s", self.dry_run, self.user_lang)

    def extract_server_name(self, embed: discord.Embed) -> str:
        """Liest den Servernamen aus dem Embed-Footer, sofern vorhanden."""
        if embed.footer:
            server_name = embed.footer.text.strip()
            logging.info("extract_server_name: Found server name in footer: '%s'", server_name)
            return server_name
        logging.info("extract_server_name: No footer in embed.")
        return ""

    def get_api_base_url_from_server_name(self, extracted_server_name: str) -> str:
        """Ermittelt aus den Umgebungsvariablen den passenden base_url zur extracted_server_name."""
        if not extracted_server_name:
            return ""

        for i in range(1, MAX_SERVERS + 1):
            server_name_env_var = f"SERVER_NAME_{i}"
            if os.getenv(server_name_env_var) == extracted_server_name:
                base_url = os.getenv(f"API_BASE_URL_{i}", "")
                logging.info("get_api_base_url_from_server_name: Found base_url=%s for server='%s'",
                             base_url, extracted_server_name)
                return base_url
        logging.info("get_api_base_url_from_server_name: No match found for '%s'", extracted_server_name)
        return ""

    async def on_ready(self):
        logging.info("Bot successfully logged in as: %s (id: %s)", self.user, self.user.id)
        print(f"{self.user} has logged in.")

    def get_effective_text(self, message: discord.Message) -> str:
        """
        Falls das Embed eine Description mit !admin enthält -> verwende das, sonst message.content.
        """
        if message.embeds and len(message.embeds) > 0:
            embed = message.embeds[0]
            if embed.description:
                desc_clean = remove_markdown(embed.description)
                # Falls description mit "!admin" beginnt, bevorzugen wir sie
                if desc_clean.lower().startswith("!admin"):
                    return desc_clean
        return message.content

    async def on_message(self, message: discord.Message):
        """
        Haupt-Logik für eingehende Nachrichten:
        - Wenn kein !admin => KI-Analyse
        - Wenn !admin <unit|player> => versuche Unit- oder Spieler-Suche
        - Sonst => fallback => KI-Analyse
        """
        if message.author == self.user:
            return
        if message.channel.id != ALLOWED_CHANNEL_ID:
            return

        logging.info("on_message: Received from '%s' content=%r", message.author, message.content)

        # Reportername cachen
        if not get_author_name():
            set_author_name(message.author.display_name)
            logging.info("on_message: set_author_name to '%s'", message.author.display_name)

        # Falls Embed => versuche Server/Team
        if message.embeds:
            embed = message.embeds[0]
            # Server-Footer => base_url
            if embed.footer:
                server_name = self.extract_server_name(embed)
                if server_name:
                    base_url = self.get_api_base_url_from_server_name(server_name)
                    if base_url:
                        self.api_client.base_url = base_url
                        logging.info("on_message: Setting self.api_client.base_url to %s", base_url)
            # Author => Team
            if embed.author and embed.author.name:
                pattern = r"(.+?)\s+\[(Axis|Allies)\](?:\[\w+\])?"
                match = re.match(pattern, embed.author.name)
                if match:
                    set_author_name(match.group(1).strip())
                    team = match.group(2).strip()
                    logging.info("on_message: Extracted name=%s, team=%s from embed.author",
                                 get_author_name(), team)
                else:
                    set_author_name(message.author.display_name)

        eff_text = self.get_effective_text(message).strip().lower()
        if not eff_text.startswith("!admin"):
            logging.info("on_message: No '!admin' => analyze_with_ai")
            await self.analyze_with_ai(message, eff_text)
        else:
            splitted = eff_text.split(None, 2)
            if len(splitted) < 2:
                # => Nur "!admin"
                logging.info("on_message: only '!admin' => fallback => KI")
                await self.analyze_with_ai(message, eff_text)
                return

            possible_unit_or_player = splitted[1]
            reason_part = splitted[2] if len(splitted) > 2 else ""
            logging.info("on_message: splitted => %s => possible_unit_or_player=%r, reason_part=%r",
                         splitted, possible_unit_or_player, reason_part)

            if possible_unit_or_player in UNIT_KEYWORDS:
                logging.info("on_message: recognized as UNIT_KEYWORD => find_and_respond_unit")
                if 'team' in locals() and team:
                    roles = ["officer", "spotter", "tankcommander", "armycommander"]
                    await self.find_and_respond_unit(team, possible_unit_or_player, roles, message)
                else:
                    logging.info("on_message: No team found => fallback => analyze_with_ai")
                    await self.analyze_with_ai(message, eff_text)
            else:
                logging.info("on_message: => find_and_respond_player")
                found = await self.find_and_respond_player(message, splitted[1:], reason_part)
                if not found:
                    logging.info("on_message: no match => fallback => analyze_with_ai")
                    await self.analyze_with_ai(message, eff_text)

    async def analyze_with_ai(self, message: discord.Message, raw_text: str = ""):
        """
        Falls kein Unit / Player gematcht => nutze KI (classify_comprehensive).
        """
        logging.info("analyze_with_ai: message.id=%s raw_text=%r", message.id, raw_text)

        if not raw_text:
            raw_text = message.content

        players_data = await self.api_client.get_players()
        if players_data and 'result' in players_data:
            valid_player_names = [p['name'] for p in players_data['result']]
        else:
            valid_player_names = []

        text_clean = remove_player_names(raw_text, valid_player_names)
        logging.info("analyze_with_ai: text_to_classify => %r", text_clean)

        category, severity, reason_text, explanation = await classify_comprehensive(
            self.ai_client,
            text_clean,
            self.user_lang
        )
        logging.info("analyze_with_ai: classification => category=%s, severity=%s, reason=%r, explanation=%r",
                     category, severity, reason_text, explanation)

        embed_response = discord.Embed(color=discord.Color.blurple())
        embed_response.add_field(name=get_translation(self.user_lang, "player_text"),
                                 value=text_clean,
                                 inline=False)

        def add_justification(embed_obj, text_just):
            embed_obj.add_field(
                name=get_translation(self.user_lang, "justification"),
                value=text_just,
                inline=False
            )
            return embed_obj

        author_name = get_author_name() or message.author.display_name
        author_player_id = await get_playerid_from_name(author_name, self.api_client)
        logging.info("analyze_with_ai: author_name=%r => steam_id=%s", author_name, author_player_id)

        # Weiterverarbeiten je nach category
        if category == "perma":
            if author_player_id:
                p_text = await generate_permaban_text(self.ai_client, author_name, reason_text, self.user_lang)
                logging.info("analyze_with_ai: permaban_text => %r", p_text)
                if not self.dry_run:
                    await self.api_client.do_perma_ban(author_name, author_player_id, p_text)
                    await self.api_client.add_blacklist_record(author_player_id, reason_text)

                embed_response.title = get_translation(self.user_lang, "permanent_ban")
                embed_response.description = p_text
                embed_response.color = discord.Color.red()
                add_justification(embed_response, reason_text)
                embed_response.add_field(name=get_translation(self.user_lang, "reporter"), value=author_name, inline=False)
                embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                await message.reply(embed=embed_response)
            return

        elif category in ["insult", "temp_ban"]:
            if not author_player_id:
                logging.info("analyze_with_ai: no author_player_id => returning")
                return

            if severity == "warning":
                # Check ob bereits 1 Warn
                warnings_so_far = self.warning_counts.get(author_player_id, 0)
                logging.info("analyze_with_ai: current warnings=%d", warnings_so_far)

                if warnings_so_far >= 1:
                    # => Kick
                    k_text = await generate_kick_text(self.ai_client, author_name, reason_text, self.user_lang)
                    embed_response.title = get_translation(self.user_lang, "kick")
                    embed_response.description = k_text
                    embed_response.color = discord.Color.blue()
                    add_justification(embed_response, reason_text)
                    embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                    if not self.dry_run:
                        await self.api_client.do_kick(author_name, author_player_id, k_text)
                    await message.reply(embed=embed_response)
                    self.warning_counts[author_player_id] = 0
                else:
                    # 1. Verwarnung
                    w_text = await generate_warning_text(self.ai_client, author_name, reason_text, self.user_lang)
                    embed_response.title = get_translation(self.user_lang, "warning")
                    embed_response.description = w_text
                    embed_response.color = discord.Color.orange()
                    add_justification(embed_response, reason_text)
                    embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                    if not self.dry_run:
                        await self.api_client.do_message_player(author_name, author_player_id, w_text)
                    self.warning_counts[author_player_id] = warnings_so_far + 1
                    await message.reply(embed=embed_response)

            elif severity == "temp_ban":
                tb_text = await generate_tempban_text(self.ai_client, author_name, reason_text, self.user_lang)
                embed_response.title = get_translation(self.user_lang, "24_hour_ban")
                embed_response.description = tb_text
                embed_response.color = discord.Color.gold()
                add_justification(embed_response, reason_text)
                embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                if not self.dry_run:
                    await self.api_client.do_temp_ban(author_name, author_player_id, 24, tb_text)
                await message.reply(embed=embed_response)

            elif severity == "perma":
                pm_text = await generate_permaban_text(self.ai_client, author_name, reason_text, self.user_lang)
                embed_response.title = get_translation(self.user_lang, "permanent_ban")
                embed_response.description = pm_text
                embed_response.color = discord.Color.red()
                add_justification(embed_response, reason_text)
                embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                if not self.dry_run:
                    await self.api_client.do_perma_ban(author_name, author_player_id, pm_text)
                    await self.api_client.add_blacklist_record(author_player_id, reason_text)
                await message.reply(embed=embed_response)

            return

        elif category == "legit":
            if author_player_id:
                pos_text = await generate_positive_response_text(self.ai_client, author_name, reason_text, self.user_lang)
                embed_response.title = get_translation(self.user_lang, "positive_response_title")
                embed_response.description = pos_text
                embed_response.color = discord.Color.green()
                embed_response.add_field(name=get_translation(self.user_lang, "steam_id"), value=str(author_player_id), inline=False)
                if not self.dry_run:
                    await self.api_client.do_message_player(author_name, author_player_id, pos_text)
                await message.reply(embed=embed_response)
            return

        else:
            logging.info("analyze_with_ai: category=%s => no specific action", category)

    async def find_and_respond_unit(self, team: str, unit_name: str, roles, message: discord.Message):
        logging.info("find_and_respond_unit: team=%r, unit_name=%r, roles=%r", team, unit_name, roles)
        data = await self.api_client.get_detailed_players()
        if not data or 'result' not in data or 'players' not in data['result']:
            logging.info("find_and_respond_unit: no detailed player data => calling player_not_found")
            await self.player_not_found(message)
            return

        matching_player = None
        for pid, info in data['result']['players'].items():
            p_unit = info.get('unit_name', "") or ""
            if (info['team'] and info['team'].lower() == team.lower() and
                p_unit.lower() == unit_name.lower() and
                info['role'].lower() in [r.lower() for r in roles]):
                matching_player = {
                    "name": info['name'],
                    "level": info['level'],
                    "kills": info['kills'],
                    "deaths": info['deaths'],
                    "player_id": info['player_id']
                }
                logging.info("find_and_respond_unit: Found match => %s", matching_player)
                break

        if matching_player:
            player_add = await self.api_client.get_player_by_id(matching_player['player_id'])
            embed = await unitreportembed(player_add, self.user_lang, unit_name, roles, team, matching_player)
            view = Reportview(self.api_client)
            await view.add_buttons(self.user_lang, matching_player['name'], matching_player['player_id'])
            resp_msg = await message.reply(embed=embed, view=view)
            self.last_response_message_id = resp_msg.id
        else:
            logging.info("find_and_respond_unit: no matching_player => calling player_not_found")
            await self.player_not_found(message)

    async def find_and_respond_player(self,
                                      message: discord.Message,
                                      splitted_args: list[str],
                                      reason_part: str,
                                      combined_threshold=3.0) -> bool:
        """
        Erzeugt Tokens aus splitted_args, bildet N-grams (bis 3 Wörter),
        vergleicht sie fuzzy mit allen PlayerNames (combined_fuzzy_score).
        Wenn best_score < combined_threshold => match.
        """
        logging.info("find_and_respond_player: splitted_args=%r, reason_part=%r, combined_threshold=%.2f",
                     splitted_args, reason_part, combined_threshold)

        full_str = " ".join(splitted_args)
        tokens = full_str.strip().split()  # => ["jackie","jackfruit","redet","nicht"]
        ngrams = []
        max_ngram_length = 3

        for start_i in range(len(tokens)):
            for length in range(1, max_ngram_length + 1):
                end_i = start_i + length
                if end_i <= len(tokens):
                    candidate = " ".join(tokens[start_i:end_i])
                    ngrams.append(candidate)

        logging.info("find_and_respond_player: tokens=%s => ngrams=%s", tokens, ngrams)

        players_list = await self.api_client.get_players()
        if not players_list or 'result' not in players_list:
            logging.info("find_and_respond_player: no player data => return False")
            return False

        best_score = float('inf')
        best_player = None
        best_candidate = ""

        for ply in players_list['result']:
            p_clean = remove_clantags(ply['name'].lower())

            for cand in ngrams:
                c_clean = remove_clantags(cand.lower())
                score = combined_fuzzy_score(c_clean, p_clean)
                logging.debug("Fuzzy: c=%r vs p_name=%r => score=%.3f", c_clean, p_clean, score)

                if score < best_score:
                    best_score = score
                    best_player = ply
                    best_candidate = cand

        if not best_player:
            logging.info("find_and_respond_player: no best_player => return False")
            return False

        logging.info("find_and_respond_player: best_player=%s => best_score=%.3f, best_candidate=%r",
                     best_player['name'], best_score, best_candidate)

        if best_score > combined_threshold:
            logging.info("find_and_respond_player: best_score=%.3f > combined_threshold=%.3f => no match",
                         best_score, combined_threshold)
            return False

        # Live stats
        live_data = await self.api_client.get_player_data(best_player['player_id'])
        if not live_data or 'result' not in live_data or 'stats' not in live_data['result']:
            logging.info("find_and_respond_player: no valid live_data => False")
            return False

        p_stats = next((x for x in live_data['result']['stats']
                        if x['player_id'] == best_player['player_id']), None)
        if not p_stats:
            logging.info("find_and_respond_player: no p_stats => False")
            return False

        # Zusätzliche Daten
        p_add = await self.api_client.get_player_by_id(best_player['player_id'])
        total_seconds = p_add.get('total_playtime_seconds', 0) if p_add else 0
        total_hours = total_seconds / 3600

        embed = await playerreportembed(self.user_lang,
                                        best_player['name'],
                                        p_stats,
                                        total_hours,
                                        best_player)
        response_msg = await message.reply(embed=embed)
        self.last_response_message_id = response_msg.id

        view = Reportview(self.api_client)
        await view.add_buttons(self.user_lang, best_player['name'], best_player['player_id'])
        await response_msg.edit(view=view)
        return True

    async def player_not_found(self, message: discord.Message):
        logging.info("player_not_found: Building fallback embed.")
        author = get_author_name() or message.author.display_name
        author_id = await get_playerid_from_name(author, self.api_client)
        not_found_txt = await generate_player_not_found_text(self.ai_client, author, self.user_lang)

        if author_id and not self.dry_run:
            msg_ok = await self.api_client.do_message_player(author, author_id, not_found_txt)
            logging.info("player_not_found: do_message_player => %s", msg_ok)

        embed = await player_not_found_embed(author_id, author, self.user_lang)
        embed.add_field(name=get_translation(self.user_lang, "ai_generated_response"),
                        value=not_found_txt,
                        inline=False)
        view = Reportview(self.api_client)
        await view.add_buttons(self.user_lang, author, author_id, self_report=False, player_found=False)
        await message.reply(embed=embed, view=view)

    async def on_close(self):
        logging.info("Bot is shutting down -> closing API client session.")
        if self.api_client.session:
            await self.api_client.close_session()


bot = MyBot(intents)
bot.run(TOKEN)
