"""Все кейсы сборки KZ на iOS: запуск, вход, язык, создание заявки.

Код и локаторы этой папки — только для iOS. Android-версия тех же кейсов — отдельный,
независимый tests/kz/ в корне проекта; общих модулей между платформами нет.
"""
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import POLL, button

from . import factories
from .application_wizard import BorrowerStep, CarPhotosStep, CarStep, ConfirmStep, ExtraDataStep
from .flows import login, switch_to_russian
from .pages.applications_page import ApplicationsPage
from .pages.start_page import StartPage

APP_RUNNING_FOREGROUND = 4  # driver.query_app_state


def app_opens_first_screen(driver, project):
    """Запуск приложения: открывается стартовый экран с кнопкой «Кіру»."""
    WebDriverWait(driver, 30, poll_frequency=POLL).until(
        lambda d: d.query_app_state(project.bundle_id) == APP_RUNNING_FOREGROUND)
    assert StartPage(driver).wait_loaded().is_enabled()


def manager_login(driver, manager):
    """Авторизация: менеджер входит по логину/паролю и создаёт код входа."""
    home = login(driver, manager)
    assert home.role_label(manager.role).is_displayed()
    assert home.applications_button().is_displayed()


def switch_language_to_russian(driver, manager):
    """Настройки: меню → «Баптаулар» → «Тіл» → выбран русский язык."""
    login(driver, manager)
    language = switch_to_russian(driver)
    assert language.wait_visible(language.TITLE_RU).is_displayed()
    for tab in ("главная", "профиль", "меню"):
        assert driver.find_element(*button(tab)).is_displayed()


def prepare_russian_home(driver, manager):
    """Вход + переключение на русский + возврат на главную — подготовка перед бизнес-кейсами."""
    login(driver, manager)
    # Язык сохраняется между запусками (no_reset) — если уже русский, меню не трогаем
    if not driver.find_elements(*button("главная")):
        switch_to_russian(driver).go_home()


def _start_application(driver, manager, loan_type):
    """Вход на русском → «Заявки» (все вкладки на месте) → новая заявка нужного типа."""
    prepare_russian_home(driver, manager)
    apps = ApplicationsPage(driver).open()
    for tab in ApplicationsPage.TABS:
        assert apps.tab(tab).is_displayed(), f"Нет вкладки «{tab}»"
    apps.start_new(loan_type)


def _add_borrower_car_and_photos(driver, data, add_borrower=None):
    """Общие шаги всех типов заявки: заёмщик (физ. лицо, вручную) → авто → 6 фото.

    add_borrower: как добавить заёмщика — по умолчанию «Удостоверение личности»
    (BorrowerStep.add_manually); для «Паспорт РК»/«Вид на жительство» — своя функция
    (driver, person) -> BorrowerStep, см. PASSPORT / RESIDENCE_PERMIT."""
    if data.company:
        _add_legal_entity(driver, data)
        _add_car_and_photos(driver, data)
        return
    b = data.borrower
    add_borrower = add_borrower or (lambda d, p: BorrowerStep(d).add_manually(p))
    borrower = add_borrower(driver, b)
    assert borrower.summary_value("ИИН") == b.iin
    assert borrower.summary_value("Фамилия") == b.last_name
    assert borrower.summary_value("Имя") == b.first_name
    assert borrower.summary_value("Номер документа") == b.doc_number
    # На iOS выбранная дата в форме не видна автоматизации — проверяем её на сводке
    assert borrower.summary_value("Дата рождения") == b.birth_date.strftime("%d.%m.%Y")
    borrower.next()
    _add_car_and_photos(driver, data)


def _add_legal_entity(driver, data):
    """«Юр. лицо»: субъект (тип «Заемщик», удостоверение личности и его фото) → данные
    компании (название, ОПФ, дата/место регистрации, БИН) → сводка → «Далее»."""
    s, company = data.borrower, data.company
    borrower = BorrowerStep(driver)
    subject_card, company_card = borrower.add_legal_entity(s, company)
    assert subject_card == f"Заемщик · {s.last_name} {s.first_name}"
    assert company_card == f"{company.name} · {company.bin}"
    borrower.open_legal_entity_summary()
    # С 04.11.2026 сводка показывает данные компании, а ФИО субъекта — отдельными полями
    # «Фамилия» / «Имя» / «Отчество»
    for value, what in ((company.name, "названия компании"), (company.bin, "БИН компании"), (s.iin, "ИИН субъекта"),
                        (s.last_name, "фамилии субъекта"), (s.first_name, "имени субъекта"),
                        (s.patronymic, "отчества субъекта")):
        assert borrower.has_text(value), f"На сводке нет {what}: {value}"
    borrower.next()


def _add_car_and_photos(driver, data):
    c = data.car
    car = CarStep(driver).add_manually(c)
    assert car.summary_value("ГРНЗ") == c.grnz
    assert car.summary_value("Номер техпаспорта") == c.tech_passport
    assert car.summary_value("VIN код") == c.vin
    assert car.summary_value("Марка, Модель") == f"{c.brand.upper()} / {c.model}"
    car.next()

    photos = CarPhotosStep(driver)
    photos.take_required()
    photos.comment(data.photos_comment)
    photos.next()


# Документ заёмщика, отличный от удостоверения личности (по умолчанию)
def PASSPORT(d, p):
    return BorrowerStep(d).add_manually_passport(p)


def RESIDENCE_PERMIT(d, p):
    return BorrowerStep(d).add_manually_residence_permit(p)


def _confirm(driver, data, amount=None):
    """«Подтверждение»: сводка по заёмщику/авто/сумме → отправка. Кейс пройден, когда
    приложение подтвердило создание заявки — дальше ничего не проверяем."""
    b, c = data.borrower, data.car
    confirm = ConfirmStep(driver).wait_loaded()
    if data.company:
        # У юр. лица вместо ФИО/ИИН — компания; БИН подписан «БИН продавца» (04.11.2026) или «БИН» (13.11.2026)
        assert confirm.summary_value("Наименование компании") == data.company.name
        assert confirm.summary_value_any("БИН", "БИН продавца") == data.company.bin
    else:
        assert confirm.summary_value("ФИО") == f"{b.first_name} {b.last_name} {b.patronymic}"
        assert confirm.summary_value("ИИН") == b.iin
    assert confirm.summary_value("ГРНЗ") == c.grnz
    if amount:
        assert confirm.summary_value("Желаемая сумма").replace(" ", "") == amount
    success = confirm.submit(comment=data.confirm_comment)
    assert success.is_displayed(), "Нет сообщения «Заявка успешно отправлена на оценку!»"


def create_application_basic(driver, manager):
    """Заявка «Новая»: заёмщик + авто + 6 фото + доп. данные (без доп. фото и созаёмщика)."""
    _create_application_new(driver, manager, with_co_borrower=False)


def create_application_with_co_borrower(driver, manager):
    """Заявка «Новая» с созаёмщиком («Добавить созаемщика вручную», удостоверение личности)."""
    _create_application_new(driver, manager, with_co_borrower=True)


def create_application_new_passport(driver, manager, with_co_borrower=False):
    """Заявка «Новая», документ заёмщика — «Паспорт РК» (номер: буква + 8 цифр)."""
    _create_application_new(driver, manager, with_co_borrower,
                            doc_number=factories.random_passport_number(), add_borrower=PASSPORT)


def create_application_new_residence_permit(driver, manager, with_co_borrower=False):
    """Заявка «Новая», документ заёмщика — «Вид на жительство» (доп. поле «Страна»)."""
    _create_application_new(driver, manager, with_co_borrower, add_borrower=RESIDENCE_PERMIT)


def _create_application_new(driver, manager, with_co_borrower, doc_number=None, add_borrower=None, legal=False):
    """Общий ход «Новая»: различаются документ заёмщика и созаёмщик (всегда с удостоверением)."""
    data = factories.application(with_co_borrower=with_co_borrower, doc_number=doc_number)
    if legal:
        data = factories.as_legal_entity(data)
    _start_application(driver, manager, ApplicationsPage.TYPE_NEW)
    _add_borrower_car_and_photos(driver, data, add_borrower)
    _fill_amounts_and_co_borrower(driver, data, "Новая")
    _confirm(driver, data, data.amount)


def _fill_amounts_and_co_borrower(driver, data, loan_type):
    """«Дополнительные данные» у «Новая» и обоих рефинансирований устроены одинаково: обе суммы —
    свободный ввод, созаёмщик (если есть), сделка в bitrix."""
    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == loan_type
    extra.fill_amounts(data.amount, data.collateral)
    co = data.co_borrower
    if co:
        assert extra.add_co_borrower(co) == f"{co.first_name} {co.last_name}"
    extra.pick_bitrix_deal()
    extra.next()


def create_application_legal_entity(driver, manager):
    """Заявка «Новая» для юр. лица: «Юр. лицо» → субъект + компания → сводка → авто + 6 фото →
    доп. данные → подтверждение → заявка отправлена.

    «Сделка в bitrix» для юр. лица ищется по ИИН субъекта — для случайного ИИН визит
    создаёт бэкенд (обход с 22.10.2026)."""
    _create_application_new(driver, manager, with_co_borrower=False, legal=True)


def create_application_autocredit(driver, manager):
    """Заявка «Автокредит»: заёмщик + авто + 6 фото + продавец (владелец авто, физ. лицо).

    Отличия от «Новая»: вместо «Желаемая сумма» вводится «Первоначальный взнос» — сумму
    приложение считает само (Стоимость залога − Первоначальный взнос), и обязателен
    продавец: «Физ. лицо» → «Добавить продавца вручную» → форма удостоверения и его фото.
    """
    _create_application_autocredit(driver, manager)


def create_application_autocredit_passport(driver, manager):
    """Заявка «Автокредит», документ заёмщика — «Паспорт РК» (номер: буква + 8 цифр)."""
    _create_application_autocredit(driver, manager, doc_number=factories.random_passport_number(),
                                   add_borrower=PASSPORT)


def create_application_autocredit_residence_permit(driver, manager):
    """Заявка «Автокредит», документ заёмщика — «Вид на жительство» (доп. поле «Страна»)."""
    _create_application_autocredit(driver, manager, add_borrower=RESIDENCE_PERMIT)


def create_application_legal_entity_autocredit(driver, manager):
    """Заявка «Автокредит» для юр. лица: субъект + компания, дальше как у физ. лица (продавец,
    первоначальный взнос)."""
    _create_application_autocredit(driver, manager, legal=True)


def _create_application_autocredit(driver, manager, doc_number=None, add_borrower=None, legal=False):
    data = factories.application_autocredit(doc_number=doc_number)
    if legal:
        data = factories.as_legal_entity(data)
    _start_application(driver, manager, ApplicationsPage.TYPE_AUTOCREDIT)
    _add_borrower_car_and_photos(driver, data, add_borrower)

    seller = data.seller
    expected_amount = str(int(data.collateral) - int(data.down_payment))
    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == "Автокредит"
    extra.fill_collateral_and_down_payment(data.collateral, data.down_payment)
    assert extra.amount().replace(" ", "") == expected_amount
    assert extra.add_seller(seller) == f"{seller.first_name} {seller.last_name}"
    extra.pick_bitrix_deal()
    extra.next()

    _confirm(driver, data, expected_amount)


def create_application_transh_passport(driver, manager, fixture):
    """Заявка «Транш», документ заёмщика — «Паспорт РК» (ИИН — из кредитной линии)."""
    create_application_transh(driver, manager, fixture, doc_number=factories.random_passport_number(),
                              add_borrower=PASSPORT)


def create_application_transh_residence_permit(driver, manager, fixture):
    """Заявка «Транш», документ заёмщика — «Вид на жительство» (ИИН — из кредитной линии)."""
    create_application_transh(driver, manager, fixture, add_borrower=RESIDENCE_PERMIT)


def create_application_legal_entity_transh(driver, manager, fixture):
    """Заявка «Транш» для юр. лица: ИИН субъекта и авто — от реальной кредитной линии."""
    create_application_transh(driver, manager, fixture, legal=True)


def create_application_transh(driver, manager, fixture, doc_number=None, add_borrower=None, legal=False):
    """Заявка «Транш» без созаёмщика: ИИН заёмщика и VIN/ГРНЗ/номер техпаспорта авто — от
    реальной кредитной линии (`fixture`, поля в админке), остальное — случайное.

    На «Дополнительные данные» приложение само находит договор (блок «Договор»), сумма
    транша — в пределах «Остаток КЛ», «Сумма всех траншей» = «Остаток ОД» + сумма транша.
    """
    data = factories.application_transh(fixture, doc_number=doc_number)
    if legal:
        data = factories.as_legal_entity(data)
    _start_application(driver, manager, ApplicationsPage.TYPE_TRANSH)
    _add_borrower_car_and_photos(driver, data, add_borrower)

    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == "Транш"
    extra.wait_contract()
    assert fixture.grnz in extra.contract_value("Автомобиль")
    amount = factories.transh_amount(extra.contract_value("Остаток КЛ"))
    debt = factories.money(extra.contract_value("Остаток ОД"))
    extra.fill_transh_amounts(amount, data.collateral)
    assert factories.money(extra.transh_total()) == debt + int(amount)
    extra.next()

    _confirm(driver, data)


def create_application_refinance(driver, manager, fixture, loan_type, with_co_borrower=False, doc_number=None,
                                 add_borrower=None, legal=False):
    """Заявка «Внутреннее/Внешнее рефинансирование» (`loan_type`): ИИН заёмщика + VIN/ГРНЗ/номер
    техпаспорта авто — данные реального клиента (`fixture`, поля в админке), остальное — случайное.
    В приложении продукты заполняются одинаково, различаются только credit_type на бэке.

    В отличие от «Транш» договор не ищется и совпадение не проверяется: «Дополнительные
    данные» устроены как у «Новая» (см. Android-проект, tests/kz/scenarios.py)."""
    data = factories.application_refinance(fixture, with_co_borrower=with_co_borrower, doc_number=doc_number)
    if legal:
        data = factories.as_legal_entity(data)
    _start_application(driver, manager, loan_type)
    _add_borrower_car_and_photos(driver, data, add_borrower)
    _fill_amounts_and_co_borrower(driver, data, loan_type)
    _confirm(driver, data, data.amount)


def create_application_legal_entity_refinance(driver, manager, fixture, loan_type):
    """Заявка-рефинансирование для юр. лица: ИИН субъекта и авто — данные реального клиента."""
    create_application_refinance(driver, manager, fixture, loan_type, legal=True)


def create_application_refinance_with_co_borrower(driver, manager, fixture, loan_type):
    """Заявка-рефинансирование с созаёмщиком (удостоверение личности, добавлен вручную)."""
    create_application_refinance(driver, manager, fixture, loan_type, with_co_borrower=True)


def create_application_refinance_residence_permit(driver, manager, fixture, loan_type):
    """Заявка-рефинансирование, документ заёмщика — «Вид на жительство» (доп. поле «Страна»)."""
    create_application_refinance(driver, manager, fixture, loan_type, add_borrower=RESIDENCE_PERMIT)


def create_application_refinance_passport(driver, manager, fixture, loan_type):
    """Заявка-рефинансирование, документ заёмщика — «Паспорт РК» (номер: буква + 8 цифр)."""
    create_application_refinance(driver, manager, fixture, loan_type, doc_number=factories.random_passport_number(),
                                 add_borrower=PASSPORT)
