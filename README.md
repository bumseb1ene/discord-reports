# Discord Report Bot

This Discord bot is based on CRCON, a community-developed management tool for Hell Let Loose. It efficiently scans admin ping messages for reported player names and provides important information to help your admins make quick and informed decisions. It includes details such as player names, Steam IDs, number of team kills, team kill streaks, and total game time on the server.

In addition, the bot responds to reports if only squad leaders of a specific squad are reported. For example:

!admin Squadleader dog not communicating

In response, the bot displays the specific squad leader of the reported squad. For both scenarios, the bot offers the option to either remove the player from the server with a simple click of a kick button or not to kick him if the report is deemed unfounded.

In addition, the player who reported the group leader or another player will immediately receive feedback from the Discord bot as to whether the player was kicked or whether the report was not investigated.

Important: The bot may sometimes provide incorrect messages as the input depends on the player.

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

1. **Bot Token and Privileged Gateway Intents**:
   
   To get your Discord bot token and enable the necessary Privileged Gateway Intents, follow these steps:

   a. **Create a Discord Bot Account**:
      - Go to the [Discord Developer Portal](https://discord.com/developers/applications).
      - Log in with your Discord account.
      - Click on the "New Application" button.
      - Give your application a name and click "Create".

   b. **Set up a Bot User**:
      - In your application settings, click on the “Bot” tab in the sidebar.
      - Click the "Add Bot" button and confirm by clicking "Yes, do it!".
      - Customize your bot by giving it a name and an avatar if desired.

   c. **Enable Privileged Gateway Intents**:
      - Still on the “Bot” tab, scroll down to find the “Privileged Gateway Intents” section.
      - Enable the intents that your bot requires. For most bots, enabling the following intents is necessary:
        - `Presence Intent`: Allows the bot to receive presence updates (online status, game playing, etc.).
        - `Server Members Intent`: Allows the bot to receive updates about server members (join, leave, update, etc.).
        - `Message Content Intent`: Required to receive notifications about new messages and message content in text channels.
      - Note that enabling these intents might require additional verification steps depending on your bot's use case and the number of servers it's in.

   d. **Configure Bot Permissions**:
      - Under “Bot Permissions”, select the necessary permissions your bot requires to function. For this bot, you should consider the following permissions:
        - `Send Messages`: Allows the bot to send messages in channels.
        - `Read Message History`: Enables the bot to read previous messages in a channel.
        - `Add Reactions`: Allows the bot to add reactions to messages.
        - `Manage Messages`: If the bot needs to edit or delete messages.
        - `Embed Links`: Allows the bot to use embedded links in messages.
        - `View Channel`: Enables the bot to see and access channels.
      - Be mindful of the permissions you choose, as granting overly permissive or administrative permissions can pose a security risk.

   e. **Get the Bot Token**:
      - Under the “Token” section, click on the “Copy” button to copy your bot’s token.
      - Be sure to keep this token secure and never share it publicly, as it allows control over your bot.

   f. **Add the Token to Your Bot's Configuration**:
      - Add the copied token to your environment variables or a `.env` file in your bot's directory:
        ```
        DISCORD_BOT_TOKEN=your_discord_bot_token
        ```
      - Replace `your_discord_bot_token` with the token you copied.

   This token is essential for your bot to log in and connect to the Discord servers. Additionally, enabling the correct Privileged Gateway Intents is crucial for your bot to function properly.

2. **Using CRCON API**: Add a new user to CRCON and generate a new API token by following these steps:

   a. **Access Your CRCON Admin Interface**:
      - Navigate to your CRCON admin interface. For example: `https://rcon.xyz.com/admin`.
   
   b. **Create a New User and Set a Password**:
      - Create a new user and assign a password. Ensure that this user has sufficient rights, including the ability to kick and ban players.
   
   c. **Generate an API Key**:
      - Return to the landing page and click on 'Add' under the Django API Key section.
      - Select the user you created and copy the generated API Key.
      - Example of an API Key: `493ac44e-5543-4e58-9359-c08943992c6e`
   
   d. **Add the API Key to Your `.env` File**:
      - Add this API Key to your `.env` file in your bot's directory. It should look something like this:
        ```
        API_TOKEN=your_api_token
        ```
      - Replace `your_api_token` with the API Key you copied.
   
   This API key is crucial for your bot to communicate with the CRCON system and perform administrative actions like kicking or banning players.


3. **.env File Example**:
   ```
   DISCORD_BOT_TOKEN=your_discord_bot_token
   API_BASE_URL=https://rcon.xyz.com 
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
