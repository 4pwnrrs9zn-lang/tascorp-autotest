from pages.base_page import BasePage

from ..locators import Start


class StartPage(BasePage):
    """Стартовый экран: логотип TAS и кнопка «Кіру» (кириллица)."""

    timeout = 60
    LOGIN_BUTTON = Start.LOGIN

    def wait_loaded(self):
        return self.wait_visible(self.LOGIN_BUTTON)
