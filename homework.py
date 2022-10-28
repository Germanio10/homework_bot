from http import HTTPStatus
from dotenv import load_dotenv
import os
import telegram
import time
import requests
import logging

load_dotenv()

logging.basicConfig(level=logging.DEBUG,
                    filename='main.log',
                    format='%(asctime)s, %(levelname)s, %(message)s')

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
        logging.info('Сообщение отправлено')
    except Exception:
        logging.error('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Получает ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT,
                                params=params,
                                headers=HEADERS)
    except Exception:
        logging.error('Недоступен ENDPOINT')

    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        raise Exception(f'Ошибка {status_code}')
    if response.status_code == 503:
        status_code = response.status_code
        logging.error('Сбой при запросе')
    try:
        return response.json()
    except ValueError:
        raise ValueError('Ошибка перевода в json')


def check_response(response):
    """Получаем последнюю работу."""
    try:
        response['homeworks']
    except KeyError:
        logging.error('Ошибка в словаре')
    try:
        homework = response.get('homeworks')[0]
        return homework
    except IndexError:
        raise IndexError('Список работ пуст')


def parse_status(homework):
    """Узнаем статус работы"""
    if 'homework_name' not in homework:
        raise KeyError('Отсутсвует ключ имени')
    if 'status' not in homework:
        logging.error('Отсутствует ключ статуса в словаре')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logging.error('Неизвестный статус работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    try:
        if not PRACTICUM_TOKEN:
            return False
        elif not TELEGRAM_CHAT_ID:
            return False
        elif not TELEGRAM_TOKEN:
            return False
        return True
    except Exception as error:
        logging.critical(f'Не хватает токена {error}')
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - ONE_DAY * 10

    prev_work_status = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_status = response.get('homeworks')[0].get('status')
            message = parse_status(check_response(response))
            if prev_work_status != current_status:
                send_message(bot, message)
                prev_work_status = current_status
            time.sleep(RETRY_TIME)
        except Exception as error:
            logging.error(error)
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
