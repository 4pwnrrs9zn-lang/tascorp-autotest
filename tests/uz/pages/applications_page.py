from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


class ApplicationsPage(BasePage):
    """Раздел «Заявки» (интерфейс на русском)."""

    ENTRY = (AppiumBy.ACCESSIBILITY_ID, "Заявки")
    TABS = ("В работе", "На оценке", "Завершенные")
    NEW_APPLICATION = (AppiumBy.ACCESSIBILITY_ID, "Новая заявка")
    TYPE_NEW = (AppiumBy.ACCESSIBILITY_ID, "Новая")

    def open(self):
        self.tap(self.ENTRY)
        self.wait_visible(self.NEW_APPLICATION)
        return self

    def tab(self, name):
        return self.wait_visible((AppiumBy.ACCESSIBILITY_ID, name))

    def start_new(self):
        self.tap(self.NEW_APPLICATION)
        self.tap(self.TYPE_NEW)  # «Тип заявки» → «Новая»

    def card_with(self, text, tab="На оценке"):
        """Карточка заявки во вкладке, в описании которой есть text (например, ГРНЗ)."""
        self.tap((AppiumBy.ACCESSIBILITY_ID, tab))
        return self.wait_visible((AppiumBy.XPATH, f"//*[contains(@content-desc, '{text}')]"), timeout=60)
