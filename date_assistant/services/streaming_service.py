# services/streaming_service.py

from interfaces.streaming import StreamingInterface, StreamingError
from models.recommendation import ShowRecommendation, StreamingAvailability
from config.logger_config import get_logger

logger = get_logger(__name__)

class StreamingService:
    def __init__(self, provider: StreamingInterface, platforms: list[str]):
        self._provider = provider
        self._platforms = platforms

    def find_show_availability(self, show: ShowRecommendation) -> tuple[StreamingAvailability, str]:
        """
        Ищет сериал на платформах.
        Возвращает (StreamingAvailability, actual_title).
        actual_title — название сериала, который реально был найден
        (может отличаться от show.title, если использована альтернатива).
        """
        logger.info("Ищем '%s' на: %s", show.title, ", ".join(self._platforms))

        # Шаг 1: главный сериал
        result = self._try_find(show.title)
        if result and result.is_available:
            return result, show.title

        # Шаг 2: альтернативы
        if show.alternatives:
            logger.info("Пробуем альтернативы: %s", show.alternatives)
            for alt in show.alternatives:
                result = self._try_find(alt)
                if result and result.is_available:
                    return result, alt   # возвращаем реальное название альтернативы

        # Шаг 3: ничего не нашли
        return StreamingAvailability(title=show.title, not_available_on=self._platforms), show.title

    def _try_find(self, title: str) -> StreamingAvailability | None:
        try:
            return self._provider.find_show(title, self._platforms)
        except StreamingError as e:
            logger.warning("Ошибка поиска '%s': %s", title, e)
            return None