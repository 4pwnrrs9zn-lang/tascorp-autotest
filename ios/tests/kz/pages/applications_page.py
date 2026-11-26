from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import POLL, BasePage, by_name

from ..locators import Applications, Borrower


def handle_evaluator_rating(driver, expect, option="Сумма соответствует рынку"):
    """Модалка «Оценка работы» — см. описание в Android-проекте (tests/kz/pages/applications_page.py):
    всплывает непредсказуемо, пока менеджер не подтвердит оценку прошлой заявки.
    Возвращает True, если оценку пришлось отправить (на iOS вживую 15.10.2026)."""
    rated = False
    while True:
        shown = WebDriverWait(driver, 30, poll_frequency=POLL).until(EC.any_of(
            EC.visibility_of_element_located(Applications.RATING_TITLE), EC.visibility_of_element_located(expect)))
        if shown.get_attribute("name") != "Оценка работы":
            return rated
        rated = True
        BasePage(driver).tap_still(by_name(option), timeout=10)
        BasePage(driver).tap(Applications.SAVE, timeout=10)
        WebDriverWait(driver, 10, poll_frequency=POLL).until(
            EC.invisibility_of_element_located(Applications.RATING_TITLE))
        # Дальше — следующая оценка, ожидаемый экран или (после «Новая заявка») снова список
        if expect != Applications.NEW and WebDriverWait(driver, 10, poll_frequency=POLL).until(EC.any_of(
                EC.visibility_of_element_located(Applications.RATING_TITLE),
                EC.visibility_of_element_located(expect),
                EC.visibility_of_element_located(Applications.NEW))).get_attribute("name") == "Новая заявка":
            return rated


class ApplicationsPage(BasePage):
    """Раздел «Заявки» (интерфейс на русском)."""

    TABS = Applications.TABS
    TYPE_NEW = "Новая"
    TYPE_AUTOCREDIT = "Автокредит"
    TYPE_TRANSH = "Транш"
    # С 02.11.2026 «Рефинансирование» разделено на два продукта; заявка создаётся одинаково,
    # отличается только credit_type на бэке (внутреннее — 2, внешнее — 4)
    TYPE_REFINANCE_INTERNAL = "Внутреннее рефинансирование"
    TYPE_REFINANCE_EXTERNAL = "Внешнее рефинансирование"

    def open(self):
        self.tap(Applications.ENTRY)
        handle_evaluator_rating(self.driver, expect=Applications.NEW)
        return self

    def tab(self, name):
        return self.wait_visible(Applications.tab(name))

    def start_new(self, loan_type=TYPE_NEW):
        """«Новая заявка» → тип. Если вместо заявки всплыла «Оценка работы», после её
        отправки приложение возвращается в список заявок — начинаем заявку заново."""
        for _ in range(3):
            self.tap(Applications.NEW)
            # Шторка «Тип заявки» выезжает анимацией
            self.tap_still(Applications.loan_type(loan_type))
            if not handle_evaluator_rating(self.driver, expect=Borrower.TITLE):
                return
            try:
                self.wait_visible(Borrower.TITLE, timeout=3)
                return
            except TimeoutException:
                pass  # вернулись в список заявок — начинаем заново
        raise AssertionError("Не открылась новая заявка: после «Оценки работы» снова список заявок")
