from .scenarios import switch_language_to_russian


def test_switch_language_to_russian(driver, manager):
    """Настройки: меню → «Sozlamalar» → «Til» → выбран русский язык"""
    switch_language_to_russian(driver, manager)
