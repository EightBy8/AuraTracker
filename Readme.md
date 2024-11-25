# Aura Discord Bot

This is a Discord bot that allows users to earn, track, and view their "aura" through reactions in Discord. The bot stores the aura data in a JSON file and features various commands and reactions to interact with the system. The bot is built using Python and utilizes the `discord.py` library.

## Features

- **Aura Reactions**: Users can react to messages with special emojis to earn or lose aura points.
- **Aura Leaderboard**: Displays a leaderboard of the users with the highest aura points.
- **Aura Check**: Users can check their own or others' aura points using a command.
- **Reaction Management**: The bot tracks reactions to messages and updates aura accordingly.

## Requirements

- Python 3.8 or higher
- Required libraries:
  - `discord.py`
  - `python-dotenv`
  - `colorama`

Install the necessary libraries by running:

```bash
pip install discord.py python-dotenv colorama
```

## Setup

### Environment Variables

Before running the bot, create a `.env` file in the project directory and add your Discord bot token:

```env
DISCORD_TOKEN=your_discord_bot_token
```

### Running the Bot

1. Clone or download the repository.
2. Install the required dependencies using `pip` (as mentioned above).
3. Create a `.env` file in the root directory of the project and set the `DISCORD_TOKEN` to your bot's token.
4. Run the bot by executing:

```bash
python main.py
```

### File Structure

```
.
├── main.py           # Main bot file containing bot logic and commands
├── aura.json         # File where aura data is stored
├── .env              # Environment file storing your Discord bot token
└── requirements.txt  # List of required packages (for pip install)
```

## Bot Commands

### `?aura [@member]`
Check the aura of a user. If no user is mentioned, it checks your own aura.

Example:

```
?aura @User
```

The bot will reply with the aura points of the mentioned user.

### `?leaderboard`
Displays the current leaderboard of aura points.

Example:

```
?leaderboard
```

The bot will display the top users with the most aura, with special titles for the top three:

1. **Sigma** - Highest aura.
2. **Alpha** - Second highest aura.
3. **Skibidi** - Third highest aura.

### Reactions to Update Aura

Users can react to messages with the following emojis:

- **✨ aura**: Adds 1 aura point to the user you react to.
- **💢 auradown**: Removes 1 aura point from the user you react to.

The bot will update the aura of the user who owns the message being reacted to based on the reaction.

## Aura Storage

The bot stores aura data in a JSON file (`aura.json`). This file contains a dictionary of user IDs and their corresponding aura points. Aura data is automatically saved and loaded when the bot starts.

## Logging

The bot logs key events, such as:
- Aura being updated for a user
- Aura leaderboard being requested
- Errors or warnings during execution

Logs are printed to the console with color-coded messages for easier identification.

## Contributing

Feel free to fork this repository and make pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

---

Enjoy your aura journey with the Aura Discord Bot!
