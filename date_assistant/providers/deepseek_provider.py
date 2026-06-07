# providers/deepseek_provider.py

import time
import openai  # Тот же SDK! Только base_url другой.
from interfaces.llm import LLMInterface, LLMError
from config.settings import config
from config.logger_config import get_logger

logger = get_logger(__name__)


class DeepSeekProvider(LLMInterface):
    """
    LLM-провайдер через DeepSeek API.

    ГЛАВНАЯ ХИТРОСТЬ: DeepSeek использует OpenAI-совместимый API.
    То есть те же эндпоинты, тот же формат запросов/ответов.
    Нам нужен тот же openai SDK, только с другим base_url:

        openai.OpenAI(
            api_key=deepseek_key,
            base_url="https://api.deepseek.com"  ← вся разница!
        )

    Это называется "drop-in replacement".
    Многие новые LLM-провайдеры делают OpenAI-совместимый API
    специально чтобы разработчики могли быстро переключиться.

    ПРАКТИКА:
    - Разрабатываем на DeepSeek (дёшево: $0.14/1M токенов)
    - Финальный прогон на Claude (дорого: $3/1M токенов, но лучше)
    - Переключение: одна строка в .env
    """

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        if not api_key:
            raise LLMError("DEEPSEEK_API_KEY не задан", provider="deepseek")
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def get_model_name(self) -> str:
        return self._model

    def complete(
            self, prompt: str, system: str = "", max_tokens: int = 1024
    ) -> str:
        # Код идентичен OpenAIProvider — та же структура messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    messages=messages,
                )
                text = response.choices[0].message.content
                logger.debug("DeepSeek ответ: %d символов", len(text))
                return text

            except openai.RateLimitError as e:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning("DeepSeek rate limit, ждём %ds...", wait)
                    time.sleep(wait)
                else:
                    raise LLMError(
                        "Rate limit", provider="deepseek", original_error=e
                    )
            except openai.AuthenticationError as e:
                raise LLMError(
                    "Неверный DEEPSEEK_API_KEY", provider="deepseek",
                    original_error=e
                )
            except openai.APIError as e:
                raise LLMError(
                    f"DeepSeek ошибка: {e}", provider="deepseek",
                    original_error=e
                )