"""Шаги мастера создания заявки — по требованиям законодательства Казахстана.

Покрывает полный путь «Новая» заявки: заёмщик (удостоверение личности) → авто
(залог) → фото авто → доп. данные → подтверждение. Не переиспользовать для UZ:
там свой независимый tests/uz/application_wizard.py — поля и справочники разные.
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from . import factories
from .pages.components import Camera, Form, label_xpath
from pages.base_page import POLL

ADD_MANUALLY = (AppiumBy.ACCESSIBILITY_ID, "Добавить вручную")
ADD_DOC_PHOTO = "//*[@content-desc='Добавить фото документа']"
SAVE = (AppiumBy.ACCESSIBILITY_ID, "Сохранить")
NEXT = "//android.widget.Button[@content-desc='Далее']"


def photo_slot(name):
    """Ячейка фото. Если снимок не загрузился, приложение дописывает ошибку в её описание
    («Загрузите фото, Обратная сторона»), поэтому ищем по вхождению, а не по точному имени."""
    return AppiumBy.XPATH, f"//*[@clickable='true' and contains(@content-desc, '{name}')]"


FRONT = photo_slot("Лицевая сторона")
BACK = photo_slot("Обратная сторона")


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

    # Ошибки загрузки снимка: красная надпись на ячейке, она же — в описании ячейки
    PHOTO_ERRORS = ("Загрузите фото", "Заполните это поле")

    def has_photo_error(self, slot):
        desc = slot.get_attribute("content-desc") or ""
        return any(err in desc for err in self.PHOTO_ERRORS)

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
        # Снимок загружается на сервер не сразу: ранний «Сохранить» даёт «Загрузите фото».
        # Жмём, пока экран фото не закроется; сторону, которая так и не загрузилась
        # (красная ошибка на ячейке), снимаем заново.
        for attempt in range(5):
            self.tap(SAVE)
            try:
                WebDriverWait(self.driver, 5, poll_frequency=POLL).until(EC.invisibility_of_element_located(FRONT))
                return
            except TimeoutException:
                pass
            if attempt >= 1:
                for side in (FRONT, BACK):
                    found = self.driver.find_elements(*side)
                    if found and self.has_photo_error(found[0]):
                        camera.take_photo(side)
        raise AssertionError(f"Фото документа не сохранились: {self.upload_errors()}")

    def upload_errors(self):
        return [e.text for e in self.driver.find_elements(*title("Загрузите фото"))]


class IdCardForm(Step):
    """Форма удостоверения личности (одинаковая для заёмщика и созаёмщика).

    Тот же набор полей — с тем же порядком и локаторами — используется и для типа
    документа «Паспорт РК»: разница только в формате «Номер документа» (буква + цифры,
    задаётся самими тестовыми данными), сама форма идентична."""

    def fill_person(self, p):
        self.wait_still((AppiumBy.XPATH, label_xpath("ИИН")))  # шторка формы выезжает анимацией
        self.fill("ИИН", p.iin)
        self.fill("Фамилия", p.last_name)
        self.fill("Имя", p.first_name)
        self.fill("Отчество", p.patronymic)
        self.pick_date("Дата рождения", p.birth_date)
        self.fill("Номер документа", p.doc_number)
        self.fill("Место рождения", p.birth_place)
        self.pick_date("Дата выдачи", p.issue_date)
        self.pick_date("Действителен до", p.expiry_date)
        self.pick_simple("Орган выдачи", p.issuer)
        self.open_document_photos()


class ResidencePermitForm(Step):
    """Форма «Вид на жительство»: те же поля, что у IdCardForm, плюс «Страна» —
    полный справочник с поиском (тот же компонент, что «Марка»/«Модель» авто) —
    между «Действителен до» и «Орган выдачи». Подтверждено вживую."""
    TITLE = "Вид на жительство"

    def fill_person(self, p):
        self.wait_still((AppiumBy.XPATH, label_xpath("ИИН")))  # шторка формы выезжает анимацией
        self.fill("ИИН", p.iin)
        self.fill("Фамилия", p.last_name)
        self.fill("Имя", p.first_name)
        self.fill("Отчество", p.patronymic)
        self.pick_date("Дата рождения", p.birth_date)
        self.fill("Номер документа", p.doc_number)
        self.fill("Место рождения", p.birth_place)
        self.pick_date("Дата выдачи", p.issue_date)
        self.pick_date("Действителен до", p.expiry_date)
        p.country = self.pick("Страна")
        self.pick_simple("Орган выдачи", p.issuer)
        self.open_document_photos()


class BorrowerStep(Step):
    TITLE = "Данные заемщика"
    DOC_TYPE_PICKER = (AppiumBy.XPATH, "//android.widget.TextView[@text='Тип документа']/following-sibling::*[1]")

    def add_manually(self, person):
        self.wait_loaded()
        # Тип документа по умолчанию — удостоверение личности
        self.tap(ADD_MANUALLY)
        IdCardForm(self.driver).fill_person(person)
        self.document_photos()
        self.wait_visible((AppiumBy.XPATH, NEXT))  # открылась сводка по заёмщику
        return self

    def choose_document_type(self, doc_type):
        """Шторка «Тип документа»: подтверждены вживую варианты «Удостоверение личности»
        (по умолчанию), «Вид на жительство», «Паспорт РК»."""
        self.wait_loaded()
        self.tap(self.DOC_TYPE_PICKER)
        self.tap_still((AppiumBy.ACCESSIBILITY_ID, doc_type))
        return self

    def add_manually_residence_permit(self, person):
        self.choose_document_type("Вид на жительство")
        self.tap(ADD_MANUALLY)
        ResidencePermitForm(self.driver).fill_person(person)
        self.document_photos()
        self.wait_visible((AppiumBy.XPATH, NEXT))
        return self

    def add_manually_passport(self, person):
        self.choose_document_type("Паспорт РК")
        self.tap(ADD_MANUALLY)
        IdCardForm(self.driver).fill_person(person)
        self.document_photos()
        self.wait_visible((AppiumBy.XPATH, NEXT))
        return self


class CarStep(Step):
    TITLE = "Автомобиль"

    def add_manually(self, car):
        self.wait_loaded()
        self.tap(ADD_MANUALLY)
        self.wait_still((AppiumBy.XPATH, label_xpath("Марка")))  # шторка формы выезжает анимацией
        # Иногда выбор марки не подтягивает список моделей (не ошибка таймаута —
        # поле «Модель» просто не появляется вообще), помогает выбрать марку заново.
        for attempt in range(3):
            car.brand = self.pick("Марка")
            try:
                self.wait_field("Модель", timeout=20)
                break
            except TimeoutException:
                if attempt == 2:
                    raise
        car.model = self.pick("Модель")
        self.fill("Год выпуска авто", car.year)
        self.fill("ГРНЗ", car.grnz)
        self.fill("Номер техпаспорта", car.tech_passport)
        self.pick_date("Дата выдачи", car.issue_date)
        self.fill("VIN код", car.vin)
        self.fill("Цвет", car.color)
        self.open_document_photos()
        self.document_photos()
        self.wait_visible((AppiumBy.XPATH, NEXT))  # открылась сводка по автомобилю
        return self


class CarPhotosStep(Step):
    TITLE = "Фото авто"
    REQUIRED = ("вид спереди", "вид сзади", "вид слева", "вид справа", "Клиент на фоне авто", "VIN код")

    def take_required(self):
        self.wait_loaded()
        camera = Camera(self.driver)
        for slot in self.REQUIRED:
            self.scroll_to(photo_slot(slot)[1])
            camera.take_photo(photo_slot(slot), image=factories.CAR_PHOTOS.get(slot))

    def comment(self, text):
        self.fill("Комментарий", text)

    def next(self, attempts=3):
        """«Далее» с проверкой фото. Сервис иногда не успевает загрузить снимок — тогда
        «Далее» не уводит со страницы, а на ячейке появляется красная ошибка. Такие
        ячейки снимаем заново и жмём «Далее» ещё раз."""
        camera = Camera(self.driver)
        failed = []
        for _ in range(attempts):
            super().next()
            try:
                WebDriverWait(self.driver, 20, poll_frequency=POLL).until(
                    EC.invisibility_of_element_located(title(self.TITLE)))
                return
            except TimeoutException:
                pass
            failed = self.failed_slots()
            for slot in failed:
                self.scroll_to(photo_slot(slot)[1])
                camera.take_photo(photo_slot(slot), image=factories.CAR_PHOTOS.get(slot))
        raise AssertionError(f"Не удалось уйти с «Фото авто»: не загрузились {failed or 'фото'}; "
                             f"ошибки формы: {self.validation_errors()}")

    def failed_slots(self):
        """Ячейки с красной ошибкой загрузки — сверху вниз по всей странице."""
        self.driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR,
                                  "new UiScrollable(new UiSelector().scrollable(true)).scrollToBeginning(5)")
        return [slot for slot in self.REQUIRED
                if self.has_photo_error(self.scroll_to(photo_slot(slot)[1]))]


class ExtraDataStep(Step):
    TITLE = "Дополнительные данные"
    ADD_CO_BORROWER = "//*[@content-desc='Добавить созаемщика вручную']"
    ADD_SELLER = "//*[@content-desc='Добавить продавца вручную']"

    def loan_type(self):
        return self.field_value("Тип займа")

    def fill_amounts(self, amount, collateral):
        """Для «Новая»: обе суммы — свободный ввод."""
        self.wait_loaded()
        self.fill("Желаемая сумма", amount)
        self.fill("Стоимость залога", collateral)

    def fill_collateral_and_down_payment(self, collateral, down_payment):
        """Для «Автокредит»: «Желаемая сумма» тут недоступна для ввода — она считается
        сама как «Стоимость залога» минус «Первоначальный взнос» (проверено вживую:
        enabled=false, значение появляется само после заполнения этих двух полей)."""
        self.wait_loaded()
        self.fill("Стоимость залога", collateral)
        self.fill("Первоначальный взнос", down_payment)

    def fill_transh_amounts(self, amount, collateral):
        """Для «Транш»: «Сумма всех траншей» недоступна для ввода (enabled=false,
        подтягивается из найденного договора). «Сделка в bitrix» на этом экране нет вовсе —
        не вызывать pick_bitrix_deal() для «Транш»."""
        self.wait_loaded()
        self.fill("Желаемая сумма транша", amount)
        self.fill("Стоимость залога", collateral)

    CONTRACT_NUMBER = (AppiumBy.XPATH, f"{label_xpath('№ договора')}/following-sibling::"
                                       "android.widget.TextView[1][string-length(@text) > 0]")

    def wait_contract(self, attempts=3):
        """«Транш»: кредитная линия найдена — в блоке «Договор» появился номер договора.

        Поиск линии на сервере нестабилен: на тех же данных то находит договор, то пишет
        «нет кредитной линии» (проверено 20.10.2026 подряд идущими прогонами). Тогда
        возвращаемся на «Фото авто» и снова жмём «Далее» — приложение ищет заново."""
        for attempt in range(attempts):
            WebDriverWait(self.driver, 30, poll_frequency=POLL).until(
                lambda d: d.find_elements(*self.CONTRACT_NUMBER) or d.find_elements(*self.NO_CREDIT_LINE))
            number = self.driver.find_elements(*self.CONTRACT_NUMBER)
            if number:
                return number[0].text
            if attempt < attempts - 1:
                self.scroll_to("//*[@content-desc='Назад']").click()
                CarPhotosStep(self.driver).next()
                self.wait_loaded()
        raise AssertionError(f"Кредитная линия не найдена ({attempts} попытки): сервер отвечает «нет кредитной "
                             "линии» — проверьте ИИН/VIN/ГРНЗ/номер техпаспорта в админке")

    def contract_value(self, label):
        """Строка блока «Договор» («Остаток КЛ», «Остаток ОД», «Автомобиль»…)."""
        return self.summary_value(label)

    def transh_total(self):
        """«Сумма всех траншей» — недоступна для ввода, = Остаток ОД + Желаемая сумма транша."""
        return self.field_value("Сумма всех траншей")

    NO_CREDIT_LINE = (
        AppiumBy.XPATH,
        "//android.widget.TextView[contains(@text, 'нет кредитной линии')]",
    )

    def contract_matched(self, timeout=15):
        """После заполнения сумм экран асинхронно ищет кредитную линию по ИИН/VIN/
        ГРНЗ/номеру техпаспорта — «Нет данных» в «Договоре» это просто исходное
        состояние ДО поиска, не результат (проверять его сразу после fill — гонка,
        поймал вживую: contract_matched() успевал вернуть True до того, как поиск
        вообще случался). Признак реального результата — текст «...нет кредитной
        линии...» под «Стоимость залога» (тогда «Далее» остаётся неактивной) или то,
        что «Далее» стала активной (совпадение нашлось — сам экран найденного
        договора не видел, нет реальных тестовых данных)."""
        try:
            WebDriverWait(self.driver, timeout, poll_frequency=POLL).until(
                lambda d: d.find_elements(*self.NO_CREDIT_LINE)
                or d.find_element(AppiumBy.XPATH, NEXT).is_enabled()
            )
        except TimeoutException:
            pass
        return not self.driver.find_elements(*self.NO_CREDIT_LINE)

    def add_co_borrower(self, person):
        """«Добавить созаемщика вручную» — та же форма удостоверения личности, что у заёмщика."""
        self.scroll_to(self.ADD_CO_BORROWER).click()
        id_card = IdCardForm(self.driver)
        id_card.fill_person(person)
        id_card.document_photos()
        return self.field_value("Созаемщик")

    def add_seller(self, person):
        """«Добавить продавца вручную» — обязательное поле для «Автокредит», та же форма ID card."""
        self.scroll_to(self.ADD_SELLER).click()
        id_card = IdCardForm(self.driver)
        id_card.fill_person(person)
        id_card.document_photos()
        return self.field_value("Продавец")

    BITRIX = "Сделка в bitrix"
    # Кнопка ⟳ (перезапрос сделок из Bitrix) лежит поверх поля, но в дереве — не внутри
    # него, а следующим соседом подписи: подпись, поле, ⟳
    BITRIX_REFRESH = (AppiumBy.XPATH, f"{label_xpath(BITRIX)}/following-sibling::*[2][@clickable='true']")
    MODAL_CANCEL = (AppiumBy.XPATH, "//*[@resource-id='undefined.modal.topBar.cancel']")

    def pick_bitrix_deal(self):
        """«Сделка в bitrix» — обязательное поле; выбираем любой доступный вариант справочника.

        Список сделок иногда приходит пустым (Bitrix не успел ответить) — тогда
        закрываем справочник, жмём ⟳ в поле и открываем заново.
        """
        for attempt in range(3):
            try:
                return self.pick(self.BITRIX, items_timeout=10)
            except TimeoutException:
                if attempt == 2:
                    raise
                for cancel in self.driver.find_elements(*self.MODAL_CANCEL):
                    cancel.click()
                self.scroll_to(self.BITRIX_REFRESH[1]).click()


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
