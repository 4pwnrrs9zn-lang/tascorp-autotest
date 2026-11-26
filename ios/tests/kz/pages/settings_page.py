from pages.base_page import BasePage

from ..locators import Menu


class MenuPage(BasePage):
    """Вкладка «мәзір/меню» нижней навигации."""

    def open(self):
        self.tap(Menu.TAB)
        return self

    def open_settings(self):
        self.tap(Menu.SETTINGS)
        return SettingsPage(self.driver)


class SettingsPage(BasePage):
    def open_language(self):
        self.tap(Menu.LANGUAGE)
        return LanguagePage(self.driver)


class LanguagePage(BasePage):
    TITLE_RU = Menu.TITLE_RU

    def choose_russian(self):
        self.tap(Menu.RUSSIAN)
        self.wait_visible(Menu.TITLE_RU)
        return self

    def go_home(self):
        self.tap(Menu.TAB_HOME_RU)
