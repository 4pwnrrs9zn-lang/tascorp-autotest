"""Механика входа для сборки KZ: стартовый экран → логин/пароль → код → главная."""
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import POLL

APP_RUNNING_IN_FOREGROUND = 4  # query_app_state: 1 — не запущено, 3 — в фоне

from .pages.home_page import HomePage
from .pages.login_page import LoginPage
from .pages.pin_page import PinPage
from .pages.settings_page import MenuPage
from .pages.start_page import StartPage


def login(driver, user):
    """Вход с любого из двух состояний приложения (данные сохраняются — no_reset):
    не авторизован → «Кіру» → логин/пароль → создание кода; авторизован → ввод кода.

    Стартовый экран с «Кіру» мелькает и у авторизованного приложения, прежде чем
    оно откроет «Код доступа», — поэтому «Кіру» сам по себе ничего не решает: жмём
    его, если он ещё есть, и смотрим, куда приложение в итоге пришло.

    Если сервер уже завершил сессию входа, код не принимается («Нужно
    переавторизоваться») — сбрасываем код и входим заново по логину и паролю.
    """
    start, login_page, pin_page = StartPage(driver), LoginPage(driver), PinPage(driver)
    package = driver.capabilities.get("appPackage")
    restarts = []

    def screen(d):
        if d.find_elements(*pin_page.FIRST_DIGIT):
            return "pin"
        if d.find_elements(*login_page.LOGIN_INPUT):
            return "login"
        if d.find_elements(*start.LOGIN_BUTTON):
            return "start"
        # Первый запуск после загрузки эмулятора медленный, и приложение падает на старте
        # (гонка в Yandex MapKit: «setLocale() should be called before initialize()»).
        # Тест в этом не виноват — поднимаем приложение заново.
        if package and len(restarts) < 2 and d.query_app_state(package) < APP_RUNNING_IN_FOREGROUND:
            restarts.append(package)
            d.activate_app(package)
        return False

    def past_start(d):
        current = screen(d)
        return current if current in ("pin", "login") else False

    home = HomePage(driver)

    def after_pin(d):
        if d.find_elements(*home.TAB_HOME):
            return "home"
        if d.find_elements(*pin_page.REAUTH_ERROR):
            return "reauth"
        return False

    wait = WebDriverWait(driver, 60, poll_frequency=POLL)
    for _ in range(2):
        current = wait.until(screen)
        if current == "start":
            try:
                start.tap(start.LOGIN_BUTTON, timeout=5)
            except WebDriverException:
                pass  # кнопка исчезла — приложение само ушло на «Код доступа»
            current = wait.until(past_start)

        if current == "login":
            login_page.login(user.login, user.password)
            pin_page.wait_loaded()
            pin_page.create(user.pin)
            return home.wait_loaded()

        pin_page.enter(user.pin)
        try:
            result = WebDriverWait(driver, 20, poll_frequency=POLL).until(after_pin)
        except TimeoutException:
            # Код принят не был, а текст ошибки не распознан (другой язык) — тоже через сброс
            result = "reauth" if driver.find_elements(*pin_page.FIRST_DIGIT) else None
        if result == "home":
            return home
        if result != "reauth":
            return home.wait_loaded()
        # Сервер завершил сессию входа (долго не запускали) — код больше не подходит:
        # сбрасываем его и входим заново по логину и паролю
        pin_page.reset()
    raise AssertionError("Не удалось войти: после сброса кода приложение снова просит переавторизоваться")


def switch_to_russian(driver):
    """Меню → «Баптаулар» → «Тіл» → «Орысша». Возвращает страницу выбора языка."""
    language = MenuPage(driver).open().open_settings().open_language()
    return language.choose_russian()
