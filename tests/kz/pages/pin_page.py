from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import BasePage


class PinPage(BasePage):
    """Экран создания кода входа (KZ): 4 цифры, ввод дважды."""

    FIRST_DIGIT = (AppiumBy.ACCESSIBILITY_ID, "1")
    # Сервер завершил сессию входа — после кода приложение пишет «Ошибка, Нужно
    # переавторизоваться» и остаётся на этом экране
    REAUTH_ERROR = (AppiumBy.XPATH, "//*[contains(@text, 'переавториз') or contains(@content-desc, 'переавториз')]")
    # «Забыли код-пароль?» — единственная надпись с «?» на экране (без привязки к языку)
    FORGOT = (AppiumBy.XPATH, "//*[contains(@text, '?') or contains(@content-desc, '?')][@clickable='true']")
    # Диалог «Сбросить код-пароль»: «ДА» у приложения — button2 (не зависит от языка)
    RESET_CONFIRM = (AppiumBy.ID, "android:id/button2")

    def wait_loaded(self):
        return self.wait_visible(self.FIRST_DIGIT)

    def enter(self, pin):
        for digit in pin:
            self.tap((AppiumBy.ACCESSIBILITY_ID, digit))

    def reset(self):
        """«Забыли код-пароль?» → «ДА»: приложение забывает вход и возвращается к логину."""
        self.tap(self.FORGOT)
        self.tap(self.RESET_CONFIRM)

    def create(self, pin):
        self.enter(pin)  # ввод кода
        self.enter(pin)  # подтверждение
