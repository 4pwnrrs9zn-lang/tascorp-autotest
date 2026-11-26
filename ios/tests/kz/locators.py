"""Все локаторы сборки KZ на iOS — по экранам, у каждого поля и кнопки свой.

Локаторы нативные для XCUITest (class chain / predicate) — выполняются внутри
WebDriverAgent за ~0,2 с. XPath на iOS строит снимок всего экрана (0,5–6 с) — не используем.

Как устроено дерево React Native на iOS (проверено вживую, 2026-10-08):
- кнопки: Button с name = текст/testID;
- поле формы: группа Other «<подпись> <подсказка или значение>», внутри TextField —
  поэтому поле ищется по группе, имя которой начинается с подписи (контейнер самого поля
  называется по подсказке и после ввода переименовывается в значение — для поиска не годится);
- дата: кнопка name="undefined.overlay" в группе поля;
- справочник: кнопка «Select <подпись>», после выбора — «<подпись>. selected. <значение>»;
- контейнеры перенимают подписи дочерних элементов — элемент «по имени» берётся
  последний (самый глубокий): [-1].

Порядок и правила заполнения полей — как в Android-проекте (tests/kz/application_wizard.py).
"""
from appium.webdriver.common.appiumby import AppiumBy

from pages.base_page import button, by_any_name, by_name, static_text


def chain(query):
    return AppiumBy.IOS_CLASS_CHAIN, query


def _group(label):
    return f'**/XCUIElementTypeOther[`name == "{label}" OR name BEGINSWITH "{label} "`]'


def text_field(label):
    """Однострочное поле ввода под подписью."""
    return chain(f"{_group(label)}/**/XCUIElementTypeTextField")


def text_view(label):
    """Многострочное поле («Комментарий»)."""
    return chain(f"{_group(label)}/**/XCUIElementTypeTextView")


def date_field(label):
    return chain(f'{_group(label)}/**/XCUIElementTypeButton[`name == "undefined.overlay"`]')


def dictionary_field(label):
    return (AppiumBy.IOS_PREDICATE,
            f'type == "XCUIElementTypeButton" AND (name == "Select {label}" OR name BEGINSWITH "{label}. selected")')


def summary_value(label):
    """Значение на экране-сводке: группа «<подпись> <значение>», второй StaticText."""
    return chain(f'**/XCUIElementTypeOther[`name BEGINSWITH "{label} "`]/XCUIElementTypeStaticText[2]')


class Start:
    # После сброса кода-пароля стартовый экран — на языке приложения (русский, если уже переключали)
    LOGIN = (AppiumBy.IOS_PREDICATE, 'type == "XCUIElementTypeButton" AND name IN {"Кіру", "Войти"}')


class Login:
    LOGIN = (AppiumBy.CLASS_NAME, "XCUIElementTypeTextField")
    PASSWORD = (AppiumBy.CLASS_NAME, "XCUIElementTypeSecureTextField")
    SUBMIT = by_name("loginBtn")
    KEYBOARD_DONE = (AppiumBy.IOS_PREDICATE,
                     'type IN {"XCUIElementTypeButton", "XCUIElementTypeKey"} AND name == "Done"')


class Pin:
    # «Забыли код-пароль?» → диалог «Сбросить код-пароль» → «Да» → экран логина/пароля
    FORGOT = by_any_name("Забыли код-пароль?", "Код-паролді ұмытып қалдыңыз ба?")
    RESET_YES = (AppiumBy.IOS_PREDICATE, 'type == "XCUIElementTypeButton" AND name IN {"Да", "Ия"}')

    @staticmethod
    def digit(d):
        return AppiumBy.IOS_PREDICATE, f'type == "XCUIElementTypeOther" AND name == "{d}"'


class Home:
    TAB_HOME = by_any_name("бастапқы бет", "главная")
    APPLICATIONS = by_any_name("Өтінімдер", "Заявки")

    @staticmethod
    def role(role):
        return static_text(role)


class Menu:
    TAB = by_any_name("мәзір", "меню")
    SETTINGS = by_any_name("Баптаулар", "Настройки")
    LANGUAGE = by_any_name("Тіл", "Язык")
    RUSSIAN = by_any_name("Орысша", "Русский")
    TITLE_RU = static_text("Настройки")
    TAB_HOME_RU = button("главная")


class Applications:
    ENTRY = by_name("Заявки")
    TABS = ("В работе", "На оценке", "Завершенные")
    NEW = button("Новая заявка")
    RATING_TITLE = static_text("Оценка работы")
    SAVE = button("Сохранить")

    @staticmethod
    def tab(name):
        return by_name(name)

    @staticmethod
    def loan_type(name):
        return button(name)


class Wizard:
    """Общее для шагов мастера."""
    NEXT = button("Далее")
    ADD_MANUALLY = button("Добавить вручную")
    ADD_DOC_PHOTO = button("Добавить фото документа")
    # Тост приложения (ошибки бэкенда): заголовок toastText1, текст toastText2
    TOAST = chain('**/XCUIElementTypeStaticText[`name BEGINSWITH "toastText"`]')


class Dictionary:
    """Шторка справочника с поиском (Марка, Модель, Сделка в bitrix…)."""
    SEARCH = chain('**/XCUIElementTypeTextField[`name == "undefined.modal"`]')
    CANCEL = (AppiumBy.ACCESSIBILITY_ID, "undefined.modal.topBar.cancel")
    OVERLAY = (AppiumBy.ACCESSIBILITY_ID, "undefined.modal.TouchableOverlay")  # подложка под шторкой

    @staticmethod
    def item(n):
        """Пункт по номеру (с 1). Все пункты разом не запрашиваем: у марок ~150 пунктов —
        такой запрос 20 с; фильтр видимости (wdVisible) у этого списка не срабатывает."""
        return chain(f'**/XCUIElementTypeOther[`name == "undefined.modal.list"`]/**/XCUIElementTypeButton[{n}]')


class DatePicker:
    DONE = (AppiumBy.ACCESSIBILITY_ID, "undefined.done")  # «Выбрать»
    WHEELS = (AppiumBy.CLASS_NAME, "XCUIElementTypePickerWheel")  # месяц / день / год


class DocPhotos:
    """Экран «Лицевая сторона / Обратная сторона»."""
    FRONT = by_name("Лицевая сторона")
    BACK = by_name("Обратная сторона")
    SAVE = button("Сохранить")
    # Экран ещё открыт: после раннего «Сохранить» ячейка переименовывается
    # в «Загрузите фото Лицевая сторона», и FRONT её уже не находит
    SCREEN = chain('**/XCUIElementTypeOther[`name CONTAINS "Лицевая сторона"`]')
    # Ошибка загрузки фото — в имени ячейки: «Request failed with status code 502 Загрузите фото…»
    UPLOAD_ERROR = chain('**/XCUIElementTypeOther[`name BEGINSWITH "Request failed"`]')


class Camera:
    """Системная камера; на Simulator — тестовая камера с тем же идентификатором затвора."""
    SHUTTER = (AppiumBy.ACCESSIBILITY_ID, "PhotoCapture")


class Borrower:
    TITLE = static_text("Данные заемщика")
    # Тип заёмщика (с 14.10.2026): радиокнопки над «Тип документа»
    INDIVIDUAL = (AppiumBy.ACCESSIBILITY_ID, "Физ. лицо")
    LEGAL_ENTITY = (AppiumBy.ACCESSIBILITY_ID, "Юр. лицо")
    # «Тип документа»: короткий список «Удостоверение личности» (по умолчанию) /
    # «Вид на жительство» / «Паспорт РК»; после выбора — «Выбрать документ. selected. <тип>»
    DOC_TYPE = dictionary_field("Выбрать документ")
    ID_CARD = "Удостоверение личности"
    RESIDENCE_PERMIT = "Вид на жительство"
    PASSPORT = "Паспорт РК"

    @staticmethod
    def doc_type(name):
        return button(name)


class IdCard:
    """Форма «Удостоверение личности» (заёмщик, созаёмщик). Та же форма — у «Паспорт РК»
    (другой только формат номера) и «Вид на жительство» (плюс «Страна»)."""
    TITLE = static_text("ИИН")  # первая подпись формы — по ней ждём, что шторка встала
    IIN = text_field("ИИН")
    LAST_NAME = text_field("Фамилия")
    FIRST_NAME = text_field("Имя")
    PATRONYMIC = text_field("Отчество")
    BIRTH_DATE = date_field("Дата рождения")
    DOC_NUMBER = text_field("Номер документа")
    BIRTH_PLACE = text_field("Место рождения")
    ISSUE_DATE = date_field("Дата выдачи")
    EXPIRY_DATE = date_field("Действителен до")
    COUNTRY = dictionary_field("Страна")  # только «Вид на жительство»: полный справочник с поиском
    ISSUER = dictionary_field("Орган выдачи")

    @staticmethod
    def issuer_option(name):
        return button(name)


class LegalEntity:
    """«Данные заемщика» → «Юр. лицо»: субъекты (физ. лица с ролью) и данные компании.

    Субъект добавляется шторкой из трёх экранов: анкета (поля как у IdCard плюс «Тип
    субъекта») → фото удостоверения → «Документы субъектов» (необязательны) → «Сохранить».
    В каждой шторке под ней в дереве остаётся невидимая «Далее» основного экрана —
    кнопку шторки ищем только среди видимых."""
    ADD_SUBJECT = button("Добавить субъекта")
    SUBJECT_TYPE = dictionary_field("Тип субъекта")
    SUBJECT_BORROWER = "Заемщик"  # ещё: Созаемщик, Гарант, Залогодатель, Созалогодатель, Мерчант
    SUBJECT_DOCS = static_text("Документы субъектов")
    SUBJECT_CARD = text_field("Субъект 1")  # после добавления: «<тип> · Фамилия Имя», недоступно для ввода
    SHEET_NEXT = (AppiumBy.IOS_PREDICATE, 'type == "XCUIElementTypeButton" AND name == "Далее" AND visible == 1')
    SHEET_SAVE = (AppiumBy.IOS_PREDICATE, 'type == "XCUIElementTypeButton" AND name == "Сохранить" AND visible == 1')

    ADD_COMPANY = button("Добавить данные компании")
    COMPANY_NAME_LABEL = static_text("Наименование компании")
    COMPANY_NAME = text_field("Наименование компании")
    LEGAL_FORM = dictionary_field("Организационно-правовая форма")  # короткий список без поиска
    REGISTRATION_DATE = date_field("Дата регистрации компании")
    REGISTRATION_PLACE = text_field("Место регистрации")
    # Подпись была «БИН продавца», с 13.11.2026 — «БИН»; text_field("БИН") находит обе
    BIN = text_field("БИН")
    # После сохранения на основном экране — поле «Наименование компании»: «<название> · <БИН>»
    COMPANY_CARD = text_field("Наименование компании")
    # Сводка после «Далее» (подписи компании, ниже — «Субъекты»)
    SUMMARY = static_text("Дата регистрации компании")

    @staticmethod
    def subject_type(name):
        return button(name)

    @staticmethod
    def legal_form(name):
        return button(name)


class Car:
    TITLE = static_text("Автомобиль")
    FORM_TITLE = static_text("Марка")
    BRAND = dictionary_field("Марка")
    MODEL = dictionary_field("Модель")
    YEAR = text_field("Год выпуска авто")
    GRNZ = text_field("ГРНЗ")
    TECH_PASSPORT = text_field("Номер техпаспорта")
    ISSUE_DATE = date_field("Дата выдачи")
    VIN = text_field("VIN код")
    COLOR = text_field("Цвет")


class CarPhotos:
    TITLE = static_text("Фото авто")
    REQUIRED = ("вид спереди", "вид сзади", "вид слева", "вид справа", "Клиент на фоне авто", "VIN код")
    COMMENT = text_view("Комментарий")
    COMMENT_LABEL = static_text("Комментарий")
    # Ячейка, фото которой ещё загружается: имя начинается с «In progress»
    UPLOADING = chain('**/XCUIElementTypeOther[`name BEGINSWITH "In progress"`]')

    @staticmethod
    def slot(name):
        return chain(f'**/XCUIElementTypeOther[`name == "{name}"`][-1]')


class ExtraData:
    TITLE = static_text("Дополнительные данные")
    # Недоступно для ввода; в дереве iOS стоит последним, а не первым, как на экране, —
    # поиск по группе подписи вернул бы «Желаемая сумма». Единственное недоступное поле экрана
    LOAN_TYPE = chain('**/XCUIElementTypeTextField[`enabled == 0`]')
    AMOUNT = text_field("Желаемая сумма")
    COLLATERAL = text_field("Стоимость залога")
    BITRIX_DEAL = dictionary_field("Сделка в bitrix")
    NO_VISIT = static_text("По данному ИИН нет визита. Создайте визит!")
    # «Автокредит»: «Желаемая сумма» недоступна для ввода (= залог − взнос), ниже — продавец
    # (владелец авто): тип «Физ. лицо»/«Юр. лицо» и «Добавить продавца EGOV»/«…вручную»
    DOWN_PAYMENT = text_field("Первоначальный взнос")
    SELLER_INDIVIDUAL = (AppiumBy.ACCESSIBILITY_ID, "Физ. лицо")
    ADD_SELLER_MANUALLY = button("Добавить продавца вручную")
    # «Транш»: по ИИН/VIN/ГРНЗ/техпаспорту приложение находит кредитную линию и показывает
    # блок «Договор» (№ договора, Автомобиль, Остаток КЛ…); «Сумма всех траншей» недоступна
    # для ввода (= Остаток ОД + Желаемая сумма транша); «Сделки в bitrix» и созаёмщика нет
    CONTRACT_NUMBER = summary_value("№ договора")
    TRANSH_AMOUNT = text_field("Желаемая сумма транша")
    TRANSH_TOTAL = text_field("Сумма всех траншей")
    # «Новая»: блок «Созаемщик» — «Добавить созаемщика EGOV»/«…вручную»
    ADD_CO_BORROWER_MANUALLY = button("Добавить созаемщика вручную")
    CO_BORROWER = text_field("Созаемщик")  # после добавления: «Имя Фамилия», недоступно для ввода
    SELLER = text_field("Продавец")  # появляется после добавления: «Имя Фамилия», недоступно для ввода


class Confirm:
    TITLE = static_text("Подтверждение")
    COMMENT = text_view("Комментарий")
    COMMENT_LABEL = static_text("Комментарий")
    SUCCESS = static_text("Заявка успешно отправлена на оценку!")
    TO_HOME = button("На главную")
