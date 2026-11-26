import pytest

from projects.kz import PROJECT

from . import factories


@pytest.fixture
def project():
    return PROJECT


@pytest.fixture
def driver(driver):
    # Без неявного ожидания: иначе каждая проверка «элемента нет» (модалка оценки,
    # закрытие справочника/экрана фото, выбор экрана входа) стоит 5 с впустую.
    # Все ожидания в tests/kz — явные (WebDriverWait).
    driver.implicitly_wait(0)
    return driver


@pytest.fixture
def transh_fixture():
    """Данные кредитной линии для теста «Транш» (см. test_application.py).

    Отдельная fixture, а не проверка внутри теста: если данных нет, pytest.skip()
    срабатывает здесь, ДО создания fixture `driver` — не тратим время на подъём
    Appium-сессии и установку приложения ради заведомого пропуска.
    """
    fixture, missing = factories.transh_fixture_from_env()
    if fixture is None:
        pytest.skip("Нет данных кредитной линии для «Транш» — заполните в админке: " + ", ".join(missing))
    return fixture


@pytest.fixture
def refinance_fixture():
    """Данные клиента/авто для теста «Рефинансирование» (см. test_application.py) — та же
    логика раннего skip, что и у transh_fixture, до подъёма Appium-сессии."""
    fixture, missing = factories.refinance_fixture_from_env()
    if fixture is None:
        pytest.skip("Нет данных для «Рефинансирование» — заполните в админке: " + ", ".join(missing))
    return fixture
