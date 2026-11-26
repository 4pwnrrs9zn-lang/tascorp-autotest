from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage, by_text


class HomePage(BasePage):
    """Главная (UZ): карточка пользователя, разделы, новости."""

    TAB_HOME = (AppiumBy.ACCESSIBILITY_ID, "asosiy")
    APPLICATIONS = (AppiumBy.ACCESSIBILITY_ID, "Arizalar")

    def wait_loaded(self):
        self.wait_visible(self.TAB_HOME)
        return self

    def role_label(self, role):
        return self.wait_visible(by_text(role))

    def applications_button(self):
        return self.wait_visible(self.APPLICATIONS)
