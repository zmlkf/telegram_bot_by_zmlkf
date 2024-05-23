import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import WrongResponse

# Logging setup
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKEN_NAMES = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'The work has been reviewed: the reviewer liked everything.',
    'reviewing': 'The work is being reviewed by the reviewer.',
    'rejected': 'The work has been reviewed: the reviewer has comments.'
}

TOKEN_ERROR_MESSAGE = 'Environment variables {} are not available'
TELEGRAM_MESSAGE = 'The status of the homework "{name}" has changed. {verdict}'
START_SEND_MESSAGE = 'Starting to send message'
SUCCESS_SEND_MESSAGE = 'Message sent successfully: {}'
SEND_MESSAGE_ERROR = 'Error sending message {message} Error: {error}'
REQUEST_ERROR = 'Error accessing the endpoint: {error}. Parameters: {params}'
UNEXPECTED_STATUS_CODE = 'Unexpected status code: {code}. Parameters: {params}'
ERROR_MESSAGE = ('Error in the server response: {key}: {value}. '
                 'Parameters: {params}')
REQUEST_API_MESSAGE = 'Request to the API endpoint.'
CHECK_RESPONSE_MESSAGE = 'Initializing response validation'
TYPE_ERROR_MESSAGE = 'Expected type {expected_type} for {object}. Got: {type}'
KEY_ERROR_MESSAGE = 'Dictionary: {dict} does not contain key: {key}'
UNEXPECTED_STATUS = 'Unexpected homework status: {}'
PARSE_STATUS_MESSAGE = 'Extracting homework status'
NO_UPDATES_MESSAGE = 'No updates'
ERROR_PROGRAMM_MESSAGE = 'Program error: {}'


def check_tokens():
    """
    Check the availability of environment variables.

    Raises:
        EnvironmentError: If environment variables are not available.
    """
    unavailable_tokens = [
        token for token in TOKEN_NAMES if not globals().get(token)]
    if unavailable_tokens:
        message = TOKEN_ERROR_MESSAGE.format(unavailable_tokens)
        logger.critical(message)
        raise EnvironmentError(message)


def send_message(bot, message):
    """
    Send a message via the Telegram bot.

    Args:
        bot: Telegram bot object.
        message: Message to be sent.

    Returns:
        str: Message, if it was successfully sent
    """
    try:
        logger.debug(START_SEND_MESSAGE)
        sent_message = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(SUCCESS_SEND_MESSAGE.format(message))
        return sent_message
    except telegram.TelegramError as error:
        logger.error(SEND_MESSAGE_ERROR.format(
            message=message, error=error
        ), exc_info=True)


def get_api_answer(timestamp):
    """
    Make a request to the API endpoint and return the response in JSON format.

    Args:
        timestamp: Timestamp.

    Returns:
        dict: API response converted to a Python data type.

    Raises:
        ConnectionError: Error accessing the endpoint.
        WrongResponse: If an incorrect HTTP response is received.
    """
    request_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        logger.debug(REQUEST_API_MESSAGE)
        response = requests.get(**request_params)
    except requests.RequestException as error:
        raise ConnectionError(REQUEST_ERROR.format(
            error=error, params=request_params))
    if response.status_code != HTTPStatus.OK:
        raise WrongResponse(UNEXPECTED_STATUS_CODE.format(
            code=response.status_code, params=request_params))
    response = response.json()
    for key in ('code', 'error'):
        if key in response:
            raise WrongResponse(ERROR_MESSAGE.format(
                key=key, value=response[key], params=request_params))
    return response


def check_response(response):
    """
    Validate the server response.

    Args:
        response: Server response in dictionary format.

    Raises:
        TypeError: If the object is not of the expected type.
        KeyError: If the required key is missing in the response object.
    """
    logger.debug(CHECK_RESPONSE_MESSAGE)
    if not isinstance(response, dict):
        raise TypeError(
            TYPE_ERROR_MESSAGE.format(
                object='response',
                expected_type=dict,
                type=type(response)
            )
        )
    if 'homeworks' not in response:
        raise KeyError(KEY_ERROR_MESSAGE.format(
            dict='response', key='homeworks'))
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            TYPE_ERROR_MESSAGE.format(
                object='homeworks',
                expected_type=list,
                type=type(response['homeworks'])
            )
        )


def parse_status(homework):
    """
    Extract and return the status of the homework.

    Args:
        homework: Homework information in dictionary format.

    Returns:
        str: Homework status.

    Raises:
        KeyError: Required key is missing in the homework information.
        ValueError: Unexpected homework status in the API response.
    """
    logger.debug(PARSE_STATUS_MESSAGE)
    missing_keys = [
        key for key in ('homework_name', 'status') if key not in homework
    ]
    if missing_keys:
        raise KeyError(KEY_ERROR_MESSAGE.format(
            dict='homework', key=', '.join(missing_keys)))
    status = homework['status']
    verdict = HOMEWORK_VERDICTS.get(status)
    if not verdict:
        raise ValueError(UNEXPECTED_STATUS.format(status))
    return TELEGRAM_MESSAGE.format(
        name=homework['homework_name'], verdict=verdict)


def main():
    """Main bot logic."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if homeworks:
                message = parse_status(homeworks[0])
                if message != last_message:
                    if send_message(bot, message):
                        last_message = message
                        timestamp = response.get('current_date', timestamp)
            else:
                logger.debug(NO_UPDATES_MESSAGE)
        except Exception as error:
            message = ERROR_PROGRAMM_MESSAGE.format(error)
            logger.error(message, exc_info=True)
            if message != last_message:
                if send_message(bot, message):
                    last_message = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'{__file__}.log')
        ],
        format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
    )
    main()
