"""Management: задачи спринта (Azure Boards) → тест-кейсы агента → подтверждение QA → Qase.

Генерация, клиенты Azure и Qase — из соседнего проекта tascorp-testgen (его .env, prompt.md,
product_context.md). Здесь только очередь генерации, хранение черновиков до подтверждения
(SQLite) и API страницы /management.

Агент: раз в MGMT_POLL_MIN минут читает текущий спринт и ставит в очередь генерации задачи
в статусах MGMT_AUTO_STATES (по умолчанию Active), по которым кейсов ещё нет. Включается
переключателем «Автогенерация» на странице. Любую задачу можно сгенерировать и вручную.
"""
import hashlib
import json
import os
import queue
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from flask import Blueprint, jsonify, request

ROOT = Path(__file__).resolve().parent.parent
TESTGEN = Path(os.getenv("TESTGEN_DIR", ROOT.parent / "tascorp-testgen")).expanduser()
DB = Path(os.getenv("MGMT_DB", ROOT / "admin" / "management.db"))
POLL_MIN = float(os.getenv("MGMT_POLL_MIN", "10"))
AUTO_STATES = {s.strip() for s in os.getenv("MGMT_AUTO_STATES", "Active").split(",") if s.strip()}

bp = Blueprint("management", __name__)

_tg = None  # модули tascorp-testgen: импорт при первом обращении, чтобы админка автотестов
            # работала и без них (ошибка видна только на странице Management)
_jobs = queue.Queue()
_queued = set()                    # id задач в очереди или в работе
_queued_lock = threading.Lock()
_sync_lock = threading.Lock()
_state = {"last_sync": None, "last_sync_error": None, "sprints": None}


def tg():
    global _tg
    if _tg is None:
        if not (TESTGEN / "generator.py").exists():
            raise RuntimeError(f"Не найден tascorp-testgen в {TESTGEN} — задайте TESTGEN_DIR")
        sys.path.insert(0, str(TESTGEN))
        import ado, generator, qase, testgen  # noqa: E401
        testgen.load_env()
        missing = [k for k in ("ADO_ORG_URL", "ADO_PROJECT", "ADO_PAT", "QASE_TOKEN", "QASE_PROJECT")
                   if not os.environ.get(k)]
        if missing:
            raise RuntimeError(f"Не заданы {', '.join(missing)} в {TESTGEN / '.env'}")
        _tg = {"ado": ado, "generator": generator, "qase": qase, "testgen": testgen}
    return _tg


def ado_client():
    return tg()["ado"].AdoClient(os.environ["ADO_ORG_URL"], os.environ["ADO_PROJECT"],
                                 os.environ.get("ADO_TEAM"), os.environ["ADO_PAT"])


def qase_client():
    return tg()["qase"].QaseClient(os.environ["QASE_TOKEN"], os.environ["QASE_PROJECT"],
                                   os.environ.get("QASE_API_URL", "https://api.qase.io/v1"))


# ---------- хранилище ----------

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY, sprint TEXT, sprint_name TEXT, in_sprint INTEGER DEFAULT 1,
  title TEXT, type TEXT, state TEXT, area TEXT, url TEXT, tags TEXT, text TEXT, text_hash TEXT,
  gen_status TEXT DEFAULT 'none', gen_hash TEXT, gen_error TEXT, gen_at REAL, gen_cost REAL,
  summary TEXT, questions TEXT, suite_id INTEGER, updated_at REAL
);
CREATE TABLE IF NOT EXISTS cases (
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, kind TEXT, data TEXT,
  status TEXT DEFAULT 'pending', reason TEXT, qase_id INTEGER, error TEXT,
  created_at REAL, updated_at REAL
);
CREATE INDEX IF NOT EXISTS cases_task ON cases(task_id);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""
# Статусы кейса: pending — ждёт подтверждения, sent — подтверждён и создан в Qase,
# rejected — отклонён QA (с причиной), error — подтверждён, но Qase вернул ошибку.


@contextmanager
def db():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        with con:
            yield con
    finally:
        con.close()


def init_db():
    with db() as con:
        con.executescript(SCHEMA)
        # Генерация, прерванная перезапуском админки, — вернуть в исходное состояние
        con.execute("UPDATE tasks SET gen_status = 'none' WHERE gen_status IN ('queued', 'running') AND gen_at IS NULL")
        con.execute("UPDATE tasks SET gen_status = 'done' WHERE gen_status IN ('queued', 'running') AND gen_at IS NOT NULL")


def setting(key, default=None):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_setting(key, value):
    with db() as con:
        con.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))


def text_hash(task):
    """Хэш смысла задачи: rev в Azure растёт от любой правки (статус, комментарий), а
    «требование изменилось» — только если поменялись заголовок или описание."""
    return hashlib.sha1(f"{task['title']}\n{task['text']}".encode()).hexdigest()


def case_row(r):
    return {"id": r["id"], "task_id": r["task_id"], "kind": r["kind"], "status": r["status"],
            "reason": r["reason"], "qase_id": r["qase_id"], "error": r["error"], **json.loads(r["data"])}


def task_row(r, counts=None):
    t = {k: r[k] for k in ("id", "sprint", "sprint_name", "title", "type", "state", "area", "url",
                           "gen_status", "gen_error", "gen_at", "gen_cost", "summary", "suite_id")}
    t["tags"] = json.loads(r["tags"] or "[]")
    t["questions"] = json.loads(r["questions"] or "[]")
    t["changed"] = r["gen_status"] == "done" and r["gen_hash"] != r["text_hash"]
    t["counts"] = counts or {}
    return t


# ---------- синхронизация с Azure ----------

def sprints():
    if _state["sprints"] is None:
        _state["sprints"] = [{"name": it["name"], "path": it["path"],
                              "timeframe": it.get("attributes", {}).get("timeFrame")}
                             for it in ado_client().iterations()]
    return _state["sprints"]


def sync(sprint="current"):
    """Задачи спринта из Azure → таблица tasks. Возвращает путь спринта."""
    ado = ado_client()
    with _sync_lock:
        it = ado.iteration(sprint)
        types = [t.strip() for t in os.environ.get("ADO_TYPES", "User Story,Bug,Product Backlog Item").split(",")]
        ids = ado.sprint_item_ids(it["path"], types)
        items = ado.work_items(ids) if ids else []
        now = time.time()
        with db() as con:
            con.execute("UPDATE tasks SET in_sprint = 0 WHERE sprint = ?", (it["path"],))
            for t in items:
                con.execute("""
                  INSERT INTO tasks (id, sprint, sprint_name, in_sprint, title, type, state, area, url, tags, text,
                                     text_hash, updated_at)
                  VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                  ON CONFLICT(id) DO UPDATE SET sprint = excluded.sprint, sprint_name = excluded.sprint_name,
                    in_sprint = 1, title = excluded.title, type = excluded.type, state = excluded.state,
                    area = excluded.area, url = excluded.url, tags = excluded.tags, text = excluded.text,
                    text_hash = excluded.text_hash, updated_at = excluded.updated_at
                """, (t["id"], it["path"], it["name"], t["title"], t["type"], t["state"], t["area"], t["url"],
                      json.dumps(t["tags"], ensure_ascii=False), t["text"], text_hash(t), now))
        _state.update(last_sync=now, last_sync_error=None)
    return it["path"]


def auto_queue(sprint_path):
    """Агент: новые задачи в статусах AUTO_STATES без кейсов → в очередь генерации."""
    if not setting("autogen", False):
        return []
    marks = ",".join("?" * len(AUTO_STATES))
    with db() as con:
        rows = con.execute(f"SELECT id FROM tasks WHERE sprint = ? AND in_sprint = 1 AND gen_status = 'none' "
                           f"AND state IN ({marks})", (sprint_path, *AUTO_STATES)).fetchall()
    return [r["id"] for r in rows if enqueue(r["id"])]


def poller():
    while True:
        try:
            if setting("autogen", False):
                auto_queue(sync("current"))
        except Exception as e:  # noqa: BLE001 — сеть/токен: попробуем в следующий раз
            _state["last_sync_error"] = str(e)
        time.sleep(POLL_MIN * 60)


# ---------- генерация ----------

def enqueue(task_id):
    with _queued_lock:
        if task_id in _queued:
            return False
        _queued.add(task_id)
    with db() as con:
        con.execute("UPDATE tasks SET gen_status = 'queued', gen_error = NULL WHERE id = ?", (task_id,))
    _jobs.put(task_id)
    return True


def worker():
    # По одной задаче за раз: claude -p на задачу идёт минуты, параллельно — лишняя нагрузка на Mac
    while True:
        task_id = _jobs.get()
        try:
            generate(task_id)
        finally:
            with _queued_lock:
                _queued.discard(task_id)


def generate(task_id):
    with db() as con:
        con.execute("UPDATE tasks SET gen_status = 'running' WHERE id = ?", (task_id,))
        r = con.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    task = {"id": r["id"], "type": r["type"], "state": r["state"], "title": r["title"], "area": r["area"],
            "tags": json.loads(r["tags"] or "[]"), "text": r["text"] or ""}
    try:
        result = tg()["generator"].generate(task, r["sprint_name"], model=os.environ.get("TESTGEN_MODEL") or None)
    except Exception as e:  # noqa: BLE001
        with db() as con:
            con.execute("UPDATE tasks SET gen_status = 'error', gen_error = ? WHERE id = ?", (str(e)[:2000], task_id))
        return
    now = time.time()
    with db() as con:
        # Перегенерация заменяет только неподтверждённые черновики; отправленные в Qase
        # и отклонённые (с причинами — материал для улучшения промпта) остаются
        con.execute("DELETE FROM cases WHERE task_id = ? AND status IN ('pending', 'error')", (task_id,))
        for kind, key in (("new", "test_cases"), ("regression", "regression_cases")):
            for c in result[key]:
                con.execute("INSERT INTO cases (task_id, kind, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                            (task_id, kind, json.dumps(c, ensure_ascii=False), now, now))
        con.execute("""UPDATE tasks SET gen_status = 'done', gen_error = NULL, gen_hash = text_hash, gen_at = ?,
                       gen_cost = ?, summary = ?, questions = ? WHERE id = ?""",
                    (now, result.get("_cost_usd"), result["summary"],
                     json.dumps(result["open_questions"], ensure_ascii=False), task_id))


# ---------- отправка в Qase ----------

def send_to_qase(case_ids):
    """Подтверждённые кейсы → Qase (статус Actual) в сьют «Спринты / <спринт> / ADO-<id> · …»."""
    tgm = tg()
    with db() as con:
        rows = con.execute(f"SELECT * FROM cases WHERE id IN ({','.join('?' * len(case_ids))}) "
                           "AND status IN ('pending', 'error')", case_ids).fetchall()
    by_task = {}
    for r in rows:
        by_task.setdefault(r["task_id"], []).append(r)
    qase = qase_client()
    sent, errors = 0, []
    for task_id, crows in by_task.items():
        with db() as con:
            t = con.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        task = {"id": t["id"], "title": t["title"], "url": t["url"]}
        try:
            suite_id = t["suite_id"]
            if not suite_id:
                root_id, _ = qase.ensure_suite(os.environ.get("QASE_ROOT_SUITE") or "Спринты")
                sprint_suite, _ = qase.ensure_suite(t["sprint_name"], root_id)
                suite_id, _ = qase.ensure_suite(f"ADO-{t['id']} · {t['title']}"[:255], sprint_suite)
                summary = {"summary": t["summary"] or "", "open_questions": json.loads(t["questions"] or "[]")}
                qase.update_suite(suite_id, description=tgm["testgen"].suite_description(task, summary))
                with db() as con:
                    con.execute("UPDATE tasks SET suite_id = ? WHERE id = ?", (suite_id, task_id))
            sprint_tag = "sprint-" + tgm["testgen"].slug(t["sprint_name"]).lower()
            body = [tgm["qase"].to_qase_case(json.loads(r["data"]), kind=r["kind"], suite_id=suite_id, task=task,
                                             sprint_tag=sprint_tag, reviewed=True) for r in crows]
            qase_ids = qase.create_cases(body)
        except Exception as e:  # noqa: BLE001
            with db() as con:
                con.executemany("UPDATE cases SET status = 'error', error = ?, updated_at = ? WHERE id = ?",
                                [(str(e)[:1000], time.time(), r["id"]) for r in crows])
            errors.append(f"ADO-{task_id}: {e}")
            continue
        with db() as con:
            con.executemany("UPDATE cases SET status = 'sent', qase_id = ?, error = NULL, updated_at = ? WHERE id = ?",
                            [(qid, time.time(), r["id"]) for qid, r in zip(qase_ids, crows)])
        sent += len(qase_ids)
    return sent, errors


# ---------- API ----------

def _err(e, code=500):
    return jsonify({"error": str(e)}), code


@bp.get("/api/mgmt/state")
def api_state():
    """Задачи спринта из локальной базы (без запроса в Azure) — для частого опроса страницы."""
    sprint = request.args.get("sprint") or ""
    try:
        tg()  # подгружает .env tascorp-testgen (QASE_PROJECT для ссылок на кейсы)
    except Exception as e:  # noqa: BLE001
        _state["last_sync_error"] = str(e)
    with db() as con:
        if not sprint:
            row = con.execute("SELECT sprint FROM tasks ORDER BY updated_at DESC LIMIT 1").fetchone()
            sprint = row["sprint"] if row else ""
        rows = con.execute("SELECT * FROM tasks WHERE sprint = ? AND in_sprint = 1 ORDER BY id DESC", (sprint,)).fetchall()
        counts = {}
        for c in con.execute("SELECT task_id, status, COUNT(*) n FROM cases GROUP BY task_id, status"):
            counts.setdefault(c["task_id"], {})[c["status"]] = c["n"]
    return jsonify({
        "sprint": sprint,
        "tasks": [task_row(r, counts.get(r["id"])) for r in rows],
        "autogen": setting("autogen", False), "auto_states": sorted(AUTO_STATES), "poll_min": POLL_MIN,
        "last_sync": _state["last_sync"], "last_sync_error": _state["last_sync_error"],
        "qase_project": os.environ.get("QASE_PROJECT", ""),
    })


@bp.post("/api/mgmt/sync")
def api_sync():
    body = request.get_json(silent=True) or {}
    try:
        path = sync(body.get("sprint") or "current")
        queued = auto_queue(path)
        return jsonify({"sprint": path, "sprints": sprints(), "queued": queued})
    except Exception as e:  # noqa: BLE001
        _state["last_sync_error"] = str(e)
        return _err(e)


@bp.post("/api/mgmt/settings")
def api_settings():
    body = request.get_json(silent=True) or {}
    if "autogen" in body:
        set_setting("autogen", bool(body["autogen"]))
    return jsonify({"autogen": setting("autogen", False)})


@bp.get("/api/mgmt/tasks/<int:task_id>")
def api_task(task_id):
    with db() as con:
        t = con.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if t is None:
            return _err("Задача не найдена", 404)
        cases = con.execute("SELECT * FROM cases WHERE task_id = ? ORDER BY kind, id", (task_id,)).fetchall()
    return jsonify({**task_row(t), "text": t["text"], "cases": [case_row(c) for c in cases]})


@bp.post("/api/mgmt/tasks/<int:task_id>/generate")
def api_generate(task_id):
    with db() as con:
        if con.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone() is None:
            return _err("Задача не найдена", 404)
    if not enqueue(task_id):
        return _err("Задача уже в очереди генерации", 409)
    return jsonify({"ok": True})


def _ids(body):
    ids = body.get("ids")
    if not isinstance(ids, list) or not ids or not all(isinstance(i, int) for i in ids):
        raise ValueError("Не выбраны кейсы")
    return ids


@bp.post("/api/mgmt/cases/approve")
def api_approve():
    try:
        ids = _ids(request.get_json(silent=True) or {})
        sent, errors = send_to_qase(ids)
    except ValueError as e:
        return _err(e, 400)
    except Exception as e:  # noqa: BLE001
        return _err(e)
    if errors:
        return jsonify({"sent": sent, "error": "Qase: " + "; ".join(errors)}), 502
    return jsonify({"sent": sent})


@bp.post("/api/mgmt/cases/reject")
def api_reject():
    body = request.get_json(silent=True) or {}
    try:
        ids = _ids(body)
    except ValueError as e:
        return _err(e, 400)
    reason = " ".join(str(body.get("reason") or "").split())[:500]
    with db() as con:
        n = con.execute(f"UPDATE cases SET status = 'rejected', reason = ?, updated_at = ? "
                        f"WHERE id IN ({','.join('?' * len(ids))}) AND status IN ('pending', 'error')",
                        (reason, time.time(), *ids)).rowcount
    return jsonify({"rejected": n})


@bp.post("/api/mgmt/cases/restore")
def api_restore():
    try:
        ids = _ids(request.get_json(silent=True) or {})
    except ValueError as e:
        return _err(e, 400)
    with db() as con:
        n = con.execute(f"UPDATE cases SET status = 'pending', reason = NULL, updated_at = ? "
                        f"WHERE id IN ({','.join('?' * len(ids))}) AND status = 'rejected'",
                        (time.time(), *ids)).rowcount
    return jsonify({"restored": n})


EDITABLE = {"title", "preconditions", "steps", "priority", "severity", "behavior", "country"}


@bp.patch("/api/mgmt/cases/<int:case_id>")
def api_case_edit(case_id):
    body = request.get_json(silent=True) or {}
    patch = {k: v for k, v in body.items() if k in EDITABLE}
    if "title" in patch and not str(patch["title"]).strip():
        return _err("Название кейса не может быть пустым", 400)
    if "steps" in patch:
        steps = [{"action": str(s.get("action", "")).strip(), "data": str(s.get("data", "")).strip(),
                  "expected_result": str(s.get("expected_result", "")).strip()}
                 for s in patch["steps"] if isinstance(s, dict)]
        steps = [s for s in steps if s["action"]]
        if not steps:
            return _err("Нужен хотя бы один шаг с действием", 400)
        patch["steps"] = steps
    with db() as con:
        r = con.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if r is None:
            return _err("Кейс не найден", 404)
        if r["status"] == "sent":
            return _err("Кейс уже в Qase — правьте его там", 409)
        data = {**json.loads(r["data"]), **patch}
        con.execute("UPDATE cases SET data = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(data, ensure_ascii=False), time.time(), case_id))
        r = con.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return jsonify(case_row(r))


def init_app(app):
    init_db()
    app.register_blueprint(bp)
    threading.Thread(target=worker, daemon=True, name="mgmt-worker").start()
    threading.Thread(target=poller, daemon=True, name="mgmt-poller").start()
