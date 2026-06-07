# config/settings.py

from dataclasses import dataclass, field
from typing import Optional
from environs import Env
from config.logger_config import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# ПОЧЕМУ @dataclass ДЛЯ КАЖДОЙ СЕКЦИИ?
#
# ❌ Плоский Config (как старый settings.py):
#     config.ANTHROPIC_API_KEY
#     config.ANTHROPIC_MODEL
#     config.WATCHMODE_API_KEY    ← всё в одной куче
#     config.INSTAGRAM_MAX_POSTS
#
# ✅ Структурированный Config (как в примере fit_trainer_bot):
#     config.anthropic.api_key   ← сразу видно группировку
#     config.anthropic.model
#     config.watchmode.api_key
#     config.instagram.max_posts
#
# IDE подсказывает атрибуты секции. Как папки на диске vs всё в корне.
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class AnthropicConfig:
    api_key: str  # sk-ant-api03-...
    model: str  # claude-sonnet-4-20250514


@dataclass
class OpenAIConfig:
    api_key: str  # sk-proj-...
    model: str  # gpt-4o


@dataclass
class DeepSeekConfig:
    api_key: str
    model: str
    base_url: str  # https://api.deepseek.com


@dataclass
class InstagramConfig:
    max_posts: int  # сколько постов скачать
    request_delay: float  # пауза между запросами (защита от бана)
    use_mock: bool  # True = тестовые данные


@dataclass
class WatchmodeConfig:
    """
    Почему source_ids прямо в конфиге, а не в провайдере?

    Это данные конфигурации: числовые ID платформ в системе Watchmode.
    Они могут измениться (Watchmode обновит API) — тогда меняем здесь.
    Провайдер не должен содержать "магические числа".

    Полный список: https://api.watchmode.com/v1/sources/
    """
    api_key: str
    user_platforms: list  # ["netflix", "hbo"]
    source_ids: dict = field(default_factory=lambda: {
        "netflix": 203,
        "hbo": 387,
        "prime": 26,
        "disney": 372,
        "apple": 371,
    })


@dataclass
class AppConfig:
    debug: bool
    default_llm: str  # "claude" | "openai" | "deepseek"


@dataclass
class Config:
    """
    Главный класс конфигурации — агрегирует все секции.

    ПАТТЕРН ИЗ ПРИМЕРА fit_trainer_bot:
        config: Config = Config()  # строка в конце файла

    Python кеширует модули. Первый import → выполняет этот код.
    Все последующие импорты → возвращают тот же объект из кеша.
    Это фактически синглтон без паттерна Singleton.

    ИСПОЛЬЗОВАНИЕ везде в проекте:
        from config.settings import config
        key = config.anthropic.api_key
        model = config.anthropic.model
        platforms = config.watchmode.user_platforms
    """

    # Аннотации типов (значения заполняются в __init__)
    anthropic: AnthropicConfig
    openai: OpenAIConfig
    deepseek: DeepSeekConfig
    instagram: InstagramConfig
    watchmode: WatchmodeConfig
    app: AppConfig

    def __init__(self, env_path: Optional[str] = None) -> None:
        """
        Читаем .env и заполняем все секции.

        ПОЧЕМУ environs, А НЕ os.getenv?

        os.getenv версия — много ручной работы:
            max_posts = int(os.getenv("INSTAGRAM_MAX_POSTS", "20"))
            # Если INSTAGRAM_MAX_POSTS="abc" → ValueError: invalid literal
            # Ошибка непонятная: нет имени переменной в traceback

        environs версия — чисто и безопасно:
            max_posts = env.int("INSTAGRAM_MAX_POSTS", 20)
            # Если INSTAGRAM_MAX_POSTS="abc" → EnvValidationError: INSTAGRAM_MAX_POSTS
            # Ошибка понятная: имя переменной в сообщении

        Плюсы environs:
        ✅ env.int()   — автоматически int, понятная ошибка
        ✅ env.float() — автоматически float
        ✅ env.bool()  — "true"/"1"/"yes" → True, "false"/"0"/"no" → False
        ✅ env.list()  — "netflix,hbo" → ["netflix", "hbo"]
        """
        _env = Env()

        # Ищем .env в корне проекта (на уровень выше config/)
        from pathlib import Path
        _base = Path(__file__).parent.parent
        _dotenv = _base / ".env" if env_path is None else Path(env_path)

        if _dotenv.exists():
            _env.read_env(str(_dotenv))
            logger.debug("Загружен .env: %s", _dotenv)
        else:
            logger.warning(
                ".env не найден (%s), используем переменные окружения", _dotenv
            )

        # Заполняем каждую секцию
        self.anthropic = AnthropicConfig(
            api_key=_env("ANTHROPIC_API_KEY", ""),
            model=_env("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        )
        self.openai = OpenAIConfig(
            api_key=_env("OPENAI_API_KEY", ""),
            model=_env("OPENAI_MODEL", "gpt-4o"),
        )
        self.deepseek = DeepSeekConfig(
            api_key=_env("DEEPSEEK_API_KEY", ""),
            model=_env("DEEPSEEK_MODEL", "deepseek-chat"),
            base_url=_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        self.instagram = InstagramConfig(
            max_posts=_env.int("INSTAGRAM_MAX_POSTS", 20),
            request_delay=_env.float("INSTAGRAM_REQUEST_DELAY", 2.0),
            use_mock=_env.bool("INSTAGRAM_USE_MOCK", False),
        )
        self.watchmode = WatchmodeConfig(
            api_key=_env("WATCHMODE_API_KEY", ""),
            # env.list() — "netflix,hbo" → ["netflix", "hbo"] за одну строку
            user_platforms=_env.list("USER_PLATFORMS", ["netflix", "hbo"]),
        )
        self.app = AppConfig(
            debug=_env.bool("DEBUG", False),
            default_llm=_env("DEFAULT_LLM_PROVIDER", "claude"),
        )

    def validate(self) -> list[str]:
        """
        Проверить конфигурацию перед запуском.

        Вызывается в main() ДО начала работы.
        Лучше упасть с понятным сообщением сразу,
        чем через 15 секунд скрапинга на шаге 2.

        Возвращает список ошибок (пустой = всё ок).
        Строки начинающиеся с "⚠️" — предупреждения (не критично).
        Остальные — критические ошибки (без них не запустить).

        Использование в main():
            errors = config.validate()
            warnings  = [e for e in errors if e.startswith("⚠️")]
            critical  = [e for e in errors if not e.startswith("⚠️")]
            for w in warnings: print(w)
            if critical:
                for e in critical: print(f"  ❌ {e}")
                sys.exit(1)
        """
        errors: list[str] = []

        llm = self.app.default_llm
        if llm == "claude" and not self.anthropic.api_key:
            errors.append(
                "ANTHROPIC_API_KEY не задан в .env\n"
                "  Получить: https://console.anthropic.com/settings/keys"
            )
        elif llm == "openai" and not self.openai.api_key:
            errors.append("OPENAI_API_KEY не задан в .env")
        elif llm == "deepseek" and not self.deepseek.api_key:
            errors.append("DEEPSEEK_API_KEY не задан в .env")
        elif llm not in ("claude", "openai", "deepseek"):
            errors.append(
                f"Неверный DEFAULT_LLM_PROVIDER={llm!r}. "
                "Допустимые: claude, openai, deepseek"
            )

        if not self.watchmode.api_key:
            # Предупреждение — без него работаем, просто нет ссылок
            errors.append(
                "⚠️  WATCHMODE_API_KEY не задан — поиск по платформам отключён\n"
                "   Регистрация: https://watchmode.com/ (бесплатно)"
            )

        return errors

    def show(self) -> None:
        """Вывести настройки без секретных значений (для --config)."""

        def mask(key: str) -> str:
            if not key:
                return "(не задан)"
            if len(key) > 8:
                return f"{'*' * 8}...{key[-4:]}"
            return key

        print("⚙️  ТЕКУЩИЕ НАСТРОЙКИ:")
        print(f"  LLM провайдер:    {self.app.default_llm}")
        print(f"  Claude модель:    {self.anthropic.model}")
        print(f"  Anthropic API:    {mask(self.anthropic.api_key)}")
        print(f"  OpenAI API:       {mask(self.openai.api_key)}")
        print(f"  DeepSeek API:     {mask(self.deepseek.api_key)}")
        print(f"  Watchmode API:    {mask(self.watchmode.api_key)}")
        print(f"  Instagram постов: {self.instagram.max_posts}")
        print(f"  Instagram mock:   {self.instagram.use_mock}")
        print(f"  Платформы:        {', '.join(self.watchmode.user_platforms)}")
        print(f"  Debug:            {self.app.debug}")


# ──────────────────────────────────────────────────────────────────────────
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР — аналог fit_trainer_bot: config: Config = Config()
# ──────────────────────────────────────────────────────────────────────────
config: Config = Config()