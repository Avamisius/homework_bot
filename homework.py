import logging
import os
import time
import sys

import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus

from exceptions import APIError

ENV_ERROR = 'Отсутствует переменная окружения: {name}'
MESSAGE_SEND = 'Сообщение отправлено: {message}'
MESSAGE_SEND_ERROR = 'Не удалось отправить сообщение: {error}'
API_ERROR = ('Ошибка при выполнении запроса к API. '
             'Cтатус:{status_code}. url:{endpoint},'
             'headers:{headers}, payload:{payload}, content:{content}')
CONNECTION_ERROR = ('Сбой в работе программы: {error}. url:{endpoint},'
                    'headers:{headers}, payload:{payload}')
RESPONSE_TYPE_ERROR = ('Тип ответа API({type})'
                       'не соответствует ожидаемым(dict)')
HOMEWORKS_KEY_ERROR = 'в ответе API домашки нет ключа "homeworks"'
HOMEWORKS_TYPE_ERROR = ('Тип `homeworks`({homeworks_type})'
                        'не соответствует ожидаемым(list)')
HOMEWORKS_NAME_KEY_ERROR = 'в ответе API домашки нет ключа `homework_name`'
HOMEWORKS_STATUS_ERROR = 'Неизвестный статус домашней работы'
SEND_ERROR_MESSAGE_ERROR = ('Не удалось отправить сообщение'
                            ' об ошибке: {error}')
DEFAULT_ERROR = 'Сбой в работе программы: {error}'

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
TOKENS = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID'
]

load_dotenv()

logger = logging.getLogger(__name__)


def setup_logger():
    """Настройка логгинга."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s]'
               '{%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(filename=__file__ + '.log'),
            logging.StreamHandler(stream=sys.stdout)
        ]
    )


def check_tokens():
    """проверяет доступность переменных окружения."""
    error_messages = []
    for name in TOKENS:
        if not globals()[name]:
            error_messages.append(ENV_ERROR.format(name=name))
    if error_messages:
        logger.critical('\n'.join(error_messages))
        raise SystemExit()


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message)
        logger.debug(MESSAGE_SEND.format(message=message))
    except Exception as error:
        logger.exception(MESSAGE_SEND_ERROR.format(error=error))


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        content = response.json()
        if (
            response.status_code != HTTPStatus.OK
            or 'code' in content or 'error' in content
        ):
            raise APIError(API_ERROR.format(
                status_code=response.status_code,
                endpoint=ENDPOINT, headers=HEADERS,
                payload=payload, content=content
            ))
        return content
    except requests.RequestException as error:
        raise ConnectionError(CONNECTION_ERROR.format(
            error=error, endpoint=ENDPOINT,
            headers=HEADERS, payload=payload
        ))


def check_response(response):
    """Проверяет ответ API на соответствие."""
    if not isinstance(response, dict):
        raise TypeError(RESPONSE_TYPE_ERROR.format(type=type(response)))
    if 'homeworks' not in response:
        raise KeyError(HOMEWORKS_KEY_ERROR.format())
    if not isinstance(response['homeworks'], list):
        homeworks_type = type(response['homeworks'])
        raise TypeError(HOMEWORKS_TYPE_ERROR.format(
            homeworks_type=homeworks_type
        ))


def parse_status(homework):
    """Извлекает статус работы."""
    if 'homework_name' not in homework:
        raise KeyError(HOMEWORKS_NAME_KEY_ERROR.format())
    status = homework['status']
    if status not in HOMEWORK_VERDICTS.keys():
        raise KeyError(HOMEWORKS_STATUS_ERROR.format())

    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    last_error_message = None
    while True:
        try:
            response = get_api_answer(int(time.time()))
            check_response(response)
            homeworks = response.get('homeworks')
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot=bot, message=message)
        except Exception as error:
            message = DEFAULT_ERROR.format(error=error)
            logger.exception(message)
            if message != last_error_message:
                try:
                    send_message(bot=bot, message=message)
                    last_error_message = message
                except Exception as error:
                    logger.exception(SEND_ERROR_MESSAGE_ERROR.format(
                        error=error
                    ))
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    setup_logger()
    main()
