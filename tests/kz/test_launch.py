import pytest

from .scenarios import app_opens_first_screen


@pytest.mark.fresh_app
def test_app_activation(driver, project):
    """Активация приложения: тест открывает приложение"""
    app_opens_first_screen(driver, project)
