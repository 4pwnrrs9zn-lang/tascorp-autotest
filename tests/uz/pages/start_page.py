from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


class StartPage(BasePage):
    """Стартовый экран: логотип TAS и кнопка входа «Kirish» (узбекский)."""

    timeout = 60
    LOGIN_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "Kirish")

    def wait_loaded(self):
        return self.wait_visible(self.LOGIN_BUTTON)

    def tap_login(self):
        self.tap(self.LOGIN_BUTTON)
