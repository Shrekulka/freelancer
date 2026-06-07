# providers/instagram_provider.py
import re
import time
import json
from pathlib import Path
from interfaces.instagram import InstagramInterface, InstagramError
from models.profile import InstagramProfile, InstagramPost
from config.logger_config import get_logger

logger = get_logger(__name__)


class InstaloaderInstagramProvider(InstagramInterface):
    """
    Реальный скрапер через библиотеку instaloader.

    КАК РАБОТАЕТ instaloader:
        import instaloader
        L = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(L.context, "natasha")

        print(profile.biography)      # bio
        print(profile.followers)      # подписчики

        for post in profile.get_posts():
            print(post.caption)       # текст поста
            print(post.likes)         # лайки

    ОГРАНИЧЕНИЯ Instagram:
    - Только публичные профили
    - Rate limit: ~200 постов/час без авторизации
    - Instagram блокирует при частых запросах
    Поэтому: пауза 2 секунды между постами (INSTAGRAM_REQUEST_DELAY)

    ЛЕНИВАЯ ИНИЦИАЛИЗАЦИЯ instaloader (_loader = None):
    Не создаём Instaloader() в __init__, а только при первом fetch_profile.
    Зачем? import instaloader может упасть если пакет не установлен.
    Лучше упасть в момент использования с понятным сообщением,
    чем при импорте самого провайдера.
    """

    def __init__(
            self, max_posts: int = 20, request_delay: float = 2.0
    ) -> None:
        self._max_posts = max_posts
        self._request_delay = request_delay
        self._loader = None  # ленивая инициализация

    def _get_loader(self):
        """Инициализировать instaloader при первом обращении."""
        if self._loader is None:
            try:
                import instaloader
                self._loader = instaloader.Instaloader(
                    quiet=True,  # не выводить прогресс в stdout
                    download_pictures=False,  # не скачивать фото (только метаданные)
                    download_videos=False,
                    download_video_thumbnails=False,
                    download_geotags=False,
                    download_comments=False,
                    save_metadata=False,
                )
                logger.debug("instaloader инициализирован")
            except ImportError:
                raise InstagramError(
                    "Установите: pip install instaloader",
                    error_type="missing_dependency"
                )
        return self._loader

    def fetch_profile(self, username: str) -> InstagramProfile:
        """
        Скрапить профиль.

        АЛГОРИТМ:
        1. Profile.from_username() — один HTTP запрос → биография, подписчики
        2. profile.get_posts() — генератор, каждый пост = HTTP запрос
        3. Собираем данные с паузой между запросами

        ОБРАБОТКА ИСКЛЮЧЕНИЙ instaloader:
        Разные исключения → разные error_type → разные сообщения пользователю.
        """
        import instaloader

        loader = self._get_loader()
        logger.info(
            "Скрапим @%s (max_posts=%d, delay=%.1fs)...",
            username, self._max_posts, self._request_delay
        )

        try:
            profile = instaloader.Profile.from_username(
                loader.context, username
            )
        except instaloader.exceptions.ProfileNotExistsException:
            raise InstagramError(
                f"Профиль @{username} не найден",
                username=username, error_type="not_found"
            )
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            raise InstagramError(
                f"Профиль @{username} приватный",
                username=username, error_type="private"
            )
        except instaloader.exceptions.ConnectionException as e:
            raise InstagramError(
                f"Ошибка соединения: {e}. Попробуйте позже или VPN.",
                username=username, error_type="connection"
            )

        ig_profile = InstagramProfile(
            username=profile.username,
            full_name=profile.full_name or "",
            bio=profile.biography or "",
            followers_count=profile.followers,
            following_count=profile.followees,
        )

        logger.info(
            "@%s: %d подписчиков, bio=%d символов",
            username, profile.followers, len(ig_profile.bio)
        )

        # Собираем посты
        collected = 0
        for post in profile.get_posts():
            if collected >= self._max_posts:
                break

            caption = post.caption or ""
            # Парсим хэштеги из caption:
            hashtags = re.findall(r'#(\w+)', caption)
            hashtags = [tag.lower() for tag in hashtags]

            ig_profile.posts.append(InstagramPost(
                caption=caption,
                hashtags=hashtags,
                likes=post.likes,
                post_type="video" if post.is_video else "image",
            ))
            collected += 1

            # Пауза — защита от бана Instagram
            if collected < self._max_posts:
                time.sleep(self._request_delay)

            logger.debug(
                "Пост %d/%d: %d лайков, %d хэштегов",
                collected, self._max_posts, post.likes, len(hashtags)
            )

        # Пересчитываем агрегированные хэштеги после добавления всех постов
        ig_profile.hashtags_used = ig_profile._collect_all_hashtags()

        logger.info(
            "Скрапинг завершён: %d постов, %d хэштегов",
            len(ig_profile.posts), len(ig_profile.hashtags_used)
        )
        return ig_profile


class MockInstagramProvider(InstagramInterface):
    """
    Тестовый провайдер — заранее заготовленные данные.

    ПОЧЕМУ НУЖЕН MOCK?
    1. Разработка без интернета
    2. Тесты не зависят от Instagram (стабильный CI/CD)
    3. Демонстрация заказчику

    КАК ИСПОЛЬЗОВАТЬ:
        INSTAGRAM_USE_MOCK=true python main.py anyname

    СТРАТЕГИЯ ДАННЫХ:
    1. Сначала пытаемся загрузить из tests/fixtures/sample_profile.json
       (можно редактировать для разных сценариев тестирования)
    2. Если файла нет → встроенные данные (failsafe)

    Данные — условная девушка 26 лет: путешествия, йога, кулинария,
    современное искусство, книги. Хороший тест для промптов.
    """

    def fetch_profile(self, username: str) -> InstagramProfile:
        logger.info("[MOCK] Тестовый профиль для @%s", username)

        fixture = (
                Path(__file__).parent.parent
                / "tests" / "fixtures" / "sample_profile.json"
        )
        if fixture.exists():
            return self._load_from_fixture(username, fixture)
        return self._build_hardcoded(username)

    def _load_from_fixture(
            self, username: str, path: Path
    ) -> InstagramProfile:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            posts = [
                InstagramPost(
                    caption=p.get("caption", ""),
                    hashtags=p.get("hashtags", []),
                    likes=p.get("likes", 0),
                    post_type=p.get("post_type", "image"),
                )
                for p in data.get("posts", [])
            ]
            return InstagramProfile(
                username=username,
                full_name=data.get("full_name", ""),
                bio=data.get("bio", ""),
                posts=posts,
                followers_count=data.get("followers_count", 1000),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Ошибка фикстуры: %s. Используем встроенные.", e)
            return self._build_hardcoded(username)

    def _build_hardcoded(self, username: str) -> InstagramProfile:
        posts = [
            InstagramPost(
                caption="Бали снова украл моё сердце 🌴",
                hashtags=["bali", "travel", "indonesia", "paradise"],
                likes=342,
            ),
            InstagramPost(
                caption="Паста карбонара по рецепту от шефа. Результат — огонь!",
                hashtags=["cooking", "pasta", "foodporn", "homecooking"],
                likes=218,
            ),
            InstagramPost(
                caption="Закончила 'Атлас расправил плечи' — неоднозначно но мощно",
                hashtags=["books", "reading", "bookstagram"],
                likes=89,
            ),
            InstagramPost(
                caption="Выставка современного искусства в Гараже.",
                hashtags=["art", "modernart", "moscow", "garagemca"],
                likes=156,
            ),
            InstagramPost(
                caption="Yoga retreat в горах Алтая. 5 дней тишины.",
                hashtags=["yoga", "altai", "retreat", "mindfulness", "travel"],
                likes=445,
            ),
            InstagramPost(
                caption="Новый сезон The Bear — смотрим? 🍳",
                hashtags=["thebear", "series", "cooking", "tvshow"],
                likes=167,
            ),
            InstagramPost(
                caption="Флоренция за 48 часов.",
                hashtags=["florence", "italy", "travel", "europe", "art"],
                likes=389,
            ),
            InstagramPost(
                caption="Утренняя пробежка — лучший старт дня",
                hashtags=["running", "morning", "fitness", "lifestyle"],
                likes=203,
            ),
            InstagramPost(
                caption="Пробую акварель — оказывается это медитация",
                hashtags=["watercolor", "art", "painting", "hobby"],
                likes=134,
            ),
            InstagramPost(
                caption="Любимый рынок по воскресеньям",
                hashtags=["market", "localfood", "organic", "lifestyle"],
                likes=278,
            ),
        ]
        return InstagramProfile(
            username=username,
            full_name="Наталья К.",
            bio="путешествия • еда • книги • йога ✈️🍝📚 | Москва → везде",
            posts=posts,
            followers_count=4820,
            following_count=612,
        )