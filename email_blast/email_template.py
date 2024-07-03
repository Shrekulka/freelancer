# email_blast/email_template.py

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import config
from logger_config import logger


class EmailTemplate:
    """
        Class for creating an email template.

        Methods:
            create_email(recipient_email: str, recipient_name: str, link: str) -> MIMEMultipart:
                Creates a MIMEMultipart object for an email with the specified parameters.
    """
    @staticmethod
    def create_email(recipient_email: str, recipient_name: str, link: str) -> MIMEMultipart:
        """
            Creates a MIMEMultipart object for an email with the specified parameters.

            Args:
                recipient_email (str): Email address of the recipient.
                recipient_name (str): Name of the recipient.
                link (str): Link to include in the email.

            Returns:
                MIMEMultipart: Configured MIMEMultipart object with headers and email body text.
        """

        # Создаем объект MIMEMultipart для формирования электронного письма
        msg = MIMEMultipart()

        # Устанавливаем отправителя письма (берем из конфигурационных данных)
        msg['From'] = config.SMTP_USER

        # Устанавливаем адрес получателя письма
        msg['To'] = recipient_email

        # Устанавливаем тему письма
        msg['Subject'] = config.EMAIL_SUBJECT

        # Создаем тело письма с персонализированным сообщением и ссылкой
        body = config.EMAIL_BODY_TEMPLATE.format(name=recipient_name, link=link)

        # Прикрепляем текстовое тело письма к объекту MIMEMultipart
        msg.attach(MIMEText(body, 'plain'))

        # Добавим проверку
        if msg['To'] != recipient_email:
            logger.warning(f"Mismatch in recipient email: {msg['To']} != {recipient_email}")

        # Возвращаем готовый объект MIMEMultipart, содержащий все необходимые данные для отправки письма
        return msg
