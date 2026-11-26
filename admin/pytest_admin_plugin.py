"""Плагин pytest для админки: отдаёт список кейсов (с привязкой к проекту UZ/KZ) и статусы выполнения.

Один и тот же плагин работает и для Android (tests/), и для iOS (ios/tests/): pytest iOS
запускается из папки ios/, и его nodeid начинаются с tests/ — админка передаёт префикс
ADMIN_NODE_PREFIX="ios/", чтобы id кейсов совпадали с путём от корня проекта и не
пересекались с Android.
"""
import json
import os
import time
from pathlib import Path


def _title(item):
    marker = item.get_closest_marker("title")
    if marker and marker.args:
        return marker.args[0]
    doc = getattr(getattr(item, "obj", None), "__doc__", None)
    if doc and doc.strip():
        return doc.strip().splitlines()[0]
    return item.name


def _fields(item):
    """Доп. поля ввода перед запуском (см. pytest.mark.fields в pytest.ini).
    Пара (ENV, подпись) — обязательное поле; третий элемент "optional" — необязательное."""
    marker = item.get_closest_marker("fields")
    if not marker:
        return []
    return [{"env": env, "label": label, "optional": "optional" in rest} for env, label, *rest in marker.args]


def _project_key(nodeid):
    """tests/uz/test_launch.py::... -> "uz"; tests/test_x.py::... (без папки проекта) -> "shared"."""
    parts = Path(nodeid.split("::", 1)[0]).parts
    if len(parts) >= 3 and parts[0] == "tests":
        return parts[1]
    return "shared"


def _project_title(key):
    """Человекочитаемое имя сборки для админки — берётся из tests/projects/<key>.py."""
    if key == "shared":
        return "Общие"
    try:
        module = __import__(f"projects.{key}", fromlist=["PROJECT"])
        return module.PROJECT.title
    except Exception:  # noqa: BLE001 — на список кейсов это не должно влиять
        return key


def _prefixed(nodeid):
    return os.getenv("ADMIN_NODE_PREFIX", "") + nodeid


def _emit(event):
    path = os.getenv("ADMIN_EVENTS_OUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def pytest_collection_finish(session):
    path = os.getenv("ADMIN_COLLECT_OUT")
    if not path:
        return
    items = []
    for item in session.items:
        project = _project_key(item.nodeid)
        items.append({
            "nodeid": _prefixed(item.nodeid),
            "title": _title(item),
            "name": item.name,
            "file": item.location[0],
            "project": project,
            "project_title": _project_title(project),
            "fields": _fields(item),
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)


_state = {}


def pytest_runtest_logstart(nodeid, location):
    _state[nodeid] = {"status": "running", "duration": 0.0, "error": None, "started": time.time()}
    _emit({"nodeid": _prefixed(nodeid), "status": "running"})


def pytest_runtest_logreport(report):
    st = _state.setdefault(report.nodeid, {"status": "running", "duration": 0.0, "error": None})
    st["duration"] += report.duration
    for key, value in report.user_properties:
        if key in ("screenshot", "video"):
            st[key] = value
    if report.failed:
        st["status"] = "failed" if report.when == "call" else "error"
        st["error"] = report.longreprtext[-4000:]
    elif report.skipped:
        st["status"] = "skipped"
        st["error"] = report.longreprtext[-1000:] or None
    elif report.when == "call" and st["status"] == "running":
        st["status"] = "passed"


def pytest_runtest_logfinish(nodeid, location):
    st = _state.get(nodeid, {})
    _emit({
        "nodeid": _prefixed(nodeid),
        "status": st.get("status", "error"),
        "duration": round(st.get("duration", 0.0), 2),
        "error": st.get("error"),
        "screenshot": st.get("screenshot"),
        "video": st.get("video"),
    })
