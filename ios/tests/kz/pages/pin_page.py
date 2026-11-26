import time

from pages.base_page import BasePage

from ..locators import Pin


class PinPage(BasePage):
    """Экран кода входа: цифровая клавиатура приложения, 4 цифры (создание — дважды)."""

    FIRST_DIGIT = Pin.digit("1")
    # С 22.10.2026 при создании кода терялась одна цифра повтора (7 точек из 8): ряд для
    # повтора появляется анимацией, и нажатие в это время пропадает. Точки-индикаторы в
    # дереве одинаковые (заполненная от пустой не отличается) — ждать по ним нельзя
    DIGIT_PAUSE = 0.3
    REPEAT_PAUSE = 1.5

    def wait_loaded(self):
        return self.wait_visible(self.FIRST_DIGIT)

    def enter(self, pin):
        for d in pin:
            self.tap(Pin.digit(d))
            time.sleep(self.DIGIT_PAUSE)

    def reset(self):
        """Сброс кода: приложение возвращается на ввод логина и пароля."""
        self.tap(Pin.FORGOT)
        self.tap(Pin.RESET_YES, timeout=10)

    def create(self, pin):
        self.enter(pin)
        time.sleep(self.REPEAT_PAUSE)
        self.enter(pin)
