# email_blast/csv_reader.py

import csv
from typing import List, Dict

import aiofiles


class CSVReader:
    """
        Class for reading data from a CSV file.

        Methods:
            async read_recipients(filename: str) -> List[Dict[str, str]]:
                Asynchronously reads data from a CSV file and returns a list of dictionaries with recipient data.
    """
    @staticmethod
    async def read_recipients(filename: str) -> List[Dict[str, str]]:
        """
            Asynchronously reads data from a CSV file and returns a list of dictionaries with recipient data.

            Args:
                filename (str): Name of the CSV file.

            Returns:
                List[Dict[str, str]]: List of dictionaries with recipient data (email, name, link).

            Raises:
                ValueError: If the CSV file is empty or doesn't contain the required columns.
        """
        # Открываем CSV-файл асинхронно для чтения
        async with aiofiles.open(filename, mode='r', encoding='utf-8', newline='') as csvfile:
            # Читаем содержимое файла
            content = await csvfile.read()
            # Создаем объект DictReader для чтения CSV-данных в виде словаря
            reader = csv.DictReader(content.splitlines())

            # Проверяем, пуст ли файл
            if not reader.fieldnames:
                raise ValueError("The CSV file is empty or invalid.")

            # Определяем необходимые столбцы
            required_columns = {'email', 'name', 'link'}
            # Проверяем, содержит ли файл все необходимые столбцы
            if not required_columns.issubset(reader.fieldnames):
                # Определяем отсутствующие столбцы
                missing_columns = required_columns - set(reader.fieldnames)
                # Вызываем исключение ValueError с информацией о пропущенных столбцах
                raise ValueError(f"Missing required columns in CSV: {', '.join(missing_columns)}")

            # Формируем список словарей с данными получателей, очищая значения от лишних пробелов
            return [{
                'email': row['email'].strip(),
                'name': row['name'].strip(),
                'link': row['link'].strip()
            } for row in reader]
