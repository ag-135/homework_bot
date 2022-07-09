import time
from urllib.error import HTTPError
import requests
import os
import telegram
import logging
import sys
from dotenv import load_dotenv


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
    if bot.send_message(TELEGRAM_CHAT_ID, message):
        logger.info('Сообщение благополучно отправлено')
    else:
        logger.error('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Функция делает запрос к эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == 500:
        logger.error('Недоступность эндпоинта')
        raise HTTPError('Недоступность эндпоинта')
    if response.status_code != 200 and response.status_code != 500:
        logger.error('Сбои при запросе к эндпоинту')
        raise HTTPError('Сбои при запросе к эндпоинту')
    response = response.json()
    print(response)
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
        logger.error('В ответе API отсутствует ключ status')
        raise KeyError('В словаре homework отсутствует'
                       'ключ status')
    homework_status = homework['status']
    if 'homework_name' not in homework:
        logger.error('В ответе API отсутствует ключ name')
        raise KeyError('В словаре homework отсутствует'
                       'ключ homework_name')
    homework_name = homework.get('homework_name')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error('В ответе от API недокументированный '
                     'статус домашней работы')
        raise KeyError('В ответе от API недокументированный '
                       'статус домашней работы')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет наличие необходимых переменных."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        logger.critical('Отсутствуют обязательные переменные окружения')
        return False


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = 0
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                if len(homeworks) != 0:
                    for homework in homeworks[::-1]:
                        message = parse_status(homework)
                        bot.send_message(TELEGRAM_CHAT_ID, message)
                else:
                    logger.debug('В ответе отсутствует новый статус')
                current_timestamp = response.get('current_date')
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                bot.send_message(TELEGRAM_CHAT_ID, message)
                time.sleep(RETRY_TIME)
            else:
                message = 'Дорогу осилит идущий'
                bot.send_message(TELEGRAM_CHAT_ID, message)


if __name__ == '__main__':
    main()
