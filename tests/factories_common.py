"""Универсальные генераторы: строки/даты без привязки к формату конкретной страны.

Домен (какие поля, какой формат ПИНФЛ/ИИН, какие справочники) — не сюда,
а в tests/<uz|kz>/factories.py: это уже требования закона конкретной страны.
"""
import random
import string
from datetime import timedelta

# В VIN/номерах кузова не бывает I, O, Q — приложение отвечает «Неправильный формат»
VIN_LETTERS = "".join(c for c in string.ascii_uppercase if c not in "IOQ")


def digits(n):
    return "".join(random.choices(string.digits, k=n))


def letters(n, alphabet=string.ascii_uppercase):
    return "".join(random.choices(alphabet, k=n))


def random_day(start, end):
    """Случайная дата в [start, end]; день месяца ≤ 28, чтобы он был в любом месяце."""
    d = start + timedelta(days=random.randint(0, (end - start).days))
    return d.replace(day=min(d.day, 28))


def add_years(d, years):
    return d.replace(year=d.year + years)
