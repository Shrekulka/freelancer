# config/provider_factory.py

from interfaces.llm import LLMInterface
from interfaces.instagram import InstagramInterface
from interfaces.streaming import StreamingInterface
from config.settings import config
from config.logger_config import get_logger

logger = get_logger(__name__)


class ProviderFactory:
    """
    Фабрика провайдеров.

    БЕЗ фабрики — логика создания размазана по всему коду:
        # В use_cases/analyze_profile.py:
        if config.app.default_llm == "claude":
            llm = ClaudeProvider(config.anthropic.api_key, config.anthropic.model)
        elif config.app.default_llm == "openai":
            llm = OpenAIProvider(config.openai.api_key, config.openai.model)
        # ... и то же самое в тестах, и возможно в других местах

    С фабрикой — одна строка везде:
        llm = ProviderFactory.create_llm()

    Добавить новый провайдер?
    Добавляем elif в фабрику — весь остальной код не меняется.

    Все методы @staticmethod — не нужен экземпляр ProviderFactory,
    просто вызываем ProviderFactory.create_llm().
    """

    @staticmethod
    def create_llm(provider_name: str = None) -> LLMInterface:
        """
        Создать LLM-провайдер.

        Args:
            provider_name: None = из config.app.default_llm

        Пример:
            llm = ProviderFactory.create_llm()           # из .env
            llm = ProviderFactory.create_llm("openai")   # явно
            llm = ProviderFactory.create_llm("deepseek") # дешевле для тестов

        Почему импорты ВНУТРИ if, а не вверху файла?

        Причина 1 — не падать если пакет не установлен:
            import anthropic  # вверху файла: упадёт даже если используем openai
            # Если установлен только openai — импорт anthropic сломает запуск

        Причина 2 — избежать circular imports:
            providers/claude_provider.py импортирует config.settings
            config.provider_factory импортировал бы claude_provider вверху
            → circular import
        """
        name = provider_name or config.app.default_llm
        logger.info("Создаём LLM провайдер: %s", name)

        if name == "claude":
            from providers.claude_provider import ClaudeProvider
            return ClaudeProvider(
                api_key=config.anthropic.api_key,
                model=config.anthropic.model,
            )
        elif name == "openai":
            from providers.openai_provider import OpenAIProvider
            return OpenAIProvider(
                api_key=config.openai.api_key,
                model=config.openai.model,
            )
        elif name == "deepseek":
            from providers.deepseek_provider import DeepSeekProvider
            return DeepSeekProvider(
                api_key=config.deepseek.api_key,
                model=config.deepseek.model,
                base_url=config.deepseek.base_url,
            )
        else:
            raise ValueError(
                f"Неизвестный LLM: {name!r}. Доступные: claude, openai, deepseek"
            )

    @staticmethod
    def create_instagram() -> InstagramInterface:
        """
        Создать Instagram-провайдер.

        Автовыбор: если INSTAGRAM_USE_MOCK=true → MockInstagramProvider.

        Это позволяет разрабатывать без интернета:
            INSTAGRAM_USE_MOCK=true python main.py anyname

        И запускать CI/CD без зависимости от Instagram:
            # В GitHub Actions:
            INSTAGRAM_USE_MOCK=true pytest tests/
        """
        use_mock = config.instagram.use_mock
        logger.info("Instagram провайдер: %s", "MOCK" if use_mock else "REAL")

        if use_mock:
            from providers.instagram_provider import MockInstagramProvider
            return MockInstagramProvider()

        from providers.instagram_provider import InstaloaderInstagramProvider
        return InstaloaderInstagramProvider(
            max_posts=config.instagram.max_posts,
            request_delay=config.instagram.request_delay,
        )

    @staticmethod
    def create_streaming() -> StreamingInterface:
        """
        Создать провайдер стриминговых сервисов.

        Если WATCHMODE_API_KEY не задан → MockStreamingProvider.
        Mock возвращает "не найдено" — честно показывает что ключ нужен,
        но не ломает всё приложение.
        """
        has_key = bool(config.watchmode.api_key)
        logger.info("Streaming провайдер: %s", "WATCHMODE" if has_key else "MOCK")

        if not has_key:
            from providers.watchmode_provider import MockStreamingProvider
            return MockStreamingProvider()

        from providers.watchmode_provider import WatchmodeProvider
        return WatchmodeProvider(api_key=config.watchmode.api_key)