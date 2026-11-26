"""Все кейсы сборки KZ: вход, язык, создание заявки.

Код и локаторы этого файла — только для KZ. Аналог для UZ — отдельный,
независимый tests/uz/scenarios.py; общих модулей между ними нет.
"""
from decimal import Decimal

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait

from . import factories
from .application_wizard import BorrowerStep, CarPhotosStep, CarStep, ConfirmStep, ExtraDataStep
from .flows import login, switch_to_russian
from .pages.applications_page import ApplicationsPage
from .pages.start_page import StartPage
from pages.base_page import POLL


def app_opens_first_screen(driver, project):
    """Запуск приложения: открывается стартовый экран с кнопкой «Кіру»."""
    WebDriverWait(driver, 30, poll_frequency=POLL).until(lambda d: d.current_package == project.package)
    login_button = StartPage(driver).wait_loaded()
    assert login_button.is_enabled()


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
        assert driver.find_element(AppiumBy.ACCESSIBILITY_ID, tab).is_displayed()


def prepare_russian_home(driver, manager):
    """Вход + переключение на русский + возврат на главную — подготовка перед бизнес-кейсами."""
    login(driver, manager)
    # Язык сохраняется между запусками (no_reset) — если уже русский, меню не трогаем
    if not driver.find_elements(AppiumBy.ACCESSIBILITY_ID, "главная"):
        switch_to_russian(driver).go_home()


def _add_borrower_and_car(driver, data, add_borrower=None):
    """Заёмщик (удв. личности) + авто (залог) + 6 фото — общая часть для всех типов займа.

    Предусловие: менеджер авторизован, интерфейс на русском, открыта главная («Заявки» →
    «Новая заявка» → нужный тип уже выбраны вызывающим кодом).

    add_borrower: как добавить данные заёмщика — по умолчанию «Удостоверение личности»
    (BorrowerStep.add_manually); для «Вид на жительство»/«Паспорт РК» передаётся своя
    функция (driver, person) -> BorrowerStep — см. create_application_refinance_residence_permit.

    Модалка «Оценка работы» (всплывает непредсказуемо — только если у менеджера есть
    предыдущая заявка, уже оценённая оценщиком, но ещё не подтверждённая им самим)
    обрабатывается внутри ApplicationsPage.open()/start_new() — см.
    pages.applications_page.handle_evaluator_rating(); сюда её тащить не нужно.
    """
    b = data.borrower
    add_borrower = add_borrower or (lambda d, p: BorrowerStep(d).add_manually(p))
    borrower = add_borrower(driver, b)
    assert borrower.summary_value("ИИН") == b.iin
    assert borrower.summary_value("Фамилия") == b.last_name
    assert borrower.summary_value("Имя") == b.first_name
    assert borrower.summary_value("Номер документа") == b.doc_number
    borrower.next()

    c = data.car
    car = CarStep(driver).add_manually(c)
    assert car.summary_value("ГРНЗ") == c.grnz
    assert car.summary_value("Номер техпаспорта") == c.tech_passport
    assert car.summary_value("VIN код") == c.vin
    # Марку приложение на экране сводки рендерит заглавными буквами (модель — как есть)
    assert car.summary_value("Марка, Модель") == f"{c.brand.upper()} / {c.model}"
    car.next()

    photos = CarPhotosStep(driver)
    photos.take_required()
    photos.comment(data.photos_comment)
    photos.next()


def create_application_basic(driver, manager):
    """Заявка «Новая»: заёмщик + авто + 6 фото + доп. данные (без доп. фото и созаёмщика)."""
    _create_application_new(driver, manager)


def create_application_with_co_borrower(driver, manager):
    """Заявка «Новая» с созаёмщиком (удв. личности, «Добавить созаемщика вручную»)."""
    _create_application_new(driver, manager, with_co_borrower=True)


def create_application_new_passport(driver, manager, with_co_borrower=False):
    """Заявка «Новая», документ заёмщика — «Паспорт РК» (номер: буква + 8 цифр)."""
    _create_application_new(
        driver, manager, with_co_borrower, doc_number=factories.random_passport_number(),
        add_borrower=lambda d, p: BorrowerStep(d).add_manually_passport(p))


def create_application_new_residence_permit(driver, manager, with_co_borrower=False):
    """Заявка «Новая», документ заёмщика — «Вид на жительство» (доп. поле «Страна»)."""
    _create_application_new(
        driver, manager, with_co_borrower,
        add_borrower=lambda d, p: BorrowerStep(d).add_manually_residence_permit(p))


def _create_application_new(driver, manager, with_co_borrower=False, doc_number=None, add_borrower=None):
    """Общий ход «Новая»: различаются документ заёмщика (add_borrower, по умолчанию —
    удостоверение личности) и созаёмщик (всегда с удостоверением личности)."""
    prepare_russian_home(driver, manager)
    data = factories.application(with_co_borrower=with_co_borrower, doc_number=doc_number)
    apps = ApplicationsPage(driver).open()
    for tab in ApplicationsPage.TABS:
        assert apps.tab(tab).is_displayed(), f"Нет вкладки «{tab}»"
    apps.start_new(ApplicationsPage.TYPE_NEW)
    _add_borrower_and_car(driver, data, add_borrower=add_borrower)

    b, c, co = data.borrower, data.car, data.co_borrower
    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == "Новая"
    extra.fill_amounts(data.amount, data.collateral)
    if co:
        assert extra.add_co_borrower(co) == f"{co.first_name} {co.last_name}"
    extra.pick_bitrix_deal()
    extra.next()

    confirm = ConfirmStep(driver).wait_loaded()
    assert confirm.summary_value("ФИО") == f"{b.first_name} {b.last_name} {b.patronymic}"
    assert confirm.summary_value("ИИН") == b.iin
    assert confirm.summary_value("ГРНЗ") == c.grnz
    assert confirm.summary_value("Желаемая сумма").replace(" ", "") == data.amount
    confirm.submit(comment=data.confirm_comment)
    confirm.to_home()


def create_application_autocredit(driver, manager):
    """Заявка «Автокредит»: заёмщик + авто + 6 фото + продавец (обязателен, без созаёмщика).

    Отличия от «Новая», подтверждённые вживую: доп. поле «Первоначальный взнос»,
    «Желаемая сумма» — не ввод, а вычисляется само (Стоимость залога − Первоначальный
    взнос, поле недоступно для редактирования), «Добавить продавца вручную» обязателен
    (та же форма ID card, что у заёмщика/созаёмщика), нет полей «Созаемщик»/«Соучредители».
    """
    _create_application_autocredit(driver, manager)


def create_application_autocredit_passport(driver, manager):
    """Заявка «Автокредит», тип документа заёмщика — «Паспорт РК» (номер: буква + 8 цифр)."""
    _create_application_autocredit(
        driver, manager, doc_number=factories.random_passport_number(),
        add_borrower=lambda d, p: BorrowerStep(d).add_manually_passport(p))


def create_application_autocredit_residence_permit(driver, manager):
    """Заявка «Автокредит», тип документа заёмщика — «Вид на жительство» (доп. поле «Страна»)."""
    _create_application_autocredit(
        driver, manager, add_borrower=lambda d, p: BorrowerStep(d).add_manually_residence_permit(p))


def _create_application_autocredit(driver, manager, doc_number=None, add_borrower=None):
    """Общий ход «Автокредит»; различается только документ заёмщика (add_borrower,
    по умолчанию — удостоверение личности, см. _add_borrower_and_car)."""
    prepare_russian_home(driver, manager)
    data = factories.application_autocredit(doc_number=doc_number)
    apps = ApplicationsPage(driver).open()
    for tab in ApplicationsPage.TABS:
        assert apps.tab(tab).is_displayed(), f"Нет вкладки «{tab}»"
    apps.start_new(ApplicationsPage.TYPE_AUTOCREDIT)
    _add_borrower_and_car(driver, data, add_borrower=add_borrower)

    b, c, seller = data.borrower, data.car, data.seller
    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == "Автокредит"
    extra.fill_collateral_and_down_payment(data.collateral, data.down_payment)
    expected_amount = str(int(data.collateral) - int(data.down_payment))
    assert extra.field_value("Желаемая сумма").replace(" ", "") == expected_amount
    assert extra.add_seller(seller) == f"{seller.first_name} {seller.last_name}"
    extra.pick_bitrix_deal()
    extra.next()

    confirm = ConfirmStep(driver).wait_loaded()
    assert confirm.summary_value("ФИО") == f"{b.first_name} {b.last_name} {b.patronymic}"
    assert confirm.summary_value("ИИН") == b.iin
    assert confirm.summary_value("ГРНЗ") == c.grnz
    assert confirm.summary_value("Желаемая сумма").replace(" ", "") == expected_amount
    confirm.submit(comment=data.confirm_comment)
    confirm.to_home()


def create_application_transh_passport(driver, manager, fixture):
    """Заявка «Транш», документ заёмщика — «Паспорт РК» (ИИН — из кредитной линии)."""
    create_application_transh(
        driver, manager, fixture, doc_number=factories.random_passport_number(),
        add_borrower=lambda d, p: BorrowerStep(d).add_manually_passport(p))


def create_application_transh_residence_permit(driver, manager, fixture):
    """Заявка «Транш», документ заёмщика — «Вид на жительство» (ИИН — из кредитной линии)."""
    create_application_transh(
        driver, manager, fixture,
        add_borrower=lambda d, p: BorrowerStep(d).add_manually_residence_permit(p))


def create_application_transh(driver, manager, fixture, doc_number=None, add_borrower=None):
    """Заявка «Транш»: ИИН заёмщика + VIN/ГРНЗ/номер техпаспорта авто должны совпадать
    с реальной кредитной линией в бэкенде — их нельзя сгенерировать. `fixture` (см.
    conftest.transh_fixture) собран из KZ_TRANSH_IIN/KZ_TRANSH_VIN/KZ_TRANSH_GRNZ/
    KZ_TRANSH_TECH_PASSPORT — админка подставляет их в окружение перед запуском.
    Остальные поля заёмщика/авто (ФИО, даты, цвет и т.п.) — как обычно, случайные.

    Отличия от «Новая», подтверждённые вживую (включая реальный найденный договор):
    экран «Дополнительные данные» показывает секцию «Договор» — после заполнения сумм
    приложение асинхронно ищет кредитную линию по ИИН/VIN/ГРНЗ/номеру техпаспорта.
    Найдена — секция разворачивается (№ договора, Автомобиль, Сумма займа, Остаток КЛ,
    Остаток ОД, Сумма выкупа, Дни просрочки, Сумма оценки), «Далее» становится активной.
    Не найдена — под «Стоимость залога» текст «...нет кредитной линии...», «Далее»
    остаётся неактивной. Суммы называются «Желаемая сумма транша»/«Стоимость залога»,
    есть недоступное для ввода поле «Сумма всех траншей» (= Остаток ОД + Желаемая сумма
    транша), поля «Сделка в bitrix» здесь нет вовсе.
    """
    prepare_russian_home(driver, manager)
    data = factories.application_transh(fixture, doc_number=doc_number)
    apps = ApplicationsPage(driver).open()
    for tab in ApplicationsPage.TABS:
        assert apps.tab(tab).is_displayed(), f"Нет вкладки «{tab}»"
    apps.start_new(ApplicationsPage.TYPE_TRANSH)
    _add_borrower_and_car(driver, data, add_borrower=add_borrower)

    b, c = data.borrower, data.car
    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == "Транш"
    extra.wait_contract()
    assert fixture.grnz in extra.contract_value("Автомобиль")
    # Сумма транша — в пределах «Остаток КЛ»; «Сумма всех траншей» = «Остаток ОД» + транш
    amount = factories.transh_amount(extra.contract_value("Остаток КЛ"))
    debt = factories.money(extra.contract_value("Остаток ОД"))
    extra.fill_transh_amounts(amount, data.collateral)
    # До тиына: приложение показывает сумму с ошибкой округления float
    # («4 197 338.220 000 001» вместо 4 197 338.22) — это его баг, не повод падать
    total = factories.money(extra.transh_total()).quantize(Decimal("0.01"))
    assert total == debt + int(amount), f"Сумма всех траншей {extra.transh_total()} ≠ {debt} + {amount}"
    assert extra.contract_matched(), (
        f"Кредитная линия не найдена по ИИН {fixture.iin} / VIN {fixture.vin} / "
        f"ГРНЗ {fixture.grnz} / номеру техпаспорта {fixture.tech_passport} — "
        "проверьте данные в админке."
    )
    extra.next()

    confirm = ConfirmStep(driver).wait_loaded()
    assert confirm.summary_value("ФИО") == f"{b.first_name} {b.last_name} {b.patronymic}"
    assert confirm.summary_value("ИИН") == b.iin
    assert confirm.summary_value("ГРНЗ") == c.grnz
    confirm.submit(comment=data.confirm_comment)
    confirm.to_home()


def create_application_refinance(driver, manager, fixture):
    """Заявка «Рефинансирование»: ИИН заёмщика + VIN/ГРНЗ/номер техпаспорта авто — данные
    конкретного реального клиента/авто, их нельзя генерировать случайно. `fixture` (см.
    conftest.refinance_fixture) собран из KZ_REFINANCE_IIN/KZ_REFINANCE_VIN/KZ_REFINANCE_GRNZ/
    KZ_REFINANCE_TECH_PASSPORT — админка подставляет их в окружение перед запуском.
    Остальные поля заёмщика/авто (ФИО, даты, цвет и т.п.) — как обычно, случайные.

    В отличие от «Транш» — подтверждено вживую — здесь НЕТ секции «Договор» и никакой
    проверки совпадения: экран «Дополнительные данные» устроен как у «Новая» (просто
    «Желаемая сумма»/«Стоимость залога», без «...транша» в названии), «Далее» активна
    сразу после заполнения сумм и выбора сделки в bitrix, и заявка создаётся успешно
    даже с заведомо несовпадающими ИИН/VIN/ГРНЗ/номером техпаспорта.
    """
    prepare_russian_home(driver, manager)
    data = factories.application_refinance(fixture)
    apps = ApplicationsPage(driver).open()
    for tab in ApplicationsPage.TABS:
        assert apps.tab(tab).is_displayed(), f"Нет вкладки «{tab}»"
    apps.start_new(ApplicationsPage.TYPE_REFINANCE)
    _add_borrower_and_car(driver, data)

    b, c = data.borrower, data.car
    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == "Рефинансирование"
    extra.fill_amounts(data.amount, data.collateral)
    extra.pick_bitrix_deal()
    extra.next()

    confirm = ConfirmStep(driver).wait_loaded()
    assert confirm.summary_value("ФИО") == f"{b.first_name} {b.last_name} {b.patronymic}"
    assert confirm.summary_value("ИИН") == b.iin
    assert confirm.summary_value("ГРНЗ") == c.grnz
    assert confirm.summary_value("Желаемая сумма").replace(" ", "") == data.amount
    confirm.submit(comment=data.confirm_comment)
    confirm.to_home()


def create_application_refinance_with_co_borrower(driver, manager, fixture):
    """Заявка «Рефинансирование» с созаёмщиком (удв. личности, «Добавить созаемщика вручную»).

    Экран доп. данных для «Рефинансирование» устроен как у «Новая» (см.
    create_application_refinance) — секция «Созаемщик» там есть, форма та же, что и
    для основного заёмщика; проверено на create_application_with_co_borrower.
    """
    prepare_russian_home(driver, manager)
    data = factories.application_refinance(fixture, with_co_borrower=True)
    apps = ApplicationsPage(driver).open()
    for tab in ApplicationsPage.TABS:
        assert apps.tab(tab).is_displayed(), f"Нет вкладки «{tab}»"
    apps.start_new(ApplicationsPage.TYPE_REFINANCE)
    _add_borrower_and_car(driver, data)

    b, c, co = data.borrower, data.car, data.co_borrower
    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == "Рефинансирование"
    extra.fill_amounts(data.amount, data.collateral)
    assert extra.add_co_borrower(co) == f"{co.first_name} {co.last_name}"
    extra.pick_bitrix_deal()
    extra.next()

    confirm = ConfirmStep(driver).wait_loaded()
    assert confirm.summary_value("ФИО") == f"{b.first_name} {b.last_name} {b.patronymic}"
    assert confirm.summary_value("ИИН") == b.iin
    assert confirm.summary_value("ГРНЗ") == c.grnz
    assert confirm.summary_value("Желаемая сумма").replace(" ", "") == data.amount
    confirm.submit(comment=data.confirm_comment)
    confirm.to_home()


def create_application_refinance_residence_permit(driver, manager, fixture):
    """Заявка «Рефинансирование», тип документа заёмщика — «Вид на жительство».

    Отличие от обычного «Удостоверение личности» (см. create_application_refinance) —
    подтверждено вживую — только в самой форме документа: та же анкета плюс поле
    «Страна» (полный справочник, подходит любое значение), между «Действителен до»
    и «Орган выдачи». Всё остальное (авто, доп. данные, подтверждение) не отличается.
    """
    prepare_russian_home(driver, manager)
    data = factories.application_refinance(fixture)
    apps = ApplicationsPage(driver).open()
    for tab in ApplicationsPage.TABS:
        assert apps.tab(tab).is_displayed(), f"Нет вкладки «{tab}»"
    apps.start_new(ApplicationsPage.TYPE_REFINANCE)
    _add_borrower_and_car(
        driver, data,
        add_borrower=lambda d, p: BorrowerStep(d).add_manually_residence_permit(p),
    )

    b, c = data.borrower, data.car
    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == "Рефинансирование"
    extra.fill_amounts(data.amount, data.collateral)
    extra.pick_bitrix_deal()
    extra.next()

    confirm = ConfirmStep(driver).wait_loaded()
    assert confirm.summary_value("ФИО") == f"{b.first_name} {b.last_name} {b.patronymic}"
    assert confirm.summary_value("ИИН") == b.iin
    assert confirm.summary_value("ГРНЗ") == c.grnz
    assert confirm.summary_value("Желаемая сумма").replace(" ", "") == data.amount
    confirm.submit(comment=data.confirm_comment)
    confirm.to_home()


def create_application_refinance_passport(driver, manager, fixture):
    """Заявка «Рефинансирование», тип документа заёмщика — «Паспорт РК».

    Отличие от «Удостоверение личности» (см. create_application_refinance) —
    подтверждено вживую — только в формате «Номер документа»: буква + 8 цифр
    (например, N15115334, см. factories.random_passport_number()). Сама форма —
    та же IdCardForm, остальное не отличается.
    """
    prepare_russian_home(driver, manager)
    data = factories.application_refinance(fixture, doc_number=factories.random_passport_number())
    apps = ApplicationsPage(driver).open()
    for tab in ApplicationsPage.TABS:
        assert apps.tab(tab).is_displayed(), f"Нет вкладки «{tab}»"
    apps.start_new(ApplicationsPage.TYPE_REFINANCE)
    _add_borrower_and_car(
        driver, data,
        add_borrower=lambda d, p: BorrowerStep(d).add_manually_passport(p),
    )

    b, c = data.borrower, data.car
    extra = ExtraDataStep(driver)
    extra.wait_loaded()
    assert extra.loan_type() == "Рефинансирование"
    extra.fill_amounts(data.amount, data.collateral)
    extra.pick_bitrix_deal()
    extra.next()

    confirm = ConfirmStep(driver).wait_loaded()
    assert confirm.summary_value("ФИО") == f"{b.first_name} {b.last_name} {b.patronymic}"
    assert confirm.summary_value("ИИН") == b.iin
    assert confirm.summary_value("ГРНЗ") == c.grnz
    assert confirm.summary_value("Желаемая сумма").replace(" ", "") == data.amount
    confirm.submit(comment=data.confirm_comment)
    confirm.to_home()
