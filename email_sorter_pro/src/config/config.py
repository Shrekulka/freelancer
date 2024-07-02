# email_sorter_pro/src/config/config.py

import os
from typing import Dict, Any

# Конфигурация стран и доменов
########################################################################################################################
# Здесь мы определяем, какие домены принадлежат какой стране
COUNTRIES: Dict[str, list] = {
    "US": ["com", "net", "org", "edu"],  # США
    "UK": ["co.uk", "org.uk", "ac.uk"],  # Великобритания
    "FR": ["fr"],                        # Франция
    "DE": ["de"],                        # Германия
    "JP": ["jp"],                        # Япония
    "RU": ["ru"],                        # Россия
    "CN": ["cn"],                        # Китай
    "BR": ["com.br"],                    # Бразилия
    "IN": ["in"]                         # Индия
}
########################################################################################################################

# Конфигурация API-сервиса
########################################################################################################################
# Настройки для вызовов API, который определяет страну по домену
API_SERVICE: Dict[str, Any] = {
    "url": "https://ipapi.co/{domain}/country/",  # URL для API с параметром домена
    "timeout": 5,                                 # Таймаут для запроса
    "batch_size": 100,                            # Размер пакета для батчевого запроса
    "max_retries": 3,                             # Максимальное количество повторных попыток при неудаче
}
########################################################################################################################

# Настройки тестовых данных
########################################################################################################################
# Опции для генерации и использования тестовых данных
GENERATE_TEST_DATA: bool = False              # Флаг для генерации тестовых данных
TEST_DATA_COUNT: int = 10000                 # Количество тестовых email
TEST_FILE: str = 'tests/test_emails.txt'     # Путь к файлу с тестовыми данными
########################################################################################################################

# Настройки входных файлов
########################################################################################################################
# Пути к входным файлам для обработки
INPUT_FILES: list = [
    'tests/test_emails*.txt',  # Все файлы, начинающиеся с "test_emails" в директории tests
    'data/emails_1.txt',       # Конкретный файл
    'data/batch_*.txt',        # Все файлы, начинающиеся с "batch_" в директории data
]
########################################################################################################################

# Общие настройки
########################################################################################################################
OUTPUT_DIR: str = "output/sorted_emails"  # Директория для сохранения отсортированных email
USE_API: bool = True                      # Флаг для использования API
CHUNK_SIZE: int = 10 * 1024 * 1024        # Размер чанка для обработки файлов (10 MB)
MAX_CONCURRENT_REQUESTS: int = 100        # Максимальное количество одновременных запросов к API
CHUNK_SIZE_EMAILS: int = 10000            # Количество email в одном чанке
BUFFER_SIZE: int = 8192                   # Размер буфера для записи в файл
MAX_WORKERS: int = os.cpu_count() * 2     # Количество потоков для обработки (в два раза больше количества CPU)
########################################################################################################################

# Настройки состояния и производительности
########################################################################################################################
STATE_DIR: str = "state"                                     # Директория для хранения состояния
RESUME_FILE: str = os.path.join(STATE_DIR, "state.json")     # Файл для сохранения состояния
SAVE_STATE_INTERVAL: int = 1000000                           # Сохранять состояние каждые 1 000 000 обработанных email
PROGRESS_BAR_UPDATE_INTERVAL: int = 1000                     # Обновлять прогресс-бар каждые 1000 обработанных email
MAX_PARALLEL_FILES: int = 4                                  # Максимальное количество файлов для параллельной обработки
########################################################################################################################

# Функция для получения конфигурации
########################################################################################################################
def get_config() -> Dict[str, Any]:
    """
        Returns the application configuration.

        :return: Dictionary with configuration settings.
        :rtype: dict

        Configuration includes the following parameters:
        - countries: configuration of countries and domains
        - api_service: settings for the API service to determine country by domain
        - test_data: settings for generating and using test data
        - input_files: paths to input files for processing
        - output_dir: directory for saving sorted emails
        - use_api: flag for API usage
        - chunk_size: chunk size for file processing (in bytes)
        - max_concurrent_requests: maximum number of concurrent API requests
        - chunk_size_emails: number of emails in each chunk
        - buffer_size: buffer size for file writing (in bytes)
        - max_workers: number of threads for processing
        - state_dir: directory for storing state
        - resume_file: file for saving state
        - save_state_interval: interval for saving state (in number of processed emails)
        - progress_bar_update_interval: interval for updating the progress bar (in number of processed emails)
        - max_parallel_files: maximum number of files for parallel processing
    """
    return {
        "countries": COUNTRIES,                              # Конфигурация стран и доменов
        "api_service": API_SERVICE,                          # Настройки API-сервиса
        "test_data": {                                       # Настройки тестовых данных
            "generate": GENERATE_TEST_DATA,                  # Генерировать ли тестовые данные
            "count": TEST_DATA_COUNT,                        # Количество тестовых email
            "file": TEST_FILE,                               # Путь к файлу с тестовыми данными
        },
        "input_files": INPUT_FILES,                          # Пути к входным файлам
        "output_dir": OUTPUT_DIR,                            # Директория для сохранения отсортированных email
        "use_api": USE_API,                                  # Использовать ли API для определения страны по домену
        "chunk_size": CHUNK_SIZE,                            # Размер чанка для обработки файлов
        "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,  # Максимальное количество одновременных запросов к API
        "chunk_size_emails": CHUNK_SIZE_EMAILS,              # Количество email в одном чанке
        "buffer_size": BUFFER_SIZE,                          # Размер буфера для записи в файл
        "max_workers": MAX_WORKERS,                          # Количество потоков для обработки
        "state_dir": STATE_DIR,                              # Директория для хранения состояния
        "resume_file": RESUME_FILE,                          # Файл для сохранения состояния
        "save_state_interval": SAVE_STATE_INTERVAL,          # Интервал для сохранения состояния
        "progress_bar_update_interval": PROGRESS_BAR_UPDATE_INTERVAL,  # Интервал обновления прогресс-бара
        "max_parallel_files": MAX_PARALLEL_FILES,            # Максимальное количество файлов для параллельной обработки
    }
########################################################################################################################
