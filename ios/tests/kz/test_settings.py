from .scenarios import switch_language_to_russian


def test_switch_language_to_russian(driver, manager):
    """Смена языка на русский: меню → Баптаулар → Тіл → Орысша"""
    switch_language_to_russian(driver, manager)
