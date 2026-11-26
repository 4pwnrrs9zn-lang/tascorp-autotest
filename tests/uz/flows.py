"""Механика входа для сборки UZ: стартовый экран → логин/пароль → код → главная."""
from .pages.home_page import HomePage
from .pages.login_page import LoginPage
from .pages.pin_page import PinPage
from .pages.settings_page import MenuPage
from .pages.start_page import StartPage


def login(driver, user):
    start = StartPage(driver)
    start.wait_loaded()
    start.tap_login()
    login_page = LoginPage(driver)
    login_page.wait_loaded()
    login_page.login(user.login, user.password)
    pin_page = PinPage(driver)
    pin_page.wait_loaded()
    pin_page.create(user.pin)
    return HomePage(driver).wait_loaded()


def switch_to_russian(driver):
    """Меню → «Sozlamalar» → «Til» → «Русский». Возвращает страницу выбора языка."""
    language = MenuPage(driver).open().open_settings().open_language()
    return language.choose_russian()
