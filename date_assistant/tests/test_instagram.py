# tests/test_instagram.py

"""
Юнит-тесты для Instagram-слоя.

КАК ЗАПУСТИТЬ:
    python -m pytest tests/ -v
    python -m pytest tests/test_instagram.py -v -k "test_normalize"

ФИЛОСОФИЯ ТЕСТИРОВАНИЯ:

  Тестируем: бизнес-логику (нормализация, валидация), работу с Mock
  НЕ тестируем: реальный скрапинг, внешние API (медленно, нестабильно)

  Принцип: тестируем собственный код в изоляции от внешних сервисов.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

# Добавляем корень проекта в sys.path для корректных импортов при запуске тестов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.instagram_service import InstagramService
from providers.instagram_provider import MockInstagramProvider
from models.profile import InstagramProfile, InstagramPost
from interfaces.instagram import InstagramError


class TestNormalization(unittest.TestCase):
    """
    Тесты нормализации username.

    Тестируем _normalize_username — это @staticmethod,
    можно вызывать без экземпляра класса.
    """

    def test_removes_at_sign(self):
        """@username → username"""
        result = InstagramService._normalize_username("@natasha_travels")
        self.assertEqual(result, "natasha_travels")

    def test_strips_whitespace(self):
        result = InstagramService._normalize_username("  natasha_travels  ")
        self.assertEqual(result, "natasha_travels")

    def test_lowercases(self):
        result = InstagramService._normalize_username("Natasha.Travels")
        self.assertEqual(result, "natasha.travels")

    def test_removes_full_url(self):
        result = InstagramService._normalize_username(
            "https://www.instagram.com/natasha"
        )
        self.assertEqual(result, "natasha")

    def test_removes_url_without_www(self):
        result = InstagramService._normalize_username(
            "https://instagram.com/natasha"
        )
        self.assertEqual(result, "natasha")

    def test_removes_trailing_slash(self):
        result = InstagramService._normalize_username("natasha/")
        self.assertEqual(result, "natasha")

    def test_at_and_spaces_combined(self):
        result = InstagramService._normalize_username(" @Natasha ")
        self.assertEqual(result, "natasha")


class TestValidation(unittest.TestCase):
    """Тесты валидации username."""

    def test_valid_passes(self):
        """Корректный username не бросает исключение."""
        InstagramService._validate_username("natasha_travels")  # норм
        InstagramService._validate_username("natasha.travels.2024")  # норм
        InstagramService._validate_username("user123")  # норм

    def test_empty_raises(self):
        with self.assertRaises(ValueError) as ctx:
            InstagramService._validate_username("")
        self.assertIn("пустым", str(ctx.exception))

    def test_too_long_raises(self):
        with self.assertRaises(ValueError) as ctx:
            InstagramService._validate_username("a" * 31)
        self.assertIn("длинный", str(ctx.exception))

    def test_at_inside_raises(self):
        """@ внутри username — некорректно (после нормализации убирается)."""
        with self.assertRaises(ValueError):
            InstagramService._validate_username("natasha@travels")

    def test_space_inside_raises(self):
        with self.assertRaises(ValueError):
            InstagramService._validate_username("natasha travels")


class TestServiceWithMock(unittest.TestCase):
    """
    Тесты InstagramService с MockInstagramProvider.

    Проверяем что сервис правильно оркестрирует провайдер.
    Реальный Instagram не нужен — MockInstagramProvider возвращает
    заготовленные данные.
    """

    def setUp(self):
        """setUp() вызывается перед каждым test_* методом."""
        self.service = InstagramService(provider=MockInstagramProvider())

    def test_returns_instagram_profile(self):
        profile = self.service.get_profile("natasha_travels")
        self.assertIsInstance(profile, InstagramProfile)

    def test_normalizes_at_sign(self):
        """@ убирается до вызова провайдера."""
        profile = self.service.get_profile("@natasha_travels")
        self.assertIsNotNone(profile)

    def test_profile_has_posts(self):
        profile = self.service.get_profile("test_user")
        self.assertGreater(len(profile.posts), 0)

    def test_profile_has_hashtags(self):
        """__post_init__ агрегирует хэштеги автоматически."""
        profile = self.service.get_profile("test_user")
        self.assertGreater(len(profile.hashtags_used), 0)

    def test_propagates_instagram_error(self):
        """
        InstagramError от провайдера должна дойти до caller'а.

        MagicMock — объект-заглушка который можно настроить
        бросать исключения при вызове методов.

        side_effect = исключение которое бросить при вызове метода.
        """
        failing_provider = MagicMock()
        failing_provider.fetch_profile.side_effect = InstagramError(
            "Профиль не найден", error_type="not_found"
        )
        service = InstagramService(provider=failing_provider)

        with self.assertRaises(InstagramError):
            service.get_profile("nonexistent")


class TestInstagramPost(unittest.TestCase):
    """Тесты модели InstagramPost."""

    def test_get_all_text_combines(self):
        post = InstagramPost(
            caption="Привет из Бали!",
            hashtags=["bali", "travel"],
        )
        text = post.get_all_text()
        self.assertIn("Привет из Бали!", text)
        self.assertIn("#bali", text)
        self.assertIn("#travel", text)

    def test_empty_caption_works(self):
        post = InstagramPost(hashtags=["yoga"])
        self.assertIn("#yoga", post.get_all_text())

    def test_empty_hashtags_works(self):
        post = InstagramPost(caption="Просто фото")
        self.assertEqual(post.get_all_text(), "Просто фото")


class TestInstagramProfile(unittest.TestCase):
    """Тесты модели InstagramProfile."""

    def _make(self) -> InstagramProfile:
        return InstagramProfile(
            username="test",
            bio="тест",
            posts=[
                InstagramPost(hashtags=["travel", "bali"]),
                InstagramPost(hashtags=["travel", "yoga"]),
                InstagramPost(hashtags=["food"]),
            ]
        )

    def test_hashtags_aggregated_on_init(self):
        p = self._make()
        self.assertIn("travel", p.hashtags_used)

    def test_most_common_first(self):
        """travel встречается 2 раза — должен быть первым."""
        p = self._make()
        self.assertEqual(p.hashtags_used[0], "travel")

    def test_text_includes_bio(self):
        text = self._make().get_text_for_analysis()
        self.assertIn("тест", text)

    def test_text_includes_hashtags(self):
        text = self._make().get_text_for_analysis()
        self.assertIn("travel", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)