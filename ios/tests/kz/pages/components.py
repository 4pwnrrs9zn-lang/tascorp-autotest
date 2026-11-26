"""Действия с формами приложения на iOS: ввод, справочники, даты, прокрутка, камера.

Методы принимают локатор конкретного поля из kz/locators.py.
"""
import os
import random
from pathlib import Path

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import POLL, BasePage

from ..locators import Camera as CameraLoc
from ..locators import DatePicker, Dictionary

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")
# Случайный пункт справочника — из первых: список открывается с начала, они всегда на экране
SAFE_DICTIONARY_ITEMS = 8


class Form(BasePage):
    _window = None

    @property
    def window(self):
        if Form._window is None:
            Form._window = self.driver.get_window_size()
        return Form._window

    # ---------- прокрутка ----------
    def _swipe_up(self):
        """Листает форму вниз на ~половину экрана быстрым жестом без инерции, у правого края —
        мимо полей. Вверх не листаем: свайп вниз закрывает bottom-sheet с формой."""
        w, h = self.window["width"], self.window["height"]
        self.driver.execute_script("mobile: dragFromToWithVelocity", {
            "pressDuration": 0.05, "holdDuration": 0.05, "velocity": 2500,
            "fromX": w - 12, "fromY": int(h * 0.75), "toX": w - 12, "toY": int(h * 0.3),
        })

    def _in_work_area(self, el):
        """Ниже шапки и выше нижнего края экрана: у самого края тап по дате не открывал шторку."""
        rect = el.rect
        h = self.window["height"]
        return rect["y"] > h * 0.1 and rect["y"] + rect["height"] < h * 0.85

    def on_screen(self, locator, max_swipes=8):
        """Элемент формы на экране — одно чтение координат; если он ниже, листаем."""
        el = self.driver.find_element(*locator)
        for _ in range(max_swipes):
            try:
                if self._in_work_area(el):
                    return el
            except StaleElementReferenceException:
                pass  # форма перерисовалась — найдём заново
            self._swipe_up()
            el = self.driver.find_element(*locator)
        return el

    # ---------- поля ----------
    def type_text(self, locator, value):
        """Ввод в однострочное поле — сразу, без прокрутки: XCUITest сам доводит поле до
        видимой области. Return в конце закрывает клавиатуру той же командой (проверено и на
        цифровых полях) — сразу можно заполнять следующее."""
        try:
            self.driver.find_element(*locator).send_keys(f"{value}\n")
        except WebDriverException:
            self.on_screen(locator).send_keys(f"{value}\n")

    def type_multiline(self, locator, label_locator, value):
        """Многострочное поле: Return дал бы перенос строки — клавиатуру прячем тапом по подписи."""
        self.on_screen(locator).send_keys(value)
        self.driver.find_element(*label_locator).click()

    def value_of(self, locator):
        return self.driver.find_element(*locator).get_attribute("value")

    # ---------- справочники ----------
    def open_dictionary(self, field_locator, items_timeout=None):
        self.press(field_locator)
        self.wait_still(Dictionary.item(1), items_timeout)  # шторка выезжает анимацией

    def choose_random(self, field_locator, items_timeout=None):
        """Случайный пункт справочника с поиском. Возвращает выбранное."""
        self.open_dictionary(field_locator, items_timeout)
        found = self.driver.find_elements(*Dictionary.item(random.randint(1, SAFE_DICTIONARY_ITEMS)))
        item = found[0] if found else self.driver.find_element(*Dictionary.item(1))  # короткий список
        chosen = item.get_attribute("name")
        item.click()
        WebDriverWait(self.driver, self.timeout, poll_frequency=POLL).until(
            EC.invisibility_of_element_located(Dictionary.SEARCH))
        return chosen

    def choose_option(self, field_locator, option_locator):
        """Короткий список без поиска (например, «Орган выдачи»): открыть и выбрать пункт.

        Поле у нижнего края экрана сначала прокручиваем вверх: с 14.10.2026 шторка,
        открытая оттуда, остаётся за пределами экрана (пункты не видны, тап по ним не
        выбирает), а прозрачная подложка перекрывает форму. Выбор проверяем по самому
        полю — после него имя «<подпись>. selected. <значение>»; если нет — повторяем."""
        for _ in range(3):
            self.on_screen(field_locator).click()
            try:
                self.tap_still(option_locator, timeout=15)
            except StaleElementReferenceException:
                pass
            try:
                WebDriverWait(self.driver, 3, poll_frequency=POLL).until(
                    lambda d: ". selected" in (d.find_element(*field_locator).get_attribute("name") or ""))
                return
            except (TimeoutException, StaleElementReferenceException):
                # Шторка могла застрять за экраном — закрываем её тапом по подложке над ней
                for overlay in self.driver.find_elements(*Dictionary.OVERLAY):
                    if overlay.get_attribute("visible") == "true":
                        self.driver.execute_script("mobile: tap", {"x": self.window["width"] // 2, "y": 150})
                        break
        raise AssertionError("Пункт справочника не выбрался: поле осталось пустым после 3 попыток")

    # ---------- даты ----------
    def set_date(self, field_locator, date):
        """Шторка с колёсами месяц / день / год (месяцы по-английски — локаль Simulator en-US).
        Выбранная дата в дереве не видна (пустой label) — проверяется на экране-сводке."""
        # Сразу тап; если шторка не открылась (тап пришёлся на сдвиг формы после клавиатуры
        # или поле у самого края экрана) — показываем поле и повторяем
        self.press(field_locator)
        for attempt in range(3):
            try:
                self.wait_visible(DatePicker.DONE, timeout=2)
                break
            except TimeoutException:
                if attempt == 2:
                    raise
                self.on_screen(field_locator).click()
        month, day, year = self.driver.find_elements(*DatePicker.WHEELS)
        year.send_keys(str(date.year))
        month.send_keys(MONTHS[date.month - 1])
        day.send_keys(str(date.day))
        self.tap(DatePicker.DONE)

    # ---------- кнопки ----------
    def press(self, locator):
        """Кнопка формы: сразу нажатием (XCUITest сам доводит её до видимой области);
        если не вышло — показываем её и нажимаем снова."""
        try:
            self.driver.find_element(*locator).click()
        except WebDriverException:
            self.on_screen(locator).click()


class Camera(BasePage):
    """Системная камера (UIImagePickerController). На Simulator поверх неё — тестовая камера
    tools/test_camera (своя кнопка затвора с тем же идентификатором «PhotoCapture»)."""
    timeout = 30

    def take_photo(self, slot_locator, image=None):
        """Тап по ячейке фото → затвор → возврат в приложение.

        Затвор виден в дереве уже во время анимации появления камеры, а тап в это время
        iOS игнорирует (так бывает на первом прогоне после загрузки Simulator) — если
        камера не закрылась, жмём затвор ещё раз."""
        if image:
            # Снимок именно этим файлом (только на этот кадр) — см. tools/test_camera
            Path(os.environ["TAS_TEST_CAMERA_NEXT"]).write_text(str(image))
        self.tap(slot_locator)
        for attempt in range(3):
            try:
                self.tap(CameraLoc.SHUTTER, timeout=None if attempt == 0 else 2)
            except (StaleElementReferenceException, TimeoutException):
                if attempt == 0:
                    raise
                # повторный тап: камера успела закрыться — снимок сделан
            try:
                WebDriverWait(self.driver, 4, poll_frequency=POLL).until(
                    EC.invisibility_of_element_located(CameraLoc.SHUTTER))
                return
            except TimeoutException:
                continue
        raise AssertionError("Тестовая камера не сделала снимок: экран камеры не закрылся после 3 нажатий затвора")
