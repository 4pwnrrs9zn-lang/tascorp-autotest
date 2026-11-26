from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def by_text(text):
    return AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{text}")'


def by_test_id(test_id, class_name="android.widget.Button"):
    """testID из React Native попадает в resource-id без префикса пакета."""
    return (
        AppiumBy.ANDROID_UIAUTOMATOR,
        f'new UiSelector().resourceId("{test_id}").className("{class_name}")',
    )


POLL = 0.2  # по умолчанию WebDriverWait опрашивает раз в 0.5 с — это до 0.5 с на каждое ожидание


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
