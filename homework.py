import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import requests
import time
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# handler = RotatingFileHandler(
#     'my_logger.log', maxBytes=50000000, backupCount=5)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Посылает сообщение от бота в чат с TELEGRAM_CHAT_ID."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logger.error(error)
    else:
        logger.info(f'Отправлено сообщение: "{message}"')


def get_api_answer(current_timestamp):
    """Получает json со списком работ."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.error(error)
    else:
        if response.status_code != 200:
            raise OSError("Response " + str(response.status_code)
                          + ": " + response.content)
        else:
            return response.json()


def check_response(response):
    """Проверяет наличие работы в ответе от сервера."""
    if isinstance(response['homeworks'], list):
        return response['homeworks']


def parse_status(homework):
    """Выносит вердикт о проверке работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for token in tokens:
        if not tokens[token]:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {token}'
            )
            return False
    return True


def main():
    """Основная логика работы бота."""
    check_tokens_result = check_tokens()
    if not check_tokens_result:
        exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    homework_preload_id = 0
    homework_preload_status = 'initial'
    while True:
        try:
            response = get_api_answer(1)
            homeworks = check_response(response)
            homework = homeworks[0]
            if homework_preload_status != homework['status'] or homework_preload_id != homework['id']:
                verdict = parse_status(homework)
                send_message(bot, verdict)
            else:
                logger.debug('В ответе нет новых статусов.')
            if homework_preload_id != homework['id']:
                homework_preload_id = homework['id']
                homework_preload_status = homework['status']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        else:
            current_timestamp = response['current_date']
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
