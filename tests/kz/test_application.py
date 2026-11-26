import pytest

from .factories import REFINANCE_ENV_FIELDS, TRANSH_ENV_FIELDS
from .scenarios import (
    create_application_autocredit,
    create_application_autocredit_passport,
    create_application_autocredit_residence_permit,
    create_application_basic,
    create_application_new_passport,
    create_application_new_residence_permit,
    create_application_refinance,
    create_application_refinance_passport,
    create_application_refinance_residence_permit,
    create_application_refinance_with_co_borrower,
    create_application_transh,
    create_application_transh_passport,
    create_application_transh_residence_permit,
    create_application_with_co_borrower,
)


def test_create_application_basic(driver, manager):
    """Заявка «Новая»: заёмщик + авто + 6 фото + доп. данные (без доп. фото и созаёмщика)"""
    create_application_basic(driver, manager)


def test_create_application_with_co_borrower(driver, manager):
    """Заявка «Новая» с созаёмщиком (удостоверение личности, добавлен вручную)"""
    create_application_with_co_borrower(driver, manager)


def test_create_application_new_passport(driver, manager):
    """Заявка «Новая» без созаёмщика (Паспорт)"""
    create_application_new_passport(driver, manager)


def test_create_application_new_passport_with_co_borrower(driver, manager):
    """Заявка «Новая» с созаёмщиком (Паспорт)"""
    create_application_new_passport(driver, manager, with_co_borrower=True)


def test_create_application_new_residence_permit(driver, manager):
    """Заявка «Новая» без созаёмщика (ВНЖ)"""
    create_application_new_residence_permit(driver, manager)


def test_create_application_new_residence_permit_with_co_borrower(driver, manager):
    """Заявка «Новая» с созаёмщиком (ВНЖ)"""
    create_application_new_residence_permit(driver, manager, with_co_borrower=True)


def test_create_application_autocredit(driver, manager):
    """Заявка «Автокредит»: заёмщик + авто + 6 фото + продавец (первоначальный взнос)"""
    create_application_autocredit(driver, manager)


def test_create_application_autocredit_passport(driver, manager):
    """Заявка «Автокредит» (Паспорт)"""
    create_application_autocredit_passport(driver, manager)


def test_create_application_autocredit_residence_permit(driver, manager):
    """Заявка «Автокредит» (ВНЖ)"""
    create_application_autocredit_residence_permit(driver, manager)


@pytest.mark.fields(*TRANSH_ENV_FIELDS)
def test_create_application_transh(transh_fixture, driver, manager):
    """Заявка «Транш»: ИИН/VIN/ГРНЗ/номер техпаспорта — из активной кредитной линии (задать в админке)"""
    create_application_transh(driver, manager, transh_fixture)


@pytest.mark.fields(*TRANSH_ENV_FIELDS)
def test_create_application_transh_passport(transh_fixture, driver, manager):
    """Заявка «Транш» (Паспорт)"""
    create_application_transh_passport(driver, manager, transh_fixture)


@pytest.mark.fields(*TRANSH_ENV_FIELDS)
def test_create_application_transh_residence_permit(transh_fixture, driver, manager):
    """Заявка «Транш» (ВНЖ)"""
    create_application_transh_residence_permit(driver, manager, transh_fixture)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance(refinance_fixture, driver, manager):
    """Заявка «Рефинансирование»: ИИН/VIN/ГРНЗ/номер техпаспорта реального клиента (задать в админке)"""
    create_application_refinance(driver, manager, refinance_fixture)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_with_co_borrower(refinance_fixture, driver, manager):
    """Заявка «Рефинансирование» с созаёмщиком (удостоверение личности, добавлен вручную)"""
    create_application_refinance_with_co_borrower(driver, manager, refinance_fixture)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_residence_permit(refinance_fixture, driver, manager):
    """Заявка «Рефинансирование», тип документа заёмщика — «Вид на жительство» (доп. поле «Страна»)"""
    create_application_refinance_residence_permit(driver, manager, refinance_fixture)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_passport(refinance_fixture, driver, manager):
    """Заявка «Рефинансирование», тип документа заёмщика — «Паспорт РК» (номер документа: буква + 8 цифр)"""
    create_application_refinance_passport(driver, manager, refinance_fixture)
