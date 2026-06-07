# interfaces/__init__.py
# Делаем импорты удобными: from interfaces import LLMInterface
# вместо:                   from interfaces.llm import LLMInterface

from interfaces.llm import LLMInterface, LLMError
from interfaces.instagram import InstagramInterface, InstagramError
from interfaces.streaming import StreamingInterface, StreamingError

__all__ = [
    "LLMInterface", "LLMError",
    "InstagramInterface", "InstagramError",
    "StreamingInterface", "StreamingError",
]