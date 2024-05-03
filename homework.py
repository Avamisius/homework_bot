import logging
import os
import requests
import telegram
import time
import sys


from dotenv import load_dotenv
from http import HTTPStatus

from exceptions import EmptyResponseFromApiError

load_dotenv()


file_handler = logging.FileHandler(filename='tmp.log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s]'
    '{%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger(__name__)
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
    """проверяет доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    error_message = []
    for tname, tvalue in tokens.items():
        if not tvalue:
            error_message.append(
                f'Отсутствует переменная окружения: {tname}'
            )
    return error_message


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message)
        logger.debug('Сообщение отправлено.')
    except Exception as error:
        logger.error(error)


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    logging.debug('Начало работы функции get_api_answer.')
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException:
        raise ConnectionError(
            'Сбой в работе программы.'
        )
    if response.status_code != HTTPStatus.OK:
        raise EmptyResponseFromApiError(
            'Пришёл пустой ответ от API.'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие."""
    if not isinstance(response, dict):
        raise TypeError('в ответе API структура'
                        'данных не соответствует ожидаемым')
    if 'homeworks' not in response:
        raise KeyError('в ответе API домашки нет ключа "homeworks"')
    if not isinstance(response['homeworks'], list):
        raise TypeError('в ответе API домашки под ключом `homeworks`'
                        'данные приходят не в виде списка')
    return True


def parse_status(homework):
    """Извлекает статус работы."""
    if 'homework_name' not in homework:
        raise Exception('в ответе API домашки нет ключа `homework_name`')
    status = homework['status']
    if status in HOMEWORK_VERDICTS.keys():
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise KeyError('Неизвестный статус домашней работы')


def main():
    """Основная логика работы бота."""
    list_errors_tockens = check_tokens()
    if list_errors_tockens:
        logging.critical('\n'.join(list_errors_tockens))
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot=bot, message=message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != last_error_message:
                message = f'Сбой в работе программы: {error}'
                send_message(bot=bot, message=message)
                last_error_message = message
                logging.exception(message, exc_info=False)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
