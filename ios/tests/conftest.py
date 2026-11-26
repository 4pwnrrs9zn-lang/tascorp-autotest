import os
import signal
import subprocess
import time
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.ios import XCUITestOptions

IOS_ROOT = Path(__file__).resolve().parent.parent
# Отдельный Appium-сервер для iOS (порт 4724, драйвер xcuitest в ~/.appium-ios) — scripts/appium.sh
APPIUM_URL = os.getenv("IOS_APPIUM_URL", "http://127.0.0.1:4724")
DEVICE_NAME = os.getenv("IOS_DEVICE_NAME", "Autotest iPhone 15")
PLATFORM_VERSION = os.getenv("IOS_PLATFORM_VERSION", "17.2")
DEVELOPER_DIR = os.getenv("DEVELOPER_DIR", "/Applications/Xcode.app/Contents/Developer")
# Порт на Mac для живой трансляции экрана в админке (тот же, что у Android: за раз идёт одна платформа)
MJPEG_PORT = int(os.getenv("MJPEG_PORT", "9100"))
# Тестовая камера: у Simulator нет камеры (см. tools/test_camera/TasTestCamera.m)
TEST_CAMERA = IOS_ROOT / "tools" / "test_camera" / "TasTestCamera.dylib"
# Файл-указатель «следующий снимок — из этого файла» (пишет Camera.take_photo, читает камера)
TEST_CAMERA_NEXT = Path(os.environ.setdefault(
    "TAS_TEST_CAMERA_NEXT", f"/tmp/tascorp-ios-test-camera-next-{os.getpid()}"))
FAILED_SCREENSHOTS = Path(os.getenv("ADMIN_RUN_DIR", IOS_ROOT)) / "screenshots"
# Видео — в ту же папку: админка уже раздаёт файлы из reports/<запуск>/screenshots/
VIDEOS = FAILED_SCREENSHOTS
VIDEO_TAIL = 3  # с — запись после конца теста, см. screen_recording


def _simctl(*args, timeout=60):
    return subprocess.run(["xcrun", "simctl", *args], check=False, timeout=timeout, capture_output=True,
                          text=True, env={**os.environ, "DEVELOPER_DIR": DEVELOPER_DIR})


@pytest.fixture(scope="session", autouse=True)
def simulator():
    """Simulator загружен, раскладка — только английская.

    С русской раскладкой XCUITest вводил в поле пароля половину символов, и вход не проходил.
    Сам Simulator создаёт scripts/sim_setup.sh.
    """
    if DEVICE_NAME not in _simctl("list", "devices", "available").stdout:
        pytest.exit(f"Нет Simulator «{DEVICE_NAME}» — запустите ios/scripts/sim_setup.sh", returncode=4)
    _simctl("boot", DEVICE_NAME)  # уже загружен — просто ошибка, не страшно
    _simctl("bootstatus", DEVICE_NAME, "-b", timeout=300)
    _simctl("spawn", DEVICE_NAME, "defaults", "write", ".GlobalPreferences",
            "AppleKeyboards", "-array", "en_US@sw=QWERTY;hw=Automatic")


@pytest.fixture(autouse=True)
def screen_recording(request, simulator):
    """Метка record_video: запись экрана Simulator (simctl recordVideo, h264) на весь тест —
    с подъёма сессии до её закрытия. Имя файла уходит в отчёт (user_properties «video»)."""
    if not request.node.get_closest_marker("record_video"):
        yield
        return
    VIDEOS.mkdir(parents=True, exist_ok=True)
    path = VIDEOS / f"{request.node.name}.mp4"
    proc = subprocess.Popen(
        ["xcrun", "simctl", "io", DEVICE_NAME, "recordVideo", "--codec=h264", "--force", str(path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env={**os.environ, "DEVELOPER_DIR": DEVELOPER_DIR})
    yield
    # Последние ~2 с simctl при остановке теряет (в ролике не было финального экрана) — ждём
    time.sleep(VIDEO_TAIL)
    # Ctrl+C — штатная остановка: simctl дописывает файл и закрывает его
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
    if path.exists() and path.stat().st_size:
        request.node.user_properties.append(("video", path.name))


@pytest.fixture
def manager(project):
    """Менеджер, под которым проходят сценарии, — свой для каждой сборки (project).
    Логин и пароль — из .env (см. .env.example)."""
    user = project.manager
    if not (user.login and user.password):
        pytest.fail(f"Не заданы логин/пароль менеджера «{project.title}» — заполните .env по образцу .env.example")
    return user


@pytest.fixture
def driver(project, request):
    """Сессия XCUITest под сборку (project приходит из tests/<key>/conftest.py)."""
    app = Path(project.app_path)
    if not app.exists():
        pytest.skip(f"Сборка «{project.title}» не найдена: {app}. Соберите её: ios/scripts/build_app.sh")
    if not TEST_CAMERA.exists():
        pytest.skip(f"Не собрана тестовая камера: {TEST_CAMERA}. Соберите: ios/tools/test_camera/build.sh")

    # fresh_app — удаляем приложение, Appium поставит его заново (чистые данные).
    # Не full_reset: на Simulator он стирает весь симулятор вместе с настройкой раскладки
    if request.node.get_closest_marker("fresh_app"):
        _simctl("uninstall", DEVICE_NAME, project.bundle_id)

    options = XCUITestOptions()
    options.device_name = DEVICE_NAME
    options.platform_version = PLATFORM_VERSION
    options.app = str(app)
    options.bundle_id = project.bundle_id
    options.no_reset = True
    options.new_command_timeout = 120
    options.auto_accept_alerts = True  # системные запросы разрешений (уведомления, камера)
    options.set_capability("appium:forceAppLaunch", True)  # каждый тест — с перезапуска приложения
    options.set_capability("appium:processArguments", {"env": {
        "DYLD_INSERT_LIBRARIES": str(TEST_CAMERA),
        # Подпись на снимках тестовой камеры — видно, каким тестом сделано фото
        "TAS_TEST_CAMERA_LABEL": request.node.name,
        "TAS_TEST_CAMERA_NEXT": str(TEST_CAMERA_NEXT),
    }})
    options.set_capability("appium:wdaLaunchTimeout", 240000)
    options.set_capability("appium:wdaConnectionTimeout", 240000)
    options.set_capability("appium:simulatorStartupTimeout", 300000)
    options.set_capability("appium:mjpegServerPort", MJPEG_PORT)
    options.set_capability("appium:reduceMotion", True)
    options.set_capability("appium:connectHardwareKeyboard", False)
    # Скорость: не ждать «простоя» приложения перед каждым действием — в React Native
    # с анимациями это ~0,5 с на каждый клик. Все ожидания в тестах — явные (WebDriverWait)
    options.set_capability("appium:waitForQuiescence", False)

    drv = webdriver.Remote(APPIUM_URL, options=options)
    drv.update_settings({
        "mjpegServerFramerate": 15, "mjpegScalingFactor": 40,
        # По умолчанию WDA после действий ждёт окончания анимаций (до 2 с) — не ждём
        "animationCoolOffTimeout": 0,
        # Скорость ввода текста (нажатий в минуту, по умолчанию 60): поля без масок,
        # символы не теряются — проверено на полном прогоне заявки
        "maxTypingFrequency": 300,
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
