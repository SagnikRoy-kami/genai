import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3
import json
from config import SQLITE_DB_PATH


def _conn():
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id    INTEGER NOT NULL,
            task_name     TEXT NOT NULL,
            start_date    TEXT NOT NULL,
            end_date      TEXT NOT NULL,
            current_status TEXT NOT NULL,
            description   TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS resources (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id      INTEGER NOT NULL,
            resource_type   TEXT NOT NULL,
            needed          REAL NOT NULL,
            currently_used  REAL NOT NULL,
            unit            TEXT DEFAULT 'count',
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS dependencies (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id       INTEGER NOT NULL,
            dependency_name  TEXT NOT NULL,
            dependency_type  TEXT DEFAULT 'internal',
            status           TEXT DEFAULT 'pending',
            blocking_tasks   TEXT DEFAULT '[]',
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS risk_reports (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            report_json TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
                           
        CREATE TABLE IF NOT EXISTS file_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_hash   TEXT UNIQUE NOT NULL,
            file_name   TEXT NOT NULL,
            file_path   TEXT,
            project_id  INTEGER NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        """)


# ── CRUD Operations ─────────────────────────────────────────────────

def save_project(plan) -> int:
    """Persist a ProjectPlanInput and return the project ID."""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (plan.project_name, plan.project_description),
        )
        pid = cur.lastrowid

        for t in plan.tasks:
            conn.execute(
                "INSERT INTO tasks (project_id, task_name, start_date, end_date, current_status, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pid, t.task_name, str(t.start_date), str(t.end_date), t.current_status.value, t.description),
            )

        for r in plan.resources:
            conn.execute(
                "INSERT INTO resources (project_id, resource_type, needed, currently_used, unit) "
                "VALUES (?, ?, ?, ?, ?)",
                (pid, r.resource_type, r.needed, r.currently_used, r.unit),
            )

        for d in plan.dependencies:
            conn.execute(
                "INSERT INTO dependencies (project_id, dependency_name, dependency_type, status, blocking_tasks) "
                "VALUES (?, ?, ?, ?, ?)",
                (pid, d.dependency_name, d.dependency_type, d.status, json.dumps(d.blocking_tasks)),
            )

        conn.commit()
    return pid


def get_project(project_id: int) -> dict:
    """Load a full project with tasks, resources, and dependencies."""
    with _conn() as conn:
        proj = dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
        proj["tasks"] = [dict(r) for r in conn.execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,)).fetchall()]
        proj["resources"] = [dict(r) for r in conn.execute("SELECT * FROM resources WHERE project_id = ?", (project_id,)).fetchall()]
        proj["dependencies"] = [dict(r) for r in conn.execute("SELECT * FROM dependencies WHERE project_id = ?", (project_id,)).fetchall()]
        for d in proj["dependencies"]:
            d["blocking_tasks"] = json.loads(d["blocking_tasks"])
    return proj


def list_projects() -> list:
    with _conn() as conn:
        return [dict(r) for r in conn.execute("SELECT id, name, created_at FROM projects ORDER BY id DESC").fetchall()]


def save_report(project_id: int, report_json: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO risk_reports (project_id, report_json) VALUES (?, ?)",
            (project_id, report_json),
        )
        conn.commit()


def get_latest_report(project_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT report_json FROM risk_reports WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
    return json.loads(row["report_json"]) if row else None

def save_file_cache(file_hash: str, file_name: str, file_path: str, project_id: int):
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO file_cache (file_hash, file_name, file_path, project_id) VALUES (?, ?, ?, ?)",
            (file_hash, file_name, file_path, project_id),
        )
        conn.commit()

def get_cached_project(file_hash: str):
    """Check if this exact file has been uploaded before. Returns project_id or None."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT project_id FROM file_cache WHERE file_hash = ?",
            (file_hash,),
        ).fetchone()
    return row["project_id"] if row else None

# ── Delete Project ─────────────────────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3
import json
from config import SQLITE_DB_PATH


def _conn():
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id    INTEGER NOT NULL,
            task_name     TEXT NOT NULL,
            start_date    TEXT NOT NULL,
            end_date      TEXT NOT NULL,
            current_status TEXT NOT NULL,
            description   TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS resources (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id      INTEGER NOT NULL,
            resource_type   TEXT NOT NULL,
            needed          REAL NOT NULL,
            currently_used  REAL NOT NULL,
            unit            TEXT DEFAULT 'count',
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS dependencies (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id       INTEGER NOT NULL,
            dependency_name  TEXT NOT NULL,
            dependency_type  TEXT DEFAULT 'internal',
            status           TEXT DEFAULT 'pending',
            blocking_tasks   TEXT DEFAULT '[]',
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS risk_reports (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            report_json TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
                           
        CREATE TABLE IF NOT EXISTS file_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_hash   TEXT UNIQUE NOT NULL,
            file_name   TEXT NOT NULL,
            file_path   TEXT,
            project_id  INTEGER NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        """)


# ── CRUD Operations ─────────────────────────────────────────────────

def save_project(plan) -> int:
    """Persist a ProjectPlanInput and return the project ID."""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (plan.project_name, plan.project_description),
        )
        pid = cur.lastrowid

        for t in plan.tasks:
            conn.execute(
                "INSERT INTO tasks (project_id, task_name, start_date, end_date, current_status, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pid, t.task_name, str(t.start_date), str(t.end_date), t.current_status.value, t.description),
            )

        for r in plan.resources:
            conn.execute(
                "INSERT INTO resources (project_id, resource_type, needed, currently_used, unit) "
                "VALUES (?, ?, ?, ?, ?)",
                (pid, r.resource_type, r.needed, r.currently_used, r.unit),
            )

        for d in plan.dependencies:
            conn.execute(
                "INSERT INTO dependencies (project_id, dependency_name, dependency_type, status, blocking_tasks) "
                "VALUES (?, ?, ?, ?, ?)",
                (pid, d.dependency_name, d.dependency_type, d.status, json.dumps(d.blocking_tasks)),
            )

        conn.commit()
    return pid


def get_project(project_id: int) -> dict:
    """Load a full project with tasks, resources, and dependencies."""
    with _conn() as conn:
        proj = dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
        proj["tasks"] = [dict(r) for r in conn.execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,)).fetchall()]
        proj["resources"] = [dict(r) for r in conn.execute("SELECT * FROM resources WHERE project_id = ?", (project_id,)).fetchall()]
        proj["dependencies"] = [dict(r) for r in conn.execute("SELECT * FROM dependencies WHERE project_id = ?", (project_id,)).fetchall()]
        for d in proj["dependencies"]:
            d["blocking_tasks"] = json.loads(d["blocking_tasks"])
    return proj


def list_projects() -> list:
    with _conn() as conn:
        return [dict(r) for r in conn.execute("SELECT id, name, created_at FROM projects ORDER BY id DESC").fetchall()]


def save_report(project_id: int, report_json: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO risk_reports (project_id, report_json) VALUES (?, ?)",
            (project_id, report_json),
        )
        conn.commit()


def get_latest_report(project_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT report_json FROM risk_reports WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
    return json.loads(row["report_json"]) if row else None

def save_file_cache(file_hash: str, file_name: str, file_path: str, project_id: int):
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO file_cache (file_hash, file_name, file_path, project_id) VALUES (?, ?, ?, ?)",
            (file_hash, file_name, file_path, project_id),
        )
        conn.commit()

def get_cached_project(file_hash: str):
    """Check if this exact file has been uploaded before. Returns project_id or None."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT project_id FROM file_cache WHERE file_hash = ?",
            (file_hash,),
        ).fetchone()
    return row["project_id"] if row else None

# ── Delete Project ─────────────────────────────────────────────────────────────

def delete_project(project_id: int):
    with _conn() as conn:
        # delete child data first (important for consistency)
        conn.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM resources WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM dependencies WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM risk_reports WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM file_cache WHERE project_id = ?", (project_id,))

        # finally delete main project
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

        conn.commit()