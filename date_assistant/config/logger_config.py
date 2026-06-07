# logger_config.py

import logging
import os
import traceback
from datetime import datetime
from pathlib import Path
from colorama import Style, Fore, Back, init

# ──────────────────────────────────────────────────────────────────────────
# ФОРМАТЫ СТРОК
# ──────────────────────────────────────────────────────────────────────────
#
# Расшифровка placeholders:
#   %(asctime)s   → "2025-06-01 22:14:53"
#   %(levelname)s → "INFO", "WARNING", "ERROR"
#   %(name)s      → "services.instagram_service" (из get_logger(__name__))
#   %(funcName)s  → "fetch_profile"
#   %(lineno)d    → 142
#   %(message)s   → текст сообщения
#
# Формат консоли — с colorama escape-кодами для цвета:
_CONSOLE_FMT_BASE = (
    f"{Fore.MAGENTA}%(asctime)s{Style.RESET_ALL} | "
    f"{Back.GREEN + Style.BRIGHT + Fore.BLACK}%(levelname)-8s{Style.RESET_ALL} | "
    f"{Fore.CYAN}%(name)-25s{Style.RESET_ALL} | "
    f"{Fore.GREEN}%(funcName)-20s{Style.RESET_ALL} | "
    f"{Style.BRIGHT}%(message)s{Style.RESET_ALL}"
)
# %-8s и %-25s — выравнивание по левому краю в 8/25 символов.
# Без него уровни "INFO" и "WARNING" будут разной ширины — некрасиво.

_CONSOLE_FMT_WARNING = (
    f"{Back.YELLOW + Style.BRIGHT + Fore.BLACK}%(asctime)s{Style.RESET_ALL} | "
    f"{Back.YELLOW + Style.BRIGHT + Fore.BLACK}%(levelname)-8s{Style.RESET_ALL} | "
    f"{Back.YELLOW + Style.BRIGHT + Fore.BLACK}%(name)-25s{Style.RESET_ALL} | "
    f"{Back.YELLOW + Style.BRIGHT + Fore.BLACK}%(funcName)-20s{Style.RESET_ALL} | "
    f"{Back.YELLOW + Style.BRIGHT + Fore.BLACK}%(message)s{Style.RESET_ALL}"
)

_CONSOLE_FMT_ERROR = (
    f"{Back.MAGENTA + Style.BRIGHT + Fore.BLACK}%(asctime)s{Style.RESET_ALL} | "
    f"{Back.MAGENTA + Style.BRIGHT + Fore.BLACK}%(levelname)-8s{Style.RESET_ALL} | "
    f"{Back.MAGENTA + Style.BRIGHT + Fore.BLACK}%(name)-25s{Style.RESET_ALL} | "
    f"{Back.MAGENTA + Style.BRIGHT + Fore.BLACK}%(funcName)-20s{Style.RESET_ALL} | "
    f"{Back.MAGENTA + Style.BRIGHT + Fore.BLACK}%(message)s{Style.RESET_ALL}"
)

_CONSOLE_FMT_CRITICAL = (
    f"{Back.RED + Style.BRIGHT + Fore.BLACK}%(asctime)s{Style.RESET_ALL} | "
    f"{Back.RED + Style.BRIGHT + Fore.BLACK}%(levelname)-8s{Style.RESET_ALL} | "
    f"{Back.RED + Style.BRIGHT + Fore.BLACK}%(name)-25s{Style.RESET_ALL} | "
    f"{Back.RED + Style.BRIGHT + Fore.BLACK}%(funcName)-20s{Style.RESET_ALL} | "
    f"{Back.RED + Style.BRIGHT + Fore.BLACK}%(message)s{Style.RESET_ALL}"
)

# Формат файла — БЕЗ escape-кодов.
# Почему? Откроешь logs/app_2025-06-01.log в текстовом редакторе
# и увидишь: "\x1b[35m2025-06-01...\x1b[0m" — нечитаемый мусор.
_FILE_FMT = (
    "%(asctime)s | %(levelname)-8s | %(name)-25s | "
    "%(funcName)-20s:%(lineno)d | %(message)s"
)


# ──────────────────────────────────────────────────────────────────────────
# ФОРМАТТЕР С ЦВЕТАМИ (вложенный класс — деталь реализации, снаружи не нужен)
# ──────────────────────────────────────────────────────────────────────────
class _ColoredFormatter(logging.Formatter):
    """
    Выбирает цветовой формат по уровню лога.

    Почему вложенный класс, а не на уровне модуля?
    Это деталь реализации CustomLogger. Снаружи никому не нужен.
    Инкапсуляция — прячем то, что не является публичным API.

    Как работает:
    Python вызывает format(record) для каждого лог-сообщения.
    Мы смотрим record.levelno и выбираем нужный формат.
    """
    _FORMATS: dict[int, str] = {
        logging.DEBUG: _CONSOLE_FMT_BASE,
        logging.INFO: _CONSOLE_FMT_BASE,
        logging.WARNING: _CONSOLE_FMT_WARNING,
        logging.ERROR: _CONSOLE_FMT_ERROR,
        logging.CRITICAL: _CONSOLE_FMT_CRITICAL,
    }

    def format(self, record: logging.LogRecord) -> str:
        fmt = self._FORMATS.get(record.levelno, _CONSOLE_FMT_BASE)
        return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S").format(record)


# ──────────────────────────────────────────────────────────────────────────
# ОСНОВНОЙ КЛАСС ЛОГГЕРА
# ──────────────────────────────────────────────────────────────────────────
class CustomLogger:
    """
    Настраивает Python logging для нашего CLI.

    СХЕМА РАБОТЫ:
        root_logger
        ├── ConsoleHandler → _ColoredFormatter → stdout  (цветной)
        └── FileHandler    → Formatter         → logs/app_YYYY-MM-DD.log (без цветов)

    РЕЖИМЫ (из переменной окружения DEBUG):
        DEBUG=false → уровень INFO, меньше шума
        DEBUG=true  → уровень DEBUG, все детали включая промпты LLM
    """

    def __init__(self, log_to_file: bool = True) -> None:
        # Читаем DEBUG из env ДО инициализации логгера
        # (settings.py ещё не загружен в этот момент)
        _debug_env = os.getenv("DEBUG", "false").lower()
        self.is_debug_mode: bool = _debug_env in ("true", "1", "yes")
        self.level: int = logging.DEBUG if self.is_debug_mode else logging.INFO

        self.log_to_file = log_to_file
        self._log_file: str | None = None
        self._current_date: str = ""

        # Папка logs/ рядом с logger_config.py (корень проекта)
        # Path(__file__).parent → директория где лежит logger_config.py
        self._logs_dir: Path = Path(__file__).parent.parent / "logs"

        if self.log_to_file:
            self._logs_dir.mkdir(exist_ok=True)  # создаём если нет
            self._current_date = datetime.now().strftime("%Y-%m-%d")
            self._log_file = str(
                self._logs_dir / f"app_{self._current_date}.log"
            )

    def configure(self) -> None:
        """
        Настроить root logger — вызывается ОДИН РАЗ при импорте модуля.

        Root logger — корневой логгер Python. Все именованные логгеры
        (logging.getLogger("my_module")) наследуют его handlers.
        Это значит: настроив root один раз, мы настраиваем ВСЕ логгеры.

        Почему handlers.clear()?
        При ротации файла мы вызываем configure() повторно.
        Без clear() добавятся дублирующие handlers — каждое сообщение
        напечатается дважды (или трижды, или больше).
        """
        try:
            init(autoreset=True)  # colorama: сбрасывать цвет после каждой строки

            root = logging.getLogger()
            root.handlers.clear()  # важно! убираем старые handlers
            root.setLevel(self.level)

            # В INFO-режиме заглушаем шумные библиотеки.
            # instaloader пишет DEBUG на каждый HTTP-запрос — это десятки строк.
            # anthropic SDK тоже довольно многословен.
            if not self.is_debug_mode:
                for noisy in ("instaloader", "urllib3", "httpx", "anthropic"):
                    logging.getLogger(noisy).setLevel(logging.WARNING)

            # ── Handler 1: Консоль ──────────────────────────────────────
            console = logging.StreamHandler()
            console.setLevel(self.level)
            console.setFormatter(_ColoredFormatter())
            root.addHandler(console)

            # ── Handler 2: Файл ─────────────────────────────────────────
            if self.log_to_file and self._log_file:
                file_h = logging.FileHandler(
                    self._log_file,
                    mode="a",  # append — дописываем, не перезаписываем
                    encoding="utf-8",  # критично для кириллицы в сообщениях
                )
                file_h.setLevel(self.level)
                file_h.setFormatter(
                    logging.Formatter(_FILE_FMT, datefmt="%Y-%m-%d %H:%M:%S")
                )
                root.addHandler(file_h)

            # Первое сообщение после инициализации
            level_label = "DEBUG" if self.is_debug_mode else "INFO"
            log_dest = f"→ {self._log_file}" if self._log_file else "→ только консоль"
            logging.getLogger("logger_config").info(
                "Logger ready | level=%s | %s", level_label, log_dest
            )

        except Exception:
            print(f"[CRITICAL] Ошибка логгера:\n{traceback.format_exc()}")
            raise SystemExit(1)

    def rotate_if_needed(self) -> None:
        """
        Переключить файл лога при смене дня.

        Зачем ротация?
        Без ротации за месяц накопится один огромный app.log.
        С ротацией: app_2025-06-01.log, app_2025-06-02.log, ...
        Удобно искать проблему по дате.

        Когда вызывается?
        В get_logger() — при каждом запросе именованного логгера.
        Проверка дешёвая: просто сравниваем строки дат.
        """
        if not self.log_to_file:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._current_date:
            self._current_date = today
            self._log_file = str(self._logs_dir / f"app_{today}.log")
            self.configure()  # переинициализируем с новым файлом


# ──────────────────────────────────────────────────────────────────────────
# ИНИЦИАЛИЗАЦИЯ — один раз при первом импорте модуля
# ──────────────────────────────────────────────────────────────────────────
# Python кеширует модули. Первый `import logger_config` выполняет этот код.
# Все последующие импорты возвращают уже готовый объект из кеша.
_custom_logger = CustomLogger(log_to_file=True)
_custom_logger.configure()

# Функция для перенастройки логгера (например, после изменения DEBUG)
def reconfigure_logging(debug: bool) -> None:
    """
    Позволяет динамически изменить уровень логирования.
    Вызывается в main() после парсинга аргументов, если установлен --debug.
    """
    _custom_logger.is_debug_mode = debug
    _custom_logger.level = logging.DEBUG if debug else logging.INFO
    _custom_logger.configure()


def get_logger(name: str) -> logging.Logger:
    """
    Получить именованный логгер для модуля.

    СТАНДАРТНОЕ СОГЛАШЕНИЕ — всегда передавать __name__:

        # В файле services/instagram_service.py:
        logger = get_logger(__name__)
        # __name__ == "services.instagram_service"

        logger.info("Профиль получен")
        # → ... | INFO | services.instagram_service | get_profile | Профиль получен

    Почему __name__, а не строка "instagram_service"?
    __name__ автоматически содержит полный путь модуля с пакетом.
    Это удобно: сразу видно в каком файле написано сообщение.

    ФОРМАТИРОВАНИЕ строк лога:
        # ❌ f-строки — Python вычислит f-строку ДАЖЕ если уровень отключён
        logger.debug(f"Данные: {json.dumps(big_dict)}")

        # ✅ %-форматирование — вычисляется только если уровень активен
        logger.debug("Данные: %s", big_dict)
        # При DEBUG=false → second arg никогда не сериализуется → быстрее
    """
    _custom_logger.rotate_if_needed()
    return logging.getLogger(name)