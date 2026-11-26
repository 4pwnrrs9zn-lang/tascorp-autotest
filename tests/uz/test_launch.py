from .scenarios import app_opens_first_screen


def test_app_opens_first_screen(driver, project):
    """Запуск приложения: открывается стартовый экран с кнопкой «Kirish»"""
    app_opens_first_screen(driver, project)
