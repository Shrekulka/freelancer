# main.py

"""
Точка входа CLI.

ЗАПУСК:
    python main.py natasha_travels
    python main.py @natasha --llm openai
    python main.py anyname --mock-instagram
    python main.py --config
    python main.py natasha --platforms netflix prime --debug

ПОЧЕМУ argparse, А НЕ click/typer?

    argparse — стандартная библиотека, нет зависимостей.
    click    — удобнее, декораторы, нужна установка.
    typer    — type hints, автодокументация, нужна установка.

    Выбор: argparse — для нашего простого CLI достаточно.
    При 5+ командах и сложных опциях выбрали бы click.
"""

import sys
import argparse
import time

from config.settings import config
from use_cases.analyze_profile import AnalyzeProfileUseCase
from interfaces.instagram import InstagramError
from interfaces.llm import LLMError
from config.logger_config import get_logger, reconfigure_logging

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """
    Создать парсер аргументов.

    Выносим в отдельную функцию — легче тестировать.
    main() сложно тестировать (sys.argv, sys.exit).
    build_parser() — просто функция, возвращает объект.
    """
    parser = argparse.ArgumentParser(
        prog="date_assistant",
        description=(
            "🎬 Date Assistant — подбирает сериал по Instagram профилю\n"
            "\n"
            "ПРИМЕРЫ:\n"
            "  python main.py natasha_travels\n"
            "  python main.py @natasha --llm openai\n"
            "  python main.py test --mock-instagram\n"
            "  python main.py --config\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Позиционный аргумент (без --)
    # nargs="?" — опциональный (нужен для --config без username)
    parser.add_argument(
        "username",
        nargs="?",
        help="Instagram username (с @ или без)"
    )

    # Опция --llm
    # choices — argparse сам проверит что значение из списка
    parser.add_argument(
        "--llm",
        choices=["claude", "openai", "deepseek"],
        default=None,  # None = из .env (DEFAULT_LLM_PROVIDER)
        help="LLM провайдер (по умолчанию из .env)"
    )

    # Опция --platforms
    # nargs="+" — один или несколько аргументов: --platforms netflix hbo
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=["netflix", "hbo", "prime", "disney", "apple"],
        default=None,
        help="Платформы: --platforms netflix hbo"
    )

    # Флаги (action="store_true" → True если указан, иначе False)
    parser.add_argument(
        "--mock-instagram",
        action="store_true",
        help="Тестовые данные вместо реального скрапинга"
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Показать настройки и выйти"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Подробные логи (промпты, ответы LLM)"
    )

    return parser


def main() -> int:
    """
    Главная функция.

    Возвращает int (exit code):
    - 0 = успех
    - 1 = ошибка

    Зачем возвращать int?
    Стандарт Unix: 0 = OK, !=0 = ошибка.
    sys.exit(main()) передаёт код OS.
    Позволяет использовать в pipeline:
        python main.py natasha && echo "Готово!" || echo "Ошибка"
    """
    parser = build_parser()
    args = parser.parse_args()

    # --debug: включаем DEBUG-режим
    if args.debug:
        import os
        os.environ["DEBUG"] = "true"
        reconfigure_logging(debug=True)
    else:
        reconfigure_logging(debug=False)

    # --config: показать настройки и выйти
    if args.config:
        config.show()
        return 0

    # Без username: показать help
    if not args.username:
        parser.print_help()
        return 1

    # Применяем CLI-аргументы
    platforms = args.platforms or config.watchmode.user_platforms
    if args.mock_instagram:
        config.instagram.use_mock = True

    # Валидация конфигурации
    errors = config.validate()
    warnings = [e for e in errors if e.startswith("⚠️")]
    critical = [e for e in errors if not e.startswith("⚠️")]

    for w in warnings:
        print(w)

    if critical:
        print("\n❌ ОШИБКИ КОНФИГУРАЦИИ:")
        for e in critical:
            print(f"  {e}")
        print("\nСоздайте .env из .env.example и заполните ключи.")
        return 1

    # Заголовок
    print("\n" + "═" * 50)
    print("  🎬 DATE ASSISTANT")
    print("═" * 50)
    print(f"  Instagram: @{args.username.lstrip('@')}")
    print(f"  LLM:       {args.llm or config.app.default_llm}")
    print(f"  Платформы: {', '.join(p.upper() for p in platforms)}")
    if config.instagram.use_mock:
        print("  Режим:     MOCK (тестовые данные)")
    print("═" * 50)

    start = time.time()

    try:
        use_case = AnalyzeProfileUseCase(platforms=platforms)

        # Переопределяем LLM если передан --llm
        if args.llm:
            from config.provider_factory import ProviderFactory
            from services.recommendation_service import RecommendationService
            llm = ProviderFactory.create_llm(args.llm)
            use_case.set_llm(llm)

        result = use_case.execute(args.username)
        elapsed = time.time() - start
        print(result.display())
        print(f"\n⏱  Время: {elapsed:.1f} сек")
        return 0
    except (ValueError, InstagramError, LLMError) as e:
        print(f"\n❌ {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано")
        return 1
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        logger.exception("Неожиданная ошибка")
        if config.app.debug:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())