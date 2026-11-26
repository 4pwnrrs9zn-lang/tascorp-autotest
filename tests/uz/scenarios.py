"""Все кейсы сборки UZ: вход, язык, создание заявки.

Код и локаторы этого файла — только для UZ. Аналог для KZ — отдельный,
независимый tests/kz/scenarios.py; общих модулей между ними нет.
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait

from . import factories
from .application_wizard import (
    BorrowerStep, CarPhotosStep, CarStep, ConfirmStep, ExtraDataStep,
)
from .flows import login, switch_to_russian
from .pages.applications_page import ApplicationsPage
from .pages.start_page import StartPage


def app_opens_first_screen(driver, project):
    """Запуск приложения: открывается стартовый экран с кнопкой «Kirish»."""
    WebDriverWait(driver, 30).until(lambda d: d.current_package == project.package)
    login_button = StartPage(driver).wait_loaded()
    assert login_button.is_enabled()


def manager_login(driver, manager):
    """Авторизация: менеджер входит по логину/паролю и создаёт код входа."""
    home = login(driver, manager)
    assert home.role_label(manager.role).is_displayed()
    assert home.applications_button().is_displayed()


def switch_language_to_russian(driver, manager):
    """Настройки: меню → «Sozlamalar» → «Til» → выбран русский язык."""
    login(driver, manager)
    language = switch_to_russian(driver)
    assert language.wait_visible(language.TITLE_RU).is_displayed()
    for tab in ("главная", "профиль", "меню"):
        assert driver.find_element(AppiumBy.ACCESSIBILITY_ID, tab).is_displayed()


def prepare_russian_home(driver, manager):
    """Вход + переключение на русский + возврат на главную — подготовка перед бизнес-кейсами."""
    login(driver, manager)
    switch_to_russian(driver).go_home()


def _create_application(driver, data):
    """Полный путь создания заявки типа «Новая» (UZ). Проверяет сводки по дороге.

    Предусловие: менеджер авторизован, интерфейс на русском, открыта главная —
    обеспечивает общий scenarios.prepare_russian_home().
    """
    apps = ApplicationsPage(driver).open()
    for tab in ApplicationsPage.TABS:
        assert apps.tab(tab).is_displayed(), f"Нет вкладки «{tab}»"
    apps.start_new()

    b = data.borrower
    borrower = BorrowerStep(driver).add_manually(b)
    assert borrower.summary_value("ПИНФЛ") == b.pinfl
    assert borrower.summary_value("Фамилия") == b.last_name.upper()
    assert borrower.summary_value("Имя") == b.first_name.upper()
    assert borrower.summary_value("Номер документа") == b.doc_number
    borrower.next()

    c = data.car
    car = CarStep(driver).add_manually(c)
    assert car.summary_value("ГРНЗ") == c.grnz
    assert car.summary_value("Номер техпаспорта") == c.tech_passport
    assert car.summary_value("Марка, Модель") == f"{c.brand} / {c.model}"
    car.next()

    photos = CarPhotosStep(driver)
    photos.take_required()
    if data.extra_photo:
        photos.add_extra_photo()
    photos.comment(data.photos_comment)
    photos.next()

    extra = ExtraDataStep(driver)
    extra.fill_amounts(data.amount, data.collateral)
    assert extra.loan_type() == "Новая"
    if data.co_borrower:
        extra.add_co_borrower(data.co_borrower)
        co = data.co_borrower
        assert extra.field_value("Созаемщик") == f"{co.first_name} {co.last_name}".upper()
    extra.next()

    confirm = ConfirmStep(driver).wait_loaded()
    assert confirm.summary_value("ФИО") == f"{b.first_name} {b.last_name} {b.patronymic}".upper()
    assert confirm.summary_value("ПИНФЛ") == b.pinfl
    assert confirm.summary_value("ГРНЗ") == c.grnz
    assert confirm.summary_value("Номер техпаспорта") == c.tech_passport
    assert confirm.summary_value("Желаемая сумма").replace(" ", "") == data.amount
    confirm.submit(comment="Автотест: заявка создана автоматически")

    # Заявка появилась во вкладке «На оценке»
    confirm.to_home()
    return ApplicationsPage(driver).open().card_with(c.grnz)


def create_application_basic(driver, manager):
    """Заявка «Новая»: заёмщик + авто + 6 фото + комментарий (без доп. фото и созаёмщика)."""
    prepare_russian_home(driver, manager)
    data = factories.application()
    card = _create_application(driver, data)
    assert data.car.grnz in card.get_attribute("content-desc")


def create_application_with_extra_photo(driver, manager):
    """Заявка «Новая» с дополнительным фото авто."""
    prepare_russian_home(driver, manager)
    data = factories.application(extra_photo=True)
    card = _create_application(driver, data)
    assert data.car.grnz in card.get_attribute("content-desc")


def create_application_with_extra_photo_and_co_borrower(driver, manager):
    """Заявка «Новая» с дополнительным фото и созаёмщиком (ID card)."""
    prepare_russian_home(driver, manager)
    data = factories.application(extra_photo=True, with_co_borrower=True)
    card = _create_application(driver, data)
    assert data.car.grnz in card.get_attribute("content-desc")
