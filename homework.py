from asyncio.log import logger
from http import HTTPStatus
from dotenv import load_dotenv
import os
import telegram
import time
import requests
import logging

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ONE_DAY = 86400

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Бот отправляет сообщение."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        raise Exception('Сообщение не отправлено')
    else:
        logger.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Получает ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT,
                                params=params,
                                headers=HEADERS)
        if response.status_code != HTTPStatus.OK:
            status_code = response.status_code
            raise Exception(f'Ошибка {status_code}, запрос: {ENDPOINT}')
        return response.json()
    except Exception as error:
        raise Exception(f'Ошибка при запросе к API: {error}')


def check_response(response):
    """Получаем последнюю работу."""
    if response:
        response['homeworks'] and response['current_date']
    else:
        raise KeyError(f'Ошибка словаря {response}')
    if response:
        homework = response.get('homeworks')[0]
        return homework
    else:
        raise IndexError('Список работ пуст')


def parse_status(homework):
    """Узнаем статус работы."""
    if 'homework_name' not in homework:
        raise KeyError(f'Отсутсвует ключ имени в {homework}')
    if 'status' not in homework:
        raise KeyError(f'Отсутствует ключ статуса в словаре {homework}')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутсвуют токены')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - ONE_DAY * 10

    status_messgage = ''
    error_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            message = parse_status(check_response(response))
            if message != status_messgage:
                send_message(bot, message)
                status_messgage = message
        except Exception as error:
            logging.error(error)
            message = f'Сбой в работе программы: {error}'
            if message != error_message:
                send_message(bot, message)
                error_message = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        filename='main.log',
                        format='%(asctime)s, %(levelname)s, %(message)s')

    main()
