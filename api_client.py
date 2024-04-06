import aiohttp
import logging
from helpers import get_translation
from dotenv import load_dotenv

class APIClient:
    def __init__(self, base_url, api_token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.session = None

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def login(self, username, password):
        await self.create_session()
        url = f'{self.base_url}/api/login'
        data = {'username': username, 'password': password}
        async with self.session.post(url, json=data) as response:
            if response.status != 200:
                text = await response.text()
                logging.error(f"Fehler beim Login: {response.status}, Antwort: {text}")
                return False
            return True

    async def get_player_data(self, steam_id_64):
        url = f'{self.base_url}/api/get_live_game_stats'
        try:
            # Verwenden von async with zur Erstellung der ClientSession
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        # Du kannst hier entscheiden, ob du eine Fehlermeldung ausgeben möchtest
                        return None

                    return await response.json()  # Return JSON response if successful
        except Exception as e:
            # Auch hier kannst du entscheiden, ob du eine Fehlermeldung ausgeben möchtest
            return None


    async def get_detailed_players(self):
        url = f'{self.base_url}/api/get_detailed_players'
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logging.error(f"Error fetching detailed players data: {e}")
            return None

    async def do_kick(self, player, steam_id_64, user_lang):
        url = f'{self.base_url}/api/do_kick'
        reason = get_translation(user_lang, "kick_reason")
        data = {
            'player': player,
            'reason': reason,
            'by': "Admin",
            'steam_id_64': steam_id_64
        }
        logging.info(f"Sending kick request to API: {data}")

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(url, json=data) as response:
                    response_text = await response.text()
                    logging.info(f"API response for do_kick: Status {response.status}, Body {response_text}")

                    if response.status != 200:
                        logging.error(f"Fehler beim Kicken des Spielers: {response.status}, Antwort: {response_text}")
                        return False
                    return True
        except Exception as e:
            logging.error(f"Error sending kick request: {e}")
            return False

    async def get_player_by_steam_id(self, steam_id_64):
        url = f'{self.base_url}/api/player?steam_id_64={steam_id_64}'
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data and 'result' in data and 'names' in data['result']:
                        first_name_record = data['result']['names'][0]  # Änderung hier
                        return first_name_record['name']
                    return None
        except Exception as e:
            logging.error(f"Error fetching player data for Steam ID {steam_id_64}: {e}")
            return None



    async def get_player_by_id(self, steam_id_64):
        url = f'{self.base_url}/api/player?steam_id_64={steam_id_64}'
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data and 'result' in data:
                        return data['result']
                    return None
        except Exception as e:
            logging.error(f"Error fetching player data for Steam ID {steam_id_64}: {e}")
            return None



    async def get_players_fast(self):
        url = f'{self.base_url}/api/get_players_fast'
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logging.error(f"Error fetching fast players data: {e}")
            return None


    async def do_temp_ban(self, player, steam_id_64, duration_hours, reason, by):
        # Überprüfen, ob eine Sitzung existiert. Wenn nicht, erstellen Sie eine.
        if not self.session:
            await self.create_session()

        url = f'{self.base_url}/api/do_temp_ban'
        data = {
            'player': player,
            'steam_id_64': steam_id_64,
            'duration_hours': duration_hours,
            'reason': reason,
            'by': by
        }

        try:
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    # Logging der Fehlermeldung
                    response_text = await response.text()
                    logging.error(f"Fehler beim Anwenden des temporären Bans: {response.status}, Antwort: {response_text}")
                    return False
                return True
        except Exception as e:
            logging.error(f"Fehler beim Senden der Temp-Ban-Anfrage: {e}")
            return False
            
    async def do_perma_ban(self, player, steam_id_64, reason, by):
        # Überprüfen, ob eine Sitzung existiert. Wenn nicht, erstellen Sie eine.
        if not self.session:
            await self.create_session()

        url = f'{self.base_url}/api/do_perma_ban'
        data = {
            'player': player,
            'steam_id_64': steam_id_64,
            'reason': reason,
            'by': by
        }

        try:
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    # Logging der Fehlermeldung
                    response_text = await response.text()
                    logging.error(f"Fehler beim Anwenden des permanenten Bans: {response.status}, Antwort: {response_text}")
                    return False
                return True
        except Exception as e:
            logging.error(f"Fehler beim Senden der Perma-Ban-Anfrage: {e}")
            return False

    async def do_message_player(self, player, steam_id_64, message):
        url = f'{self.base_url}/api/do_message_player'
        data = {
            "player": player,
            "steam_id_64": steam_id_64,
            "message": message
        }
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(url, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logging.error(f"Error sending message to player {player}: {e}")
            return None
