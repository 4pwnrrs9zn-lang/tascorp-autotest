"""Случайные тестовые данные для заявки — по требованиям законодательства Узбекистана.

Формат ПИНФЛ (14 цифр), ГРНЗ, справочники областей/органов выдачи — свои для UZ.
Не переиспользовать для KZ: там свой tests/kz/factories.py с ИИН/своими форматами.
"""
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from factories_common import add_years, digits, letters, random_day, VIN_LETTERS

LAST_NAMES = ["Тестов", "Иванов", "Петров", "Каримов", "Алиев", "Юсупов", "Рахимов"]
FIRST_NAMES = ["Автотест", "Иван", "Алишер", "Тимур", "Руслан", "Азамат", "Бахтиёр"]
PATRONYMICS = ["Тестович", "Иванович", "Алишерович", "Тимурович", "Русланович"]
CITIES = ["Ташкент", "Самарканд", "Бухара", "Наманган", "Андижан", "Фергана", "Алматы"]
ISSUERS = ["МВД РК", "МЮ РК", "МВД РУз", "ДВД РК"]
GRNZ_REGIONS = ["01", "02", "05", "10", "15"]


@dataclass
class Person:
    pinfl: str
    last_name: str
    first_name: str
    patronymic: str
    birth_date: date
    series: str
    doc_number: str
    birth_place: str
    issue_date: date
    expiry_date: date
    issuer: str
    region: str = None    # заполняется выбранным значением из справочника
    district: str = None


@dataclass
class Car:
    year: str
    grnz: str
    tech_passport: str
    issue_date: date
    issuer: str
    mileage: str
    body_number: str
    engine_number: str
    chassis_number: str
    brand: str = None     # выбранные значения справочников
    model: str = None
    picked: dict = field(default_factory=dict)


@dataclass
class ApplicationData:
    borrower: Person
    car: Car
    amount: str = "1000000"
    collateral: str = "5000000"
    photos_comment: str = "Автотест: фото авто"
    extra_photo: bool = False
    co_borrower: Person = None


def random_person(today=None):
    today = today or date.today()
    # Старше 18 лет: 21–35 лет (узкий диапазон — меньше прокрутки в календаре)
    birth = random_day(add_years(today, -35), add_years(today, -21))
    # Выдан в последние 3 года, но не позже вчерашнего дня
    issue = random_day(add_years(today, -3), today - timedelta(days=30))
    return Person(
        pinfl=random.choice("3456") + digits(13),     # 14 цифр
        last_name=random.choice(LAST_NAMES),
        first_name=random.choice(FIRST_NAMES),
        patronymic=random.choice(PATRONYMICS),
        birth_date=birth,
        series=letters(2),                            # 2 латинские буквы
        doc_number=digits(7),                         # 7 цифр
        birth_place=random.choice(CITIES),
        issue_date=issue,
        expiry_date=add_years(issue, 10) + timedelta(days=30),  # действует ≥ 10 лет
        issuer=random.choice(ISSUERS),
    )


def random_car(today=None):
    today = today or date.today()
    return Car(
        year=str(random.randint(2000, today.year - 1)),
        grnz=digits(3) + letters(3) + random.choice(GRNZ_REGIONS),   # казахский ГРНЗ: 323FFM05
        tech_passport=letters(3) + digits(7),                        # 3 буквы + 7 цифр
        issue_date=random_day(add_years(today, -2), today - timedelta(days=30)),
        issuer=random.choice(ISSUERS),
        mileage=str(random.randint(5, 200) * 1000),
        body_number=letters(3, VIN_LETTERS) + digits(8),       # как HMV09765676
        engine_number=letters(3) + digits(5),
        chassis_number=letters(6, VIN_LETTERS) + digits(4),
    )


def application(extra_photo=False, with_co_borrower=False):
    return ApplicationData(
        borrower=random_person(),
        car=random_car(),
        extra_photo=extra_photo,
        co_borrower=random_person() if with_co_borrower else None,
    )
