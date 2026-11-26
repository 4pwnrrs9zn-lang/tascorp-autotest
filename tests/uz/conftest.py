import pytest

from projects.uz import PROJECT


@pytest.fixture
def project():
    return PROJECT
