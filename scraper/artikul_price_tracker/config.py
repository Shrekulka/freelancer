# selenium/config.py

from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    """
    Класс для хранения настроек приложения.
    """
    geckodriver_path: str = './geckodriver'

    # URLs для поиска по артикулу на маркетплейсах
    wildberries_url: str = 'https://www.wildberries.ru/catalog/{artikul}/detail.aspx'
    ozone_url: str = 'https://www.ozon.ru/search/?from_global=true&text={artikul}'
    yandex_url: str = 'https://market.yandex.ru/search?text={artikul}'
    avito_url: str = 'https://www.avito.ru/moskva?q={artikul}'

    min_pause_time: float = 1.2
    max_pause_time: float = 2.5
    headless_mode: bool = True
    disable_cache: bool = True
    tracking_protection: bool = True
    custom_user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0'

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаем экземпляр класса Settings для хранения конфигурационных данных
config: Settings = Settings()
