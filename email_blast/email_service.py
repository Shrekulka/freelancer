# email_blast/email_service.py

import asyncio
import smtplib
import traceback
from asyncio import Semaphore
from contextlib import asynccontextmanager
from typing import List, Dict, AsyncIterator

from tqdm import tqdm

from config import config
from email_template import EmailTemplate
from logger_config import logger


@asynccontextmanager
async def get_smtp_connection() -> AsyncIterator[smtplib.SMTP]:
    """
       Context manager for establishing and automatically closing a connection to an SMTP server.

       Yields:
           smtplib.SMTP: An SMTP server object for sending emails.

       Raises:
           Exception: If there's an error connecting to or authenticating with the SMTP server.
    """
    logger.info(f"Connecting to SMTP server: {config.SMTP_SERVER}:{config.SMTP_PORT}")
    # Инициализируем SMTP соединение с сервером, указанным в конфигурации.
    server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
    try:
        # Начинаем TLS-соединение с SMTP-сервером для защищённой передачи данных.
        logger.info("Starting TLS connection")
        server.starttls()

        # Логинимся на SMTP-сервере с использованием указанного в конфигурации пользователя.
        logger.info(f"Logging in as {config.SMTP_USER}")
        server.login(config.SMTP_USER, config.SMTP_PASSWORD.get_secret_value())

        # Устанавливаем успешное соединение с SMTP-сервером и передаём управление далее.
        logger.info("SMTP connection established")
        yield server

    # В случае возникновения исключения логируем ошибку подключения к SMTP-серверу.
    except Exception as e:
        detailed_error_message = traceback.format_exc()
        logger.error(f"Failed to connect to SMTP server: {str(e)}\n{detailed_error_message}")
        raise

    # Независимо от результата операции, закрываем соединение с SMTP-сервером.
    finally:
        logger.info("Closing SMTP connection")
        server.quit()


class EmailService:
    """
        The EmailService class provides methods for sending personalized emails via an SMTP server.

        Methods:
            async def send_emails(email_list: List[Dict[str, str]], max_concurrent: int = config.MAX_CONCURRENT_EMAILS) -> None:
                Asynchronously sends emails from the email_list using an SMTP server.

        Notes:
            Utilizes asyncio for managing parallel email sending and tracks progress using tqdm progress bar.
    """
    @staticmethod
    async def send_emails(email_list: List[Dict[str, str]], max_concurrent: int = config.MAX_CONCURRENT_EMAILS) -> None:
        """
            Asynchronously sends emails from a list through an SMTP server.

            Args:
                email_list (List[Dict[str, str]]): A list of dictionaries containing recipient email, name, and link.
                max_concurrent (int, optional): Maximum number of concurrent email sending tasks. Defaults to config.MAX_CONCURRENT_EMAILS.

            Raises:
                Exception: If there's an error sending an email.

            Notes:
                Uses asyncio to manage concurrent sending of emails and tracks progress with a tqdm progress bar.
        """
        # Создаем семафор для управления количеством одновременных асинхронных задач отправки писем
        semaphore = Semaphore(max_concurrent)

        # Устанавливаем соединение с SMTP-сервером через контекстный менеджер
        async with get_smtp_connection() as server:
            # Инициализируем прогресс-бар для отслеживания отправки писем
            progress_bar = tqdm(total=len(email_list), desc=config.PROGRESS_BAR_DESC, leave=True)

            async def send_email(email_data: Dict[str, str]) -> None:
                """
                    Asynchronously sends an email based on data from email_data dictionary.

                    Args:
                        email_data (Dict[str, str]): Dictionary containing email, name, and link.

                    Raises:
                        Exception: If there's an error sending an email.
                """
                # Асинхронно захватываем семафор для ограничения количества одновременных задач отправки
                async with semaphore:
                    try:
                        # Извлекаем данные получателя из словаря email_data
                        recipient_email = email_data['email']
                        recipient_name = email_data['name']
                        link = email_data['link']

                        # Создаем объект письма с помощью шаблона EmailTemplate
                        msg = EmailTemplate.create_email(recipient_email, recipient_name, link)
                        # Отправляем письмо через SMTP-сервер
                        server.sendmail(config.SMTP_USER, recipient_email, msg.as_string())
                        logger.info(f"Email sent successfully to {recipient_email}")
                    except Exception as e:
                        # Логируем ошибку, если не удалось отправить письмо
                        logger.error(f"Error sending email to {recipient_email}: {str(e)}", exc_info=True)
                    finally:
                        # Обновляем прогресс-бар и ожидаем указанное время перед следующей отправкой
                        progress_bar.update(1)
                        await asyncio.sleep(config.SLEEP_DURATION)

            # Создаем задачи для отправки каждого письма в списке email_list
            tasks = [asyncio.create_task(send_email(email_data)) for email_data in email_list]
            # Собираем все задачи вместе для асинхронного выполнения
            await asyncio.gather(*tasks, return_exceptions=True)
            # Закрываем прогресс-бар после завершения отправки
            progress_bar.close()

        # Логируем завершение отправки всех писем
        logger.info(f"All emails have been processed. Total: {len(email_list)}")
