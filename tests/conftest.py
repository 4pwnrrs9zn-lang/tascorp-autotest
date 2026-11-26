import os
import re
import subprocess
import time
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options

ROOT = Path(__file__).resolve().parent.parent
APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")
# Порт на Mac, куда пробрасывается живая трансляция экрана (MJPEG) для админки
MJPEG_PORT = int(os.getenv("MJPEG_PORT", "9100"))
# Куда класть скриншоты упавших тестов: папка запуска из админки или screenshots/
FAILED_SCREENSHOTS = Path(os.getenv("ADMIN_RUN_DIR", ROOT)) / "screenshots"

ADB = Path(os.getenv("ANDROID_HOME", Path.home() / "Library/Android/sdk")) / "platform-tools/adb"


@pytest.fixture(scope="session", autouse=True)
def no_soft_keyboard():
    """Не показывать экранную клавиатуру (у эмулятора есть аппаратная).

    Экранная клавиатура перекрывает поля, а свайп по ней Gboard принимает за ввод текста.
    """
    subprocess.run([str(ADB), "shell", "settings", "put", "secure", "show_ime_with_hard_keyboard", "0"],
                   check=False, timeout=30)


@pytest.fixture(scope="session", autouse=True)
def android_test_camera():
    """Тестовая камера вместо системной, если она стоит на эмуляторе (tools/android_test_camera).

    Системная камера эмулятора снимает виртуальную сцену — такие снимки приложение
    иногда не принимает, и своё фото («Клиент на фоне авто») ей не подставить. Тестовая
    камера отвечает на тот же intent, но только системной (Android 11+), поэтому
    системную на время сессии отключаем — и включаем обратно в конце."""
    installed = "kz.tascorp.testcamera" in _adb("pm", "list", "packages", "-s", "kz.tascorp.testcamera")
    if not installed or os.getenv("TAS_USE_SYSTEM_CAMERA") == "1":  # принудительно — системной
        _adb("pm", "enable", "com.android.camera2")
        if installed:  # обе камеры сразу — Android спрашивает, какой снимать
            _adb("pm", "disable-user", "--user", "0", "kz.tascorp.testcamera")
        yield
        if installed:
            _adb("pm", "enable", "kz.tascorp.testcamera")
        return
    _adb("pm", "disable-user", "--user", "0", "com.android.camera2")
    # Первый запуск создаёт её папку, куда тест кладёт фото для следующего снимка
    _adb("am", "start", "-W", "-n", "kz.tascorp.testcamera/.CaptureActivity")
    os.environ["TAS_ANDROID_TEST_CAMERA"] = "1"
    yield
    os.environ.pop("TAS_ANDROID_TEST_CAMERA", None)
    _adb("pm", "enable", "com.android.camera2")


@pytest.fixture
def manager(project):
    """Менеджер, под которым проходят сценарии, — свой для каждой сборки (project).
    Логин и пароль — из .env (см. .env.example)."""
    user = project.manager
    if not (user.login and user.password):
        pytest.fail(f"Не заданы логин/пароль менеджера «{project.title}» — заполните .env по образцу .env.example")
    return user


def _adb(*args, timeout=30):
    return subprocess.run([str(ADB), "shell", *args], check=False, timeout=timeout,
                          capture_output=True, text=True).stdout


def _grant_runtime_permissions(package):
    """Appium выдаёт разрешения (autoGrantPermissions) только при установке APK — при
    noReset их нет после pm clear, и системный диалог перекрывает экран приложения."""
    perms = set(re.findall(r"(android\.permission\.\w+): granted=false", _adb("dumpsys", "package", package)))
    for perm in perms:
        _adb("pm", "grant", package, perm)


def _fresh_app(package, activity):
    """Чистое приложение (как после установки), но без краша холодного старта.

    Первый запуск с пустыми данными под Appium роняет KZ-сборку (гонка в Yandex
    MapKit), а без Appium — нет. Поэтому: стираем данные, возвращаем разрешения
    (pm clear их отзывает), один раз запускаем приложение голым am start, чтобы оно
    само создало свои данные, и закрываем. Сессия Appium после этого — тёплый старт.
    """
    _adb("am", "force-stop", package)
    _adb("pm", "clear", package)
    _grant_runtime_permissions(package)
    _adb("am", "start", "-W", "-n", f"{package}/{activity}", timeout=60)
    time.sleep(8)
    _adb("am", "force-stop", package)


@pytest.fixture
def driver(project, request):
    """Сессия Appium под конкретную сборку (project приходит из tests/<uz|kz>/conftest.py)."""
    apk = Path(project.apk_path)
    if not apk.exists():
        pytest.skip(f"APK для проекта «{project.title}» не найден: {apk}. Положите файл и повторите запуск.")

    if project.no_reset and request.node.get_closest_marker("fresh_app"):
        _fresh_app(project.package, project.activity)
    else:
        # При noReset прошлая сессия могла оборваться посреди сценария (например, на
        # экране фото) — без force-stop Appium развернёт приложение на том же месте.
        _adb("am", "force-stop", project.package)
        if project.no_reset:
            _grant_runtime_permissions(project.package)

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = os.getenv("DEVICE_NAME", "Android Emulator")
    options.app = str(apk)
    options.app_package = project.package
    options.app_activity = project.activity
    options.auto_grant_permissions = True
    options.no_reset = project.no_reset
    options.new_command_timeout = 120
    # APK ~220 MB — установка может занять время
    options.set_capability("appium:uiautomator2ServerInstallTimeout", 120000)
    options.set_capability("appium:androidInstallTimeout", 300000)
    options.set_capability("appium:uiautomator2ServerLaunchTimeout", 90000)
    options.set_capability("appium:adbExecTimeout", 60000)
    # Зависший UiAutomator2 (бывает при нехватке памяти на хосте) по умолчанию держит
    # команду 240 с — падаем быстрее, а не висим по 4 минуты на одном поиске.
    options.set_capability("appium:uiautomator2ServerReadTimeout", 60000)
    options.set_capability("appium:mjpegServerPort", MJPEG_PORT)
    # Скорость: без системных анимаций на время сессии
    options.set_capability("appium:disableWindowAnimation", True)

    drv = webdriver.Remote(APPIUM_URL, options=options)
    drv.update_settings({
        "mjpegServerFramerate": 15,
        "mjpegScalingFactor": 40,
        # По умолчанию UiAutomator2 перед каждым действием ждёт «простоя» UI до 10 с —
        # в React Native с анимациями это главная причина медленных тестов
        "waitForIdleTimeout": 0,
    })
    drv.implicitly_wait(5)
    yield drv
    drv.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    drv = item.funcargs.get("driver") if hasattr(item, "funcargs") else None
    if report.when == "call" and report.failed and drv is not None:
        FAILED_SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        path = FAILED_SCREENSHOTS / f"{item.name}_failed.png"
        try:
            drv.save_screenshot(str(path))
            report.user_properties.append(("screenshot", path.name))
        except Exception:  # noqa: BLE001 — сессия могла уже умереть
            pass
