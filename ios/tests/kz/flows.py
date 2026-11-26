"""Механика входа для сборки KZ iOS: стартовый экран → логин/пароль → код → главная."""
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import POLL

from .pages.home_page import HomePage
from .pages.login_page import LoginPage
from .pages.pin_page import PinPage
from .pages.settings_page import MenuPage
from .pages.start_page import StartPage


def login(driver, user):
    """Вход из любого состояния (no_reset) — всегда по логину и паролю: «Кіру» → логин/пароль →
    создание кода. Если приложение открылось на «Код доступа», код сбрасывается.

    Вход по коду не используем: токен сессии протухает, а приложение после верного кода
    просто остаётся на «Код доступа» (30.10.2026 так падали все кейсы)."""
    start, login_page, pin_page = StartPage(driver), LoginPage(driver), PinPage(driver)

    def screen(d):
        if d.find_elements(*pin_page.FIRST_DIGIT):
            return "pin"
        if d.find_elements(*login_page.LOGIN_INPUT):
            return "login"
        if d.find_elements(*start.LOGIN_BUTTON):
            return "start"
        return False

    def past_start(d):
        current = screen(d)
        return current if current in ("pin", "login") else False

    wait = WebDriverWait(driver, 60, poll_frequency=POLL)
    current = wait.until(screen)
    if current == "start":
        try:
            start.tap(start.LOGIN_BUTTON, timeout=5)
        except WebDriverException:
            pass  # кнопка исчезла — приложение само ушло на «Код доступа»
        current = wait.until(past_start)

    if current == "pin":
        pin_page.reset()
        login_page.wait_loaded()

    login_page.login(user.login, user.password)
    pin_page.wait_loaded()
    pin_page.create(user.pin)
    return HomePage(driver).wait_loaded()


def switch_to_russian(driver):
    """Меню → «Баптаулар» → «Тіл» → «Орысша»."""
    return MenuPage(driver).open().open_settings().open_language().choose_russian()
