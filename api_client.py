import aiohttp
import logging
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

    async def get_player_data(self, player_id):
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

    async def do_kick(self, player, player_id, reason):
        url = f'{self.base_url}/api/kick'
        data = {
            'player_name': player,
            'reason': reason,
            'by': "Admin",
            'player_id': player_id
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


    async def get_player_by_steam_id(self, player_id):
        url = f'{self.base_url}/api/get_player_profile?player_id={player_id}'
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
            logging.error(f"Error fetching player data for Steam ID {player_id}: {e}")
            return None

    async def get_player_by_id(self, player_id):
        url = f'{self.base_url}/api/get_player_profile?player_id={player_id}'
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data and 'result' in data:
                        return data['result']
                    return None
        except Exception as e:
            logging.error(f"Error fetching player data for Steam ID {player_id}: {e}")
            return None

    async def get_players(self):
        url = f'{self.base_url}/api/get_players'
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logging.error(f"Error fetching fast players data: {e}")
            return None

    async def do_temp_ban(self, player, player_id, duration_hours, reason):
        if not self.session:
            await self.create_session()
        url = f'{self.base_url}/api/temp_ban'
        data = {
            'player_name': player,
            'player_id': player_id,
            'duration_hours': int(duration_hours),
            'reason': reason,
            'by': "Admin"
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

    async def do_perma_ban(self, player, player_id, reason):
        if not self.session:
            await self.create_session()
        url = f'{self.base_url}/api/perma_ban'
        data = {
            'player_name': player,
            'player_id': player_id,
            'reason': reason,
            'by': 'Admin'
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

    async def add_blacklist_record(self, player_id, reason):
        if not self.session:
            await self.create_session()
        url = f'{self.base_url}/api/perma_ban'
        data = {
            'player_id': player_id,
            "blacklist_id": "0",  # Default Blacklist
            'reason': reason,
            'admin_name': 'Admin',

        }
        try:
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    response_text = await response.text()
                    logging.error(f"Fehler beim Hinzufügen des Blacklist-Eintrags: {response.status}, Antwort: {response_text}")
                    return False
                return True
        except Exception as e:
            logging.error(f"Fehler beim Senden der Perma-Ban-Anfrage: {e}")
            return False

    async def do_message_player(self, player, player_id, message):
        url = f'{self.base_url}/api/message_player'
        data = {
            "player_name": player,
            "player_id": player_id,
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

    async def post_player_comment(self, player_id, comment):
        url = f'{self.base_url}/api/post_player_comment'
        data = {
            "player_id": player_id,
            "comment": comment
        }
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(url, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logging.error(f"Error posting comment '{comment}' for player {player_id}: {e}")
            return None

    async def get_all_standard_message_config(self):
        url = f'{self.base_url}/api/get_all_standard_message_config'
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data["result"]["StandardPunishmentMessagesUserConfig"]["messages"]
        except Exception as e:
            logging.error(f"Error fetching structured logs: {e}")
            return None

    async def do_punish(self, player_id, player_name, reason):
        url = f'{self.base_url}/api/punish'
        data = {
            'player_name': player_name,
            'reason': reason,
            'by': "Admin",
            'player_id': player_id
        }
        logging.info(f"Sending punish request to API: {data}")

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(url, json=data) as response:
                    response_text = await response.text()
                    logging.info(f"API response for punish: Status {response.status}, Body {response_text}")

                    if response.status != 200:
                        logging.error(f"Fehler beim Punishen des Spielers: {response.status}, Antwort: {response_text}")
                        return False
                    return True
        except Exception as e:
            logging.error(f"Error sending punish request: {e}")