# email_sorter_pro/main.py

import asyncio
import traceback
import glob

from scripts.generate_test_data import generate_test_emails
from src.config.config import get_config
from src.config.logger_config import logger
from src.sorter.email_sorter import EmailSorter


async def main() -> None:
    """
        The main function of the application for sorting emails.

        This function initializes necessary components, reads the application configuration,
        processes input files, and starts the sorting process.

        Raises:
            KeyboardInterrupt: If the user interrupts the application execution.
            Exception: Catches any unexpected errors and logs them.

        Example usage:
            asyncio.run(main())
    """

    config = get_config()  # Получаем конфигурацию приложения

    # Генерируем тестовые email, если установлен соответствующий флаг в конфигурации
    if config['test_data']['generate']:
        generate_test_emails()

    sorter = EmailSorter()  # Создаем экземпляр класса EmailSorter для сортировки email

    # Собираем список всех файлов, которые нужно обработать, используя шаблоны из конфигурации
    input_files = []
    for file_pattern in config['input_files']:
        input_files.extend(glob.glob(file_pattern))

    # Если список файлов пуст, записываем ошибку в лог и выходим
    if not input_files:
        logger.error("No input files found.")
        return

    # Удаляем дубликаты и сортируем список файлов
    input_files = sorted(set(input_files))

    logger.info(f"Files to process: {input_files}")  # Логируем список файлов для обработки

    # Запускаем асинхронную сортировку email по всем файлам
    await sorter.sort_emails(input_files)
########################################################################################################################

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Приложение завершено пользователем")
    except Exception as error:
        detailed_error_message = traceback.format_exc()
        logger.error(f"Неожиданная ошибка в приложении: {error}\n{detailed_error_message}")
########################################################################################################################
