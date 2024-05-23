# Homework Bot

This is a Telegram bot that checks the status of homework assignments via the Practicum by Yandex API and notifies the user of any updates. 

## Features

- Periodically checks the Practicum by Yandex API for updates on homework status.
- Sends notifications to a specified Telegram chat when there are changes in the status of a homework assignment.
- Logs all operations and errors for debugging and tracking purposes.

## Getting Started

### Prerequisites

- Python 3.7 or higher
- A Practicum by Yandex account
- A Telegram account and a bot created through BotFather
- The `python-telegram-bot` and `python-dotenv` libraries installed

### Installation

1. Clone the repository:

```sh
git clone git@github.com:zmlkf/telegram_bot_by_zmlkf.git
cd telegram_bot_by_zmlkf
```

2. Create a virtual environment and activate it:

```sh
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install the required packages:

```sh
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory of the project and add your environment variables:

```sh
PRACTICUM_TOKEN=your_practicum_token
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### Usage

To run the bot, simply execute:

```sh
python main.py
```

The bot will start running and checking for homework updates every 10 minutes. It will send a message to the specified Telegram chat if there is any change in the status of your homework.

### Logging

Logs are written to both the console and a file named `main.py.log`. The logging level is set to `DEBUG` to capture detailed information about the bot's operations.

## Code Overview

### Main Functions

- `check_tokens()`: Verifies the availability of required environment variables.
- `send_message(bot, message)`: Sends a message via the Telegram bot.
- `get_api_answer(timestamp)`: Makes a request to the Practicum by Yandex API and returns the response in JSON format.
- `check_response(response)`: Validates the server response.
- `parse_status(homework)`: Extracts and returns the status of the homework.
- `main()`: Contains the main logic of the bot, including the periodic checking of homework statuses and sending of notifications.

### Custom Exceptions

- `WrongResponse`: Raised when an incorrect HTTP response is received from the API.

### Error Handling

The bot includes comprehensive error handling to ensure that any issues are logged and, where possible, that the bot continues to run.

## Author

Roman Zemliakov  
GitHub: [zmlkf](https://github.com/zmlkf)