from .scenarios import manager_login


def test_manager_login(driver, manager):
    """Авторизация: менеджер входит по логину/паролю и создаёт код входа"""
    manager_login(driver, manager)
