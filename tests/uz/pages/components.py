"""Общие действия с формами приложения: поля по подписи, справочники, даты, прокрутка."""
import random

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage

DICTIONARY_ITEMS = (AppiumBy.XPATH, "//*[@resource-id='undefined.modal.list']//android.widget.Button")
DICTIONARY_SEARCH = (AppiumBy.XPATH, "//android.widget.EditText[@resource-id='undefined.modal']")

YEAR_HEADER = (AppiumBy.ID, "android:id/date_picker_header_year")
YEAR_LIST = "android:id/date_picker_year_picker"
MONTH_VIEW = "android:id/month_view"
DATE_OK = (AppiumBy.ID, "android:id/button1")


def label_xpath(label):
    return f"//android.widget.TextView[@text='{label}']"


def input_xpath(label):
    """Поле ввода, идущее сразу за подписью (так устроены все формы приложения)."""
    return f"{label_xpath(label)}/following-sibling::*[1]/descendant-or-self::android.widget.EditText"


def picker_xpath(label):
    """Кликабельная область выпадающего поля/даты сразу за подписью."""
    return f"{label_xpath(label)}/following-sibling::*[1]"


class Form(BasePage):
    swipe_limit = 12
    _window = None

    @property
    def window(self):
        if Form._window is None:
            Form._window = self.driver.get_window_size()
        return Form._window

    # ---------- прокрутка ----------
    def swipe_up(self, ratio=0.35):
        """Листает контент вниз на долю экрана без инерции. Возвращает, можно ли листать дальше."""
        size = self.window
        top, height = int(size["height"] * 0.25), int(size["height"] * 0.5)
        return self.driver.execute_script("mobile: scrollGesture", {
            "left": 0, "top": top, "width": size["width"], "height": height,
            "direction": "down", "percent": min(ratio / 0.5, 1.0), "speed": 1500,
        })

    def _visible_enough(self, el):
        """Элемент целиком выше нижней части экрана (не под клавиатурой / нижней кнопкой)."""
        rect = el.rect
        return rect["y"] + rect["height"] < self.window["height"] * 0.8

    def scroll_to(self, xpath, max_swipes=None):
        """Листает экран вниз, пока элемент не окажется в видимой части.

        Вверх намеренно не листаем: формы открыты в bottom-sheet, и свайп вниз его закрывает.
        Поэтому поля заполняются строго сверху вниз.
        """
        self.driver.implicitly_wait(0)
        try:
            for _ in range(max_swipes or self.swipe_limit):
                found = self.driver.find_elements(AppiumBy.XPATH, xpath)
                if found and self._visible_enough(found[0]):
                    return found[0]
                if not self.swipe_up():  # дальше листать некуда
                    break
            found = self.driver.find_elements(AppiumBy.XPATH, xpath)
            if found:
                return found[0]
            raise NoSuchElementException(f"Не найден элемент после прокрутки: {xpath}")
        finally:
            self.driver.implicitly_wait(5)

    def hide_keyboard(self, label):
        """Снимает фокус с поля тапом по его подписи.

        Экранная клавиатура на эмуляторе отключена (conftest.no_soft_keyboard), но если она
        всё же появится, тап по подписи её спрячет. driver.hide_keyboard() нельзя: он жмёт
        «Назад», и это закрывает bottom-sheet с формой.
        """
        self.driver.find_element(AppiumBy.XPATH, label_xpath(label)).click()

    # ---------- поля ----------
    def fill(self, label, value):
        el = self.scroll_to(input_xpath(label))
        el.click()
        el.clear()
        el.send_keys(value)
        self.hide_keyboard(label)

    def field_value(self, label):
        return self.scroll_to(input_xpath(label)).text

    def wait_field(self, label, timeout=None):
        """Ждёт появления поля, которое показывается не сразу (Модель после Марки, Район после Области)."""
        return self.wait_visible((AppiumBy.XPATH, picker_xpath(label)), timeout)

    def pick(self, label, option=None):
        """Открывает справочник поля и выбирает пункт: по тексту или случайный. Возвращает выбранное."""
        self.scroll_to(picker_xpath(label)).click()
        items = WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_all_elements_located(DICTIONARY_ITEMS)
        )
        if option is None:
            item = random.choice(items)
        else:
            matches = [i for i in items if i.get_attribute("content-desc") == option]
            if not matches:
                self.driver.find_element(*DICTIONARY_SEARCH).send_keys(option)
                matches = WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_all_elements_located(DICTIONARY_ITEMS)
                )
            item = matches[0]
        chosen = item.get_attribute("content-desc")
        item.click()
        WebDriverWait(self.driver, self.timeout).until(EC.invisibility_of_element_located(DICTIONARY_ITEMS))
        return chosen

    # ---------- даты (системный DatePicker Android) ----------
    def pick_date(self, label, date):
        """Выбирает дату. Месяц — текущий месяц календаря (приложение открывает его на сегодня)."""
        self.scroll_to(picker_xpath(label)).click()
        self.tap(YEAR_HEADER)
        self._select_year(date.year)
        self._select_month(date.month)
        self.tap((
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().resourceId("{MONTH_VIEW}").childSelector(new UiSelector().text("{date.day}"))',
        ))
        self.tap(DATE_OK)

    def _select_year(self, year):
        """Прокручивает список годов до нужного и выбирает его.

        Прокрутка — mobile: scrollGesture на низкой скорости: без инерции, иначе список
        продолжает крутиться после жеста и тап попадает не туда.
        """
        locator = (
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().resourceId("{YEAR_LIST}").childSelector(new UiSelector().text("{year}"))',
        )
        year_list = self.wait_visible((AppiumBy.ID, YEAR_LIST))
        rows = year_list.find_elements(AppiumBy.ID, "android:id/text1")
        # Типичная высота строки (строка выбранного года крупнее, крайние — обрезаны)
        heights = sorted(e.rect["height"] for e in rows)
        row_height = heights[len(heights) // 2]
        # Список открыт на выбранном годе (он в шапке); up — к более ранним годам
        direction = "up" if year < self._header_year() else "down"
        self.driver.implicitly_wait(0)
        try:
            for _ in range(40):
                found = self.driver.find_elements(*locator)
                # Жмём только по году, видимому целиком: у края списка клик уходит мимо
                if found and found[0].rect["height"] >= row_height * 0.9:
                    if self._click_year(locator, year):
                        return
                    continue
                self.driver.execute_script("mobile: scrollGesture", {
                    "elementId": year_list.id, "direction": direction, "percent": 0.9, "speed": 1200,
                })
        finally:
            self.driver.implicitly_wait(5)
        raise TimeoutException(f"Год {year} не найден в календаре")

    def _list_signature(self):
        try:
            return [(e.text, e.rect["y"]) for e in self.driver.find_elements(AppiumBy.ID, "android:id/text1")]
        except Exception:  # noqa: BLE001 — строки пересоздаются, пока список движется
            return None

    def _wait_list_still(self, timeout=3):
        import time
        end = time.time() + timeout
        prev = self._list_signature()
        while time.time() < end:
            time.sleep(0.15)
            cur = self._list_signature()
            if cur is not None and cur == prev:
                return
            prev = cur

    def _click_year(self, locator, year):
        """Клик по году с проверкой: пока список движется, тап лишь останавливает его."""
        for _ in range(3):
            self._wait_list_still()
            found = self.driver.find_elements(*locator)
            if not found:
                return False
            found[0].click()
            try:
                WebDriverWait(self.driver, 1.5, poll_frequency=0.2).until(lambda d: self._header_year() == year)
                return True
            except TimeoutException:
                continue
        return False

    def _header_year(self):
        return int(self.driver.find_element(*YEAR_HEADER).text)

    def _shown_month(self):
        """(год, месяц), которые сейчас показывает календарь — по подписи дня «01 September 1990»."""
        import calendar
        day = self.wait_visible((
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().resourceId("{MONTH_VIEW}").childSelector(new UiSelector().text("1"))',
        ))
        _, month_name, year = day.get_attribute("content-desc").split()
        return int(year), list(calendar.month_name).index(month_name)

    def _select_month(self, month):
        """Листает месяцы стрелками, пока календарь не покажет нужный."""
        for _ in range(24):
            year, current = self._shown_month()
            if current == month:
                return
            self.tap((AppiumBy.ID, "android:id/next" if month > current else "android:id/prev"))
            WebDriverWait(self.driver, self.timeout).until(lambda d: self._shown_month() != (year, current))
        raise TimeoutException(f"Не удалось перейти на месяц {month}")


class Camera(BasePage):
    """Системная камера Android (приложение открывает её через intent)."""

    SHUTTER = (AppiumBy.ID, "com.android.camera2:id/shutter_button")
    DONE = (AppiumBy.ID, "com.android.camera2:id/done_button")
    timeout = 30

    def take_photo(self, slot_locator, app_package="kz.tasgroup.tascorp.uz"):
        """Тап по ячейке фото → снимок → подтверждение → возврат в приложение."""
        self.tap(slot_locator)
        # Кнопка съёмки видна раньше, чем камера готова, — первый тап может не сработать
        for _ in range(5):
            self.tap(self.SHUTTER)
            try:
                self.wait_visible(self.DONE, timeout=4)
                break
            except TimeoutException:
                continue
        self.tap(self.DONE)
        WebDriverWait(self.driver, self.timeout).until(lambda d: d.current_package == app_package)
