import pytest

from .factories import LEGAL_ENTITY_ENV_FIELDS, REFINANCE_ENV_FIELDS, TRANSH_ENV_FIELDS
from .pages.applications_page import ApplicationsPage
from .scenarios import (create_application_autocredit, create_application_autocredit_passport,
                        create_application_autocredit_residence_permit, create_application_basic,
                        create_application_legal_entity, create_application_legal_entity_autocredit,
                        create_application_legal_entity_refinance, create_application_legal_entity_transh,
                        create_application_new_passport,
                        create_application_new_residence_permit,
                        create_application_refinance, create_application_refinance_passport,
                        create_application_refinance_residence_permit,
                        create_application_refinance_with_co_borrower, create_application_transh,
                        create_application_transh_passport, create_application_transh_residence_permit,
                        create_application_with_co_borrower)


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


@pytest.mark.record_video
@pytest.mark.fields(*LEGAL_ENTITY_ENV_FIELDS)
def test_create_application_legal_entity(driver, manager):
    """Заявка «Новая» для юр. лица: субъект (заёмщик) + данные компании + авто + фото → заявка отправлена"""
    create_application_legal_entity(driver, manager)


@pytest.mark.record_video
@pytest.mark.fields(*LEGAL_ENTITY_ENV_FIELDS)
def test_create_application_legal_entity_autocredit(driver, manager):
    """Заявка «Автокредит» для юр. лица: субъект (заёмщик) + компания + авто + продавец → заявка отправлена"""
    create_application_legal_entity_autocredit(driver, manager)


@pytest.mark.record_video
@pytest.mark.fields(*LEGAL_ENTITY_ENV_FIELDS, *TRANSH_ENV_FIELDS)
def test_create_application_legal_entity_transh(transh_fixture, driver, manager):
    """Заявка «Транш» для юр. лица: ИИН субъекта и авто — из кредитной линии (задать в админке)"""
    create_application_legal_entity_transh(driver, manager, transh_fixture)


@pytest.mark.record_video
@pytest.mark.fields(*LEGAL_ENTITY_ENV_FIELDS, *REFINANCE_ENV_FIELDS)
def test_create_application_legal_entity_refinance_internal(refinance_fixture, driver, manager):
    """Заявка «Внутреннее рефинансирование» для юр. лица: ИИН субъекта и авто — реального клиента"""
    create_application_legal_entity_refinance(driver, manager, refinance_fixture,
                                              ApplicationsPage.TYPE_REFINANCE_INTERNAL)


@pytest.mark.record_video
@pytest.mark.fields(*LEGAL_ENTITY_ENV_FIELDS, *REFINANCE_ENV_FIELDS)
def test_create_application_legal_entity_refinance_external(refinance_fixture, driver, manager):
    """Заявка «Внешнее рефинансирование» для юр. лица: ИИН субъекта и авто — реального клиента"""
    create_application_legal_entity_refinance(driver, manager, refinance_fixture,
                                              ApplicationsPage.TYPE_REFINANCE_EXTERNAL)


def test_create_application_autocredit(driver, manager):
    """Заявка «Автокредит»: заёмщик + авто + 6 фото + владелец авто (продавец, физ. лицо)"""
    create_application_autocredit(driver, manager)


def test_create_application_autocredit_passport(driver, manager):
    """Заявка «Автокредит» (Паспорт)"""
    create_application_autocredit_passport(driver, manager)


def test_create_application_autocredit_residence_permit(driver, manager):
    """Заявка «Автокредит» (ВНЖ)"""
    create_application_autocredit_residence_permit(driver, manager)


@pytest.mark.fields(*TRANSH_ENV_FIELDS)
def test_create_application_transh(transh_fixture, driver, manager):
    """Заявка «Транш» без созаёмщика (ИИН/VIN/ГРНЗ/техпаспорт — от кредитной линии, поля в админке)"""
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
def test_create_application_refinance_internal(refinance_fixture, driver, manager):
    """Заявка «Внутреннее рефинансирование»: ИИН/VIN/ГРНЗ/номер техпаспорта реального клиента (задать в админке)"""
    create_application_refinance(driver, manager, refinance_fixture, ApplicationsPage.TYPE_REFINANCE_INTERNAL)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_internal_with_co_borrower(refinance_fixture, driver, manager):
    """Заявка «Внутреннее рефинансирование» с созаёмщиком (удостоверение личности, добавлен вручную)"""
    create_application_refinance_with_co_borrower(driver, manager, refinance_fixture, ApplicationsPage.TYPE_REFINANCE_INTERNAL)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_internal_residence_permit(refinance_fixture, driver, manager):
    """Заявка «Внутреннее рефинансирование», тип документа заёмщика — «Вид на жительство» (доп. поле «Страна»)"""
    create_application_refinance_residence_permit(driver, manager, refinance_fixture, ApplicationsPage.TYPE_REFINANCE_INTERNAL)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_internal_passport(refinance_fixture, driver, manager):
    """Заявка «Внутреннее рефинансирование», тип документа заёмщика — «Паспорт РК» (номер документа: буква + 8 цифр)"""
    create_application_refinance_passport(driver, manager, refinance_fixture, ApplicationsPage.TYPE_REFINANCE_INTERNAL)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_external(refinance_fixture, driver, manager):
    """Заявка «Внешнее рефинансирование»: ИИН/VIN/ГРНЗ/номер техпаспорта реального клиента (задать в админке)"""
    create_application_refinance(driver, manager, refinance_fixture, ApplicationsPage.TYPE_REFINANCE_EXTERNAL)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_external_with_co_borrower(refinance_fixture, driver, manager):
    """Заявка «Внешнее рефинансирование» с созаёмщиком (удостоверение личности, добавлен вручную)"""
    create_application_refinance_with_co_borrower(driver, manager, refinance_fixture, ApplicationsPage.TYPE_REFINANCE_EXTERNAL)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_external_residence_permit(refinance_fixture, driver, manager):
    """Заявка «Внешнее рефинансирование», тип документа заёмщика — «Вид на жительство» (доп. поле «Страна»)"""
    create_application_refinance_residence_permit(driver, manager, refinance_fixture, ApplicationsPage.TYPE_REFINANCE_EXTERNAL)


@pytest.mark.fields(*REFINANCE_ENV_FIELDS)
def test_create_application_refinance_external_passport(refinance_fixture, driver, manager):
    """Заявка «Внешнее рефинансирование», тип документа заёмщика — «Паспорт РК» (номер документа: буква + 8 цифр)"""
    create_application_refinance_passport(driver, manager, refinance_fixture, ApplicationsPage.TYPE_REFINANCE_EXTERNAL)
