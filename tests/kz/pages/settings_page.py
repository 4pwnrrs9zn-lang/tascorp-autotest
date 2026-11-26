from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage, by_text


class MenuPage(BasePage):
    """Вкладка «мәзір/меню» нижней навигации."""

    TAB = (AppiumBy.XPATH, "//android.widget.Button[@content-desc='мәзір' or @content-desc='меню']")
    SETTINGS = (AppiumBy.XPATH, "//*[@content-desc='Баптаулар' or @content-desc='Настройки']")

    def open(self):
        self.tap(self.TAB)
        return self

    def open_settings(self):
        self.tap(self.SETTINGS)
        return SettingsPage(self.driver)


class SettingsPage(BasePage):
    LANGUAGE = (AppiumBy.XPATH, "//*[@content-desc='Тіл' or @content-desc='Язык']")

    def open_language(self):
        self.tap(self.LANGUAGE)
        return LanguagePage(self.driver)


class LanguagePage(BasePage):
    # Пункт списка подписан на текущем языке интерфейса: «Орысша», если сейчас
    # казахский, или «Русский», если уже переключено (noReset=True хранит язык
    # между запусками) — локатор принимает оба варианта.
    RUSSIAN = (AppiumBy.XPATH, "//*[@content-desc='Орысша' or @content-desc='Русский']")
    TITLE_RU = by_text("Настройки")
    TAB_HOME_RU = (AppiumBy.ACCESSIBILITY_ID, "главная")

    def choose_russian(self):
        self.tap(self.RUSSIAN)
        self.wait_visible(self.TITLE_RU)  # интерфейс перерисовался на русском
        return self

    def go_home(self):
        self.tap(self.TAB_HOME_RU)
