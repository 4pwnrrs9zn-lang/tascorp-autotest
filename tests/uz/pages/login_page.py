from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage, by_test_id


class LoginPage(BasePage):
    """Экран ввода логина/пароля (UZ): «Login va parolni kiriting»."""

    # У полей нет testID: логин — первое поле, пароль — поле с password=true
    LOGIN_INPUT = (AppiumBy.XPATH, "(//android.widget.EditText)[1]")
    PASSWORD_INPUT = (AppiumBy.XPATH, "//android.widget.EditText[@password='true']")
    SUBMIT_BUTTON = by_test_id("loginBtn")

    def wait_loaded(self):
        return self.wait_visible(self.LOGIN_INPUT)

    def login(self, login, password):
        self.wait_visible(self.LOGIN_INPUT).send_keys(login)
        self.wait_visible(self.PASSWORD_INPUT).send_keys(password)
        # Экранная клавиатура отключена (conftest.no_soft_keyboard) — прятать нечего
        self.tap(self.SUBMIT_BUTTON)
