# providers/watchmode_provider.py

import httpx
from interfaces.streaming import StreamingInterface, StreamingError
from models.recommendation import StreamingAvailability
from config.logger_config import get_logger

logger = get_logger(__name__)

_BASE = "https://api.watchmode.com/v1"
_TIMEOUT = 10.0


class WatchmodeProvider(StreamingInterface):
    """
    Поиск контента через Watchmode API.

    ПОЧЕМУ httpx, А НЕ requests?

    requests:
    - Популярный, но устаревающий
    - Нет нативного async
    - Слабые type hints

    httpx:
    - Современный стандарт
    - Поддерживает sync И async (одно API!)
    - Отличные type hints
    - Для нас нужен sync (CLI, не async) → httpx.Client()

    КАК РАБОТАЕТ WATCHMODE API:

    Шаг 1 — поиск по названию:
        GET /v1/search/?search_field=name&search_value=Succession&types=tv_series&apiKey=...
        → {"title_results": [{"id": 1234567, "name": "Succession", ...}]}

    Шаг 2 — источники для id:
        GET /v1/title/1234567/sources/?regions=US&apiKey=...
        → [{"source_id": 387, "name": "HBO Max", "web_url": "https://max.com/..."}]

    source_id — числовой ID платформы в Watchmode:
        203 = Netflix,  387 = HBO Max,  26 = Prime Video
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise StreamingError("WATCHMODE_API_KEY не задан")
        self._api_key = api_key
        # Создаём клиент один раз — переиспользуем для нескольких запросов
        # timeout применяется ко всем запросам этого клиента
        self._client = httpx.Client(timeout=_TIMEOUT)

    def find_show(
            self, title: str, platforms: list[str]
    ) -> StreamingAvailability:
        logger.info("Ищем '%s' на: %s", title, ", ".join(platforms))

        watchmode_id = self._search_title(title)
        if not watchmode_id:
            logger.warning("'%s' не найден в Watchmode", title)
            return StreamingAvailability(
                title=title, not_available_on=platforms
            )

        sources = self._get_sources(watchmode_id)
        logger.debug("Источников для '%s': %d", title, len(sources))

        from config.settings import config
        available_on = {}
        not_available_on = []

        for platform in platforms:
            source_id = config.watchmode.source_ids.get(platform)
            if source_id is None:
                logger.warning("Неизвестная платформа: %s", platform)
                continue

            # Ищем среди источников совпадение по source_id
            matching = [s for s in sources if s.get("source_id") == source_id]
            if matching:
                url = matching[0].get("web_url", "")
                available_on[platform] = url
                logger.info("  ✅ %s: доступен", platform.upper())
            else:
                not_available_on.append(platform)
                logger.info("  ❌ %s: не найден", platform.upper())

        return StreamingAvailability(
            title=title,
            available_on=available_on,
            not_available_on=not_available_on,
        )

    def _search_title(self, title: str) -> int | None:
        """
        Найти watchmode_id по названию.

        types=tv_series — только сериалы, не фильмы.
        Без этого "Succession" мог бы вернуть фильм с похожим названием.
        """
        try:
            resp = self._client.get(
                f"{_BASE}/search/",
                params={
                    "apiKey": self._api_key,
                    "search_field": "name",
                    "search_value": title,
                    "types": "tv_series",
                }
            )
            resp.raise_for_status()  # raise если 4xx/5xx
            results = resp.json().get("title_results", [])
            if not results:
                return None
            first = results[0]
            logger.debug(
                "Watchmode: id=%s, name=%s", first.get("id"), first.get("name")
            )
            return first.get("id")

        except httpx.TimeoutException:
            raise StreamingError(f"Таймаут при поиске '{title}'")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise StreamingError("Неверный WATCHMODE_API_KEY")
            raise StreamingError(f"HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            raise StreamingError(f"Ошибка сети: {e}")

    def _get_sources(self, watchmode_id: int) -> list[dict]:
        """
        Получить источники (платформы) для тайтла.

        regions=US — без региона возвращаются все регионы,
        source_id дублируется. US = стандарт для Netflix/HBO.
        """
        try:
            resp = self._client.get(
                f"{_BASE}/title/{watchmode_id}/sources/",
                params={"apiKey": self._api_key, "regions": "US"}
            )
            resp.raise_for_status()
            return resp.json()

        except httpx.TimeoutException:
            raise StreamingError(f"Таймаут для id={watchmode_id}")
        except httpx.HTTPStatusError as e:
            raise StreamingError(f"HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            raise StreamingError(f"Ошибка сети: {e}")

    def __del__(self):
        """Закрыть HTTP-соединения при уничтожении объекта."""
        try:
            self._client.close()
        except Exception:
            pass


class MockStreamingProvider(StreamingInterface):
    """
    Тестовый провайдер стриминга.

    ЧЕСТНЫЙ MOCK: не всегда говорит "доступно".
    Основан на словаре известных тайтлов.
    Остальные → "не найдено".

    Это тестирует ВСЕ ветви кода, включая "сериал не на платформах".
    """
    _KNOWN: dict[str, dict] = {
        "succession": {"hbo": "https://www.max.com/shows/succession"},
        "the bear": {"netflix": "https://www.netflix.com/title/81391186"},
        "white lotus": {"hbo": "https://www.max.com/shows/the-white-lotus"},
        "fleabag": {"prime": "https://www.primevideo.com/detail/Fleabag"},
        "ozark": {"netflix": "https://www.netflix.com/title/80117552"},
        "euphoria": {"hbo": "https://www.max.com/shows/euphoria"},
        "the crown": {"netflix": "https://www.netflix.com/title/80025678"},
        "squid game": {"netflix": "https://www.netflix.com/title/81040344"},
        "house of the dragon": {"hbo": "https://www.max.com/shows/house-of-the-dragon"},
        "severance": {"apple": "https://tv.apple.com/us/show/severance"},
    }

    def find_show(
            self, title: str, platforms: list[str]
    ) -> StreamingAvailability:
        logger.info("[MOCK] Ищем '%s' (платформы: %s)", title, platforms)
        known = self._KNOWN.get(title.lower().strip())

        if not known:
            return StreamingAvailability(title=title, not_available_on=platforms)

        available_on = {p: url for p, url in known.items() if p in platforms}
        not_available = [p for p in platforms if p not in known]
        return StreamingAvailability(
            title=title,
            available_on=available_on,
            not_available_on=not_available,
        )