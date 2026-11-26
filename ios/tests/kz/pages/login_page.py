from pages.base_page import BasePage

from ..locators import Login


class LoginPage(BasePage):
    """Экран логина/пароля: «Логин мен парольді еңгізіңіз»."""

    LOGIN_INPUT = Login.LOGIN

    def wait_loaded(self):
        return self.wait_visible(Login.LOGIN)

    def login(self, login, password):
        # Экран выезжает анимацией: без ожидания «простоя» приложения (waitForQuiescence
        # выключен ради скорости) ввод на ходу терялся — поле оставалось пустым
        field = self.wait_still(Login.LOGIN)
        field.send_keys(login)
        if field.get_attribute("value") != login.lower():  # поле само переводит логин в нижний регистр
            field.clear()
            field.send_keys(login)
        # Пароль доходит целиком только при английской раскладке (conftest.simulator):
        # с русской раскладкой в защищённое поле попадала половина символов
        self.wait_visible(Login.PASSWORD).send_keys(password)
        # Клавиатура закрывает «Кіру» — прячем её «Готово», тап по подписи её не убирает
        self.tap(Login.KEYBOARD_DONE, timeout=5)
        self.tap(Login.SUBMIT)
