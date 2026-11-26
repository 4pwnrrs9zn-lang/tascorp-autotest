"""Локальная админка автотестов: список кейсов, выбор чекбоксами, запуск выбранных."""
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
PYTHON = sys.executable
ADB = Path(os.getenv("ANDROID_HOME", Path.home() / "Library/Android/sdk")) / "platform-tools/adb"
APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")
MJPEG_PORT = int(os.getenv("MJPEG_PORT", "9100"))  # должен совпадать с tests/conftest.py и ios/tests/conftest.py
IOS_APPIUM_URL = os.getenv("IOS_APPIUM_URL", "http://127.0.0.1:4724")
DEVELOPER_DIR = os.getenv("DEVELOPER_DIR", "/Applications/Xcode.app/Contents/Developer")
# Платформы — полностью раздельные проекты автотестов: свой каталог, свой pytest.ini, свой
# Appium. prefix — начало id кейса (nodeid от корня проекта), по нему видно платформу кейса.
PLATFORMS = {
    "android": {"title": "Android", "cwd": ROOT, "prefix": "", "appium_url": APPIUM_URL},
    "ios": {"title": "iOS", "cwd": ROOT / "ios", "prefix": "ios/", "appium_url": IOS_APPIUM_URL},
}
PLUGIN = "admin.pytest_admin_plugin"
# Названия кейсов и папки, заданные в админке. Код тестов не меняется: если своего
# названия нет — показывается исходное (из описания теста).
CATALOG = Path(os.getenv("ADMIN_CATALOG", ROOT / "admin" / "catalog.json"))
NAME_MAX = 120

app = Flask(__name__, static_folder="static", static_url_path="/static")

_lock = threading.Lock()
_catalog_lock = threading.Lock()
_current = {"id": None, "proc": None}


def load_catalog():
    data = _read_json(CATALOG, {})
    return {
        "titles": data.get("titles", {}),
        "folders": data.get("folders", []),
        "placement": data.get("placement", {}),
    }


def save_catalog(catalog):
    tmp = CATALOG.with_suffix(".tmp")
    tmp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CATALOG)  # атомарно: при сбое файл не останется наполовину записанным


def platform_of(nodeid):
    """ios/tests/kz/... -> "ios", tests/kz/... -> "android"."""
    return "ios" if nodeid.startswith(PLATFORMS["ios"]["prefix"]) else "android"


def project_of(nodeid):
    """tests/kz/test_x.py::test_y -> "kz", ios/tests/kz/test_x.py::test_y -> "ios:kz".

    Ключ проекта iOS — с префиксом платформы: у вкладок и папок iOS и Android свои
    пространства (а ключи Android остаются прежними — сохранённые папки не теряются).
    """
    platform = platform_of(nodeid)
    rel = nodeid[len(PLATFORMS[platform]["prefix"]):]
    parts = Path(rel.split("::", 1)[0]).parts
    key = parts[1] if len(parts) >= 3 and parts[0] == "tests" else "shared"
    return key if platform == "android" else f"{platform}:{key}"


def clean_name(value):
    name = " ".join(str(value or "").split())
    if not name:
        raise ValueError("Название не может быть пустым")
    if len(name) > NAME_MAX:
        raise ValueError(f"Название длиннее {NAME_MAX} символов")
    return name


def apply_catalog(tests, catalog):
    folders = {f["id"] for f in catalog["folders"]}
    for t in tests:
        t["original_title"] = t["title"]
        t["title"] = catalog["titles"].get(t["nodeid"], t["title"])
        folder = catalog["placement"].get(t["nodeid"])
        t["folder"] = folder if folder in folders else None
    return tests


def _env(**extra):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT), env.get("PYTHONPATH")]))
    env["PYTHONUNBUFFERED"] = "1"
    env.update(extra)
    return env


def _collect_platform(platform):
    conf = PLATFORMS[platform]
    out = REPORTS / f".collect-{platform}.json"
    out.unlink(missing_ok=True)
    proc = subprocess.run(
        [PYTHON, "-m", "pytest", "--collect-only", "-q", "-p", PLUGIN],
        cwd=conf["cwd"], env=_env(ADMIN_COLLECT_OUT=str(out), ADMIN_NODE_PREFIX=conf["prefix"]),
        capture_output=True, text=True, timeout=120,
    )
    if not out.exists():
        raise RuntimeError(proc.stdout[-3000:] + proc.stderr[-3000:])
    tests = json.loads(out.read_text(encoding="utf-8"))
    for t in tests:
        t["platform"] = platform
        t["project"] = project_of(t["nodeid"])
    return tests


def collect_tests(errors=None):
    """Кейсы обеих платформ. Если одна платформа не собирается — другая всё равно видна,
    а текст ошибки уходит в errors (показывается в админке)."""
    REPORTS.mkdir(exist_ok=True)
    tests = []
    for platform in PLATFORMS:
        try:
            tests += _collect_platform(platform)
        except Exception as e:  # noqa: BLE001
            if errors is None:
                raise
            errors[platform] = str(e)
    return tests


def _read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def run_summary(run_id):
    run_dir = REPORTS / run_id
    meta = _read_json(run_dir / "meta.json", None)
    if meta is None:
        return None
    results = {nodeid: {"status": "queued"} for nodeid in meta["nodeids"]}
    events = run_dir / "events.jsonl"
    if events.exists():
        for line in events.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            results[ev["nodeid"]] = ev
    if meta["state"] in ("finished", "stopped"):
        for r in results.values():
            if r["status"] in ("queued", "running"):
                r["status"] = "not_run"
    counts = {}
    for r in results.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {**meta, "results": results, "counts": counts}


def _watch(run_id, proc):
    run_dir = REPORTS / run_id
    code = proc.wait()
    meta = _read_json(run_dir / "meta.json", {})
    if meta.get("state") != "stopped":
        meta["state"] = "finished"
    meta["exit_code"] = code
    meta["finished_at"] = time.time()
    (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    with _lock:
        if _current["id"] == run_id:
            _current["proc"] = None


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/management")
def management_page():
    return send_from_directory(app.static_folder, "management.html")


@app.get("/api/tests")
def api_tests():
    errors = {}
    tests = collect_tests(errors)
    if not tests and errors:
        return jsonify({"error": "\n\n".join(f"{PLATFORMS[k]['title']}: {v}" for k, v in errors.items())}), 500
    with _catalog_lock:
        tests = apply_catalog(tests, load_catalog())
    platforms = [{"key": k, "title": v["title"]} for k, v in PLATFORMS.items()]
    return jsonify({"tests": tests, "platforms": platforms, "errors": errors})


@app.get("/api/folders")
def api_folders():
    with _catalog_lock:
        return jsonify(load_catalog()["folders"])


@app.post("/api/folders")
def api_folder_create():
    body = request.get_json(silent=True) or {}
    project = str(body.get("project") or "")
    if not project or "/" in project or project == "all":
        return jsonify({"error": "Папка создаётся внутри вкладки проекта"}), 400
    try:
        name = clean_name(body.get("name"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    with _catalog_lock:
        catalog = load_catalog()
        if any(f["project"] == project and f["name"].lower() == name.lower() for f in catalog["folders"]):
            return jsonify({"error": f"Папка «{name}» уже есть"}), 409
        folder = {"id": "f_" + secrets.token_hex(4), "project": project, "name": name}
        catalog["folders"].append(folder)
        save_catalog(catalog)
    return jsonify(folder)


@app.patch("/api/folders/<folder_id>")
def api_folder_rename(folder_id):
    body = request.get_json(silent=True) or {}
    try:
        name = clean_name(body.get("name"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    with _catalog_lock:
        catalog = load_catalog()
        folder = next((f for f in catalog["folders"] if f["id"] == folder_id), None)
        if folder is None:
            return jsonify({"error": "Папка не найдена"}), 404
        if any(f["id"] != folder_id and f["project"] == folder["project"] and f["name"].lower() == name.lower()
               for f in catalog["folders"]):
            return jsonify({"error": f"Папка «{name}» уже есть"}), 409
        folder["name"] = name
        save_catalog(catalog)
    return jsonify(folder)


@app.delete("/api/folders/<folder_id>")
def api_folder_delete(folder_id):
    """Удаляет только папку: её кейсы переходят в «Без папки»."""
    with _catalog_lock:
        catalog = load_catalog()
        before = len(catalog["folders"])
        catalog["folders"] = [f for f in catalog["folders"] if f["id"] != folder_id]
        if len(catalog["folders"]) == before:
            return jsonify({"error": "Папка не найдена"}), 404
        catalog["placement"] = {k: v for k, v in catalog["placement"].items() if v != folder_id}
        save_catalog(catalog)
    return jsonify({"ok": True})


@app.patch("/api/tests/meta")
def api_test_meta():
    """Своё название кейса (title: пусто/null — вернуть исходное) и/или папка (folder: id или null)."""
    body = request.get_json(silent=True) or {}
    nodeid = str(body.get("nodeid") or "")
    if not nodeid.startswith(("tests/", "ios/tests/")) or "::" not in nodeid or len(nodeid) > 300:
        return jsonify({"error": "Неизвестный кейс"}), 400
    with _catalog_lock:
        catalog = load_catalog()
        if "title" in body:
            title = body["title"]
            if title is None or not str(title).strip():
                catalog["titles"].pop(nodeid, None)
            else:
                try:
                    catalog["titles"][nodeid] = clean_name(title)
                except ValueError as e:
                    return jsonify({"error": str(e)}), 400
        if "folder" in body:
            folder_id = body["folder"]
            if folder_id is None:
                catalog["placement"].pop(nodeid, None)
            else:
                folder = next((f for f in catalog["folders"] if f["id"] == folder_id), None)
                if folder is None:
                    return jsonify({"error": "Папка не найдена"}), 404
                if folder["project"] != project_of(nodeid):
                    return jsonify({"error": "Папка относится к другому проекту"}), 400
                catalog["placement"][nodeid] = folder_id
        save_catalog(catalog)
        return jsonify({
            "nodeid": nodeid,
            "title": catalog["titles"].get(nodeid),
            "folder": catalog["placement"].get(nodeid),
        })


def _appium_ready(url):
    try:
        with urllib.request.urlopen(f"{url}/status", timeout=1.5) as r:
            return json.load(r).get("value", {}).get("ready", False)
    except Exception:  # noqa: BLE001
        return False


def _android_devices():
    try:
        out = subprocess.run([str(ADB), "devices"], capture_output=True, text=True, timeout=5).stdout
        return [l.split("\t")[0] for l in out.splitlines()[1:] if l.endswith("\tdevice")]
    except Exception:  # noqa: BLE001
        return []


def _ios_simulators():
    """Загруженные iOS Simulator (имена)."""
    try:
        out = subprocess.run(["xcrun", "simctl", "list", "devices", "booted", "-j"], capture_output=True,
                             text=True, timeout=5, env={**os.environ, "DEVELOPER_DIR": DEVELOPER_DIR}).stdout
        return [d["name"] for devs in json.loads(out)["devices"].values() for d in devs if d.get("state") == "Booted"]
    except Exception:  # noqa: BLE001
        return []


@app.get("/api/health")
def api_health():
    platforms = {
        "android": {"appium": _appium_ready(APPIUM_URL), "appium_url": APPIUM_URL, "devices": _android_devices()},
        "ios": {"appium": _appium_ready(IOS_APPIUM_URL), "appium_url": IOS_APPIUM_URL, "devices": _ios_simulators()},
    }
    try:
        with socket.create_connection(("127.0.0.1", MJPEG_PORT), timeout=0.5):
            stream = True
    except OSError:
        stream = False
    return jsonify({
        "platforms": platforms,
        "stream": stream, "stream_url": f"http://127.0.0.1:{MJPEG_PORT}/",
    })


@app.post("/api/run")
def api_run():
    body = request.get_json(silent=True) or {}
    nodeids = body.get("nodeids") or []
    extra_env = body.get("env") or {}
    if not nodeids:
        return jsonify({"error": "Не выбран ни один кейс"}), 400
    platforms = {platform_of(n) for n in nodeids}
    if len(platforms) > 1:
        # Одно устройство за раз: на Mac с 8 ГБ эмулятор и Simulator вместе не помещаются
        return jsonify({"error": "За один запуск — кейсы одной платформы (Android или iOS)"}), 400
    platform = platforms.pop()
    conf = PLATFORMS[platform]
    if platform == "android" and not _android_devices():
        # Иначе Appium 20 с ищет устройство и падает длинной трассировкой в каждом кейсе
        return jsonify({"error": "Нет Android-устройства: запустите эмулятор (см. README) и повторите. "
                                 "Перед этим остановите iOS Simulator — вместе они не помещаются в память"}), 400
    all_tests = {t["nodeid"]: t for t in _collect_platform(platform)}
    unknown = [n for n in nodeids if n not in all_tests]
    if unknown:
        return jsonify({"error": f"Неизвестные кейсы: {unknown}"}), 400

    # env принимаем только для полей, которые кейсы реально объявили (pytest.mark.fields) —
    # так с фронтенда нельзя подсунуть произвольную переменную окружения процессу pytest.
    allowed = {f["env"] for n in nodeids for f in all_tests[n].get("fields", [])}
    bad = [k for k in extra_env if k not in allowed]
    if bad:
        return jsonify({"error": f"Недопустимые поля: {bad}"}), 400
    extra_env = {k: str(v) for k, v in extra_env.items() if str(v).strip()}

    with _lock:
        if _current["proc"] is not None and _current["proc"].poll() is None:
            return jsonify({"error": "Уже идёт запуск", "run_id": _current["id"]}), 409

        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = REPORTS / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        meta = {"id": run_id, "nodeids": nodeids, "platform": platform, "state": "running", "started_at": time.time()}
        (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

        log = open(run_dir / "log.txt", "w", encoding="utf-8")
        # pytest платформы запускается из её папки: id кейсов — без префикса платформы
        local_ids = [n[len(conf["prefix"]):] for n in nodeids]
        proc = subprocess.Popen(
            [PYTHON, "-m", "pytest", "-p", PLUGIN, *local_ids],
            cwd=conf["cwd"],
            env=_env(ADMIN_EVENTS_OUT=str(run_dir / "events.jsonl"), ADMIN_RUN_DIR=str(run_dir),
                     ADMIN_NODE_PREFIX=conf["prefix"], **extra_env),
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        _current.update(id=run_id, proc=proc)
    threading.Thread(target=_watch, args=(run_id, proc), daemon=True).start()
    return jsonify({"run_id": run_id})


@app.post("/api/stop")
def api_stop():
    with _lock:
        proc, run_id = _current["proc"], _current["id"]
        if proc is None or proc.poll() is not None:
            return jsonify({"error": "Нет активного запуска"}), 400
        meta_path = REPORTS / run_id / "meta.json"
        meta = _read_json(meta_path, {})
        meta["state"] = "stopped"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        os.killpg(proc.pid, signal.SIGTERM)
    return jsonify({"ok": True})


@app.get("/api/runs")
def api_runs():
    REPORTS.mkdir(exist_ok=True)
    runs = []
    for d in sorted((p for p in REPORTS.iterdir() if p.is_dir()), reverse=True)[:30]:
        summary = run_summary(d.name)
        if summary:
            summary.pop("results")
            runs.append(summary)
    return jsonify(runs)


@app.get("/api/runs/<run_id>")
def api_run_detail(run_id):
    if "/" in run_id or ".." in run_id:
        abort(400)
    summary = run_summary(run_id)
    if summary is None:
        abort(404)
    log_path = REPORTS / run_id / "log.txt"
    log = log_path.read_text(encoding="utf-8", errors="replace")[-60000:] if log_path.exists() else ""
    return jsonify({**summary, "log": log})


@app.get("/reports/<run_id>/screenshots/<name>")
def run_screenshot(run_id, name):
    if "/" in run_id or ".." in run_id:
        abort(400)
    return send_from_directory(REPORTS / run_id / "screenshots", name)


if __name__ == "__main__":
    import management  # задачи спринта → кейсы агента → подтверждение → Qase (admin/management.py)

    management.init_app(app)
    port = int(os.getenv("ADMIN_PORT", "5050"))
    print(f"Админка автотестов: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
