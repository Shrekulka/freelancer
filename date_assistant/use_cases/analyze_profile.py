# use_cases/analyze_profile.py

from config.provider_factory import ProviderFactory
from config.settings import config
from models.recommendation import FinalRecommendation, ShowRecommendation
from services.instagram_service import InstagramService
from services.recommendation_service import RecommendationService
from services.streaming_service import StreamingService
from interfaces.instagram import InstagramError
from interfaces.llm import LLMError
from interfaces.streaming import StreamingError
from config.logger_config import get_logger

logger = get_logger(__name__)

class AnalyzeProfileUseCase:
    def __init__(self, ig_service=None, rec_service=None, str_service=None, platforms=None):
        self._platforms = platforms or config.watchmode.user_platforms
        self._ig = ig_service or InstagramService(ProviderFactory.create_instagram())
        self._rec = rec_service or RecommendationService(ProviderFactory.create_llm())
        self._str = str_service or StreamingService(ProviderFactory.create_streaming(), self._platforms)

    # --- FIXED: метод для смены LLM провайдера ---
    def set_llm(self, llm):
        """Позволяет заменить LLM провайдер после создания use_case (например, из CLI)."""
        self._rec = RecommendationService(llm)
        logger.info("LLM провайдер изменён на %s", llm.get_model_name())

    def execute(self, username: str) -> FinalRecommendation:
        print(f"\n🔍 Анализирую профиль @{username}...")
        print("━" * 50)

        print("📸 Шаг 1/4: Скрапим Instagram...")
        try:
            profile = self._ig.get_profile(username)
        except InstagramError as e:
            self._handle_instagram_error(e, username)
            raise
        print(f"  ✅ Профиль: {len(profile.posts)} постов, {len(profile.hashtags_used)} хэштегов")

        print(f"\n🧠 Шаг 2/4: Анализируем интересы [{self._rec._llm.get_model_name()}]...")
        try:
            interests = self._rec.analyze_interests(profile)
        except LLMError as e:
            print(f"  ❌ Ошибка LLM: {e}")
            raise
        print(f"  ✅ Интересы: {', '.join(interests.topics[:4])}")
        if interests.vibe:
            print(f"  ✅ Настроение: {interests.vibe}")

        print("\n🎬 Шаг 3/4: Подбираем сериал...")
        try:
            show = self._rec.recommend_show(interests)
        except LLMError as e:
            print(f"  ❌ Ошибка LLM: {e}")
            raise
        print(f"  ✅ Рекомендован: {show.title} ({show.year})")

        print("\n📺 Шаг 4/4: Ищем на Netflix и HBO...")
        # --- FIXED: обрабатываем StreamingError и получаем реальный найденный тайтл ---
        try:
            streaming, actual_title = self._str.find_show_availability(show)
        except StreamingError as e:
            print(f"  ⚠️ Ошибка при поиске на стримингах: {e}")
            streaming = None
            actual_title = show.title

        # --- FIXED: если найден альтернативный сериал, обновляем show.title ---
        if actual_title != show.title:
            print(f"  ℹ️ Альтернатива: '{actual_title}' вместо '{show.title}'")
            show.title = actual_title
            # также можно обновить описание, но оставим как есть

        if streaming and streaming.is_available:
            best = streaming.get_best_platform(self._platforms)
            platform = best[0].upper() if best else "?"
            print(f"  ✅ Доступен на: {platform}")
        else:
            print("  ⚠️  Не в подписках — ищем альтернативу...")

        print("━" * 50)
        return FinalRecommendation(
            username=profile.username,
            interests=interests,
            show=show,
            streaming=streaming,
        )

    @staticmethod
    def _handle_instagram_error(error: InstagramError, username: str) -> None:
        messages = {
            "not_found": f"❌ Профиль @{username} не найден.\n   Проверьте username.",
            "private": f"❌ Профиль @{username} приватный.\n   Только публичные профили.",
            "connection": "❌ Нет соединения с Instagram.\n   Попробуйте позже или VPN.",
            "missing_dependency": "❌ Не установлен instaloader.\n   pip install instaloader",
        }
        msg = messages.get(error.error_type, f"❌ Instagram: {error}")
        print(f"\n{msg}")