import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (
    EndpointUnavailableError,
    HTTPError,
    SendMessageError,
    TokenAccessError
)

# Настройка логгирования
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s')
)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Загрузка переменных окружения
load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """
    Проверка доступности переменных окружения.

    Raises:
        TokenAccessError: Если переменные окружения недоступны.
    """
    if not all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        message = 'Недоступны переменные окружения'
        logging.critical(message)
        raise TokenAccessError(message)


def send_message(bot, message):
    """
    Отправка сообщения через бота Telegram.

    Args:
        bot: Объект бота Telegram.
        message: Сообщение для отправки.

    Raises:
        SendMessageError: Если не удалось отправить сообщение.
    """
    try:
        logger.debug('Отправка сообщения')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Сообщение успешно отправлено')
    except Exception as error:
        message = f'Не удалось отправить сообщение: {error}'
        logger.error(message)
        raise SendMessageError(message)


def get_api_answer(timestamp):
    """
    Выполняет запрос к эндпоинту API-сервиса и возвращает ответ в формате JSON.

    Args:
        timestamp: Метка времени.

    Returns:
        dict: Ответ от API-сервиса приведенный к типу данных Python.

    Raises:
        EndpointUnavailableError: Если возникла ошибка при доступе к эндпоинту.
        HTTPError: Если получен некорректный HTTP-ответ.
    """
    payload = {'from_date': timestamp}
    try:
        logger.debug('Запрос к эндпоинту API-сервиса.')
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise HTTPError('Статус код ответа не равен 200')
        logger.info('Запрос выполнен успешно')
        return response.json()
    except requests.RequestException as error:
        message = f'Ошибка доступа: {error}'
        logger.error(message)
        raise EndpointUnavailableError(message)
    except HTTPError as error:
        message = f'Ошибка HTTP: {error}'
        logger.error(message)
        raise HTTPError(message)


def check_response(response):
    """
    Проверяет ответ сервера на корректность.

    Args:
        response: Ответ от сервера в формате словаря.

    Raises:
        TypeError: Если объект не является ожидаемым типом.
        KeyError: Если отсутствует необходимый ключ в объекте ответа.
    """
    try:
        logger.debug('Иницилизация проверки ответа сервера')
        response['current_date']
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            raise TypeError('Значение ключа "homeworks" - не список')
        logger.debug('Проверка пройдена успешно')
    except KeyError as error:
        message = f'Ошибка проверки ответа сервера: отсутствует ключ {error}'
        logger.error(message)
        raise KeyError(message)
    except TypeError as error:
        message = f'Ошибка проверки ответа сервера: {error}'
        logger.error(message)
        raise TypeError(message)


def parse_status(homework):
    """
    Извлекает и возвращает статус домашней работы.

    Args:
        homework: Информация о домашней работе в формате словаря.

    Returns:
        str: Статус домашней работы.

    Raises:
        KeyError: Если в информации о домашней работе
        отсутствует необходимый ключ.
    """
    try:
        logger.debug('Извлечение статуса домашней работы')
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[homework['status']]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        message = f'Ошибка извлечения статуса: отсутствует ключ {error}'
        logger.error(message)
        raise KeyError(message)


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            timestamp = response['current_date']
            homeworks = response['homeworks']
            if homeworks:
                message = parse_status(homeworks[0])
                if message != last_message:
                    send_message(bot, message)
                    last_message = message
            else:
                logger.debug('Обновлений нет')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if not isinstance(error, SendMessageError):
                if message != last_message:
                    send_message(bot, message)
                    last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
