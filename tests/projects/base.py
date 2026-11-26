"""Описание тестируемого приложения: одна запись на страну/сборку.

Только техданные для запуска сессии Appium: какой APK ставить, package/activity,
под каким менеджером входить. Локаторы, экранные тексты, сценарии и тестовые данные —
не сюда: они целиком свои у каждой сборки, в tests/<uz|kz>/ (pages/, flows.py,
scenarios.py, factories.py) — один проект не должен зависеть от кода другого.
Новая сборка добавляется файлом в этой папке plus своей папкой tests/<key>/.
"""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


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


_load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class User:
    login: str
    password: str
    pin: str
    role: str


@dataclass(frozen=True)
class Project:
    key: str            # папка в tests/ и apks/, ключ в админке: "uz", "kz"
    title: str          # человекочитаемое название для админки: "TasCorp UZ"
    package: str        # Android package приложения
    activity: str        # стартовая activity
    apk_env: str         # переменная окружения с путём к APK (переопределить в CI)
    apk_filename: str    # имя файла по умолчанию внутри apks/<key>/
    manager: User        # менеджер, под которым проходят сценарии создания заявки
    # Не чистить данные приложения между сессиями (вход и язык сохраняются).
    # Для тестов, которым нужно «чистое» приложение, — маркер fresh_app (см. conftest).
    no_reset: bool = False

    @property
    def apk_path(self):
        return os.getenv(self.apk_env, str(ROOT / "apks" / self.key / self.apk_filename))
