# email_sorter_pro/scripts/generate_test_data.py

import random

from src.config.config import get_config
from src.config.logger_config import logger

# Список имен для генерации email
########################################################################################################################
names: list[str] = [
    "john", "alice", "bob", "emma", "alex", "maria", "ivan", "yuki", "li", "ahmed",
    "sofia", "miguel", "anna", "chen", "priya", "mohammed", "olivia", "carlos", "lena", "dmitri"
]
########################################################################################################################

# Список доменов для генерации email
########################################################################################################################
domains: list[str] =  [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",  # US
    "mail.ru", "yandex.ru", "rambler.ru",  # RU
    "163.com", "qq.com", "126.com",  # CN
    "ukr.net", "co.uk", "bt.com",  # UK
    "orange.fr", "free.fr", "sfr.fr",  # FR
    "web.de", "gmx.de", "t-online.de",  # DE
    "yahoo.co.jp", "docomo.ne.jp", "ezweb.ne.jp",  # JP
    "terra.com.br", "uol.com.br", "bol.com.br",  # BR
    "rediffmail.com", "indiatimes.com", "yahoo.co.in",  # IN
    "protonmail.com", "tutanota.com", "zoho.com"  # Other
]
########################################################################################################################

def generate_email() -> str:
    """
        Generates a random valid email.

        Returns:
            str: The generated email.
    """
    name = random.choice(names)                                                     # Выбираем случайное имя из списка
    domain = random.choice(domains)                                                 # Выбираем случайный домен из списка
    email_type = random.choice(["simple", "with_dot", "with_underscore", "with_number"])  # Выбираем тип email

    # Если email_type равен "simple", возвращается простой email формата name@domain.
    if email_type == "simple":
        return f"{name}@{domain}"  # Простой email формата name@domain

    # Если email_type равен "with_dot", возвращается email, где между именами добавлена точка.
    elif email_type == "with_dot":
        return f"{name}.{random.choice(names)}@{domain}"  # email с точкой между именами

    # Если email_type равен "with_underscore", возвращается email, где между именами добавлено подчеркивание.
    elif email_type == "with_underscore":
        return f"{name}_{random.choice(names)}@{domain}"  # email с подчеркиванием между именами

    # Если email_type не соответствует ни одному из вышеперечисленных, возвращается email с номером в конце.
    else:  # with_number
        return f"{name}{random.randint(1, 9999)}@{domain}"  # email с номером в конце
########################################################################################################################


def generate_invalid_email() -> str:
    """
        Generates a random invalid email.

        Returns:
            str: The generated invalid email.
    """
    # Список invalid_types определяет различные типы невалидных email-адресов, которые могут быть сгенерированы.
    invalid_types = ["no_at", "double_at", "invalid_domain", "invalid_chars"]

    # Выбираем случайный тип невалидного email
    invalid_type = random.choice(invalid_types)

    # Если invalid_type равен "no_at", возвращается невалидный email без символа '@'.
    if invalid_type == "no_at":
        return f"{random.choice(names)}{random.choice(domains)}"  # Невалидный email без символа '@'

    # Если invalid_type равен "double_at", возвращается невалидный email с двумя символами '@'.
    elif invalid_type == "double_at":
        return f"{random.choice(names)}@{random.choice(names)}@{random.choice(domains)}"  # Невалидный email с двумя '@'

    # Если invalid_type равен "invalid_domain", возвращается невалидный email с некорректным доменом.
    elif invalid_type == "invalid_domain":
        return f"{random.choice(names)}@.com"  # Невалидный email с некорректным доменом

    # Если invalid_type не соответствует ни одному из вышеперечисленных, возвращается невалидный email с некорректными
    # символами.
    else:
        return f"{random.choice(names)}!#$%@{random.choice(domains)}"  # Невалидный email с некорректными символами
########################################################################################################################


def generate_test_emails() -> None:
    """
        Generates a test file with email addresses based on the configuration.

        If specified in the configuration, generates invalid emails with a 5% probability.

        Raises:
            FileNotFoundError: If the file specified in the configuration is not found.
    """

    config = get_config()                         # Получаем конфигурацию приложения
    test_data_config = config['test_data']        # Получаем конфигурацию тестовых данных
    filename = test_data_config['file']           # Получаем путь к файлу для записи email
    count = test_data_config['count']             # Получаем количество email для генерации

    # Открываем файл filename для записи ("w"), который затем используем для записи тестовых email-адресов
    with open(filename, "w") as f:
        for _ in range(count):
            if random.random() < 0.05:                                            # 5% шанс генерации невалидного email
                email = generate_invalid_email()                                  # Генерируем невалидный email
            else:
                email = generate_email()                                          # Генерируем валидный email
            f.write(email + "\n")                                                 # Записываем email в файл

    logger.info(f"Test file created with {count} email addresses at {filename}")  # Логируем создание файла
########################################################################################################################

# Вызываем функцию генерации тестовых email при запуске скрипта
########################################################################################################################
if __name__ == "__main__":
    generate_test_emails()
########################################################################################################################
