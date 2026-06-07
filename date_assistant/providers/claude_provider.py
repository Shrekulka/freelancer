# providers/claude_provider.py

import time
import anthropic
from interfaces.llm import LLMInterface, LLMError
from config.settings import config
from config.logger_config import get_logger

logger = get_logger(__name__)


class ClaudeProvider(LLMInterface):
    """
    LLM-провайдер через Anthropic Claude API.

    ANTHROPIC SDK — базовый пример:
        client = anthropic.Anthropic(api_key="sk-ant-...")
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Привет!"}]
        )
        print(msg.content[0].text)

    МЫ ДОБАВЛЯЕМ:
    - system prompt как отдельный параметр
    - Retry с exponential backoff при rate limit (429)
    - Конвертацию всех Anthropic-исключений в LLMError
    """

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY не задан. Добавьте в .env файл.",
                provider="claude"
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def get_model_name(self) -> str:
        return self._model

    def complete(
            self, prompt: str, system: str = "", max_tokens: int = 1024
    ) -> str:
        """
        Отправить запрос к Claude с retry при rate limit.

        КЛЮЧЕВОЕ ОТЛИЧИЕ ANTHROPIC ОТ OPENAI:

        Anthropic — system как ОТДЕЛЬНЫЙ параметр:
            client.messages.create(
                model=...,
                system="Ты эксперт по сериалам...",    ← отдельный параметр
                messages=[{"role": "user", "content": "..."}]
            )

        OpenAI — system как ПЕРВОЕ СООБЩЕНИЕ:
            client.chat.completions.create(
                model=...,
                messages=[
                    {"role": "system", "content": "Ты эксперт..."},  ← первое
                    {"role": "user", "content": "..."}
                ]
            )

        Интерфейс complete(prompt, system) скрывает это различие.

        EXPONENTIAL BACKOFF для rate limit:
        Попытка 1: ждём 2 сек
        Попытка 2: ждём 4 сек
        Попытка 3: ждём 8 сек
        Формула: 2^(attempt+1) секунд
        Это стандартная практика работы с API.
        """
        if config.app.debug:
            logger.debug(
                "Claude запрос: model=%s, system=%s...",
                self._model,
                (system[:80] + "...") if system else "(нет)"
            )

        params = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            params["system"] = system  # только у Anthropic!

        max_retries = 3
        for attempt in range(max_retries):
            try:
                message = self._client.messages.create(**params)
                response_text = message.content[0].text

                if config.app.debug:
                    logger.debug(
                        "Claude ответ: %d символов",
                        len(response_text)
                    )
                return response_text

            except anthropic.RateLimitError as e:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)  # 2, 4, 8 секунд
                    logger.warning(
                        "Rate limit, ждём %ds (попытка %d/%d)...",
                        wait, attempt + 1, max_retries
                    )
                    time.sleep(wait)
                else:
                    raise LLMError(
                        f"Rate limit после {max_retries} попыток",
                        provider="claude", original_error=e
                    )

            except anthropic.AuthenticationError as e:
                # 401 — неверный ключ. Ретраить бессмысленно.
                raise LLMError(
                    "Неверный ANTHROPIC_API_KEY. Проверьте .env.",
                    provider="claude", original_error=e
                )

            except anthropic.APIConnectionError as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise LLMError(
                        "Не удалось подключиться к Anthropic API",
                        provider="claude", original_error=e
                    )

            except anthropic.APIError as e:
                raise LLMError(
                    f"Anthropic API ошибка: {e}",
                    provider="claude", original_error=e
                )