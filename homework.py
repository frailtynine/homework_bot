"""Модуль для телеграм-бота, проверяющего статус заданий."""

import logging
import os
import sys
from http import HTTPStatus
import requests
import time

from dotenv import load_dotenv
import telegram

import exceptions


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(stream=sys.stdout)]
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия токенов в окружении."""
    all_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN
    }
    for key, value in all_tokens.items():
        if not value:
            logging.critical(
                f'Критическая ошибка. Токен {key} не найден.'
            )
            raise exceptions.TokenNotFoundError
    return True


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Сообщение "{message}" успешно отправлено.')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Запрос к API Яндекс.Практикума."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={
                'from_date': timestamp
            }
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            logging.error(f'Ошибка доступа к API: {response.status_code}')
            raise exceptions.APINotAvailableError(response.status_code)
    except requests.RequestException as error:
        logging.error(f'Ошибка запроса к API: {error}')


def check_response(response):
    """Проверка ответа от API."""
    if not isinstance(response, dict):
        logging.error('Ответ от API не содержит словаря')
        raise TypeError('Ответ от API не содержит словаря')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        logging.error('Объект homeworks в ответе от API - не список.')
        raise TypeError('Объект homeworks в ответе от API - не список.')
    return homework


def parse_status(homework):
    """Создание сообщения для бота."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logging.error('В словаре homeworks нет ключа homework_name.')
        raise KeyError('В словаре homeworks нет ключа homework_name.')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS.keys():
        logging.error(exceptions.StatusError(status))
        raise exceptions.StatusError(status)
    else:
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Телеграм-бот для проверки домашней работы.

    Проверяет наличие токенов в окружении, запрашивает
    последние данные о статусе домашней работы у Яндекс.Практикума
    и передает сообщение об изменении статуса работы.
    """
    if not check_tokens():
        raise exceptions.TokenNotFoundError

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                send_message(bot, message)
            else:
                message = 'Статус работы не изменился'
                logging.debug(message)
            timestamp = response.get('current_date')
            print(timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
