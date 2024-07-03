# email_blast/main.py

import asyncio
import traceback

from config import config
from csv_reader import CSVReader
from email_service import EmailService
from logger_config import logger


async def main() -> None:
    """
         Asynchronous function that orchestrates the process of reading recipients from a CSV file
         and sending personalized emails to each recipient.

         Raises:
             Exception: If there's an unexpected error during the process.
     """
    try:
        # Читаем информацию о получателях из CSV-файла
        email_list = await CSVReader.read_recipients(config.CSV_FILENAME)
        logger.info(f"Read recipients: {email_list}")

        # Логируем начало отправки писем
        logger.info(f"Starting to send emails to {len(email_list)} recipients")

        # Отправляем письма получателям с использованием класса EmailService
        await EmailService.send_emails(email_list)

        # Логируем завершение отправки писем
        logger.info("Finished sending emails")

    except Exception as e:
        # Логируем неожиданные исключения вместе с трейсбэком
        error_message = traceback.format_exc()
        logger.error(f"An unexpected error occurred in the application: {e}\n{error_message}")


if __name__ == "__main__":
    try:
        # Запускаем основную функцию с использованием asyncio
        asyncio.run(main())

    except KeyboardInterrupt:
        # Обрабатываем прерывание пользователем
        logger.warning("Application terminated by user")

    except Exception as error:
        # Логируем неожиданные исключения во время выполнения
        detailed_error_message = traceback.format_exc()
        logger.error(f"Unexpected error in the application: {error}\n{detailed_error_message}")

    finally:
        # Логируем завершение работы приложения
        logger.info("Application finished")