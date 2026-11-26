import pytest

from . import factories

from projects.kz import PROJECT


@pytest.fixture
def project():
    return PROJECT


@pytest.fixture
def driver(driver):
    # Все ожидания в tests/kz — явные (WebDriverWait)
    driver.implicitly_wait(0)
    return driver


@pytest.fixture
def transh_fixture():
    """Данные кредитной линии для «Транш» (поля в админке). Нет данных — пропуск ещё до
    подъёма сессии Appium."""
    fixture, missing = factories.transh_fixture_from_env()
    if fixture is None:
        pytest.skip("Нет данных кредитной линии для «Транш» — заполните в админке: " + ", ".join(missing))
    return fixture


@pytest.fixture
def refinance_fixture():
    """Данные клиента/авто для внутреннего и внешнего рефинансирования (поля в админке) — тот же ранний пропуск,
    что у transh_fixture."""
    fixture, missing = factories.refinance_fixture_from_env()
    if fixture is None:
        pytest.skip("Нет данных для рефинансирования — заполните в админке: " + ", ".join(missing))
    return fixture

