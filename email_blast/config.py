# email_blast/config.py

from pydantic.v1 import BaseSettings, SecretStr, EmailStr


class Settings(BaseSettings):
    """
        Class for storing application configuration data.

        Attributes:
            SMTP_SERVER (str): Address of the SMTP server for sending emails.
            SMTP_PORT (int): Port of the SMTP server.
            SMTP_USER (EmailStr): Email address of the SMTP user for authentication.
            SMTP_PASSWORD (SecretStr): Secret password of the SMTP user.
            CSV_FILENAME (str): Name of the file with recipients (CSV).
            EMAIL_SUBJECT (str): Subject of the email.
            EMAIL_BODY_TEMPLATE (str): Template of the email body with a personalized message and link.
            PROGRESS_BAR_DESC (str): Description for the progress bar during email sending.
            MAX_CONCURRENT_EMAILS (int): Maximum number of concurrent email sends.
            SLEEP_DURATION (int): Waiting time between email sends (in seconds).

        Configuration:
            env_file (str): Name of the environment variables file.
            env_file_encoding (str): Encoding of the environment variables file.
    """
    SMTP_SERVER: str                             # Адрес SMTP сервера (строка)
    SMTP_PORT: int                               # Порт SMTP сервера (целое число)
    SMTP_USER: EmailStr                          # Электронная почта пользователя SMTP (строка, валидация формата почты)
    SMTP_PASSWORD: SecretStr                     # Секретный пароль пользователя SMTP (строка, скрытая при выводе)
    CSV_FILENAME: str = 'recipients.csv'         # Имя файла с получателями (CSV)
    PROGRESS_BAR_DESC: str = 'Sending emails'    # Описание для прогресс-бара при отправке писем
    MAX_CONCURRENT_EMAILS: int = 5               # Максимальное количество одновременных отправок писем
    SLEEP_DURATION: int = 2                      # Время ожидания между отправками писем (в секундах)
    # Тема электронного письма
    EMAIL_SUBJECT: str = 'Ваша персонализированная ссылка'
    # Шаблон тела письма с персонализированным сообщением и ссылкой
    EMAIL_BODY_TEMPLATE: str = "Привет, {name}!\n\nВот ваша ссылка: {link}\n\nС уважением, Ваша команда."

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаем экземпляр класса Settings для хранения конфигурационных данных
config: Settings = Settings()
