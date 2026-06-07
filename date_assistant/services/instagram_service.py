# services/instagram_service.py

import re
from interfaces.instagram import InstagramInterface, InstagramError
from models.profile import InstagramProfile
from config.logger_config import get_logger

logger = get_logger(__name__)


class InstagramService:
    """
    Бизнес-логика работы с Instagram.

    ЗАЧЕМ СЕРВИС, ЕСЛИ ЕСТЬ ПРОВАЙДЕР?

    Провайдер = почтальон (доставляет данные)
    Сервис    = офис-менеджер (решает что с ними делать)

    Провайдер знает КАК скачать (HTTP, SDK).
    Сервис знает ЧТО делать: нормализовать, валидировать, логировать.

    DEPENDENCY INJECTION — получаем провайдер через __init__:

    ❌ Жёсткая зависимость:
        class InstagramService:
            def __init__(self):
                self._p = InstaloaderProvider()  # намертво!
                # В тестах нельзя подменить

    ✅ Dependency Injection:
        class InstagramService:
            def __init__(self, provider: InstagramInterface):
                self._p = provider  # любая реализация

        # Продакшен:
        service = InstagramService(InstaloaderProvider())
        # Тест:
        service = InstagramService(MockInstagramProvider())
    """

    def __init__(self, provider: InstagramInterface) -> None:
        self._provider = provider

    def get_profile(self, username: str) -> InstagramProfile:
        """
        Получить и нормализовать профиль Instagram.

        Нормализация обрабатывает все варианты ввода пользователя:
            "@natasha_travels"                → "natasha_travels"
            "https://instagram.com/natasha"   → "natasha"
            " Natasha.TRAVELS "              → "natasha.travels"
        """
        clean = self._normalize_username(username)
        self._validate_username(clean)

        logger.info("Получаем профиль @%s...", clean)
        try:
            profile = self._provider.fetch_profile(clean)
            logger.info(
                "@%s: %d постов, bio=%d символов",
                clean, len(profile.posts), len(profile.bio)
            )
            return profile
        except InstagramError:
            raise  # перебрасываем как есть — use_case обработает
        except Exception as e:
            logger.error("Неожиданная ошибка @%s: %s", clean, e)
            raise InstagramError(
                f"Неожиданная ошибка: {e}",
                username=clean, error_type="unexpected"
            ) from e

    @staticmethod
    def _normalize_username(username: str) -> str:
        """
        Привести username к стандартному виду.

        Обрабатываем все варианты которые может вставить пользователь.
        """
        username = username.strip()
        if username.startswith("@"):
            username = username[1:]
        for prefix in (
                "https://www.instagram.com/",
                "https://instagram.com/",
                "www.instagram.com/",
                "instagram.com/",
        ):
            if username.startswith(prefix):
                username = username[len(prefix):]
                break
        return username.rstrip("/").lower()

    @staticmethod
    def _validate_username(username: str) -> None:
        """
        Проверить корректность username по правилам Instagram.

        Правила Instagram:
        - 1-30 символов
        - Только буквы, цифры, точки, подчёркивания

        Raises:
            ValueError: если username некорректен
        """
        if not username:
            raise ValueError("Username не может быть пустым")
        if len(username) > 30:
            raise ValueError(
                f"Username слишком длинный: {len(username)} символов (макс. 30)"
            )
        if not re.match(r'^[a-zA-Z0-9._]+$', username):
            raise ValueError(
                f"Некорректный username: {username!r}\n"
                "Допустимы только буквы, цифры, точки и подчёркивания"
            )