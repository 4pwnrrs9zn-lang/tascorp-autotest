import os

from projects.base import Project, User

# bundle id / версия — из apps/kz/TasCorp.app/Info.plist: Enterprise-IPA со стенда
# (https://tascorp-admincp.tascredit.kz/res/test.html), перепакованный под Simulator
# скриптом scripts/build_app.sh (проверено 2026-10-08: 1.2 (96))
PROJECT = Project(
    key="kz",
    title="TasCorp KZ",
    bundle_id="kz.tasgroup.tascorp.enterprise",
    app_env="KZ_IOS_APP_PATH",
    app_filename="TasCorp.app",
    manager=User(
        login=os.getenv("KZ_MANAGER_LOGIN", ""),
        password=os.getenv("KZ_MANAGER_PASSWORD", ""),
        pin=os.getenv("KZ_MANAGER_PIN", "2222"),
        role="Менеджер",
    ),
    no_reset=True,
)
