# Discord Report Bot

This Discord bot is designed to interact with users in a Discord server, responding to specific triggers and commands. It's built using Python and leverages the `discord.py` library.

## Prerequisites

- Python 3.8 or higher.
- `discord.py` library.
- Additional dependencies: `python-dotenv`.
- CRCON: [HLL RCON Tool](https://github.com/MarechJ/hll_rcon_tool)

## Installation

1. **Python**: Ensure Python 3.8 or higher is installed on your system. Download from [python.org](https://www.python.org/downloads/).

2. **Dependencies**: Install the required libraries using pip:
   ```bash
   pip install discord.py
   pip install python-dotenv
   ```

## Configuration

1. **Bot Token**: Obtain your Discord bot token from the Discord Developer Portal. Add it to your environment variables or a `.env` file in your bot's directory.

2. **API Credentials**: If your bot interacts with external APIs, include necessary credentials like API keys in your environment variables or the `.env` file.

3. **.env File Example**:
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token
   API_BASE_URL=https://example.com
   API_TOKEN=your_api_token
   USERNAME=api_username
   PASSWORD=api_password
   ALLOWED_CHANNEL_ID=DISCORD_CHANNEL_ID
   USER_LANG=en
   ```

4. **Bot Script (`bot.py`)**: Update specific configurations in `bot.py` as needed.

## Running the Bot

1. Navigate to the bot directory in a terminal.

2. Run the bot using:
   ```bash
   python bot.py
   ```

## Running Permanently with Systemctl

1. **Systemd Service File**: Create `discord_bot.service` in `/etc/systemd/system/` with appropriate content. Adjust paths as needed.

2. **Reload Systemd**:
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Enable and Start the Service**:
   ```bash
   sudo systemctl enable discord_bot.service
   sudo systemctl start discord_bot.service
   ```

4. **Check Status**:
   ```bash
   sudo systemctl status discord_bot.service
   ```

## Monitoring and Logs

- Monitor logs using:
  ```bash
  journalctl -u discord_bot.service -f
  ```

- Stop the bot:
  ```bash
  sudo systemctl stop discord_bot.service
  ```

## Adding a New Language

1. Modify `languages.json` to include translations for the new language.

2. Add a new section for the language with key-value pairs for translations.

3. Save the file and ensure the bot can load the new language.