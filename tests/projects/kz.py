import os

from projects.base import Project, User

# package/activity — из aapt dump badging apks/kz/app-release.apk (проверено 2026-09-25)
PROJECT = Project(
    key="kz",
    title="TasCorp KZ",
    package="com.tascorp.second",
    activity="com.tascorp.second.MainActivity",
    apk_env="KZ_APK_PATH",
    apk_filename="app-release.apk",
    manager=User(
        login=os.getenv("KZ_MANAGER_LOGIN", ""),
        password=os.getenv("KZ_MANAGER_PASSWORD", ""),
        pin=os.getenv("KZ_MANAGER_PIN", "2222"),
        role="Менеджер",  # нужно перепроверить вживую под новым логином
    ),
    # Холодный старт под Appium роняет KZ-сборку (гонка setLocale/initialize в Yandex
    # MapKit), поэтому данные приложения между сессиями не чистим — см. conftest.driver.
    no_reset=True,
)
