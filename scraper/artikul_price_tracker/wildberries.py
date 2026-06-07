import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def setup_driver():
    options = webdriver.FirefoxOptions()
    options.headless = True  # Запуск в фоновом режиме
    service = Service('./geckodriver')  # Укажите путь к вашему geckodriver
    driver = webdriver.Firefox(service=service, options=options)
    return driver


def get_product_data(driver, article):
    url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
    driver.get(url)

    # Ожидаем загрузку страницы
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-page__header-wrap"))
        )
    except Exception as e:
        print(f"Ошибка загрузки страницы для артикула {article}: {e}")
        return {
            "Артикул": article,
            "Наименование": "Нет данных",
            "Цена": "Нет данных",
            "Цена со скидкой": "Нет данных",
            "Наличие": "Нет данных"
        }

    # Получаем HTML-код страницы
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Парсим название товара
    name_tag = soup.find("h1", {"class": "product-page__title"})
    name = name_tag.text.strip() if name_tag else "Название не найдено"

    # Парсим цену и цену со скидкой
    price_tag = soup.find("ins", {"class": "price-block__final-price"})
    price = price_tag.text.strip().replace("\xa0", "") if price_tag else "Нет скидки"

    old_price_tag = soup.find("del", {"class": "price-block__old-price"})
    old_price = old_price_tag.text.strip().replace("\xa0", "") if old_price_tag else "Нет цены"

    # Парсим наличие товара
    availability_tag = soup.find("p", {"class": "sold-out-product"})
    availability = "Нет в наличии" if availability_tag else "В наличии"

    return {
        "Артикул": article,
        "Наименование": name,
        "Цена": old_price,
        "Цена со скидкой": price,
        "Наличие": availability
    }


def create_excel_report(data, filename):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"Данные сохранены в файл {filename}")


def main():
    articles = ["13158614", "12345678", "87654321"]  # Список артикулов
    driver = setup_driver()

    all_data = []
    for article in articles:
        try:
            data = get_product_data(driver, article)
            all_data.append(data)
            print(f"Данные по артикулу {article} получены успешно.")
        except Exception as e:
            print(f"Не удалось получить данные по артикулу {article}: {e}")
            all_data.append({
                "Артикул": article,
                "Наименование": "Нет данных",
                "Цена": "Нет данных",
                "Цена со скидкой": "Нет данных",
                "Наличие": "Нет данных"
            })

    driver.quit()

    # Сохраняем данные в файл даже если есть только одна запись
    create_excel_report(all_data, "prices_report.xlsx")
    print("Данные сохранены в файл prices_report.xlsx")


if __name__ == "__main__":
    main()
