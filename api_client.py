import aiohttp
import logging
from helpers import get_translation
from dotenv import load_dotenv
import json

class APIClient:
    def __init__(self, base_url, api_token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.session = None
        self.api_version = ""

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
            text = await response.text()
            res = json.loads(text)
            self.api_version = res["version"]
            return True

    def is_v10(self):
        if self.api_version > "v10":
            return True
        else:
            return False

    async def get_player_data(self, steam_id_64):
        url = f'{self.base_url}/api/get_live_game_stats'
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    return await response.json()
        except Exception as e:
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

    async def do_kick(self, player, steam_id_64, reason, user_lang):
        if self.is_v10():
            url = f'{self.base_url}/api/kick'
            data = {
                'player_name': player,
                'reason': reason,
                'by': "Admin",
                'player_id': steam_id_64
            }
        else:
            url = f'{self.base_url}/api/do_kick'
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

# TODO: Check
    async def get_player_by_steam_id(self, steam_id_64):
        url = f'{self.base_url}/api/player?steam_id_64={steam_id_64}'
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data and 'result' in data and 'names' in data['result']:
                        first_name_record = data['result']['names'][0]
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

    async def get_players(self):
        if self.is_v10():
            url = f'{self.base_url}/api/get_players'
        else:
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
        if not self.session:
            await self.create_session()
        if self.is_v10():
            url = f'{self.base_url}/api/temp_ban'
            data = {
                'player_name': player,
                'player_id': steam_id_64,
                'duration_hours': duration_hours,
                'reason': reason,
                'by': by
            }
        else:
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
                    response_text = await response.text()
                    logging.error(f"Fehler beim Anwenden des temporären Bans: {response.status}, Antwort: {response_text}")
                    return False
                return True
        except Exception as e:
            logging.error(f"Fehler beim Senden der Temp-Ban-Anfrage: {e}")
            return False

    async def do_perma_ban(self, player, steam_id_64, reason, by):
        if not self.session:
            await self.create_session()
        if self.is_v10():
            url = f'{self.base_url}/api/perma_ban'
            data = {
                'player_name': player,
                'player_id': steam_id_64,
                'reason': reason,
                'by': by
            }
        else:
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
                    response_text = await response.text()
                    logging.error(f"Fehler beim Anwenden des permanenten Bans: {response.status}, Antwort: {response_text}")
                    return False
                return True
        except Exception as e:
            logging.error(f"Fehler beim Senden der Perma-Ban-Anfrage: {e}")
            return False

    async def do_message_player(self, player, steam_id_64, message):
        if self.is_v10():
            url = f'{self.base_url}/api/message_player'
            data = {
                "player_name": player,
                "player_id": steam_id_64,
                "message": message
            }
        else:
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

    async def get_structured_logs(self, since_min_ago, filter_action=None, filter_player=None):
        url = f'{self.base_url}/api/get_structured_logs'
        params = {
            "since_min_ago": since_min_ago,
        }

        if filter_action is not None:
            params["filter_action"] = filter_action
        if filter_player is not None:
            params["filter_player"] = filter_player

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data
        except Exception as e:
            logging.error(f"Error fetching structured logs: {e}")
            return None

    async def post_player_comment(self, steam_id_64, comment):
        if self.is_v10():
            url = f'{self.base_url}/api/post_player_comment'
            data = {
                "player_id": steam_id_64,
                "comment": comment
            }
        else:
            url = f'{self.base_url}/api/post_player_comment'
            data = {
                "steam_id_64": steam_id_64,
                "comment": comment
            }
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(url, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logging.error(f"Error posting comment '{comment}' for player {steam_id_64}: {e}")
            return None