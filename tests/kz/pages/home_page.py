from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage, by_text


class HomePage(BasePage):
    """Главная (KZ): карточка пользователя, разделы, новости.

    Подтверждено скриншотом главной страницы: Мерей Бурабай, роль «Менеджер».
    """

    # noReset=True сохраняет язык интерфейса между запусками — на главную можно
    # попасть и на казахском (первый вход после сброса), и на русском (если язык
    # переключили в прошлом запуске), поэтому локаторы принимают оба варианта.
    TAB_HOME = (AppiumBy.XPATH, "//*[@content-desc='бастапқы бет' or @content-desc='главная']")
    APPLICATIONS = (AppiumBy.XPATH, "//*[@content-desc='Өтінімдер' or @content-desc='Заявки']")

    def wait_loaded(self):
        self.wait_visible(self.TAB_HOME)
        return self

    def role_label(self, role):
        return self.wait_visible(by_text(role))

    def applications_button(self):
        return self.wait_visible(self.APPLICATIONS)
