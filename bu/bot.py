import os
import re
import discord
from discord.ext import commands
from discord.ui import View

from dotenv import load_dotenv
from api_client import APIClient
from Levenshtein import distance as levenshtein_distance
from Levenshtein import jaro_winkler
from helpers import (
    remove_markdown,
    remove_bracketed_content,
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

# KI-Client (OpenAI)
from openai import AsyncOpenAI

logging.basicConfig(
    filename='bot_log.txt',
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_TOKEN = os.getenv('RCON_API_TOKEN')
ALLOWED_CHANNEL_ID = int(os.getenv('ALLOWED_CHANNEL_ID', '0'))
MAX_SERVERS = int(os.getenv('MAX_SERVERS', '1'))
user_lang = os.getenv('USER_LANG', 'en')
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("true", "1")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

class MyBot(commands.Bot):
    def __init__(self, intents):
        super().__init__(command_prefix="!", intents=intents)
        self.api_client = APIClient(None, API_TOKEN)
        self.api_base_url = None
        self.excluded_words = load_excluded_words('exclude_words.json')
        self.autorespond_trigger = load_autorespond_tigger('autorespond_trigger.json')
        self.user_lang = os.getenv('USER_LANG', 'en')
        self.ai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.dry_run = DRY_RUN
        # Dictionary to track warnings for Kick-Logik
        self.warning_counts = {}

    def extract_server_name(self, embed):
        if embed.footer:
            return embed.footer.text.strip()
        return None

    def get_api_base_url_from_server_name(self, extracted_server_name):
        for i in range(1, MAX_SERVERS + 1):
            server_name_env_var = f"SERVER_NAME_{i}"
            if os.getenv(server_name_env_var) == extracted_server_name:
                return os.getenv(f"API_BASE_URL_{i}")
        return None

    async def on_ready(self):
        print(f'{self.user} has logged in.')

    async def generate_warning_text(self, author_name: str, reason: str) -> str:
        """
        Generiert eine individuelle, witzige Verwarnung für Hell Let Loose in einer Zeile,
        maximal 200 Zeichen, unter Verwendung von ' statt " und ohne Emojis.
        """
        prompt = (
            f"- Sprich den Spieler {author_name} an "
            f"- Antworte kurz (max. 200 Zeichen) "
            f"- Verwarnung auf witzige Art "
            f"- Wir spielen das Spiel 'Hell Let Loose' "
            f"- nutze ' anstatt \" "
            f"- schreibe alles in eine Zeile ohne Emojis "
            f"- Grund: {reason}"
        )
        try:
            response = await self.ai_client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0.7
            )
            text = response.choices[0].message.content.strip()
            if len(text) > 200:
                text = text[:200].rstrip() + "…"
            return text
        except Exception as e:
            logging.error(f"Error generating warning text: {e}")
            return f"Hey {author_name}, änder dein Verhalten, sonst gibt's Ärger!"

    async def generate_tempban_text(self, author_name: str, reason: str) -> str:
        """
        Generiert eine individuelle Temp-Bann Nachricht für Hell Let Loose in einer Zeile,
        maximal 240 Zeichen, unter Verwendung von ' statt " und ohne Emojis.
        (Wird jetzt NICHT mehr genutzt für die Anzeige – stattdessen wird der warnende Text verwendet.)
        """
        prompt = (
            f"- Sprich den Spieler {author_name} an "
            f"- Antworte kurz (max. 240 Zeichen) "
            f"- Tempban (24 Std.) auf witzige Art "
            f"- Wir spielen das Spiel 'Hell Let Loose' "
            f"- nutze ' anstatt \" "
            f"- schreibe alles in eine Zeile ohne Emojis "
            f"- Grund: {reason}"
        )
        try:
            response = await self.ai_client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.7
            )
            text = response.choices[0].message.content.strip()
            if len(text) > 240:
                text = text[:240].rstrip() + "…"
            return text
        except Exception as e:
            logging.error(f"Error generating temp ban text: {e}")
            return f"Hey {author_name}, du bekommst 24h Bann – ändere sofort dein Verhalten!"

    async def generate_permaban_text(self, author_name: str, reason: str) -> str:
        """
        Generiert eine individuelle permanente Bann Nachricht für Hell Let Loose in einer Zeile,
        maximal 240 Zeichen, unter Verwendung von ' statt " und ohne Emojis.
        (Wird jetzt NICHT mehr genutzt für die Anzeige – stattdessen wird der warnende Text verwendet.)
        """
        prompt = (
            f"- Sprich den Spieler {author_name} an "
            f"- Antworte kurz (max. 240 Zeichen) "
            f"- Permaban auf witzige Art "
            f"- Wir spielen das Spiel 'Hell Let Loose' "
            f"- nutze ' anstatt \" "
            f"- deutschlandweiter Ban "
            f"- schreibe alles in eine Zeile ohne Emojis "
            f"- Grund: {reason}"
        )
        try:
            response = await self.ai_client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.7
            )
            text = response.choices[0].message.content.strip()
            if len(text) > 240:
                text = text[:240].rstrip() + "…"
            return text
        except Exception as e:
            logging.error(f"Error generating perma ban text: {e}")
            return f"Hey {author_name}, dein Verhalten ist untragbar – du bist dauerhaft aus Hell Let Loose ausgeschlossen!"

    async def generate_kick_text(self, author_name: str, reason: str) -> str:
        """
        Generiert eine individuelle Kick-Nachricht für Hell Let Loose in einer Zeile,
        maximal 240 Zeichen, unter Verwendung von ' statt " und ohne Emojis.
        """
        prompt = (
            f"- Sprich den Spieler {author_name} an "
            f"- Antworte kurz (max. 240 Zeichen) "
            f"- Kick vom Server auf witzige Art "
            f"- Wir spielen das Spiel 'Hell Let Loose' "
            f"- nutze ' anstatt \" "
            f"- schreibe alles in eine Zeile ohne Emojis "
            f"- Grund: {reason}"
        )
        try:
            response = await self.ai_client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.7
            )
            text = response.choices[0].message.content.strip()
            if len(text) > 240:
                text = text[:240].rstrip() + "…"
            return text
        except Exception as e:
            logging.error(f"Error generating kick text: {e}")
            return f"Hey {author_name}, du wirst jetzt gekickt, weil dein Verhalten nicht akzeptabel ist!"

    async def on_message(self, message):
        if not get_author_name():
            set_author_name(message.author.display_name)
        if message.author == self.user or message.channel.id != ALLOWED_CHANNEL_ID:
            return

        server_name = None
        api_base_url = None
        clean_description = None

        if message.embeds:
            embed = message.embeds[0]
            if embed.footer:
                server_name = self.extract_server_name(embed)
                if server_name:
                    api_base_url = self.get_api_base_url_from_server_name(server_name)
                    if api_base_url:
                        self.api_client.base_url = api_base_url
                        print(get_translation(user_lang, "api_login_successful").format(api_base_url))
                    else:
                        print(get_translation(user_lang, "no_api_base_url_found"))
                else:
                    print(get_translation(user_lang, "no_server_name_found"))
            if embed.description:
                clean_description = remove_markdown(embed.description)
            if embed.author and embed.author.name:
                updated_regex_pattern = r"(.+?)\s+\[(Axis|Allies)\](?:\[\w+\])?"
                match = re.match(updated_regex_pattern, embed.author.name)
                if match:
                    set_author_name(match.group(1).strip())
                    team = match.group(2).strip()
                    logging.info(f"Embed Author Name: {get_author_name()}")
                    logging.info(f"Detected team: {team}")
                else:
                    logging.error("Could not extract author name and team from the embed author. Falling back to message.author.display_name")
                    set_author_name(message.author.display_name)
            else:
                set_author_name(message.author.display_name)

        if not clean_description:
            return

        # --- Triggerwörter für Squad-Reports einfügen ---
        trigger_words = [
            "able", "baker", "charlie", "commander", "kommandant", "dog", "easy", "fox",
            "george", "how", "item", "jig", "king", "love", "mike", "negat", "option",
            "prep", "queen", "roger", "sugar", "tare", "uncle", "victor", "william",
            "x-ray", "yoke", "zebra"
        ]
        reported_parts = clean_description.split()
        if reported_parts and any(word in reported_parts for word in trigger_words):
            logging.info("Identified as unit report.")
            trigger_word_index = next(i for i, part in enumerate(reported_parts) if part in trigger_words)
            unit_name = reported_parts[trigger_word_index]
            if "commander" in reported_parts or "kommandant" in reported_parts:
                unit_name = "command"
            roles = ["officer", "spotter", "tankcommander", "armycommander"]
            logging.info(f"Unit name: {unit_name}, Roles: {roles}")
            if 'team' in locals() and team:
                await self.find_and_respond_unit(team, unit_name, roles, message)
            else:
                logging.error("Team not identified for unit report.")
            return
        # --- Ende Triggerwörter-Block ---

        kategorie, begruendung = await self.classify_report_text(clean_description)
        logging.info(f"[KI-Klassifizierung]: {kategorie} - {begruendung}")

        if kategorie == "perma":
            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            if author_player_id:
                # Verwende hier den warnenden Text, der lockerer klingt
                warning_text = await self.generate_warning_text(author_name, begruendung)
                ban_success = await self.api_client.do_perma_ban(author_name, author_player_id, begruendung)
                blacklist_success = await self.api_client.add_blacklist_record(author_player_id, begruendung)
                if ban_success and blacklist_success:
                    log_entry = f"Automatischer Perma-Bann durch KI: {begruendung}"
                    embed = discord.Embed(
                        title=get_translation(self.user_lang, "automatic_perma_ban_title") or "Automatischer Perma-Bann",
                        description=warning_text,
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Reporter (Melder)", value=author_name, inline=False)
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    embed.add_field(name=get_translation(self.user_lang, "logbook"), value=log_entry, inline=False)
                    await message.reply(embed=embed)
                else:
                    logging.error("Perma-Bann oder Blacklist-Eintrag konnte nicht ausgeführt werden.")
            else:
                logging.error("Kein passender Spieler für den Perma-Bann gefunden.")
            return

        # Behandlung von Beleidigungen:
        if kategorie == "beleidigung":
            severity, severity_reason = await self.classify_insult_severity(clean_description)
            logging.info(f"Insult severity: {severity} - {severity_reason}")
            author_name = get_author_name() or message.author.display_name
            author_player_id = await get_playerid_from_name(author_name, self.api_client)
            if severity == "warning":
                # Falls bereits eine Verwarnung vorliegt, erfolgt ein Kick
                if author_player_id in self.warning_counts and self.warning_counts[author_player_id] >= 1:
                    kick_text = await self.generate_kick_text(author_name, severity_reason)
                    if not self.dry_run:
                        kick_success = await self.api_client.do_kick(author_name, author_player_id, severity_reason)
                    else:
                        kick_success = True
                    if self.dry_run:
                        embed = discord.Embed(
                            title="DRY RUN: Kick",
                            description=f"DRY RUN: Kick für {author_name} – {severity_reason}",
                            color=discord.Color.blue()
                        )
                    else:
                        if kick_success:
                            embed = discord.Embed(
                                title="Kick",
                                description=kick_text,
                                color=discord.Color.blue()
                            )
                        else:
                            embed = discord.Embed(
                                title="Fehler",
                                description="Kick konnte nicht ausgeführt werden.",
                                color=discord.Color.blue()
                            )
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    embed.add_field(name="Begründung", value=severity_reason, inline=False)
                    if self.dry_run:
                        embed.set_footer(text="DRY RUN: Testmodus")
                    await message.reply(embed=embed)
                    self.warning_counts[author_player_id] = 0
                else:
                    warning_text = await self.generate_warning_text(author_name, severity_reason)
                    if author_player_id not in self.warning_counts:
                        self.warning_counts[author_player_id] = 0
                    self.warning_counts[author_player_id] += 1
                    embed = discord.Embed(
                        title="Verwarnung",
                        description=warning_text,
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    embed.add_field(name="Begründung", value=severity_reason, inline=False)
                    if self.dry_run:
                        embed.set_footer(text="DRY RUN: Testmodus")
                    else:
                        await self.api_client.do_message_player(author_name, author_player_id, f"{warning_text}")
                    await message.reply(embed=embed)
            elif severity == "temp_ban":
                # Verwende auch hier den warnenden Text statt des strikteren Tempban-Textes
                warning_text = await self.generate_warning_text(author_name, severity_reason)
                if not self.dry_run:
                    ban_success = await self.api_client.do_temp_ban(author_name, author_player_id, 24, severity_reason)
                if self.dry_run:
                    embed = discord.Embed(
                        title="24-Stunden-Bann",
                        description=f"DRY RUN: Temp-Bann (24h) für {author_name} – {warning_text}",
                        color=discord.Color.gold()
                    )
                else:
                    if ban_success:
                        embed = discord.Embed(
                            title="24-Stunden-Bann",
                            description=warning_text,
                            color=discord.Color.gold()
                        )
                    else:
                        embed = discord.Embed(
                            title="Fehler",
                            description="Temp-Bann konnte nicht ausgeführt werden.",
                            color=discord.Color.gold()
                        )
                embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                embed.add_field(name="Begründung", value=severity_reason, inline=False)
                if self.dry_run:
                    embed.set_footer(text="DRY RUN: Testmodus")
                await message.reply(embed=embed)
            elif severity == "perma":
                # Verwende auch hier den warnenden Text statt des strikteren Permaban-Textes
                warning_text = await self.generate_warning_text(author_name, severity_reason)
                if not self.dry_run:
                    ban_success = await self.api_client.do_perma_ban(author_name, author_player_id, severity_reason)
                    blacklist_success = await self.api_client.add_blacklist_record(author_player_id, severity_reason)
                if self.dry_run:
                    embed = discord.Embed(
                        title="Permanenter Bann",
                        description=f"DRY RUN: Perma-Bann für {author_name} – {warning_text}",
                        color=discord.Color.red()
                    )
                else:
                    if ban_success and blacklist_success:
                        embed = discord.Embed(
                            title="Permanenter Bann",
                            description=warning_text,
                            color=discord.Color.red()
                        )
                    else:
                        embed = discord.Embed(
                            title="Fehler",
                            description="Perma-Bann konnte nicht ausgeführt werden.",
                            color=discord.Color.red()
                        )
                embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                embed.add_field(name="Begründung", value=severity_reason, inline=False)
                if self.dry_run:
                    embed.set_footer(text="DRY RUN: Testmodus")
                await message.reply(embed=embed)
            return

        # Admin-Befehl bzw. Report-Unterscheidung:
        if clean_description.strip().lower().startswith("!admin"):
            admin_content = clean_description.strip()[len("!admin"):].strip()
            words = admin_content.split()
            candidate = words[0] if words else ""
            insult_severity, insult_reason = await self.classify_insult_severity(admin_content)
            if len(candidate) < 3 or insult_severity in ["temp_ban", "perma"]:
                logging.info("Admin command contains strong insulting language; processing as insult.")
                author_name = get_author_name() or message.author.display_name
                author_player_id = await get_playerid_from_name(author_name, self.api_client)
                if insult_severity == "warning":
                    warning_text = await self.generate_warning_text(author_name, insult_reason)
                    embed = discord.Embed(
                        title="Verwarnung",
                        description=warning_text,
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    embed.add_field(name="Begründung", value=insult_reason, inline=False)
                    if self.dry_run:
                        embed.set_footer(text="DRY RUN: Testmodus")
                    else:
                        await self.api_client.do_message_player(author_name, author_player_id, f"[Hell Let Loose] {warning_text}")
                    await message.reply(embed=embed)
                elif insult_severity == "temp_ban":
                    warning_text = await self.generate_warning_text(author_name, insult_reason)
                    if self.dry_run:
                        embed = discord.Embed(
                            title="24-Stunden-Bann",
                            description=f"DRY RUN: Temp-Bann (24h) für {author_name} – {warning_text}",
                            color=discord.Color.gold()
                        )
                    else:
                        ban_success = await self.api_client.do_temp_ban(author_name, author_player_id, 24, insult_reason)
                        if ban_success:
                            embed = discord.Embed(
                                title="24-Stunden-Bann",
                                description=warning_text,
                                color=discord.Color.gold()
                            )
                        else:
                            embed = discord.Embed(
                                title="Fehler",
                                description="Temp-Bann konnte nicht ausgeführt werden.",
                                color=discord.Color.gold()
                            )
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    embed.add_field(name="Begründung", value=insult_reason, inline=False)
                    if self.dry_run:
                        embed.set_footer(text="DRY RUN: Testmodus")
                    await message.reply(embed=embed)
                elif insult_severity == "perma":
                    warning_text = await self.generate_warning_text(author_name, insult_reason)
                    if self.dry_run:
                        embed = discord.Embed(
                            title="Permanenter Bann",
                            description=f"DRY RUN: Perma-Bann für {author_name} – {warning_text}",
                            color=discord.Color.red()
                        )
                    else:
                        ban_success = await self.api_client.do_perma_ban(author_name, author_player_id, insult_reason)
                        blacklist_success = await self.api_client.add_blacklist_record(author_player_id, insult_reason)
                        if ban_success and blacklist_success:
                            embed = discord.Embed(
                                title="Permanenter Bann",
                                description=warning_text,
                                color=discord.Color.red()
                            )
                        else:
                            embed = discord.Embed(
                                title="Fehler",
                                description="Perma-Bann konnte nicht ausgeführt werden.",
                                color=discord.Color.red()
                            )
                    embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)
                    embed.add_field(name="Begründung", value=insult_reason, inline=False)
                    if self.dry_run:
                        embed.set_footer(text="DRY RUN: Testmodus")
                    await message.reply(embed=embed)
                return
            else:
                reported_identifier = candidate
                logging.info(f"Admin report detected. Reported identifier extracted: {reported_identifier}")
                await self.find_and_respond_player(message, reported_identifier)
                return
        else:
            logging.info("Kein Admin-Befehl erkannt; verwende den Nachrichten-Autor als gemeldeten Spieler.")
            await self.show_punish_reporter(message, "")

    async def classify_report_text(self, text: str) -> tuple[str, str]:
        prompt = f"""
        Du bist ein Text-Klassifikationsassistent.
        Du sollst den folgenden deutschen Text in genau eine der folgenden Kategorien einteilen:
           - 'legitim'
           - 'beleidigung'
           - 'perma'
           - 'unbekannt'
        und kurz begründen, warum.
        
        Beispiel:
        Text: 'Brotskin ist ein dummer Pisser'
        => KATEGORIE: beleidigung
        => BEGRÜNDUNG: Der Autor beleidigt Brotskin.
        
        Text: '!admin able redet nicht'
        => KATEGORIE: legitim
        => BEGRÜNDUNG: Squad 'able' hat kein Mic.
        
        Text: '!admin da hat jemand Heil Hitler in den Chat geschrieben. Bitte bannen'
        => KATEGORIE: legitim
        => BEGRÜNDUNG: Der Spieler weißt den Admin darauf hin, dass ein anderer Spieler Heil Hitler in den Chat schreibt.
        
        Text: 'Heil Hitler'
        => KATEGORIE: perma
        => BEGRÜNDUNG: Rassistische Äußerungen, die hasserfüllte Inhalte verbreiten.
        Text: 'Alle Schwarzen sind minderwertig'
        => KATEGORIE: perma
        => BEGRÜNDUNG: Explizit rassistische Aussage.
        
        Gib deine Antwort im Format:
          KATEGORIE: ...
          BEGRÜNDUNG: ...
        
        Text: '{text}'
        """
        try:
            response = await self.ai_client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.0
            )
            full_answer = response.choices[0].message.content.strip()
            kategorie = "unbekannt"
            begruendung = ""
            lines = [ln.strip() for ln in full_answer.splitlines() if ln.strip()]
            for ln in lines:
                ln_low = ln.lower()
                if ln_low.startswith("kategorie:"):
                    val = ln[10:].strip().lower()
                    if "legitim" in val:
                        kategorie = "legitim"
                    elif "beleidigung" in val:
                        kategorie = "beleidigung"
                    elif "perma" in val:
                        kategorie = "perma"
                    else:
                        kategorie = "unbekannt"
                elif ln_low.startswith("begründung:") or ln_low.startswith("begruendung:"):
                    begruendung = ln.split(":", 1)[1].strip()
            return (kategorie, begruendung)
        except Exception as e:
            logging.error(f"[KI-Fehler] {e}")
            return ("unbekannt", "")

    async def classify_insult_severity(self, text: str) -> tuple[str, str]:
        prompt = f"""
        Du bist ein Schweregrad-Klassifikationsassistent für Beleidigungen im Spiel.
        Analysiere den folgenden deutschen Text und bestimme anhand dieser Kriterien, welche Maßnahme angemessen ist:
          - warning: Leichte, impulsive Beleidigungen, die lediglich eine Verwarnung rechtfertigen.
          - temp_ban: Sehr starke Beleidigungen, die einen temporären Bann (z. B. 24 Stunden) erforderlich machen.
          - perma: Extreme Beleidigungen, die das Existenzrecht leugnen oder zu Selbstverletzung auffordern – ein permanenter Bann ist hier gerechtfertigt.
        Gib deine Antwort im Format:
          SCHWEREGRAD: <warning / temp_ban / perma>
          BEGRÜNDUNG: <Kurze Begründung>
        
        Text: '{text}'
        """
        try:
            response = await self.ai_client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0.0
            )
            full_answer = response.choices[0].message.content.strip()
            severity = "warning"
            reason = ""
            lines = [ln.strip() for ln in full_answer.splitlines() if ln.strip()]
            for ln in lines:
                ln_low = ln.lower()
                if ln_low.startswith("schweregrad:"):
                    severity = ln.split(":", 1)[1].strip().lower()
                elif ln_low.startswith("begründung:") or ln_low.startswith("begruendung:"):
                    reason = ln.split(":", 1)[1].strip()
            return (severity, reason)
        except Exception as e:
            logging.error(f"[KI-Schweregrad-Fehler] {e}")
            return ("warning", "Fehler bei der Schweregradbestimmung, Standard: Verwarnung")

    async def show_punish_reporter(self, message: discord.Message, reason: str):
        fallback_name = message.author.display_name if message.author else None
        author_name = get_author_name() or fallback_name
        logging.info(f"show_punish_reporter: get_author_name() returned: {get_author_name()}, fallback: {fallback_name}")
        if not author_name:
            logging.error("Could not retrieve author_name; skipping punish_reporter.")
            return

        author_player_id = await get_playerid_from_name(author_name, self.api_client)
        if not author_player_id:
            logging.error(f"No matching player found for author: {author_name}.")
            return

        embed = discord.Embed(
            title=get_translation(self.user_lang, "reporter_insult_title"),
            description=get_translation(self.user_lang, "reporter_insult_description").format(reason=reason),
            color=discord.Color.red()
        )
        embed.add_field(name="Reporter (Melder)", value=author_name, inline=False)
        embed.add_field(name="Steam-ID", value=str(author_player_id), inline=False)

        view = Reportview(self.api_client)
        await view.add_buttons(
            user_lang=self.user_lang,
            reported_player_name=author_name,
            player_id=author_player_id,
            self_report=True,
            player_found=True
        )
        await message.reply(embed=embed, view=view)

    async def find_and_respond_unit(self, team, unit_name, roles, message):
        player_data = await self.api_client.get_detailed_players()
        if player_data is None or 'result' not in player_data or 'players' not in player_data['result']:
            logging.error("Failed to retrieve player data or player data is incomplete.")
            return

        if unit_name is None:
            unit_name = ""

        matching_player = []
        for player_id, player_info in player_data['result']['players'].items():
            player_unit_name = player_info.get('unit_name', "") or ""
            if (
                player_info['team'] and player_info['team'].lower() == team.lower()
                and player_unit_name.lower() == unit_name.lower()
                and player_info['role'].lower() in [role.lower() for role in roles]
            ):
                player_details = {
                    "name": player_info['name'],
                    "level": player_info['level'],
                    "kills": player_info['kills'],
                    "deaths": player_info['deaths'],
                    "player_id": player_info['player_id'],
                }
                matching_player = player_details
                break

        if matching_player:
            player_additional_data = await self.api_client.get_player_by_id(matching_player['player_id'])
            embed = await unitreportembed(
                player_additional_data,
                user_lang,
                unit_name,
                roles,
                team,
                matching_player
            )
            view = Reportview(self.api_client)
            await view.add_buttons(
                user_lang,
                matching_player['name'],
                player_additional_data['player_id']
            )
            response_message = await message.reply(embed=embed, view=view)
            self.last_response_message_id = response_message.id
        else:
            await self.player_not_found(message)

        logging.info(get_translation(user_lang, "response_sent").format(unit_name, ', '.join(roles), team))

    async def find_and_respond_player(self, message, reported_identifier,
                                      max_levenshtein_distance=3,
                                      jaro_winkler_threshold=0.85):
        logging.info("find_and_respond_player function called")
        logging.info(f"Searching for player report: {reported_identifier}")
        reported_identifier_cleaned = remove_bracketed_content(reported_identifier)
        potential_names = find_player_names(reported_identifier_cleaned, self.excluded_words)
        players_fast = await self.api_client.get_players()
        if not players_fast or 'result' not in players_fast:
            logging.error("Failed to retrieve players list")
            return
        max_combined_score_threshold = float(os.getenv('MAX_COMBINED_SCORE_THRESHOLD', 0.8))
        best_match = None
        best_player_data = None
        best_score = float('inf')
        for player in players_fast['result']:
            cleaned_player_name = remove_clantags(player['name'].lower())
            player_name_words = cleaned_player_name.split()
            for reported_word in potential_names:
                for player_word in player_name_words:
                    levenshtein_score = levenshtein_distance(reported_word.lower(), player_word)
                    jaro_score = jaro_winkler(reported_word.lower(), player_word)
                    if levenshtein_score <= max_combined_score_threshold or jaro_score >= jaro_winkler_threshold:
                        combined_score = levenshtein_score + (1 - jaro_score)
                        logging.info(
                            f"Scores for '{reported_word}' vs '{cleaned_player_name}': Levenshtein = {levenshtein_score}, Jaro = {jaro_score}, Combined = {combined_score}"
                        )
                        if combined_score < best_score and combined_score <= max_combined_score_threshold:
                            best_score = combined_score
                            best_match = player['name']
                            best_player_data = player
                            logging.info(f"New best match found: {best_match} with score {best_score}")
        if best_match:
            live_game_stats = await self.api_client.get_player_data(best_player_data['player_id'])
            if not live_game_stats or 'result' not in live_game_stats or 'stats' not in live_game_stats['result']:
                logging.error("Failed to retrieve live game stats for the best matching player")
                return
            player_stats = next(
                (item for item in live_game_stats['result']['stats']
                 if item['player_id'] == best_player_data['player_id']),
                None
            )
            if player_stats:
                logging.info(get_translation(user_lang, "best_match_found").format(best_match))
                player_additional_data = await self.api_client.get_player_by_id(best_player_data['player_id'])
                total_playtime_seconds = player_additional_data.get('total_playtime_seconds', 0)
                total_playtime_hours = total_playtime_seconds / 3600
                embed = await playerreportembed(
                    user_lang,
                    best_match,
                    player_stats,
                    total_playtime_hours,
                    best_player_data
                )
                response_message = await message.reply(embed=embed)
                self.last_response_message_id = response_message.id
                view = Reportview(self.api_client)
                await view.add_buttons(
                    user_lang,
                    best_match,
                    best_player_data['player_id']
                )
                await response_message.edit(view=view)
            else:
                await self.player_not_found(message)
        else:
            await self.player_not_found(message)

    async def player_not_found(self, message):
        author_name = get_author_name() or message.author.display_name
        author_player_id = await get_playerid_from_name(author_name, self.api_client)
        not_found_text = get_translation(self.user_lang, "player_not_found_auto_msg")
        if author_player_id:
            await self.api_client.do_message_player(author_name, author_player_id, not_found_text)
        embed = await player_not_found_embed(author_player_id, author_name, self.user_lang)
        view = Reportview(self.api_client)
        await view.add_buttons(
            user_lang=self.user_lang,
            reported_player_name=author_name,
            player_id=author_player_id,
            self_report=False,
            player_found=False
        )
        await message.reply(embed=embed, view=view)

    async def on_close(self):
        if self.api_client.session:
            await self.api_client.close_session()

bot = MyBot(intents)
bot.run(TOKEN)
