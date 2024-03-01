# Discord Report Bot

This Discord bot is based on CRCON, a community-developed management tool for Hell Let Loose. It efficiently scans admin ping messages for reported player names and provides important information to help your admins make quick and informed decisions. It includes details such as player names, Steam IDs, number of team kills, team kill streaks, and total game time on the server.

In addition, the bot responds to reports if only squad leaders of a specific squad are reported. For example:

!admin Squad leader dog is not communicating

In response, the bot displays the specific squad leader of the reported squad. For both scenarios, the bot offers the option to either remove the player from the server with a simple click of a kick button or to leave if the report is deemed unfounded.

Additionally, the player who reported the squad leader or another player will immediately receive feedback from the Discord bot indicating whether the player was kicked or whether the report was not followed up on.

## Prerequisites

- Python 3.8 or higher.
- `discord.py` library.
- Additional dependencies: `python-dotenv`.
- [CRCON](https://github.com/MarechJ/hll_rcon_tool)

## Installation

1. **Python**: Ensure Python 3.8 or higher is installed on your system. Download from [python.org](https://www.python.org/downloads/).

2. **Dependencies**: Install the required libraries using pip:
   ```bash
   pip install discord.py
   pip install python-dotenv
   ```
3. Create a new user:
   ```bash
   sudo adduser yourusername  # Create a new user
   su - yourusername          # Switch to the new user

   ```
4. Create a Project Folder and Clone the GitHub Repository:
   ```bash
   mkdir bot-directory        # Create a new directory for the bot
   cd bot-directory           # Change to the bot directory
   git clone https://github.com/bumseb1ene/discord-reports.git  # Clone the GitHub repository
   ```


## Configuration

1. **Bot Token**: Obtain your Discord bot token from the Discord Developer Portal. Add it to your environment variables or a `.env` file in your bot's directory.

2. **API Credentials**: Add a new user to CRCON and generate a new API token

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

## Screenshots

![SquadLead-Report](https://i.imgur.com/sdjWTMQ.jpg)
![Player-Report](https://i.imgur.com/SYFRJqT.jpeg)
![Report-to-player](https://i.imgur.com/XRQ6nKX.jpeg)
