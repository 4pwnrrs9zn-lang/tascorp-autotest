from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


class PinPage(BasePage):
    """Экран создания кода входа (UZ): 4 цифры, ввод дважды."""

    FIRST_DIGIT = (AppiumBy.ACCESSIBILITY_ID, "1")

    def wait_loaded(self):
        return self.wait_visible(self.FIRST_DIGIT)

    def enter(self, pin):
        for digit in pin:
            self.tap((AppiumBy.ACCESSIBILITY_ID, digit))

    def create(self, pin):
        self.enter(pin)  # ввод кода
        self.enter(pin)  # подтверждение
