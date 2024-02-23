import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import WrongResponse

# Настройка логгирования
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKEN_NAMES = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

TOKEN_ERROR_MESSAGE = 'Переменные {} недоступны'
TELEGRAM_MESSAGE = 'Изменился статус проверки работы "{name}". {verdict}'
START_SEND_MESSAGE = 'Начало отправки сообщения'
SUCCESS_SEND_MESSAGE = 'Успешная отправка сообщения: {}'
SEND_MESSAGE_ERROR = 'Ошибка отправки сообщения {message} Ошибка: {error}'
REQUEST_ERROR = 'Ошибка при доступе к эндпоинту: {error}. Параметры: {params}'
UNEXPECTED_STATUS_CODE = 'Некорректный статут код: {code}. Параметры: {params}'
ERROR_MESSAGE = ('Ошибка в ответе от сервера: {key}: {value}. '
                 'Параметры: {params}')
REQUEST_API_MESSAGE = 'Запрос к эндпоинту API-сервиса.'
CHECK_RESPONSE_MESSAGE = 'Иницилизация проверки ответа сервера'
TYPE_ERROR_MESSAGE = 'Ожидаемый тип {object}: {expected_type}. Тип: {type}'
KEY_ERROR_MESSAGE = 'Словарь: {dict} не содержит ключ: {key}'
UNEXPECTED_STATUS = 'Неожиданный статус домашней работы: {}'
PARSE_STATUS_MESSAGE = 'Извлечение статуса домашней работы'
NO_UPDATES_MESSAGE = 'Обновлений нет'
ERROR_PROGRAMM_MESSAGE = 'Сбой в работе программы: {}'


def check_tokens():
    """
    Проверка доступности переменных окружения.

    Raises:
        EnvironmentError: Если переменные окружения недоступны.
    """
    unavailable_tokens = [
        token for token in TOKEN_NAMES if not globals().get(token)]
    if unavailable_tokens:
        message = TOKEN_ERROR_MESSAGE.format(unavailable_tokens)
        logger.critical(message)
        raise EnvironmentError(message)


def send_message(bot, message):
    """
    Отправка сообщения через бота Telegram.

    Args:
        bot: Объект бота Telegram.
        message: Сообщение для отправки.

    Returns:
        str: Сообщение, в случае его успешной отправки
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
    Выполняет запрос к эндпоинту API-сервиса и возвращает ответ в формате JSON.

    Args:
        timestamp: Метка времени.

    Returns:
        dict: Ответ от API-сервиса приведенный к типу данных Python.

    Raises:
        ConnectionError: Ошибка при доступе к эндпоинту.
        WrongResponse: Если получен некорректный HTTP-ответ.
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
    Проверяет ответ сервера на корректность.

    Args:
        response: Ответ от сервера в формате словаря.

    Raises:
        TypeError: Если объект не является ожидаемым типом.
        KeyError: Если отсутствует необходимый ключ в объекте ответа.
    """
    logger.debug(CHECK_RESPONSE_MESSAGE)
    if not isinstance(response, dict):
        raise TypeError(
            TYPE_ERROR_MESSAGE.format(
                object='response',
                expected_type=type(dict()),
                type=type(response)
            )
        )
    if 'homeworks' not in response:
        raise KeyError(KEY_ERROR_MESSAGE.format(
            dict='homeworks', key='homeworks'))
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            TYPE_ERROR_MESSAGE(
                object='homeworks',
                expected_type=type(list()),
                type=type(response['homeworks'])
            )
        )


def parse_status(homework):
    """
    Извлекает и возвращает статус домашней работы.

    Args:
        homework: Информация о домашней работе в формате словаря.

    Returns:
        str: Статус домашней работы.

    Raises:
        KeyError: В информации о домашней работе отсутствует необходимый ключ.
        ValueError: Неожиданный статус домашней работы в ответе API
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
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None
    message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                logger.debug(NO_UPDATES_MESSAGE)
        except Exception as error:
            response = {}
            message = ERROR_PROGRAMM_MESSAGE.format(error)
            logger.error(message)
        finally:
            if message != last_message:
                if send_message(bot, message):
                    last_message = message
                    timestamp = response.get('current_date', timestamp)
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
