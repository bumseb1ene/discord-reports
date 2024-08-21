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
- Additional dependencies listed in requirements.txt
- [CRCON](https://github.com/MarechJ/hll_rcon_tool)

## Installation

1. **Python**: Ensure Python 3.8 or higher is installed on your system. Download from [python.org](https://www.python.org/downloads/).

2. Create a new user:
   ```bash
   sudo adduser yourusername  # Create a new user
   su - yourusername          # Switch to the new user

   ```
3. Create a Project Folder and Clone the GitHub Repository:
   ```bash
   mkdir bot-directory        # Create a new directory for the bot
   cd bot-directory           # Change to the bot directory
   git clone https://github.com/bumseb1ene/discord-reports.git  # Clone the GitHub repository
   ```
4. **Dependencies**: Install the required libraries using pip:
   ```bash
   pip install -r requirements.txt
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
   DISCORD_BOT_TOKEN=
   USERNAME=
   PASSWORD=
   API_TOKEN=
   ALLOWED_CHANNEL_ID=
   USER_LANG=de
   MAX_COMBINED_SCORE_THRESHOLD=1.1

   API_BASE_URL_1=https://rcon1.example.com
   SERVER_NAME_1=Server 1 # Enter the "short_name" of your CRCON SETTINGS

   API_BASE_URL_2=https://rcon2.example.com
   SERVER_NAME_2=Server 2 # Enter the "short_name" of your CRCON SETTINGS

   API_BASE_URL_3=https://rcon3.example.com
   SERVER_NAME_3=Server 3 # Enter the "short_name" of your CRCON SETTINGS

   MAX_SERVERS=3
   ```

4. **Bot Script (`bot.py`)**: Update specific configurations in `bot.py` as needed.

## Running the Bot

1. Navigate to the bot directory in a terminal.

2. Run the bot using:
   ```bash
   python bot.py
   ```

## Running the Discord Bot with Docker

This guide will walk you through the steps to run the Discord Bot using Docker.

### Prerequisites
- Docker installed on your machine. [Install Docker](https://docs.docker.com/get-docker/)

### Steps to Run the Bot

1. **Clone the Repository**: First, clone the repository to your local machine.

   ```bash
   git clone https://github.com/bumseb1ene/discord-reports.git
   cd discord-reports
   ```

2. **Create a `.env` File**: Create a `.env` file in the root directory of the project with the necessary environment variables. An example structure of the `.env` file is provided as `example.env`. Modify it as needed.

3. **Build the Docker Image**: Build the Docker image from the Dockerfile present in the project directory.

   ```bash
   docker build -t discord-reports .
   ```

   This command builds a Docker image named `discord-reports`.

4. **Run the Docker Container**: Start the Docker container in detached mode with the environment file.

   ```bash
   docker run -d --env-file .env discord-reports
   ```

   The `-d` flag runs the container in the background.

5. **Check the Bot Status**: To check if the bot is running correctly, you can view the logs.

   ```bash
   docker logs [Container-ID]
   ```

   Replace `[Container-ID]` with your actual container's ID, which you can find by using `docker ps`.

6. **Stopping the Container**: If you need to stop the bot, use:

   ```bash
   docker stop [Container-ID]
   ```

### Note
- Make sure to keep your `.env` file secure as it contains sensitive information.
- The container will run in the background and automatically restart unless you manually stop it.

---

## Running Permanently with Systemctl

1. **Systemd Service File**: To ensure your Discord bot runs continuously as a service, follow these steps to create a `discord_bot.service` file in `/etc/systemd/system/`:

   a. **Create the Service File**:
      - Open a new file with a text editor (like nano or vim) with the command:
        ```bash
        sudo nano /etc/systemd/system/discord_bot.service
        ```
      - Add the following content to the file:
        ```
        [Unit]
        Description=Discord Bot Service
        After=network.target

        [Service]
        Type=simple
        User=yourusername
        WorkingDirectory=/path/to/your/bot
        ExecStart=/usr/bin/python3 /path/to/your/bot/bot.py
        Restart=on-failure

        [Install]
        WantedBy=multi-user.target
        ```
      - Replace `yourusername` with the username of the user running the bot.
      - Replace `/path/to/your/bot` with the actual path to your bot's directory.
      - If your Python binary is located elsewhere, adjust the `ExecStart` path accordingly.

   b. **Enable and Start the Service**:
      - Enable the service to start on boot with the command:
        ```bash
        sudo systemctl enable discord_bot.service
        ```
      - Start the service with:
        ```bash
        sudo systemctl start discord_bot.service
        ```

   c. **Check Status**:
      - To check the status of your bot service, use:
        ```bash
        sudo systemctl status discord_bot.service
        ```

   This setup ensures your Discord bot runs as a system service, automatically starting on boot and restarting on failure.

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
