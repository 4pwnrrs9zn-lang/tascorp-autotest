"""Описание тестируемого iOS-приложения: одна запись на сборку (страну).

Только техданные для сессии Appium (XCUITest): какое .app ставить, bundle id,
под каким менеджером входить. Локаторы, сценарии и данные — в tests/<key>/.
"""
import os
from dataclasses import dataclass
from pathlib import Path

IOS_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_dotenv(path):
    """Логины/пароли тестовых пользователей — в .env в корне репозитория (в git не попадает,
    образец — .env.example). Переменные окружения, заданные явно, важнее файла."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(IOS_ROOT.parent / ".env")


@dataclass(frozen=True)
class User:
    login: str
    password: str
    pin: str
    role: str


@dataclass(frozen=True)
class Project:
    key: str            # папка в tests/ и apps/, ключ в админке: "kz"
    title: str          # человекочитаемое название для админки
    bundle_id: str      # CFBundleIdentifier приложения
    app_env: str        # переменная окружения с путём к .app (переопределить в CI)
    app_filename: str   # имя .app по умолчанию внутри apps/<key>/ (собирает scripts/build_app.sh)
    manager: User
    # Не удалять приложение между сессиями (вход и язык сохраняются).
    # Для тестов, которым нужно «чистое» приложение, — маркер fresh_app (см. conftest).
    no_reset: bool = False

    @property
    def app_path(self):
        return os.getenv(self.app_env, str(IOS_ROOT / "apps" / self.key / self.app_filename))
