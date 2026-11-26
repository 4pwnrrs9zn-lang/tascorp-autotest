import pytest

from .scenarios import switch_language_to_russian


@pytest.mark.fresh_app
def test_switch_language_to_russian(driver, manager):
    """Настройки: меню → «Баптаулар» → «Тіл» → выбран русский язык"""
    switch_language_to_russian(driver, manager)
