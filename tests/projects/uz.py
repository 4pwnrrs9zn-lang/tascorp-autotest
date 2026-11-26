import os

from projects.base import Project, User

PROJECT = Project(
    key="uz",
    title="TasCorp UZ",
    package="kz.tasgroup.tascorp.uz",
    activity="kz.tasgroup.tascorp.uz.MainActivity",
    apk_env="UZ_APK_PATH",
    apk_filename="TasCorpUzTest.apk",
    manager=User(
        login=os.getenv("UZ_MANAGER_LOGIN", ""),
        password=os.getenv("UZ_MANAGER_PASSWORD", ""),
        pin=os.getenv("UZ_MANAGER_PIN", "2222"),
        # Роль сразу после входа, до переключения языка (тест test_auth это делает первым
        # действием) — приложение по умолчанию на узбекском, отсюда латинское "Menejer"
        role="Menejer",
    ),
)
