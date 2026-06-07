# models/profile.py

from dataclasses import dataclass, field
from collections import Counter

@dataclass
class InstagramPost:
    """
    Один пост в Instagram.

    Нас интересуют три вещи:
    - caption  : текст поста → интересы, стиль речи, ценности
    - hashtags : явно заявленные интересы (#travel, #yoga, #cooking)
    - likes    : косвенный сигнал важности темы для человека
    """
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    likes: int = 0
    post_type: str = "image"  # "image" | "video" | "reel"

    def get_all_text(self) -> str:
        """
        Объединить caption и хэштеги в одну строку для LLM.

        Зачем объединять?
        LLM получает весь текст разом — нет смысла разделять.

        Пример:
            post = InstagramPost(
                caption="Бали снова украл сердце",
                hashtags=["bali", "travel", "indonesia"]
            )
            post.get_all_text()
            # → "Бали снова украл сердце #bali #travel #indonesia"
        """
        hashtag_str = " ".join(f"#{tag}" for tag in self.hashtags)
        return f"{self.caption} {hashtag_str}".strip()


@dataclass
class InstagramProfile:
    username: str
    full_name: str = ""
    bio: str = ""
    posts: list[InstagramPost] = field(default_factory=list)
    followers_count: int = 0
    following_count: int = 0
    # hashtags_used теперь свойство, а не поле
    # _hashtags_cache для кэширования (опционально)
    _hashtags_cache: list[str] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """
        Вызывается Python АВТОМАТИЧЕСКИ после __init__ у @dataclass.

        Зачем? Мы хотим агрегировать хэштеги сразу при создании профиля,
        но только если они ещё не заданы явно (чтобы не перетирать).

        __post_init__ — стандартное место для такой пост-инициализационной логики.
        """
        if not self.hashtags_used and self.posts:
            self.hashtags_used = self._collect_all_hashtags()

    def _collect_all_hashtags(self) -> list[str]:
        """
        Собрать все хэштеги из всех постов, отсортировать по частоте.

        Почему по частоте? Хэштег который встречается в 8 из 10 постов —
        главный интерес. Хэштег из одного поста — случайность.

        Counter из стандартной библиотеки делает это в одну строку.

        Пример:
            posts = [
                Post(hashtags=["travel", "bali"]),
                Post(hashtags=["travel", "yoga"]),
                Post(hashtags=["food"]),
            ]
            # Counter: {"travel": 2, "bali": 1, "yoga": 1, "food": 1}
            # most_common: [("travel",2), ("bali",1), ("yoga",1), ("food",1)]
            # Результат: ["travel", "bali", "yoga", "food"]
        """
        from collections import Counter
        all_tags = []
        for post in self.posts:
            all_tags.extend(post.hashtags)
        counter = Counter(all_tags)
        return [tag for tag, _ in counter.most_common(30)]  # топ-30

    @property
    def hashtags_used(self) -> list[str]:
        """Возвращает топ-30 хэштегов из всех постов, кэшируя результат."""
        if not self._hashtags_cache and self.posts:
            all_tags = []
            for post in self.posts:
                all_tags.extend(post.hashtags)
            counter = Counter(all_tags)
            self._hashtags_cache = [tag for tag, _ in counter.most_common(30)]
        return self._hashtags_cache

    def get_text_for_analysis(self) -> str:
        sections = []
        if self.bio:
            sections.append(f"БИО: {self.bio}")
        if self.hashtags_used:
            sections.append(f"ХЭШТЕГИ: {', '.join(self.hashtags_used[:20])}")
        recent_posts = self.posts[:15]
        if recent_posts:
            post_texts = []
            for i, post in enumerate(recent_posts, 1):
                text = post.get_all_text()
                if text:
                    truncated = text[:200] + "..." if len(text) > 200 else text
                    post_texts.append(f"Пост {i}: {truncated}")
            if post_texts:
                sections.append("ПОСТЫ:\n" + "\n".join(post_texts))
        return "\n\n".join(sections)

    def __repr__(self) -> str:
        return (
            f"InstagramProfile(username={self.username!r}, "
            f"posts={len(self.posts)}, "
            f"hashtags={len(self.hashtags_used)})"
        )