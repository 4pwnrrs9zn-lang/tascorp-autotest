from .scenarios import (
    create_application_basic,
    create_application_with_extra_photo,
    create_application_with_extra_photo_and_co_borrower,
)


def test_create_application_basic(driver, manager):
    """Заявка «Новая»: заёмщик + авто + 6 фото + комментарий (без доп. фото и созаёмщика)"""
    create_application_basic(driver, manager)


def test_create_application_with_extra_photo(driver, manager):
    """Заявка «Новая» с дополнительным фото авто"""
    create_application_with_extra_photo(driver, manager)


def test_create_application_with_extra_photo_and_co_borrower(driver, manager):
    """Заявка «Новая» с дополнительным фото и созаёмщиком (ID card)"""
    create_application_with_extra_photo_and_co_borrower(driver, manager)
