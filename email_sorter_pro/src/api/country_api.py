# email_sorter_pro/src/api/country_api.py

import ssl
from typing import Dict

from aiohttp import ClientSession

from src.config.config import get_config
from src.config.logger_config import logger

# Создание SSL контекста с использованием настроек по умолчанию и отключением проверок
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Получаем конфигурацию приложения
config = get_config()

# Кэш для хранения результатов запросов к API
api_cache: Dict[str, str] = {}

########################################################################################################################
async def get_country_by_domain(domain: str, session: ClientSession) -> str:
    """
        Gets the country from a domain using an API.

        :param domain: Domain name to determine the country.
        :type domain: str
        :param session: Asynchronous session for executing HTTP requests.
        :type session: aiohttp.ClientSession
        :return: Country code determined by the domain. Returns "OTHER" in case of error.
        :rtype: str
    """
    # Если домен уже есть в кэше api_cache, возвращаем результат из кэша
    if domain in api_cache:
        return api_cache[domain]

    api_url = config['api_service']['url'].format(domain=domain)         # Формируем URL для запроса к API
    timeout = config['api_service']['timeout']                           # Получаем таймаут из конфигурации

    try:
        # Выполняем асинхронный HTTP GET запрос к указанному URL (api_url)
        async with session.get(api_url, timeout=timeout, ssl=ssl_context) as response:
            if response.status == 200:                                   # Если запрос успешен
                country = await response.text()                          # Получаем текст ответа
                if country.strip():                                      # Проверяем, что страна не пустая строка
                    api_cache[domain] = country                          # Кешируем результат запроса
                    return country                                       # Возвращаем найденную страну
                else:
                    return "OTHER"                                       # Возвращаем "OTHER", если страна не определена
            else:
                return "OTHER"                                           # Возвращаем "OTHER" в случае ошибки запроса
    except Exception as e:
        logger.error(f"API request failed for domain {domain}: {str(e)}")
    return "OTHER"                                                       # Возвращаем "OTHER" в случае общей ошибки
########################################################################################################################
