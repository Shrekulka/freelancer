FROM python:3.13-slim

# Установка рабочей директории
WORKDIR /app

# Установка переменной для вывода логов Python без буферизации
ENV PYTHONUNBUFFERED=1

# Установка зависимостей системы (только postgresql-client для отладки, gcc удалён)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements.txt и установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Копируем и делаем исполняемым entrypoint.sh
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Используем entrypoint для миграций и создания суперпользователя
ENTRYPOINT ["/app/entrypoint.sh"]

# Запуск Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:$PORT"]