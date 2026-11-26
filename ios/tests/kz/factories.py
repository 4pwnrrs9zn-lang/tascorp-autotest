"""Случайные тестовые данные для заявки — по требованиям законодательства Казахстана.

Формат ИИН (12 цифр, с настоящим контрольным разрядом), номер документа, справочник
органов выдачи — свои для KZ. Не переиспользовать для UZ: там свой tests/uz/factories.py
с ПИНФЛ/своими форматами.
"""
import os
import random
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from factories_common import digits, letters, random_day, VIN_LETTERS

# Настоящие фото для ячеек, где приложение проверяет содержимое снимка
# (остальные ячейки — сгенерированные картинки тестовой камеры)
PHOTOS_DIR = Path(__file__).resolve().parents[2] / "test_data" / "photos"
CAR_PHOTOS = {
    "Клиент на фоне авто": PHOTOS_DIR / "client_on_car.jpg",
    # С 10.11.2026 бэкенд распознаёт VIN на фото и без него отвечает 400 «Протрите VIN-код…»;
    # настоящее фото выбитого VIN (JTJPBBCX304002408) — дал пользователь
    "VIN код": PHOTOS_DIR / "vin.png",
}

# «Транш»/«Рефинансирование»: ИИН/VIN/ГРНЗ/номер техпаспорта задаются перед запуском
# (админка подставляет их в окружение процесса pytest; см. tests/kz/test_application.py).
# Для «Транш» бэкенд реально сверяет их с кредитной линией и блокирует «Далее» при
# несовпадении — для «Рефинансирование» нет: заявка создаётся в любом случае (проверено
# вживую), но поля всё равно нельзя генерировать случайно — это данные конкретного
# реального клиента/авто, о которых человек должен сказать явно.
TRANSH_ENV_FIELDS = (
    ("KZ_TRANSH_IIN", "ИИН клиента (как в кредитной линии)"),
    ("KZ_TRANSH_VIN", "VIN код авто"),
    ("KZ_TRANSH_GRNZ", "ГРНЗ"),
    ("KZ_TRANSH_TECH_PASSPORT", "Номер техпаспорта"),
)
# «Новая» для юр. лица: БИН компании — необязательное поле; пусто — случайный
LEGAL_ENTITY_ENV_FIELDS = (
    ("KZ_LEGAL_BIN", "БИН компании", "optional"),
)
REFINANCE_ENV_FIELDS = (
    ("KZ_REFINANCE_IIN", "ИИН клиента"),
    ("KZ_REFINANCE_VIN", "VIN код авто"),
    ("KZ_REFINANCE_GRNZ", "ГРНЗ"),
    ("KZ_REFINANCE_TECH_PASSPORT", "Номер техпаспорта"),
)

LAST_NAMES = ["Бурабаев", "Ахметов", "Нурланов", "Сейтов", "Жумабеков", "Тестов", "Касымов"]
FIRST_NAMES = ["Аян", "Ерлан", "Нурлан", "Дамир", "Алихан", "Автотест", "Санжар"]
PATRONYMICS = ["Ерланович", "Нурланович", "Дамирович", "Тестович", "Санжарович"]
CITIES = ["Алматы", "Астана", "Шымкент", "Караганда", "Актобе", "Тараз", "Павлодар"]
ISSUERS = ["МВД РК", "МЮ РК"]
COLORS = ["Черный", "Белый", "Серебристый", "Серый", "Синий", "Красный"]
GRNZ_REGIONS = ["01", "02", "05", "10", "15"]

# 1800-е/1900-е/2000-е + пол: см. checksum() ниже — стандартная формула ИИН РК
_CENTURY_CODE = {18: 1, 19: 3, 20: 5}


@dataclass
class Person:
    iin: str
    last_name: str
    first_name: str
    patronymic: str
    birth_date: date
    doc_number: str
    birth_place: str
    issue_date: date
    expiry_date: date
    issuer: str
    country: str = None  # выбранное значение справочника — только для «Вид на жительство»


@dataclass
class Car:
    year: str
    grnz: str
    tech_passport: str
    issue_date: date
    vin: str
    color: str
    brand: str = None    # выбранные значения справочников
    model: str = None


@dataclass
class Company:
    name: str
    legal_form: str
    registration_date: date
    registration_place: str
    bin: str


@dataclass
class ApplicationData:
    borrower: Person
    car: Car
    photos_comment: str = "Автотест: фото авто"
    confirm_comment: str = "Автотест: заявка создана автоматически"
    # «Новая»: amount/collateral — свободный ввод, co_borrower — опционален
    amount: str = None
    collateral: str = None
    co_borrower: Person = None
    # «Автокредит»: amount не задаётся вручную (считается приложением), нужен down_payment и seller
    down_payment: str = None
    seller: Person = None
    # Юр. лицо: borrower — субъект-заёмщик (физ. лицо), company — данные компании
    company: Company = None


@dataclass
class TranshFixture:
    """Данные реальной кредитной линии для «Транш» — заданы человеком, не сгенерированы."""
    iin: str
    vin: str
    grnz: str
    tech_passport: str


@dataclass
class RefinanceFixture:
    """Данные реального клиента/авто для внутреннего/внешнего рефинансирования — заданы человеком."""
    iin: str
    vin: str
    grnz: str
    tech_passport: str


def _checksum(digits11):
    weights = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    s = sum(d * w for d, w in zip(digits11, weights)) % 11
    if s == 10:
        weights2 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2]
        s = sum(d * w for d, w in zip(digits11, weights2)) % 11
    return s


def random_iin(birth_date, male=True):
    """ИИН по реальной формуле: YYMMDD + век/пол + 4 случайные цифры + контрольный разряд."""
    century = _CENTURY_CODE[birth_date.year // 100] + (0 if male else 1)
    base = f"{birth_date.year % 100:02d}{birth_date.month:02d}{birth_date.day:02d}{century}"
    for _ in range(200):
        candidate = base + digits(4)
        check = _checksum([int(c) for c in candidate])
        if check != 10:  # 10 — невалидная комбинация, пробуем другой порядковый номер
            return candidate + str(check)
    raise RuntimeError("Не удалось сгенерировать валидный ИИН")


def random_bin(registration_date):
    """БИН юр. лица РК: ГГММ регистрации + 4 (юр. лицо-резидент) + 0 (головная организация)
    + 5 цифр + контрольный разряд (та же формула, что у ИИН)."""
    base = f"{registration_date.year % 100:02d}{registration_date.month:02d}40"
    for _ in range(200):
        candidate = base + digits(5)
        check = _checksum([int(c) for c in candidate])
        if check != 10:
            return candidate + str(check)
    raise RuntimeError("Не удалось сгенерировать валидный БИН")


def random_company(today=None):
    today = today or date.today()
    registered = random_day(add_years(today, -10), add_years(today, -1))
    return Company(
        name=f"ТОО Автотест {digits(4)}",
        legal_form="Товарищество с ограниченной ответственностью",
        registration_date=registered,
        registration_place=random.choice(CITIES),
        bin=random_bin(registered),
    )


def random_person(today=None):
    today = today or date.today()
    # Старше 18 лет: 21–35 лет (узкий диапазон — меньше прокрутки в календаре)
    birth = random_day(add_years(today, -35), add_years(today, -21))
    male = random.choice([True, False])
    # Выдан в последние 3 года, но не позже вчерашнего дня
    issue = random_day(add_years(today, -3), today - timedelta(days=30))
    return Person(
        iin=random_iin(birth, male=male),
        last_name=random.choice(LAST_NAMES),
        first_name=random.choice(FIRST_NAMES),
        patronymic=random.choice(PATRONYMICS),
        birth_date=birth,
        doc_number="0406" + digits(5),  # формат удостоверения личности РК
        birth_place=random.choice(CITIES),
        issue_date=issue,
        expiry_date=add_years(issue, 10),  # действует ровно 10 лет с даты выдачи
        issuer=random.choice(ISSUERS),
    )


def random_car(today=None):
    today = today or date.today()
    return Car(
        year=str(random.randint(2000, today.year - 1)),
        grnz=digits(3) + letters(3) + random.choice(GRNZ_REGIONS),      # формат «123ABC01»
        tech_passport=letters(2) + digits(8),                          # 2 буквы + 8 цифр
        issue_date=random_day(add_years(today, -2), today - timedelta(days=30)),
        vin=letters(3, VIN_LETTERS) + digits(14),                      # 3 буквы + 14 цифр = 17 симв.
        color=random.choice(COLORS),
    )


def random_passport_number():
    """Номер паспорта РК — по примеру пользователя (буква N + 8 цифр, напр. N15115334)."""
    return "N" + digits(8)


def random_person_with_iin(iin, today=None, doc_number=None):
    """Как random_person(), но с заданным ИИН — для «Транш»/«Рефинансирование», где ИИН
    должен совпадать с реальными данными; остальные поля заёмщика к ним не привязаны.
    doc_number: переопределить формат номера документа (например, random_passport_number()
    для типа документа «Паспорт РК» — по умолчанию формат удостоверения личности)."""
    today = today or date.today()
    birth = random_day(add_years(today, -35), add_years(today, -21))
    issue = random_day(add_years(today, -3), today - timedelta(days=30))
    return Person(
        iin=iin,
        last_name=random.choice(LAST_NAMES),
        first_name=random.choice(FIRST_NAMES),
        patronymic=random.choice(PATRONYMICS),
        birth_date=birth,
        doc_number=doc_number or ("0406" + digits(5)),
        birth_place=random.choice(CITIES),
        issue_date=issue,
        expiry_date=add_years(issue, 10),
        issuer=random.choice(ISSUERS),
    )


def random_car_with(vin, grnz, tech_passport, today=None):
    """Как random_car(), но с заданными VIN/ГРНЗ/номером техпаспорта — для «Транш»."""
    today = today or date.today()
    return Car(
        year=str(random.randint(2000, today.year - 1)),
        grnz=grnz,
        tech_passport=tech_passport,
        issue_date=random_day(add_years(today, -2), today - timedelta(days=30)),
        vin=vin,
        color=random.choice(COLORS),
    )


def random_amounts():
    """Желаемая сумма (> 400 000) и стоимость залога (не меньше 5 сумм)."""
    amount = random.randint(401, 900) * 1000
    collateral = amount * 5 + random.randint(1, 50) * 1000
    return str(amount), str(collateral)


def random_autocredit_amounts():
    """Первоначальный взнос и стоимость залога для «Автокредит» (залог заведомо больше взноса)."""
    down_payment = random.randint(200, 800) * 1000
    collateral = down_payment + random.randint(1000, 3000) * 1000
    return str(collateral), str(down_payment)


def application(with_co_borrower=False, doc_number=None):
    """doc_number — свой формат номера документа заёмщика (например, random_passport_number()
    для «Паспорт РК»); созаёмщик всегда с удостоверением личности."""
    amount, collateral = random_amounts()
    borrower = random_person()
    if doc_number:
        borrower = replace(borrower, doc_number=doc_number)
    return ApplicationData(
        borrower=borrower,
        car=random_car(),
        amount=amount,
        collateral=collateral,
        co_borrower=random_person() if with_co_borrower else None,
    )


def application_autocredit(doc_number=None):
    """doc_number — свой формат номера документа заёмщика (например, random_passport_number()
    для «Паспорт РК»); по умолчанию — формат удостоверения личности."""
    collateral, down_payment = random_autocredit_amounts()
    borrower = random_person()
    if doc_number:
        borrower = replace(borrower, doc_number=doc_number)
    return ApplicationData(
        borrower=borrower,
        car=random_car(),
        collateral=collateral,
        down_payment=down_payment,
        seller=random_person(),
    )


def as_legal_entity(data):
    """Та же заявка, но заёмщик — юр. лицо: borrower становится субъектом-заёмщиком,
    добавляется компания. БИН — из поля KZ_LEGAL_BIN (админка), пусто — случайный."""
    company = random_company()
    if bin_ := os.getenv("KZ_LEGAL_BIN", "").strip():
        company = replace(company, bin=bin_)
    return replace(data, company=company)


_FIXTURE_KEYS = ("iin", "vin", "grnz", "tech_passport")


def _fixture_from_env(env_fields, cls):
    """Читает пары (ENV_VAR, подпись) из окружения (админка подставляет их перед запуском).

    Возвращает (cls(...), []) или (None, [список отсутствующих подписей]) — по этому
    списку вызывающий код формирует понятный pytest.skip().
    """
    values, missing = {}, []
    for (env, label), key in zip(env_fields, _FIXTURE_KEYS):
        value = os.getenv(env, "").strip()
        values[key] = value
        if not value:
            missing.append(label)
    if missing:
        return None, missing
    return cls(**values), []


def transh_fixture_from_env():
    return _fixture_from_env(TRANSH_ENV_FIELDS, TranshFixture)


def refinance_fixture_from_env():
    return _fixture_from_env(REFINANCE_ENV_FIELDS, RefinanceFixture)


def application_transh(fixture, doc_number=None):
    amount, collateral = random_amounts()
    return ApplicationData(
        borrower=random_person_with_iin(fixture.iin, doc_number=doc_number),
        car=random_car_with(fixture.vin, fixture.grnz, fixture.tech_passport),
        amount=amount,
        collateral=collateral,
    )


def money(text):
    """Сумма с экрана («717 661.78», «600 000») → Decimal: суммы договора бывают с тиынами."""
    return Decimal(text.replace(" ", "").replace("\u00a0", "").replace(",", "."))


def transh_amount(credit_line_rest):
    """Желаемая сумма транша (целые тысячи) — в пределах остатка кредитной линии («Остаток КЛ»)."""
    top = max(10, int(money(credit_line_rest)) // 1000)
    return str(random.randint(10, top) * 1000)


def application_refinance(fixture, with_co_borrower=False, doc_number=None):
    amount, collateral = random_amounts()
    return ApplicationData(
        borrower=random_person_with_iin(fixture.iin, doc_number=doc_number),
        car=random_car_with(fixture.vin, fixture.grnz, fixture.tech_passport),
        amount=amount,
        collateral=collateral,
        co_borrower=random_person() if with_co_borrower else None,
    )


def add_years(d, years):
    return d.replace(year=d.year + years)
