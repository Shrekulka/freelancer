# providers/openai_provider.py

import time
import openai
from interfaces.llm import LLMInterface, LLMError
from config.settings import config
from config.logger_config import get_logger

logger = get_logger(__name__)


class OpenAIProvider(LLMInterface):
    """
    LLM-провайдер через OpenAI API.

    ОТЛИЧИЕ ОТ ANTHROPIC:
    OpenAI: system prompt = первое сообщение с role="system"

        messages = [
            {"role": "system", "content": "Ты эксперт..."},  ← так
            {"role": "user",   "content": "..."}
        ]

    Наш интерфейс complete(prompt, system) одинаков для всех.
    Провайдер сам знает как передать system своему API.
    """

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMError("OPENAI_API_KEY не задан", provider="openai")
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def get_model_name(self) -> str:
        return self._model

    def complete(
            self, prompt: str, system: str = "", max_tokens: int = 1024
    ) -> str:
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
                # OpenAI: choices[0].message.content
                # Anthropic: content[0].text  ← разные SDK!
                text = response.choices[0].message.content
                logger.debug("OpenAI ответ: %d символов", len(text))
                return text

            except openai.RateLimitError as e:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning("OpenAI rate limit, ждём %ds...", wait)
                    time.sleep(wait)
                else:
                    raise LLMError(
                        "Rate limit после 3 попыток", provider="openai",
                        original_error=e
                    )
            except openai.AuthenticationError as e:
                raise LLMError(
                    "Неверный OPENAI_API_KEY", provider="openai",
                    original_error=e
                )
            except openai.APIError as e:
                raise LLMError(
                    f"OpenAI ошибка: {e}", provider="openai", original_error=e
                )