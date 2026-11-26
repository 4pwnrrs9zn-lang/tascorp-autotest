"""Шаги мастера создания заявки (iOS) — по требованиям законодательства Казахстана.

Полный путь «Новая» заявки: заёмщик (удостоверение личности, паспорт РК или вид на
жительство) → авто (залог) → фото авто →
доп. данные → подтверждение. Порядок полей и правила заполнения — как в Android-проекте
(tests/kz/application_wizard.py); локаторы — kz/locators.py, у каждого поля свой.
Фото снимаются тестовой камерой Simulator (tools/test_camera).
"""
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import POLL

from . import factories
from .locators import (Borrower, Car, CarPhotos, Confirm, Dictionary, DocPhotos, ExtraData, IdCard, LegalEntity, Wizard,
                       static_text, summary_value)
from .pages.components import Camera, Form


class Step(Form):
    TITLE = None

    def wait_loaded(self):
        """Ждём заголовок шага; тосты, показанные за это время, запоминаем — если шаг не открылся,
        в ошибке будет текст приложения (например, «Ошибка создание клиента» при 500 бэкенда)."""
        toasts = []

        def loaded(driver):
            try:
                for el in driver.find_elements(*Wizard.TOAST):
                    if (text := el.get_attribute("label")) and text not in toasts:
                        toasts.append(text)
            except WebDriverException:  # тост исчез между поиском и чтением
                pass
            return driver.find_elements(*self.TITLE) and EC.visibility_of_element_located(self.TITLE)(driver)

        try:
            WebDriverWait(self.driver, self.timeout, poll_frequency=POLL).until(loaded)
        except TimeoutException:
            if toasts:
                raise AssertionError(f"Шаг не открылся, приложение показало: {' / '.join(toasts)}") from None
            raise
        return self

    def summary_value(self, label):
        """Значение строки на экране-сводке («ИИН», «ГРНЗ»…) — из дерева, без прокрутки:
        для чтения значения элемент не обязан быть на экране."""
        return self.driver.find_element(*summary_value(label)).get_attribute("value")

    def summary_value_any(self, *labels):
        """Значение строки сводки по первой найденной подписи (подпись менялась между сборками)."""
        for label in labels:
            found = self.driver.find_elements(*summary_value(label))
            if found:
                return found[0].get_attribute("value")
        raise AssertionError(f"На сводке нет строки {' / '.join(labels)}")

    def wait_summary(self):
        """Экран-сводка открылся: «Далее» появилась в дереве. Не wait_visible — на длинной
        сводке «Далее» ниже края экрана, а такой элемент XCUITest считает невидимым."""
        WebDriverWait(self.driver, self.timeout, poll_frequency=POLL).until(
            EC.presence_of_element_located(Wizard.NEXT))

    def next(self):
        self.press(Wizard.NEXT)

    def open_document_photos(self):
        """«Добавить фото документа» с повтором: первый тап может попасть в анимацию
        закрытия шторки даты/справочника — как и на Android."""
        self.press(Wizard.ADD_DOC_PHOTO)
        for _ in range(3):
            try:
                self.wait_visible(DocPhotos.FRONT, timeout=4)
                return
            except TimeoutException:
                self.on_screen(Wizard.ADD_DOC_PHOTO).click()
        raise AssertionError("Не открылся экран фото документа — форма не прошла проверку приложения")

    def document_photos(self):
        """«Лицевая сторона» + «Обратная сторона» → «Сохранить». Снимок обрабатывается не сразу:
        ранний «Сохранить» (фото ещё грузится в tascorp-media/upload — бывает до ~20 с)
        даёт «Проверьте корректность заполненных данных» — жмём, пока экран фото не закроется."""
        camera = Camera(self.driver)
        camera.take_photo(DocPhotos.FRONT)
        camera.take_photo(DocPhotos.BACK)
        for _ in range(10):
            self.tap(DocPhotos.SAVE)
            try:
                WebDriverWait(self.driver, 5, poll_frequency=POLL).until(
                    lambda d: not d.find_elements(*DocPhotos.SCREEN))
                return
            except TimeoutException:
                continue
        if errors := self.driver.find_elements(*DocPhotos.UPLOAD_ERROR):
            raise AssertionError(f"Сервер не принял фото документа (tascorp-media/upload): {errors[-1].get_attribute('name')}")
        raise AssertionError("Фото документа не сохранились")


class IdCardForm(Step):
    """Форма «Удостоверение личности» (заёмщик и созаёмщик). Порядок полей — как на экране.

    Та же форма — у типа документа «Паспорт РК»: разница только в формате «Номер документа»
    (буква + 8 цифр, задаётся тестовыми данными)."""

    def wait_opened(self):
        self.wait_still(IdCard.TITLE)  # шторка формы выезжает анимацией

    def fill_iin(self, value):
        self.type_text(IdCard.IIN, value)

    def fill_last_name(self, value):
        self.type_text(IdCard.LAST_NAME, value)

    def fill_first_name(self, value):
        self.type_text(IdCard.FIRST_NAME, value)

    def fill_patronymic(self, value):
        self.type_text(IdCard.PATRONYMIC, value)

    def set_birth_date(self, date):
        self.set_date(IdCard.BIRTH_DATE, date)

    def fill_doc_number(self, value):
        self.type_text(IdCard.DOC_NUMBER, value)

    def fill_birth_place(self, value):
        self.type_text(IdCard.BIRTH_PLACE, value)

    def set_issue_date(self, date):
        self.set_date(IdCard.ISSUE_DATE, date)

    def set_expiry_date(self, date):
        self.set_date(IdCard.EXPIRY_DATE, date)

    def pick_country(self):
        """«Страна» (только «Вид на жительство») — случайная из справочника."""
        return self.choose_random(IdCard.COUNTRY)

    def pick_issuer(self, issuer):
        """«Орган выдачи» — короткий список (МВД РК / МЮ РК), значение из тестовых данных."""
        self.choose_option(IdCard.ISSUER, IdCard.issuer_option(issuer))

    def fill_person(self, p):
        self.wait_opened()
        self.fill_iin(p.iin)
        self.fill_last_name(p.last_name)
        self.fill_first_name(p.first_name)
        self.fill_patronymic(p.patronymic)
        self.set_birth_date(p.birth_date)
        self.fill_doc_number(p.doc_number)
        self.fill_birth_place(p.birth_place)
        self.set_issue_date(p.issue_date)
        self.set_expiry_date(p.expiry_date)
        self.pick_issuer(p.issuer)


class ResidencePermitForm(IdCardForm):
    """Форма «Вид на жительство»: поля IdCardForm плюс «Страна» — между «Действителен до»
    и «Орган выдачи» (как на Android, на iOS проверено вживую 22.10.2026)."""

    def fill_person(self, p):
        self.wait_opened()
        self.fill_iin(p.iin)
        self.fill_last_name(p.last_name)
        self.fill_first_name(p.first_name)
        self.fill_patronymic(p.patronymic)
        self.set_birth_date(p.birth_date)
        self.fill_doc_number(p.doc_number)
        self.fill_birth_place(p.birth_place)
        self.set_issue_date(p.issue_date)
        self.set_expiry_date(p.expiry_date)
        p.country = self.pick_country()
        self.pick_issuer(p.issuer)


class SubjectForm(IdCardForm):
    """Шторка «Добавить субъекта» (юр. лицо): «Тип субъекта» + поля удостоверения личности →
    фото удостоверения → «Документы субъектов» (необязательны) → «Сохранить»."""

    def pick_subject_type(self, subject_type):
        self.choose_option(LegalEntity.SUBJECT_TYPE, LegalEntity.subject_type(subject_type))

    def document_photos(self):
        """Здесь после фото не «Сохранить», а «Далее» шторки — снимок обрабатывается не
        сразу, поэтому жмём, пока не откроется «Документы субъектов»."""
        camera = Camera(self.driver)
        camera.take_photo(DocPhotos.FRONT)
        camera.take_photo(DocPhotos.BACK)
        for _ in range(5):
            self.tap(LegalEntity.SHEET_NEXT)
            try:
                self.wait_visible(LegalEntity.SUBJECT_DOCS, timeout=5)
                return
            except TimeoutException:
                continue
        raise AssertionError("Фото удостоверения субъекта не сохранились")

    def add(self, person, subject_type):
        self.wait_opened()
        self.pick_subject_type(subject_type)
        self.fill_person(person)
        self.tap(LegalEntity.SHEET_NEXT)
        self.document_photos()
        self.tap(LegalEntity.SHEET_SAVE)  # «Документы субъектов» — без доп. документов


class CompanyForm(Step):
    """Шторка «Добавить данные компании». «Документы компании» необязательны."""

    def wait_opened(self):
        self.wait_still(LegalEntity.COMPANY_NAME_LABEL)

    def fill_name(self, value):
        self.type_text(LegalEntity.COMPANY_NAME, value)

    def pick_legal_form(self, name):
        """«Организационно-правовая форма» — короткий список (ГП, ПТ, КТ, ТОО, ТДО, АО)."""
        self.choose_option(LegalEntity.LEGAL_FORM, LegalEntity.legal_form(name))

    def set_registration_date(self, date):
        self.set_date(LegalEntity.REGISTRATION_DATE, date)

    def fill_registration_place(self, value):
        self.type_text(LegalEntity.REGISTRATION_PLACE, value)

    def fill_bin(self, value):
        self.type_text(LegalEntity.BIN, value)

    def add(self, company):
        self.wait_opened()
        self.fill_name(company.name)
        self.pick_legal_form(company.legal_form)
        self.set_registration_date(company.registration_date)
        self.fill_registration_place(company.registration_place)
        self.fill_bin(company.bin)
        self.tap(LegalEntity.SHEET_SAVE)


class BorrowerStep(Step):
    TITLE = Borrower.TITLE

    def add_manually(self, person):
        """Тип документа по умолчанию — удостоверение личности."""
        return self._add_manually(person, IdCardForm)

    def add_manually_passport(self, person):
        return self._add_manually(person, IdCardForm, doc_type=Borrower.PASSPORT)

    def add_manually_residence_permit(self, person):
        return self._add_manually(person, ResidencePermitForm, doc_type=Borrower.RESIDENCE_PERMIT)

    def choose_document_type(self, doc_type):
        """«Тип документа» — короткий список. По умолчанию уже выбрано «Удостоверение
        личности», поэтому выбор проверяем по названию типа в самом поле."""
        for _ in range(3):
            self.press(Borrower.DOC_TYPE)
            self.tap_still(Borrower.doc_type(doc_type), timeout=15)
            try:
                WebDriverWait(self.driver, 3, poll_frequency=POLL).until(
                    lambda d: d.find_element(*Borrower.DOC_TYPE).get_attribute("name").endswith(doc_type))
                return
            except TimeoutException:
                continue
        raise AssertionError(f"Тип документа «{doc_type}» не выбрался")

    def add_legal_entity(self, subject, company, subject_type=LegalEntity.SUBJECT_BORROWER):
        """«Юр. лицо»: сначала субъект, затем данные компании. Возвращает значения карточек
        субъекта («<тип> · Фамилия Имя») и компании («<название> · <БИН>»)."""
        self.wait_loaded()
        self.tap(Borrower.LEGAL_ENTITY)
        self.press(LegalEntity.ADD_SUBJECT)
        SubjectForm(self.driver).add(subject, subject_type)
        subject_card = self.wait_visible(LegalEntity.SUBJECT_CARD).get_attribute("value")
        self.press(LegalEntity.ADD_COMPANY)
        CompanyForm(self.driver).add(company)
        company_card = self.wait_visible(LegalEntity.COMPANY_CARD).get_attribute("value")
        return subject_card, company_card

    def open_legal_entity_summary(self):
        """«Далее» → сводка по юр. лицу (данные компании, ниже — «Субъекты»)."""
        self.next()
        WebDriverWait(self.driver, self.timeout, poll_frequency=POLL).until(
            EC.presence_of_element_located(LegalEntity.SUMMARY))
        return self

    def has_text(self, text):
        return bool(self.driver.find_elements(*static_text(text)))

    def _add_manually(self, person, form_class, doc_type=None):
        self.wait_loaded()
        self.tap(Borrower.INDIVIDUAL)
        if doc_type:
            self.choose_document_type(doc_type)
        self.tap(Wizard.ADD_MANUALLY)
        form = form_class(self.driver)
        form.fill_person(person)
        form.open_document_photos()
        form.document_photos()
        self.wait_summary()
        return self


class CarStep(Step):
    TITLE = Car.TITLE

    def pick_brand(self):
        """«Марка» — случайная из справочника."""
        return self.choose_random(Car.BRAND)

    def pick_model(self):
        """«Модель» — случайная из моделей выбранной марки."""
        return self.choose_random(Car.MODEL)

    def fill_year(self, value):
        self.type_text(Car.YEAR, value)

    def fill_grnz(self, value):
        self.type_text(Car.GRNZ, value)

    def fill_tech_passport(self, value):
        self.type_text(Car.TECH_PASSPORT, value)

    def set_issue_date(self, date):
        self.set_date(Car.ISSUE_DATE, date)

    def fill_vin(self, value):
        self.type_text(Car.VIN, value)

    def fill_color(self, value):
        self.type_text(Car.COLOR, value)

    def add_manually(self, car):
        self.wait_loaded()
        self.tap(Wizard.ADD_MANUALLY)
        self.wait_still(Car.FORM_TITLE)  # шторка формы выезжает анимацией
        # Как на Android: выбор марки иногда не подтягивает «Модель» — выбираем марку заново
        for attempt in range(3):
            car.brand = self.pick_brand()
            try:
                self.wait_visible(Car.MODEL, timeout=20)
                break
            except TimeoutException:
                if attempt == 2:
                    raise
        car.model = self.pick_model()
        self.fill_year(car.year)
        self.fill_grnz(car.grnz)
        self.fill_tech_passport(car.tech_passport)
        self.set_issue_date(car.issue_date)
        self.fill_vin(car.vin)
        self.fill_color(car.color)
        self.open_document_photos()
        self.document_photos()
        self.wait_summary()
        return self


class CarPhotosStep(Step):
    TITLE = CarPhotos.TITLE

    def take_required(self):
        self.wait_loaded()
        camera = Camera(self.driver)
        for slot in CarPhotos.REQUIRED:
            # нижние ячейки XCUITest прокрутит к себе сам; «Клиент на фоне авто» и «VIN код» —
            # настоящими фото (factories.CAR_PHOTOS)
            if slot == "VIN код":
                # VIN снимаем только после загрузки всех предыдущих фото: при параллельной
                # загрузке бэкенд отвечал 400 «Put …: ContentLength=… with Body length 0» (10.11.2026)
                self.wait_uploads()
            camera.take_photo(CarPhotos.slot(slot), image=factories.CAR_PHOTOS.get(slot))

    def wait_uploads(self, timeout=90):
        """Ждём, пока ни одна ячейка не в состоянии «In progress». Индикатор появляется
        не сразу после снимка — сначала даём ему до 2 с появиться."""
        try:
            WebDriverWait(self.driver, 2, poll_frequency=POLL).until(
                lambda d: d.find_elements(*CarPhotos.UPLOADING))
        except TimeoutException:
            pass
        WebDriverWait(self.driver, timeout, poll_frequency=POLL).until(
            lambda d: not d.find_elements(*CarPhotos.UPLOADING),
            "Фото авто не загрузились за отведённое время")

    def comment(self, text):
        self.type_multiline(CarPhotos.COMMENT, CarPhotos.COMMENT_LABEL, text)

    def next(self):
        """«Далее» с повтором: пока последние фото грузятся (tascorp-media/upload, бывает
        до ~20 с — 09.11.2026), приложение остаётся на «Фото авто»."""
        for _ in range(10):
            self.press(Wizard.NEXT)
            try:
                self.wait_visible(ExtraData.TITLE, timeout=5)
                return
            except TimeoutException:
                continue
        raise AssertionError("Не открылись «Дополнительные данные» после «Фото авто» — смотрите ошибку на ячейках фото "
                             "(с 10.11.2026 бэкенд распознаёт «VIN код» и отклоняет фото с ошибкой 400)")


class ExtraDataStep(Step):
    TITLE = ExtraData.TITLE

    def loan_type(self):
        return self.value_of(ExtraData.LOAN_TYPE)

    def fill_amount(self, value):
        self.type_text(ExtraData.AMOUNT, value)

    def fill_collateral(self, value):
        self.type_text(ExtraData.COLLATERAL, value)

    def fill_amounts(self, amount, collateral):
        """Для «Новая»: обе суммы — свободный ввод."""
        self.wait_loaded()
        self.fill_amount(amount)
        self.fill_collateral(collateral)

    def amount(self):
        return self.value_of(ExtraData.AMOUNT)

    def fill_collateral_and_down_payment(self, collateral, down_payment):
        """Для «Автокредит»: «Желаемая сумма» недоступна для ввода — приложение считает её
        само как «Стоимость залога» − «Первоначальный взнос»."""
        self.wait_loaded()
        self.fill_collateral(collateral)
        self.type_text(ExtraData.DOWN_PAYMENT, down_payment)

    def add_seller(self, person):
        """Продавец (владелец авто) — обязателен для «Автокредит»: «Физ. лицо» →
        «Добавить продавца вручную» → та же форма удостоверения, что у заёмщика, и его фото."""
        self.on_screen(ExtraData.SELLER_INDIVIDUAL).click()
        self.press(ExtraData.ADD_SELLER_MANUALLY)
        form = IdCardForm(self.driver)
        form.fill_person(person)
        form.open_document_photos()
        form.document_photos()
        self.wait_visible(ExtraData.SELLER)
        return self.value_of(ExtraData.SELLER)

    def add_co_borrower(self, person):
        """«Добавить созаемщика вручную» → та же форма удостоверения, что у заёмщика, и его фото."""
        self.press(ExtraData.ADD_CO_BORROWER_MANUALLY)
        form = IdCardForm(self.driver)
        form.fill_person(person)
        form.open_document_photos()
        form.document_photos()
        self.wait_visible(ExtraData.CO_BORROWER)
        return self.value_of(ExtraData.CO_BORROWER)

    def wait_contract(self):
        """«Транш»: кредитная линия найдена — в блоке «Договор» появился номер договора."""
        try:
            return self.wait_visible(ExtraData.CONTRACT_NUMBER, timeout=30).get_attribute("value")
        except TimeoutException:
            raise AssertionError("Кредитная линия не найдена: нет блока «Договор» — проверьте "
                                 "ИИН/VIN/ГРНЗ/номер техпаспорта в админке") from None

    def contract_value(self, label):
        """Строка блока «Договор» («Остаток КЛ», «Остаток ОД», «Автомобиль»…)."""
        return self.summary_value(label)

    def fill_transh_amounts(self, amount, collateral):
        self.type_text(ExtraData.TRANSH_AMOUNT, amount)
        self.fill_collateral(collateral)

    def transh_total(self):
        return self.value_of(ExtraData.TRANSH_TOTAL)

    def pick_bitrix_deal(self):
        """«Сделка в bitrix» — обязательное поле, случайный вариант. Список иногда приходит
        пустым (Bitrix не успел ответить) — закрываем справочник и открываем заново.
        У юр. лица сделки ищутся по ИИН субъекта: нет визита — список пуст всегда."""
        for attempt in range(3):
            try:
                # После закрытия пустого списка поле перезагружается: вместо него — индикатор
                WebDriverWait(self.driver, self.timeout, poll_frequency=POLL).until(
                    EC.presence_of_element_located(ExtraData.BITRIX_DEAL))
                return self.choose_random(ExtraData.BITRIX_DEAL, items_timeout=10)
            except (TimeoutException, NoSuchElementException):
                for cancel in self.driver.find_elements(*Dictionary.CANCEL):
                    cancel.click()
                if attempt == 2:
                    if self.driver.find_elements(*ExtraData.NO_VISIT):
                        raise AssertionError("«Сделка в bitrix» пуста: «По данному ИИН нет визита» — "
                                             "бэкенд не создал визит для ИИН субъекта") from None
                    raise


class ConfirmStep(Step):
    TITLE = Confirm.TITLE

    def submit(self, comment=None):
        if comment:
            self.type_multiline(Confirm.COMMENT, Confirm.COMMENT_LABEL, comment)
        self.next()
        return self.wait_visible(Confirm.SUCCESS, timeout=60)
