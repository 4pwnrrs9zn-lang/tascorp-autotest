from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage, by_text


class MenuPage(BasePage):
    """Вкладка «menyu/меню» нижней навигации."""

    TAB = (AppiumBy.XPATH, "//android.widget.Button[@content-desc='menyu' or @content-desc='меню']")
    SETTINGS = (AppiumBy.XPATH, "//*[@content-desc='Sozlamalar' or @content-desc='Настройки']")

    def open(self):
        self.tap(self.TAB)
        return self

    def open_settings(self):
        self.tap(self.SETTINGS)
        return SettingsPage(self.driver)


class SettingsPage(BasePage):
    LANGUAGE = (AppiumBy.XPATH, "//*[@content-desc='Til' or @content-desc='Язык']")

    def open_language(self):
        self.tap(self.LANGUAGE)
        return LanguagePage(self.driver)


class LanguagePage(BasePage):
    RUSSIAN = (AppiumBy.ACCESSIBILITY_ID, "Русский")
    TITLE_RU = by_text("Настройки")
    TAB_HOME_RU = (AppiumBy.ACCESSIBILITY_ID, "главная")

    def choose_russian(self):
        self.tap(self.RUSSIAN)
        self.wait_visible(self.TITLE_RU)  # интерфейс перерисовался на русском
        return self

    def go_home(self):
        self.tap(self.TAB_HOME_RU)
