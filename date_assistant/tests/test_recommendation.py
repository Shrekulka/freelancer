# tests/test_recommendation.py

import json
import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.recommendation_service import RecommendationService, _parse_llm_json
from models.profile import InstagramProfile, InstagramPost
from models.recommendation import InterestProfile, ShowRecommendation
from interfaces.llm import LLMInterface, LLMError


class MockLLM(LLMInterface):
    """
    Тестовый LLM — возвращает заранее заданный ответ.

    Зачем Mock, а не реальный Claude?
    - Тесты без API ключей (можно в CI/CD)
    - Детерминированные ответы (тест всегда одинаков)
    - Скорость (нет HTTP запроса)
    - Экономия денег (нет расхода токенов)
    """

    def __init__(self, response: str):
        self._response = response

    def complete(
            self, prompt: str, system: str = "", max_tokens: int = 1024
    ) -> str:
        return self._response

    def get_model_name(self) -> str:
        return "mock-llm"


# Тестовые данные — валидные JSON-ответы
VALID_INTERESTS_JSON = json.dumps({
    "topics": ["путешествия", "кулинария", "йога"],
    "preferred_genres": ["драмы", "комедии"],
    "estimated_age_range": "25-30",
    "lifestyle_tags": ["активный", "foodie"],
    "vibe": "позитивный",
    "notes": "Любит Азию"
})

VALID_RECOMMENDATION_JSON = json.dumps({
    "title": "Succession",
    "title_ru": "Наследники",
    "year": 2018,
    "genre": "Drama, Dark Comedy",
    "description": "История борьбы за власть в медиаимперии.",
    "why_recommended": "Сложные персонажи зацепят интерес к психологии.",
    "alternatives": ["The Bear", "White Lotus", "Fleabag"],
    "imdb_id": "tt7660850"
})

MARKDOWN_WRAPPED = f"```json\n{VALID_INTERESTS_JSON}\n```"
JSON_WITH_PREFIX = f"Вот результат:\n{VALID_INTERESTS_JSON}"


class TestParseLlmJson(unittest.TestCase):
    """
    Тесты парсера JSON из ответов LLM.

    Это критическая функция — от неё зависит весь пайплайн.
    Тестируем все варианты "грязного" вывода LLM.
    """

    def test_clean_json(self):
        result = _parse_llm_json(VALID_INTERESTS_JSON)
        self.assertEqual(result["topics"], ["путешествия", "кулинария", "йога"])

    def test_markdown_wrapped(self):
        """LLM часто оборачивает в ```json ... ```"""
        result = _parse_llm_json(MARKDOWN_WRAPPED)
        self.assertIn("topics", result)

    def test_json_with_text_prefix(self):
        """LLM добавляет текст перед JSON"""
        result = _parse_llm_json(JSON_WITH_PREFIX)
        self.assertIn("topics", result)

    def test_invalid_raises(self):
        """Если JSON не распарсить никак → ValueError"""
        with self.assertRaises(ValueError):
            _parse_llm_json("это просто текст", context="тест")


class TestAnalyzeInterests(unittest.TestCase):
    """Тесты analyze_interests()."""

    def _make_profile(self):
        return InstagramProfile(
            username="test",
            bio="путешествия и еда",
            posts=[
                InstagramPost(caption="Бали", hashtags=["travel", "bali"]),
                InstagramPost(caption="Паста", hashtags=["cooking"]),
            ]
        )

    def test_returns_interest_profile(self):
        service = RecommendationService(MockLLM(VALID_INTERESTS_JSON))
        result = service.analyze_interests(self._make_profile())
        self.assertIsInstance(result, InterestProfile)
        self.assertIn("путешествия", result.topics)

    def test_handles_markdown_response(self):
        service = RecommendationService(MockLLM(MARKDOWN_WRAPPED))
        result = service.analyze_interests(self._make_profile())
        self.assertIsInstance(result, InterestProfile)

    def test_propagates_llm_error(self):
        """LLMError прокидывается без изменений."""
        llm = MagicMock(spec=LLMInterface)
        llm.complete.side_effect = LLMError("API недоступен", provider="mock")
        llm.get_model_name.return_value = "mock"
        service = RecommendationService(llm)

        with self.assertRaises(LLMError):
            service.analyze_interests(self._make_profile())

    def test_invalid_json_raises(self):
        """Если LLM вернул не JSON → ValueError."""
        service = RecommendationService(
            MockLLM("Не могу проанализировать.")
        )
        with self.assertRaises(ValueError):
            service.analyze_interests(self._make_profile())


class TestRecommendShow(unittest.TestCase):
    """Тесты recommend_show()."""

    def _make_interests(self):
        return InterestProfile(
            topics=["путешествия", "кулинария"],
            vibe="позитивный",
        )

    def test_returns_show_recommendation(self):
        service = RecommendationService(MockLLM(VALID_RECOMMENDATION_JSON))
        result = service.recommend_show(self._make_interests())
        self.assertIsInstance(result, ShowRecommendation)
        self.assertEqual(result.title, "Succession")
        self.assertEqual(result.year, 2018)
        self.assertEqual(len(result.alternatives), 3)

    def test_raises_on_missing_title(self):
        """Если нет title → ValueError."""
        bad = json.dumps({"year": 2020, "genre": "Drama"})
        service = RecommendationService(MockLLM(bad))
        with self.assertRaises(ValueError) as ctx:
            service.recommend_show(self._make_interests())
        self.assertIn("названия", str(ctx.exception))


class TestInterestProfilePromptText(unittest.TestCase):
    """Тесты сериализации InterestProfile."""

    def test_includes_all_fields(self):
        p = InterestProfile(
            topics=["путешествия"],
            preferred_genres=["драмы"],
            vibe="позитивный",
            notes="Любит Азию",
        )
        text = p.to_prompt_text()
        self.assertIn("путешествия", text)
        self.assertIn("драмы", text)
        self.assertIn("позитивный", text)
        self.assertIn("Любит Азию", text)

    def test_empty_fields_omitted(self):
        """Пустые поля не добавляют лишних строк."""
        p = InterestProfile(topics=["путешествия"])
        text = p.to_prompt_text()
        self.assertNotIn("None", text)
        self.assertNotIn("Жанры:", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)