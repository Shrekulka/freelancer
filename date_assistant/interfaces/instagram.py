# interfaces/instagram.py

from abc import ABC, abstractmethod
from models.profile import InstagramProfile


class InstagramInterface(ABC):
    """
    Абстрактный скрапер Instagram.

    Почему нужна абстракция для Instagram?
    Instagram не даёт публичного API. Способов несколько:
      1. instaloader — Python-библиотека (наш выбор)
      2. Selenium — управляет браузером
      3. Apify/RapidAPI — платные сторонние сервисы
      4. Mock — тестовые данные

    С интерфейсом: меняем реализацию не трогая бизнес-логику.
    Без интерфейса: при смене способа скрапинга переписываем всё.
    """

    @abstractmethod
    def fetch_profile(self, username: str) -> InstagramProfile:
        """
        Получить данные публичного профиля Instagram.

        Args:
            username: без @, нормализованный. Пример: "natasha_travels"

        Raises:
            InstagramError: профиль приватный, не найден, лимит запросов
        """
        ...


class InstagramError(Exception):
    """
    Исключение для ошибок Instagram.

    error_type — машиночитаемый код для разных обработчиков:
        "not_found"          → показать "проверьте username"
        "private"            → показать "профиль закрытый"
        "connection"         → показать "попробуйте позже / VPN"
        "missing_dependency" → показать "pip install instaloader"

    Без error_type пришлось бы парсить строку сообщения — хрупко.
    """

    def __init__(
            self,
            message: str,
            username: str = "",
            error_type: str = "unknown"
    ):
        self.username = username
        self.error_type = error_type
        super().__init__(message)