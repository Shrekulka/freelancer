# interfaces/llm.py

from abc import ABC, abstractmethod


class LLMInterface(ABC):
    """
    Абстрактный контракт для любого LLM-провайдера.

    ABC (Abstract Base Class) + @abstractmethod:
    Python запрещает создать экземпляр класса с нереализованными
    абстрактными методами. Это гарантирует что любой "LLM" в системе
    умеет делать complete() и get_model_name().

    Попробуй:
        llm = LLMInterface()  # TypeError: Can't instantiate abstract class
    """

    @abstractmethod
    def complete(
            self,
            prompt: str,
            system: str = "",
            max_tokens: int = 1024
    ) -> str:
        """
        Отправить запрос к LLM и получить текстовый ответ.

        Почему три параметра, а не один?
        - prompt  : пользовательский запрос (что хотим узнать)
        - system  : системный промпт (кто такой LLM в этом контексте)
        - max_tokens: ограничение ответа (экономия денег)

        Anthropic и OpenAI работают с системными промптами по-разному:
        - Anthropic: отдельный параметр `system=`
        - OpenAI: первое сообщение с role="system"
        Наш интерфейс скрывает это различие. Caller не знает.

        Raises:
            LLMError: любая ошибка API — авторизация, сеть, лимиты.
                     Провайдеры конвертируют свои исключения в LLMError.
        """
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Вернуть название модели для логирования.

        Зачем?
        В логе видно: "Рекомендован 'Succession' [claude-sonnet-4-20250514]"
        При сравнении качества разных моделей — бесценно.
        """
        ...


class LLMError(Exception):
    """
    Единое исключение для всех LLM-ошибок.

    БЕЗ этого класса верхний слой должен знать о деталях каждого SDK:
        try:
            result = llm.complete(prompt)
        except anthropic.APIError:        # если claude
            ...
        except openai.OpenAIError:        # если openai
            ...
        except httpx.HTTPError:           # если deepseek
            ...

    С LLMError всё одинаково:
        try:
            result = llm.complete(prompt)
        except LLMError as e:
            print(f"Ошибка LLM [{e.provider}]: {e}")
    """

    def __init__(
            self,
            message: str,
            provider: str = "",
            original_error: Exception = None
    ):
        self.provider = provider
        self.original_error = original_error  # оригинальное для отладки
        super().__init__(f"[{provider}] {message}" if provider else message)