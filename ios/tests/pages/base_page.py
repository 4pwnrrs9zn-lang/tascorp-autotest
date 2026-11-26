from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def by_name(name):
    """Элемент по подписи (accessibilityLabel/testID → name). В React Native контейнеры
    перенимают подписи всех дочерних элементов: «Кіру» есть и у кнопки, и у обёрток
    размером во весь экран — поэтому берём последний (самый глубокий) элемент: [-1].
    Class chain выполняется внутри WebDriverAgent — в разы быстрее XPath."""
    return AppiumBy.IOS_CLASS_CHAIN, f'**/XCUIElementTypeAny[`name == "{name}"`][-1]'


def by_any_name(*names):
    """Один из вариантов подписи — интерфейс бывает на казахском или русском (no_reset)."""
    variants = ", ".join(f'"{n}"' for n in names)
    return AppiumBy.IOS_CLASS_CHAIN, f"**/XCUIElementTypeAny[`name IN {{{variants}}}`][-1]"


def button(name):
    return AppiumBy.IOS_PREDICATE, f'type == "XCUIElementTypeButton" AND name == "{name}"'


def static_text(text):
    return AppiumBy.IOS_PREDICATE, f'type == "XCUIElementTypeStaticText" AND name == "{text}"'


POLL = 0.1  # по умолчанию WebDriverWait опрашивает раз в 0.5 с — это до 0.5 с на каждое ожидание


class BasePage:
    timeout = 30

    def __init__(self, driver):
        self.driver = driver

    def wait_visible(self, locator, timeout=None):
        return WebDriverWait(self.driver, timeout or self.timeout, poll_frequency=POLL).until(
            EC.visibility_of_element_located(locator)
        )

    def tap(self, locator, timeout=None):
        WebDriverWait(self.driver, timeout or self.timeout, poll_frequency=POLL).until(
            EC.element_to_be_clickable(locator)
        ).click()

    def wait_still(self, locator, timeout=None):
        """Ждёт, пока элемент перестанет двигаться: шторки и справочники выезжают
        анимацией, и тап по пункту во время движения попадает в соседний пункт."""
        last = {}

        def still(driver):
            found = driver.find_elements(*locator)
            if not found:
                last.clear()
                return False
            try:
                rect = found[0].rect
            except StaleElementReferenceException:
                return False
            if last.get("rect") == rect:
                return found[0]
            last["rect"] = rect
            return False

        return WebDriverWait(self.driver, timeout or self.timeout, poll_frequency=POLL).until(still)

    def tap_still(self, locator, timeout=None):
        self.wait_still(locator, timeout).click()
