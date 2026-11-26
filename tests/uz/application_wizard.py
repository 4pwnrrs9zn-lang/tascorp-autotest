"""Шаги мастера создания заявки — по требованиям законодательства Узбекистана.

Поля, справочники и их порядок (ПИНФЛ, область/район, орган выдачи) заданы законом UZ.
Не переиспользовать для KZ напрямую: там свой tests/kz/application_wizard.py.
UI-механика (Form, Camera, справочники, календарь) — в tests/uz/pages/components.py.
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .pages.components import Camera, Form, label_xpath

ADD_MANUALLY = (AppiumBy.ACCESSIBILITY_ID, "Добавить вручную")
ADD_DOC_PHOTO = "//*[@content-desc='Добавить фото документа']"
SAVE = (AppiumBy.ACCESSIBILITY_ID, "Сохранить")
NEXT = "//android.widget.Button[@content-desc='Далее']"
FRONT = (AppiumBy.ACCESSIBILITY_ID, "Лицевая сторона")
BACK = (AppiumBy.ACCESSIBILITY_ID, "Обратная сторона")


def title(text):
    return AppiumBy.XPATH, f"//android.widget.TextView[@text='{text}']"


class Step(Form):
    TITLE = None

    def wait_loaded(self):
        self.wait_visible(title(self.TITLE))
        return self

    def summary_value(self, label):
        """Значение на экране-сводке: TextView сразу под подписью."""
        return self.scroll_to(f"{label_xpath(label)}/following-sibling::android.widget.TextView[1]").text

    def next(self):
        self.scroll_to(NEXT).click()

    def validation_errors(self):
        """Тексты ошибок валидации, видимые на экране (для понятного сообщения о падении)."""
        els = self.driver.find_elements(
            AppiumBy.XPATH, "//*[@resource-id='undefined.validationMessage' and string-length(@text) > 0]"
        )
        return [e.text for e in els]

    def open_document_photos(self):
        """«Добавить фото документа» с повтором: первый тап может попасть в анимацию закрытия справочника."""
        for _ in range(2):
            self.scroll_to(ADD_DOC_PHOTO).click()
            try:
                self.wait_visible(FRONT, timeout=10)
                return
            except TimeoutException:
                continue
        raise AssertionError(f"Не открылся экран фото документа. Ошибки формы: {self.validation_errors()}")

    def document_photos(self):
        """Экран «Лицевая сторона / Обратная сторона» → Сохранить."""
        camera = Camera(self.driver)
        camera.take_photo(FRONT)
        camera.take_photo(BACK)
        # Снимок обрабатывается не сразу: ранний «Сохранить» даёт «Загрузите фото».
        # Жмём, пока экран фото не закроется.
        for _ in range(5):
            self.tap(SAVE)
            try:
                WebDriverWait(self.driver, 5).until(EC.invisibility_of_element_located(FRONT))
                return
            except TimeoutException:
                continue
        raise AssertionError(f"Фото документа не сохранились: {self.upload_errors()}")

    def upload_errors(self):
        return [e.text for e in self.driver.find_elements(*title("Загрузите фото"))]


class IdCardForm(Step):
    """Форма ID card (одинаковая для заёмщика и созаёмщика)."""

    def fill_person(self, p):
        self.wait_visible((AppiumBy.XPATH, label_xpath("ПИНФЛ")))
        self.fill("ПИНФЛ", p.pinfl)
        self.fill("Фамилия", p.last_name)
        self.fill("Имя", p.first_name)
        self.fill("Отчество", p.patronymic)
        self.pick_date("Дата рождения", p.birth_date)
        self.fill("Серия", p.series)
        self.fill("Номер документа", p.doc_number)
        p.region = self.pick("Область")
        self.wait_field("Район")  # появляется после выбора области
        p.district = self.pick("Район")
        self.fill("Место рождения", p.birth_place)
        self.pick_date("Дата выдачи", p.issue_date)
        self.pick_date("Действителен до", p.expiry_date)
        self.fill("Орган выдачи", p.issuer)
        self.open_document_photos()


class BorrowerStep(Step):
    TITLE = "Данные заемщика"

    def add_manually(self, person):
        self.wait_loaded()
        # Тип документа по умолчанию — ID card
        self.tap(ADD_MANUALLY)
        IdCardForm(self.driver).fill_person(person)
        self.document_photos()
        self.wait_visible((AppiumBy.XPATH, NEXT))  # открылась сводка по заёмщику
        return self


class CarStep(Step):
    TITLE = "Автомобиль"

    def add_manually(self, car):
        self.wait_loaded()
        self.tap(ADD_MANUALLY)
        self.wait_visible((AppiumBy.XPATH, label_xpath("Марка")))
        car.brand = self.pick("Марка")
        self.wait_field("Модель")  # появляется после загрузки моделей марки
        car.model = self.pick("Модель")
        self.fill("Год выпуска авто", car.year)
        self.fill("ГРНЗ", car.grnz)
        self.fill("Номер техпаспорта", car.tech_passport)
        self.pick_date("Дата выдачи", car.issue_date)
        self.fill("Орган, выдавший техпаспорт", car.issuer)
        self.fill("Пробег", car.mileage)
        self.fill("Номер кузова", car.body_number)
        self.fill("Номер двигателя", car.engine_number)
        self.fill("Номер шасси", car.chassis_number)
        for label in ("Тип кузова", "Тип транспорта", "Цвет", "Страна производства"):
            car.picked[label] = self.pick(label)
        self.open_document_photos()
        self.document_photos()  # техпаспорт
        self.wait_visible((AppiumBy.XPATH, NEXT))  # открылась сводка по автомобилю
        return self


class CarPhotosStep(Step):
    TITLE = "Фото авто"
    REQUIRED = ("вид спереди", "вид сзади", "вид слева", "вид справа", "Клиент на фоне авто", "VIN код")
    EXTRA_EMPTY_SLOT = f"{label_xpath('Дополнительные фото')}/following-sibling::*[1]"

    def take_required(self):
        self.wait_loaded()
        camera = Camera(self.driver)
        for slot in self.REQUIRED:
            self.scroll_to(f"//*[@content-desc='{slot}']")
            camera.take_photo((AppiumBy.ACCESSIBILITY_ID, slot))

    def add_extra_photo(self, number=1):
        # Тап по пустой ячейке создаёт слот «Доп. фото #N», тап по слоту открывает камеру
        self.scroll_to(self.EXTRA_EMPTY_SLOT).click()
        slot = f"Доп. фото #{number}"
        self.scroll_to(f"//*[@content-desc='{slot}']")
        Camera(self.driver).take_photo((AppiumBy.ACCESSIBILITY_ID, slot))

    def comment(self, text):
        self.fill("Комментарий", text)


class ExtraDataStep(Step):
    TITLE = "Дополнительные данные"
    ADD_CO_BORROWER = (AppiumBy.ACCESSIBILITY_ID, "Добавить созаемщика вручную")
    DOC_ID_CARD = (AppiumBy.ACCESSIBILITY_ID, "ID card")

    def loan_type(self):
        return self.field_value("Тип займа")

    def fill_amounts(self, amount, collateral):
        self.wait_loaded()
        self.fill("Желаемая сумма", amount)
        self.fill("Стоимость залога", collateral)

    def add_co_borrower(self, person):
        self.tap(self.ADD_CO_BORROWER)
        self.tap(self.DOC_ID_CARD)  # «Тип документа» → ID card
        IdCardForm(self.driver).fill_person(person)
        self.document_photos()
        self.wait_visible(title("Созаемщик"))


class ConfirmStep(Step):
    TITLE = "Подтверждение"
    SUCCESS = title("Заявка успешно отправлена на оценку!")
    TO_HOME = (AppiumBy.ACCESSIBILITY_ID, "На главную")

    def submit(self, comment=None):
        if comment:
            self.fill("Комментарий", comment)
        self.next()
        return self.wait_visible(self.SUCCESS, timeout=60)

    def to_home(self):
        self.tap(self.TO_HOME)
