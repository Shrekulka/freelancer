# models/recommendation.py

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class InterestProfile:
    topics: list[str] = field(default_factory=list)
    preferred_genres: list[str] = field(default_factory=list)
    estimated_age_range: str = ""
    lifestyle_tags: list[str] = field(default_factory=list)
    vibe: str = ""
    notes: str = ""

    def to_prompt_text(self) -> str:
        lines = []
        if self.topics:
            lines.append(f"Интересы: {', '.join(self.topics)}")
        if self.preferred_genres:
            lines.append(f"Любимые жанры: {', '.join(self.preferred_genres)}")
        if self.estimated_age_range:
            lines.append(f"Возраст: {self.estimated_age_range}")
        if self.lifestyle_tags:
            lines.append(f"Стиль жизни: {', '.join(self.lifestyle_tags)}")
        if self.vibe:
            lines.append(f"Настроение: {self.vibe}")
        if self.notes:
            lines.append(f"Заметки: {self.notes}")
        return "\n".join(lines)

@dataclass
class ShowRecommendation:
    title: str
    title_ru: str = ""
    year: int = 0
    genre: str = ""
    description: str = ""
    why_recommended: str = ""
    alternatives: list[str] = field(default_factory=list)

@dataclass
class StreamingAvailability:
    title: str
    available_on: dict[str, str] = field(default_factory=dict)
    not_available_on: list[str] = field(default_factory=list)

    @property
    def is_available(self) -> bool:
        return bool(self.available_on)

    def get_best_platform(self, preferred: list[str]) -> Optional[tuple[str, str]]:
        for platform in preferred:
            if platform in self.available_on:
                return platform, self.available_on[platform]
        return None

@dataclass
class FinalRecommendation:
    username: str
    interests: InterestProfile
    show: ShowRecommendation
    streaming: Optional[StreamingAvailability] = None
    summary: str = ""

    def display(self) -> str:
        lines = [
            "=" * 60,
            f"🎬 РЕКОМЕНДАЦИЯ ДЛЯ @{self.username}",
            "=" * 60, "",
        ]
        lines.append("📊 ЧТО Я УЗНАЛ О НЕЙ:")
        if self.interests.topics:
            lines.append(f"  Интересы: {', '.join(self.interests.topics)}")
        if self.interests.vibe:
            lines.append(f"  Настроение: {self.interests.vibe}")
        if self.interests.lifestyle_tags:
            lines.append(f"  Стиль: {', '.join(self.interests.lifestyle_tags)}")
        lines.append("")
        title_line = f"🍿 СЕРИАЛ: {self.show.title}"
        if self.show.title_ru:
            title_line += f" / {self.show.title_ru}"
        if self.show.year:
            title_line += f" ({self.show.year})"
        lines.append(title_line)
        if self.show.genre:
            lines.append(f"  Жанр: {self.show.genre}")
        if self.show.description:
            lines.append(f"  О чём: {self.show.description}")
        if self.show.why_recommended:
            lines.append(f"  Почему ей понравится: {self.show.why_recommended}")
        lines.append("")
        if self.streaming and self.streaming.is_available:
            lines.append("📺 ГДЕ СМОТРЕТЬ:")
            for platform, url in self.streaming.available_on.items():
                if url:
                    lines.append(f"  ✅ {platform.upper()}: {url}")
                else:
                    lines.append(f"  ✅ {platform.upper()}: доступно")
        elif self.streaming:
            lines.append("⚠️  НЕТ В NETFLIX И HBO MAX")
            if self.show.alternatives:
                lines.append(f"  Альтернативы: {', '.join(self.show.alternatives)}")
        else:
            lines.append("⚠️  Информация о доступности не найдена")
        lines.append("")
        if self.summary:
            lines.append("💬 СОВЕТ ДЛЯ ВЕЧЕРА:")
            lines.append(f"  {self.summary}")
        lines.append("=" * 60)
        return "\n".join(lines)