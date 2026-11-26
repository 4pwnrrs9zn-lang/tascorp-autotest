from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import POLL, BasePage


def handle_evaluator_rating(driver, expect, option="Сумма соответствует рынку"):
    """«Оценка работы» (заголовок «Оцените работу оценщика») — всплывает, если у
    менеджера есть предыдущая заявка, которую оценщик уже оценил, а сам менеджер ещё
    не подтвердил эту оценку: дальше работать нельзя, пока не оценишь работу оценщика
    (варианты: «Сумма соответствует рынку» / «Удовлетворительно» / «Сумма не
    соответствует рынку» — кнопка «Сохранить» неактивна, пока не выбран один из них).
    Если прошлая заявка менеджера ещё не оценена — модалка не появляется вовсе,
    предсказать её заранее нельзя (зависит от того, когда оценщик отработал).
    Подтверждено на реальном устройстве + uiautomator dump, 2026-10-01.

    Вызывается в двух местах, где она замечена: при входе в «Заявки» и после выбора
    типа заявки — чтобы покрыть оба варианта, не зная точно, к какому именно шагу
    она привязана в данной сборке.

    expect — локатор экрана, который откроется, если модалки нет: ждём, что появится
    раньше, вместо фиксированной паузы на «вдруг модалка ещё всплывёт».
    """
    title = (AppiumBy.XPATH, "//android.widget.TextView[@text='Оценка работы']")
    rated = False
    while True:
        shown = WebDriverWait(driver, 30, poll_frequency=POLL).until(EC.any_of(
            EC.visibility_of_element_located(title), EC.visibility_of_element_located(expect)))
        if shown.get_attribute("text") != "Оценка работы":
            return rated
        rated = True
        BasePage(driver).tap_still((AppiumBy.ACCESSIBILITY_ID, option), timeout=10)  # модалка выезжает анимацией
        WebDriverWait(driver, 10, poll_frequency=POLL).until(EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, "Сохранить"))).click()
        WebDriverWait(driver, 10, poll_frequency=POLL).until(EC.invisibility_of_element_located(title))
        # После оценки, всплывшей на выборе типа, приложение возвращается в список заявок
        # (сборка 1.2.4 от 15.10.2026) — тогда ждать expect бессмысленно
        if expect != ApplicationsPage.NEW_APPLICATION and WebDriverWait(driver, 10, poll_frequency=POLL).until(EC.any_of(
                EC.visibility_of_element_located(title),
                EC.visibility_of_element_located(expect),
                EC.visibility_of_element_located(ApplicationsPage.NEW_APPLICATION))).get_attribute("content-desc") == "Новая заявка":
            return rated


class ApplicationsPage(BasePage):
    """Раздел «Заявки» (интерфейс на русском)."""

    ENTRY = (AppiumBy.ACCESSIBILITY_ID, "Заявки")
    TABS = ("В работе", "На оценке", "Завершенные")
    NEW_APPLICATION = (AppiumBy.ACCESSIBILITY_ID, "Новая заявка")
    # Типы займа в шторке «Тип заявки» (подтверждено вживую)
    TYPE_NEW = "Новая"
    TYPE_REFINANCE = "Рефинансирование"
    TYPE_AUTOCREDIT = "Автокредит"
    TYPE_TRANSH = "Транш"

    # Первый экран мастера — одинаковый для всех типов займа
    BORROWER_TITLE = (AppiumBy.XPATH, "//android.widget.TextView[@text='Данные заемщика']")

    def open(self):
        self.tap(self.ENTRY)
        handle_evaluator_rating(self.driver, expect=self.NEW_APPLICATION)
        return self

    def tab(self, name):
        return self.wait_visible((AppiumBy.ACCESSIBILITY_ID, name))

    def start_new(self, loan_type=TYPE_NEW):
        """«Новая заявка» → тип. Если вместо заявки всплыла «Оценка работы», после её
        отправки приложение возвращается в список заявок — начинаем заявку заново."""
        for _ in range(3):
            self.tap(self.NEW_APPLICATION)
            # Шторка «Тип заявки» выезжает анимацией: тап на ходу попадал в соседний тип
            self.tap_still((AppiumBy.ACCESSIBILITY_ID, loan_type))
            if not handle_evaluator_rating(self.driver, expect=self.BORROWER_TITLE):
                return
            try:
                self.wait_visible(self.BORROWER_TITLE, timeout=3)
                return
            except TimeoutException:
                pass  # вернулись в список заявок — начинаем заново
        raise AssertionError("Не открылась новая заявка: после «Оценки работы» снова список заявок")

    def card_with(self, text, tab="На оценке"):
        """Карточка заявки во вкладке, в описании которой есть text (например, ГРНЗ)."""
        self.tap((AppiumBy.ACCESSIBILITY_ID, tab))
        return self.wait_visible((AppiumBy.XPATH, f"//*[contains(@content-desc, '{text}')]"), timeout=60)
