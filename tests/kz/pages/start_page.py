from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


class StartPage(BasePage):
    """Стартовый экран: логотип TAS и кнопка входа «Кіру» (казахский, кириллица —
    визуально похоже на латинское "Kipy", не перепутать).
    """

    timeout = 60
    # «Кіру» — на казахском (после сброса данных), «Войти» — если язык уже русский
    LOGIN_BUTTON = (AppiumBy.XPATH, "//*[@content-desc='Кіру' or @content-desc='Войти']")

    def wait_loaded(self):
        return self.wait_visible(self.LOGIN_BUTTON)

    def tap_login(self):
        self.tap(self.LOGIN_BUTTON)
