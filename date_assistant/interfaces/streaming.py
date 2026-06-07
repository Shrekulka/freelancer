# interfaces/streaming.py

from abc import ABC, abstractmethod
from models.recommendation import StreamingAvailability


class StreamingInterface(ABC):
    """
    Абстрактный поиск на стриминговых сервисах.

    Ни Netflix, ни HBO не дают публичного API.
    Используем агрегатор Watchmode API (watchmode.com).
    Watchmode знает какой сериал есть на каком сервисе.

    Альтернативы если Watchmode не устраивает:
    - JustWatch (неофициальный API, богатый)
    - TMDB (бесплатный, но без доступности)
    - streaming-availability.p.rapidapi.com (платный)

    Абстракция позволяет переключиться не трогая бизнес-логику.
    """

    @abstractmethod
    def find_show(
            self,
            title: str,
            platforms: list[str]
    ) -> StreamingAvailability:
        """
        Найти сериал на указанных платформах.

        Args:
            title     : название НА АНГЛИЙСКОМ — для поиска по API
                        "Succession", не "Наследники"
            platforms : ["netflix", "hbo"] — только эти проверяем

        Returns:
            StreamingAvailability с результатами

        Raises:
            StreamingError: ошибка API или сеть
        """
        ...


class StreamingError(Exception):
    """Исключение для ошибок стриминговых API."""
    pass