# services/recommendation_service.py

import json
import re
from pathlib import Path
from interfaces.llm import LLMInterface, LLMError
from models.profile import InstagramProfile
from models.recommendation import InterestProfile, ShowRecommendation
from config.logger_config import get_logger

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    """
    Загрузить промпт из файла.
    Загружаем один раз в __init__ RecommendationService, не при каждом вызове.
    """
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Промпт не найден: {path}\n"
            "Создайте файлы prompts/interests.txt и prompts/recommendations.txt"
        )
    return path.read_text(encoding="utf-8")


def _parse_llm_json(text: str, context: str = "") -> dict:
    """
    Распарсить JSON из ответа LLM — устойчиво к "мусору".

    ПРОБЛЕМА: LLM не всегда возвращает чистый JSON.
    Типичные нарушения:

    1. Markdown обёртка:
```json
       {"topics": ["travel"]}
```

    2. Текст перед JSON:
       "Вот результат анализа:
       {"topics": ["travel"]}"

    3. Trailing comma (невалидный JSON):
       {"topics": ["travel",]}

    4. Ключи без кавычек:
       {topics: ["travel"]}

    СТРАТЕГИЯ — пробуем по очереди:
    1. Прямой json.loads() — самый быстрый
    2. Вырезать markdown блок ```json...```
    3. Вырезать первый { ... } из текста
    4. json_repair если установлен
    5. Raise ValueError с подробным сообщением
    """
    text = text.strip()

    # Попытка 1: прямой парсинг
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Попытка 2: markdown блок
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # Попытка 3: вырезать первый JSON-объект
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    # Попытка 4: json_repair (опциональная зависимость)
    try:
        from json_repair import repair_json
        return json.loads(repair_json(text))
    except (ImportError, Exception):
        pass

    raise ValueError(
        f"Не удалось распарсить JSON ({context}).\n"
        f"Ответ LLM:\n{text[:500]}\n\n"
        "Проверьте промпт — он должен требовать ТОЛЬКО JSON."
    )


class RecommendationService:
    """
    Двухшаговый сервис рекомендации сериала через LLM.

    ШАГ 1: analyze_interests(profile) → InterestProfile
        Промпт: prompts/interests.txt
        Вход:  текст профиля Instagram
        Выход: JSON → InterestProfile

    ШАГ 2: recommend_show(interests) → ShowRecommendation
        Промпт: prompts/recommendations.txt
        Вход:  InterestProfile.to_prompt_text()
        Выход: JSON → ShowRecommendation

    Dependency Injection: получаем LLMInterface → любой провайдер.
    """

    def __init__(self, llm: LLMInterface) -> None:
        self._llm = llm
        # Загружаем промпты ОДИН РАЗ — не читать файл при каждом вызове
        self._interests_tpl = _load_prompt("interests.txt")
        self._recommendations_tpl = _load_prompt("recommendations.txt")
        logger.debug("RecommendationService: модель %s", llm.get_model_name())

    def analyze_interests(self, profile: InstagramProfile) -> InterestProfile:
        """
        Шаг 1: Анализ интересов через LLM.

        ПРОМПТ-ИНЖИНИРИНГ — ключевые техники в interests.txt:

        1. "ВЕРНИ СТРОГО JSON без markdown"
           Без этого LLM добавляет ```json ... ``` или пояснения.

        2. Пример формата ответа в промпте
           LLM следует примеру. Пример JSON = гарантия правильной структуры.

        3. "Анализируй ТОЛЬКО то что есть, не придумывай"
           Без этого LLM галлюцинирует интересы которых нет в профиле.

        4. Шаблон {profile_text} — подставляем реальные данные
        """
        profile_text = profile.get_text_for_analysis()
        logger.info(
            "Анализируем интересы @%s (%d символов)...",
            profile.username, len(profile_text)
        )

        prompt = self._interests_tpl.replace("{profile_text}", profile_text)

        try:
            response = self._llm.complete(prompt=prompt, max_tokens=800)
        except LLMError:
            raise

        data = _parse_llm_json(response, context="анализ интересов")

        interests = InterestProfile(
            topics=data.get("topics", []),
            preferred_genres=data.get("preferred_genres", []),
            estimated_age_range=data.get("estimated_age_range", ""),
            lifestyle_tags=data.get("lifestyle_tags", []),
            vibe=data.get("vibe", ""),
            notes=data.get("notes", ""),
        )

        logger.info(
            "Интересы: %s | vibe: %s",
            ", ".join(interests.topics[:3]),
            interests.vibe or "(не определён)"
        )
        return interests

    def recommend_show(self, interests: InterestProfile) -> ShowRecommendation:
        """
        Шаг 2: Подбор сериала через LLM.

        ПРОМПТ-ИНЖИНИРИНГ — ключевые техники в recommendations.txt:

        1. Контекст "романтический вечер вдвоём"
           Задаёт критерии: не слишком мрачный, для двоих, с первых серий.

        2. Ограничение платформ "Netflix или HBO Max"
           LLM учитывает доступность при выборе.

        3. "why_recommended — КОНКРЕТНО с отсылкой к её интересам"
           Это главная часть! Даёт тему для разговора на свидании.

        4. 3 альтернативы — если главный не найден на платформах,
           StreamingService автоматически проверит альтернативы.
        """
        interests_text = interests.to_prompt_text()
        logger.info("Подбираем сериал...")

        prompt = self._recommendations_tpl.replace(
            "{interests_text}", interests_text
        )

        try:
            response = self._llm.complete(prompt=prompt, max_tokens=1000)
        except LLMError:
            raise

        data = _parse_llm_json(response, context="рекомендация сериала")

        show = ShowRecommendation(
            title=data.get("title", ""),
            title_ru=data.get("title_ru", ""),
            year=data.get("year", 0),
            genre=data.get("genre", ""),
            description=data.get("description", ""),
            why_recommended=data.get("why_recommended", ""),
            alternatives=data.get("alternatives", []),
        )

        if not show.title:
            raise ValueError("LLM вернул рекомендацию без названия сериала")

        logger.info(
            "Рекомендован: '%s' (%d) | Альтернативы: %s",
            show.title, show.year, ", ".join(show.alternatives) or "(нет)"
        )
        return show