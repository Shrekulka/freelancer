# email_sorter_pro/src/sorter/email_sorter.py

import asyncio
import json
import os
import traceback
from collections import defaultdict
from typing import List, Optional

import aiofiles
import aiohttp
from tqdm import tqdm

from src.api.country_api import get_country_by_domain
from src.config.config import get_config
from src.config.logger_config import logger


class EmailSorter:
    """
        Class for sorting and processing emails based on country and validity.

        Attributes:
            config (dict): Configuration for the sorter.
            output_dir (str): Directory to save sorted files.
            use_api (bool): Flag for using API to determine country by email domain.
            chunk_size (int): Chunk size for processing emails.
            max_concurrent_requests (int): Maximum number of concurrent API requests.
            chunk_size_emails (int): Chunk size for processing emails within files.
            buffer_size (int): Buffer size for file operations.
            file_handlers (dict): Dictionary to store file handlers.
            total_processed (int): Total number of processed emails.
            email_counts (defaultdict): Counter for emails by country.
            config_usage_count (int): Counter for configuration usage for country determination.
            api_request_count (int): Counter for API requests for country determination.
            state_dir (str): Directory to save sorter state.
            resume_file (str): File to save state for resuming work.
            save_state_interval (int): Interval for saving sorter state.
            progress_bar_update_interval (int): Interval for updating progress bar.
            invalid_emails (list): List of invalid emails.
            other_emails (list): List of emails without a determined country.
            invalid_dir (str): Directory to save invalid emails.
            other_dir (str): Directory to save emails without a determined country.

        Methods:
            get_domain(email: str) -> Optional[str]:
                Returns the domain of the email.

            get_file_handler(country: str) -> aiofiles.threadpool.AsyncTextIOWrapper:
                Retrieves a file handler for the specified country.

            process_email(email: str, session: aiohttp.ClientSession):
                Processes a single email, determines its country, and saves it to the appropriate file.

            process_chunk(chunk: List[str], session: aiohttp.ClientSession):
                Asynchronously processes a chunk of emails.

            save_state():
                Saves the current state of the sorter to a JSON file.

            sort_emails(input_files: List[str]):
                Sorts emails from the specified files, processing them in parallel.

            load_state():
                Loads the last saved state of the sorter.

            write_to_file(directory: str, filename: str, email: str):
                Asynchronously writes an email to the specified file in the specified directory.
    """

    def __init__(self):
        """
            Initialization of the EmailSorter object with loading configuration and setting initial attribute values.
        """
        # Загружаем конфигурацию с помощью функции get_config()
        self.config = get_config()

        # Извлекаем необходимые параметры из конфигурации
        self.output_dir = self.config['output_dir']  # Директория для сохранения отсортированных файлов
        self.use_api = self.config['use_api']        # Флаг использования API для определения страны по домену email
        self.chunk_size = self.config['chunk_size']  # Размер чанка для обработки email
        self.max_concurrent_requests = self.config[
            'max_concurrent_requests']               # Максимальное количество параллельных запросов к API
        self.chunk_size_emails = self.config['chunk_size_emails']  # Размер чанка для обработки email внутри файлов
        self.buffer_size = self.config['buffer_size']  # Размер буфера для файловых операций

        # Словарь для хранения файловых дескрипторов по странам
        self.file_handlers = {}

        # Счетчики и счетчики для статистики
        self.total_processed = 0  # Общее количество обработанных email
        self.email_counts = defaultdict(
            int)                   # Счетчик email по странам (используется defaultdict с int как значение по умолчанию)
        self.config_usage_count = 0  # Счетчик использования конфигурации для определения страны
        self.api_request_count = 0   # Счетчик запросов к API для определения страны

        # Директория для сохранения состояния работы сортировщика
        self.state_dir = self.config['state_dir']

        # Файл для сохранения состояния для возможности продолжения работы
        self.resume_file = self.config['resume_file']

        # Интервал сохранения состояния работы
        self.save_state_interval = self.config['save_state_interval']

        # Интервал обновления прогресс-бара
        self.progress_bar_update_interval = self.config['progress_bar_update_interval']

        # Списки для хранения невалидных и прочих email
        self.invalid_emails = []
        self.other_emails = []

        # Директории для сохранения невалидных и прочих email
        self.invalid_dir = os.path.join(self.output_dir, "INVALID_EMAIL")
        self.other_dir = os.path.join(self.output_dir, "OTHER")

    @staticmethod
    def get_domain(email: str) -> Optional[str]:
        """
            Returns the domain of an email.

            Args:
                email (str): Email from which to extract the domain.

            Returns:
                Optional[str]: Domain of the email or None if the email format is incorrect.
        """
        # Разделяем строку `email` по символу '@' на части
        parts = email.split('@')

        # Возвращаем вторую часть (после '@'), приведенную к нижнему регистру, если в parts есть две части, иначе
        # возвращаем None
        return parts[1].lower() if len(parts) == 2 else None

    async def get_file_handler(self, country: str) -> aiofiles.threadpool.AsyncTextIOWrapper:
        """
            Retrieves a file handler for the specified country.

            Args:
                country (str): Country.

            Returns:
                aiofiles.threadpool.AsyncTextIOWrapper: Asynchronous file handler.
        """
        # Если еще не открыт файловый объект для заданной страны в словаре
        if country not in self.file_handlers:
            # Создаем путь к директории для страны внутри output_dir
            country_dir = os.path.join(self.output_dir, country)
            # Создаем директорию country_dir, если она не существует
            os.makedirs(country_dir, exist_ok=True)
            # Открываем файл для записи, используя aiofiles
            self.file_handlers[country] = await aiofiles.open(os.path.join(country_dir, f"{country}.txt"), mode='a',
                                                              buffering=self.buffer_size)
        # Возвращаем открытый файловый объект для данной страны
        return self.file_handlers[country]

    async def process_email(self, email: str, session: aiohttp.ClientSession) -> None:
        """
            Processes an email: determines the country and saves it to the appropriate file.

            Args:
                email (str): Email to process.
                session (aiohttp.ClientSession): Session for asynchronous HTTP requests.

            Returns:
                None
        """
        try:
            # Получаем домен email
            domain = self.get_domain(email)
            # Если домен пустой или None
            if not domain:
                logger.warning(f"Invalid email format: {email}")
                self.invalid_emails.append(email)  # Добавляем email в список невалидных
                return

            # Инициализируем переменную country значением None перед тем, как начать определять страну, связанную с
            # email-адресом.
            country = None

            # Проходим по элементам словаря self.config['countries'], где c - это ключ (название страны),
            # а domains - список доменных окончаний, связанных с этой страной.
            for c, domains in self.config['countries'].items():
                # Проверяем, оканчивается ли домен email на один из заданных для страны доменов
                if any(domain.endswith(f".{d}") for d in domains):
                    country = c                   # Если условие выполняется, устанавливаем страну
                    self.config_usage_count += 1  # Увеличиваем счетчик использования конфигурации
                    # После того, как была найдена соответствующая страна для доменного окончания email прерываем цикл
                    break

            # Если страна не определена и используется API, получаем страну через API
            if not country and self.use_api:
                country = await get_country_by_domain(domain, session)
                self.api_request_count += 1  # Увеличиваем счетчик API запросов

            # Если страна не определена или равна "Undefined" или пустая строка, помечаем как "OTHER"
            if not country or country == "Undefined" or country.strip() == "":
                country = 'OTHER'
                self.other_emails.append(email)  # Добавляем email в список "OTHER"

            file_handler = await self.get_file_handler(country)  # Получаем файловый обработчик для данной страны
            await file_handler.write(f"{email}\n")               # Записываем email в соответствующий файл
            self.email_counts[country] += 1                      # Увеличиваем счетчик email для данной страны
            self.total_processed += 1                            # Увеличиваем общий счетчик обработанных email

            # Сохраняем состояние после каждого заданного интервала обработки
            if self.total_processed % self.save_state_interval == 0:
                await self.save_state()

        except Exception as e:
            detailed_error_message = traceback.format_exc()
            logger.error(f"Error processing email {email}: {str(e)}\n{detailed_error_message}")
            self.invalid_emails.append(email)  # Добавляем email в список невалидных

    async def process_chunk(self, chunk: List[str], session: aiohttp.ClientSession) -> None:
        """
            Asynchronously processes a chunk of emails.

            Args:
                chunk (List[str]): List of emails to process.
                session (aiohttp.ClientSession): Session for asynchronous HTTP requests.

            Returns:
                None
        """
        # Создаем список задач (coroutines), каждая из которых вызывает метод self.process_email для каждого email в
        # чанке (списке строк), который не пустой после удаления начальных и конечных пробельных символов.
        tasks = [self.process_email(email.strip(), session) for email in chunk if email.strip()]

        # Выполняем все задачи одновременно с помощью функции asyncio.gather.
        await asyncio.gather(*tasks)

    async def save_state(self) -> None:
        """
            Saves the current state of the sorter to a JSON file.
            Creates a JSON file in the state_dir directory.

            Returns:
                None
        """
        # Создаем директорию для сохранения файла состояния, если она не существует.
        os.makedirs(self.state_dir, exist_ok=True)

        # Формируем словарь state, который содержит текущие данные состояния объекта.
        state = {
            "total_processed": self.total_processed,
            "email_counts": dict(self.email_counts),
            "config_usage_count": self.config_usage_count,
            "api_request_count": self.api_request_count,
            "invalid_emails": self.invalid_emails,
            "other_emails": self.other_emails,
        }

        # Определяем путь к файлу состояния state.json в директории state_dir.
        state_file = os.path.join(self.state_dir, "state.json")

        # Асинхронно открываем файл state.json для записи.
        async with aiofiles.open(os.path.join(self.state_dir, "state.json"), mode='w') as f:
            # Записываем JSON-представление словаря state в файл.
            await f.write(json.dumps(state))

        # Логируем информацию о сохранении состояния в лог-файл.
        logger.info(f"Saved state to {state_file}")

    async def sort_emails(self, input_files: List[str]) -> None:
        """
            Sorts emails from the specified files, processing them concurrently using asyncio.

            Args:
                input_files (List[str]): List of paths to files containing emails to process.

            Returns:
                None
        """
        try:
            # Создаем необходимые директории, если они не существуют
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(self.invalid_dir, exist_ok=True)
            os.makedirs(self.other_dir, exist_ok=True)

            # Загружаем последнее сохраненное состояние
            await self.load_state()

            # Создаем асинхронную сессию для работы с HTTP запросами
            async with aiohttp.ClientSession() as session:
                # Обрабатываем каждый входной файл из списка
                for input_file in input_files:
                    # Получаем размер текущего файла
                    file_size = os.path.getsize(input_file)
                    # Инициализируем прогресс-бар для отображения процесса обработки файла
                    progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc=f"Processing {input_file}")

                    # Открываем файл для чтения асинхронно
                    async with aiofiles.open(input_file, mode='r') as file:
                        chunk = []
                        # Читаем файл построчно
                        async for line in file:
                            chunk.append(line)
                            # Если собрали достаточно строк для обработки в одном chunk, запускаем обработку
                            if len(chunk) >= self.chunk_size_emails:
                                await self.process_chunk(chunk, session)
                                chunk = []
                            # Обновляем прогресс-бар на основе количества байт в текущей строке
                            progress_bar.update(len(line.encode('utf-8')))

                        # Обработка оставшихся строк, если chunk не пустой после завершения цикла
                        if chunk:
                            await self.process_chunk(chunk, session)

                    # Закрываем прогресс-бар после обработки файла
                    progress_bar.close()

            # Закрываем все открытые файловые дескрипторы
            for handler in self.file_handlers.values():
                await handler.close()

            # Сохраняем текущее состояние объекта
            await self.save_state()

            # Записываем невалидные email в файлы INVALID_EMAIL.txt
            for email in self.invalid_emails:
                await self.write_to_file(self.invalid_dir, "INVALID_EMAIL.txt", email)

            # Записываем прочие email в файлы OTHER.txt
            for email in self.other_emails:
                await self.write_to_file(self.other_dir, "OTHER.txt", email)

            # Удаляем файл состояния после успешной обработки всех файлов
            os.remove(self.resume_file)

            # Логируем количество записанных email по странам
            for country, count in self.email_counts.items():
                logger.info(f"Emails written to {country}.txt: {count}")

            # Логируем количество невалидных email
            logger.info(f"Invalid emails: {len(self.invalid_emails)}")

            # Логируем общее количество обработанных email
            logger.info(f"Total processed emails: {self.total_processed}")

            # Логируем количество использований конфигурационных данных
            logger.info(f"Config usage count: {self.config_usage_count}")

            # Логируем количество запросов к API
            logger.info(f"API request count: {self.api_request_count}")

        except Exception as e:
            detailed_error_message = traceback.format_exc()
            logger.error(f"Error during email sorting: {str(e)}\n{detailed_error_message}")

            # Сохраняем текущее состояние объекта в случае ошибки
            await self.save_state()

    async def load_state(self) -> None:
        """
            Loads the last saved state of the sorter from a JSON file.

            Returns:
                None
        """
        try:
            # Пытаемся асинхронно открыть файл состояния на чтение
            async with aiofiles.open(self.resume_file, mode='r') as f:
                # Читаем содержимое файла и загружаем состояние в переменные
                state = json.loads(await f.read())
                self.total_processed = state["total_processed"]
                self.email_counts = defaultdict(int, state["email_counts"])
                self.config_usage_count = state["config_usage_count"]
                self.api_request_count = state["api_request_count"]
                self.invalid_emails = state.get("invalid_emails", [])
                self.other_emails = state.get("other_emails", [])
            # Логируем сообщение о успешном возобновлении работы с сохраненным состоянием
            logger.info(f"Resumed from previous state. Total processed: {self.total_processed}")

        except FileNotFoundError:
            # Если файл состояния не найден, логируем сообщение о начале работы с чистого листа
            logger.info("No resume state found. Starting from the beginning.")

    @staticmethod
    async def write_to_file(directory: str, filename: str, email: str) -> None:
        """
            Asynchronously writes an email to the specified file in the specified directory.

            Args:
                directory (str): Directory to save the file.
                filename (str): File name for writing.
                email (str): Email to write to the file.

            Returns:
                None
        """
        try:
            # Асинхронно открываем указанный файл в указанной директории для дозаписи ('a').
            async with aiofiles.open(os.path.join(directory, filename), mode='a') as f:
                # Записываем переданный email в файл с добавлением символа новой строки.
                await f.write(f"{email}\n")
        except Exception as e:
            detailed_error_message = traceback.format_exc()
            error_message = (f"Error writing email to file {filename} in directory {directory}: "
                             f"{str(e)}\n{detailed_error_message}")
            logger.error(error_message)


