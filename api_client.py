import aiohttp
import logging

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

    async def get_player_data(self):
        await self.create_session()
        url = f'{self.base_url}/api/get_live_game_stats'
        try:
            logging.info(f"Fetching player data from URL: {url}")  # Log the URL being hit
            async with self.session.get(url) as response:
                response_text = await response.text()  # Get response text for logging
                logging.info(f"API response received: Status {response.status}, Body {response_text}")  # Log status and body

                if response.status != 200:
                    logging.error(f"API response error: Status {response.status}, Body {response_text}")  # Log if status is not 200
                    return None

                return await response.json()  # Return JSON response if successful

        except Exception as e:
            logging.error(f"Error fetching player data: {e}")  # Log exceptions
            return None


    async def get_detailed_players(self):
        await self.create_session()
        url = f'{self.base_url}/api/get_detailed_players'
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logging.error(f"Error fetching detailed players data: {e}")
            return None

    async def do_kick(self, player, steam_id_64):
        await self.create_session()
        url = f'{self.base_url}/api/do_kick'

        # Die Daten, die an die API gesendet werden
        data = {
            'player': player,
            'reason': "Du hast gegen Serverregeln verstoßen",
            'by': "Admin",
            'steam_id_64': steam_id_64
        }

        # Loggen der zu sendenden Daten
        logging.info(f"Sending kick request to API: {data}")

        try:
            async with self.session.post(url, json=data) as response:
                response_text = await response.text()

                # Loggen der Antwort der API
                logging.info(f"API response for do_kick: Status {response.status}, Body {response_text}")

                if response.status != 200:
                    logging.error(f"Fehler beim Kicken des Spielers: {response.status}, Antwort: {response_text}")
                    return False
                return True
        except Exception as e:
            logging.error(f"Error sending kick request: {e}")
            return False

    async def get_player_by_steam_id(self, steam_id_64):
        await self.create_session()
        url = f'{self.base_url}/api/player?steam_id_64={steam_id_64}'

        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                if data and 'result' in data and 'names' in data['result']:
                    # Nehmen Sie das neueste Namenobjekt, das in der Regel das aktuellste sein sollte
                    latest_name_record = data['result']['names'][-1]
                    return latest_name_record['name']
                return None
        except Exception as e:
            logging.error(f"Error fetching player data for Steam ID {steam_id_64}: {e}")
            return None

    async def get_player_by_id(self, steam_id_64):
        await self.create_session()
        url = f'{self.base_url}/api/player?steam_id_64={steam_id_64}'

        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                if data and 'result' in data:
                    # Return the entire 'result' object
                    return data['result']
                return None
        except Exception as e:
            logging.error(f"Error fetching player data for Steam ID {steam_id_64}: {e}")
            return None


    async def get_players_fast(self):
        await self.create_session()
        url = f'{self.base_url}/api/get_players_fast'
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logging.error(f"Error fetching fast players data: {e}")
            return None

    async def do_temp_ban(self, player, steam_id_64, duration_hours, reason, by):
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
                response_text = await response.text()
                logging.info(f"API response for do_temp_ban: Status {response.status}, Body {response_text}")

                if response.status != 200:
                    logging.error(f"Fehler beim Anwenden des temporären Bans: {response.status}, Antwort: {response_text}")
                    return False
                return True
        except Exception as e:
            logging.error(f"Fehler beim Senden der Temp-Ban-Anfrage: {e}")
            return False

    async def do_message_player(self, player, steam_id_64, message):
        url = f'{self.base_url}/api/do_message_player'
        data = {
            "player": player,
            "steam_id_64": steam_id_64,
            "message": message
        }
        async with self.session.post(url, json=data) as response:
            response.raise_for_status()
            return await response.json()
