from http.client import OK
from urllib.error import HTTPError
import time
import requests
import os
import telegram
import logging
import sys
from dotenv import load_dotenv

from exceptions import HomeworkError


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s,%(levelname)s %(message)s'
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправляет сообщение в telegram."""
    try:
        logger.info('Сообщение отправляется.')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        raise HomeworkError(f'При отправке сообщения произошла '
                            f'следующая ошибка: {error.msg}')
    else:
        logger.info('Сообщение отправлено.')


def get_api_answer(current_timestamp):
    """Функция делает запрос к эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    api_dict = {
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    response = requests.get(ENDPOINT, **api_dict)
    if response.status_code != OK:
        raise HTTPError(f'Ошибка с получением ответа от сервера'
                        f'Код ошибки: {response.status_code}'
                        f'Параметры запроса: {ENDPOINT} {api_dict}'
                        f'{response.content}')
    response = response.json()
    return response


def check_response(response):
    """Функция проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ полученный от API не является словарём')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует ключ homeworks')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Значение ключа homeworks не является списком')
    homeworks = response.get('homeworks')
    return homeworks


def parse_status(homework):
    """Функция извлекает статус о конкректной работе."""
    if 'status' not in homework:
        raise KeyError('В словаре homework отсутствует'
                       'ключ status')
    homework_status = homework['status']
    if 'homework_name' not in homework:
        raise KeyError('В словаре homework отсутствует'
                       'ключ homework_name')
    homework_name = homework.get('homework_name')
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError('В ответе от API недокументированный '
                       'статус домашней работы')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет наличие необходимых переменных."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks):
                for homework in homeworks[::-1]:
                    message = parse_status(homework)
                    send_message(bot, message)
            else:
                logger.debug('В ответе отсутствует новый статус')
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)
            bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
