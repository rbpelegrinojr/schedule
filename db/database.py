import sqlite3
import json
import os
import sys


def _resolve_db_path():
    """Return the path to schedule.db.

    When running as a PyInstaller-frozen executable the database must live in
    a user-writable directory; Program Files is read-only on modern Windows.
    We use %APPDATA%\\ScheduleManager\\ so the file persists across upgrades.
    During normal (source) development the database stays in the current
    working directory, matching the original behaviour.
    """
    if getattr(sys, "frozen", False):
        app_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "ScheduleManager",
        )
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "schedule.db")
    return "schedule.db"


DB_PATH = _resolve_db_path()

# Time slot definitions (1-8).  Slots 1-4 = morning, 5-8 = afternoon.
TIME_SLOT_STARTS = ["7:30", "8:30", "9:30", "10:30", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM"]
TIME_SLOT_ENDS   = ["8:30", "9:30", "10:30", "11:30", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"]
TIME_SLOT_LABELS = [
    "7:30 - 8:30",
    "8:30 - 9:30",
    "9:30 - 10:30",
    "10:30 - 11:30",
    "1:00 - 2:00 PM",
    "2:00 - 3:00 PM",
    "3:00 - 4:00 PM",
    "4:00 - 5:00 PM",
]


def slot_time_range(start_slot, duration):
    """Return a human-readable time range string for a block."""
    start_idx = max(0, min(start_slot - 1, len(TIME_SLOT_STARTS) - 1))
    end_idx = max(0, min(start_slot + duration - 2, len(TIME_SLOT_ENDS) - 1))
    s = TIME_SLOT_STARTS[start_idx]
    e = TIME_SLOT_ENDS[end_idx]
    return f"{s} - {e}"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    try:
        with get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    employee_id TEXT UNIQUE NOT NULL,
                    subjects TEXT DEFAULT '[]',
                    preferred_vacant TEXT DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_number TEXT NOT NULL,
                    room_name TEXT DEFAULT '',
                    year_level INTEGER NOT NULL DEFAULT 0,
                    section TEXT NOT NULL DEFAULT '',
                    is_lab INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year_level INTEGER NOT NULL,
                    section_name TEXT NOT NULL,
                    room_id INTEGER,
                    FOREIGN KEY (room_id) REFERENCES rooms(id)
                );

                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_name TEXT NOT NULL,
                    subject_code TEXT UNIQUE NOT NULL,
                    lecture_hours INTEGER NOT NULL DEFAULT 2,
                    lab_hours INTEGER NOT NULL DEFAULT 0,
                    has_lab INTEGER NOT NULL DEFAULT 0,
                    teacher_id INTEGER,
                    year_level INTEGER,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id)
                );

                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id INTEGER NOT NULL,
                    subject_id INTEGER,
                    teacher_id INTEGER,
                    room_id INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    start_slot INTEGER NOT NULL,
                    duration INTEGER NOT NULL DEFAULT 1,
                    is_lab INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (section_id) REFERENCES sections(id),
                    FOREIGN KEY (subject_id) REFERENCES subjects(id),
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                    FOREIGN KEY (room_id) REFERENCES rooms(id)
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
        _migrate()
    except Exception as e:
        print(f"init_db error: {e}")


def _migrate():
    """Apply schema migrations to handle upgrades from older schema versions."""
    try:
        with get_connection() as conn:
            # --- rooms table ---
            rooms_cols = {row[1] for row in conn.execute("PRAGMA table_info(rooms)")}
            if "is_lab" not in rooms_cols:
                conn.execute("ALTER TABLE rooms ADD COLUMN is_lab INTEGER NOT NULL DEFAULT 0")

            # --- subjects table ---
            subj_cols = {row[1] for row in conn.execute("PRAGMA table_info(subjects)")}
            if "lecture_hours" not in subj_cols:
                conn.execute("ALTER TABLE subjects ADD COLUMN lecture_hours INTEGER NOT NULL DEFAULT 2")
            if "lab_hours" not in subj_cols:
                conn.execute("ALTER TABLE subjects ADD COLUMN lab_hours INTEGER NOT NULL DEFAULT 0")
            if "has_lab" not in subj_cols:
                conn.execute("ALTER TABLE subjects ADD COLUMN has_lab INTEGER NOT NULL DEFAULT 0")

            # --- schedules table: rename period -> start_slot ---
            sched_cols = {row[1] for row in conn.execute("PRAGMA table_info(schedules)")}
            if "period" in sched_cols and "start_slot" not in sched_cols:
                conn.execute("ALTER TABLE schedules RENAME COLUMN period TO start_slot")
                sched_cols = {row[1] for row in conn.execute("PRAGMA table_info(schedules)")}
            if "start_slot" not in sched_cols:
                conn.execute("ALTER TABLE schedules ADD COLUMN start_slot INTEGER NOT NULL DEFAULT 1")
            if "duration" not in sched_cols:
                conn.execute("ALTER TABLE schedules ADD COLUMN duration INTEGER NOT NULL DEFAULT 1")
            if "is_lab" not in sched_cols:
                conn.execute("ALTER TABLE schedules ADD COLUMN is_lab INTEGER NOT NULL DEFAULT 0")

    except Exception as e:
        print(f"_migrate error: {e}")


# ── Teachers ──────────────────────────────────────────────────────────────────

def _parse_teacher_row(row):
    d = dict(row)
    try:
        d["subjects"] = json.loads(d.get("subjects") or "[]")
    except Exception:
        d["subjects"] = []
    try:
        d["preferred_vacant"] = json.loads(d.get("preferred_vacant") or "[]")
    except Exception:
        d["preferred_vacant"] = []
    return d


def get_all_teachers():
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM teachers ORDER BY name").fetchall()
            return [_parse_teacher_row(r) for r in rows]
    except Exception as e:
        print(f"get_all_teachers error: {e}")
        return []


def get_teacher_by_id(teacher_id):
    try:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
            return _parse_teacher_row(row) if row else None
    except Exception as e:
        print(f"get_teacher_by_id error: {e}")
        return None


def create_teacher(name, employee_id, subjects=None, preferred_vacant=None):
    if subjects is None:
        subjects = []
    if preferred_vacant is None:
        preferred_vacant = []
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO teachers (name, employee_id, subjects, preferred_vacant) VALUES (?, ?, ?, ?)",
                (name, employee_id, json.dumps(subjects), json.dumps(preferred_vacant))
            )
            return cur.lastrowid
    except Exception as e:
        print(f"create_teacher error: {e}")
        raise


def update_teacher(teacher_id, name, employee_id, subjects=None, preferred_vacant=None):
    if subjects is None:
        subjects = []
    if preferred_vacant is None:
        preferred_vacant = []
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE teachers SET name=?, employee_id=?, subjects=?, preferred_vacant=? WHERE id=?",
                (name, employee_id, json.dumps(subjects), json.dumps(preferred_vacant), teacher_id)
            )
    except Exception as e:
        print(f"update_teacher error: {e}")
        raise


def delete_teacher(teacher_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM teachers WHERE id=?", (teacher_id,))
    except Exception as e:
        print(f"delete_teacher error: {e}")


# ── Rooms ─────────────────────────────────────────────────────────────────────

def get_all_rooms():
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM rooms ORDER BY year_level, section").fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_all_rooms error: {e}")
        return []


def get_room_by_id(room_id):
    try:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"get_room_by_id error: {e}")
        return None


def get_lab_rooms():
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM rooms WHERE is_lab=1 ORDER BY room_number"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_lab_rooms error: {e}")
        return []


def get_regular_rooms():
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM rooms WHERE is_lab=0 ORDER BY year_level, section"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_regular_rooms error: {e}")
        return []


def create_room(room_number, room_name, year_level, section, is_lab=False):
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO rooms (room_number, room_name, year_level, section, is_lab) "
                "VALUES (?, ?, ?, ?, ?)",
                (room_number, room_name, year_level, section, int(is_lab))
            )
            return cur.lastrowid
    except Exception as e:
        print(f"create_room error: {e}")
        raise


def update_room(room_id, room_number, room_name, year_level, section, is_lab=False):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE rooms SET room_number=?, room_name=?, year_level=?, section=?, is_lab=? WHERE id=?",
                (room_number, room_name, year_level, section, int(is_lab), room_id)
            )
    except Exception as e:
        print(f"update_room error: {e}")
        raise


def delete_room(room_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    except Exception as e:
        print(f"delete_room error: {e}")


# ── Sections ──────────────────────────────────────────────────────────────────

def get_all_sections():
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM sections ORDER BY year_level, section_name").fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_all_sections error: {e}")
        return []


def get_section_by_id(section_id):
    try:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM sections WHERE id=?", (section_id,)).fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"get_section_by_id error: {e}")
        return None


def create_section(year_level, section_name, room_id=None):
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO sections (year_level, section_name, room_id) VALUES (?, ?, ?)",
                (year_level, section_name, room_id)
            )
            return cur.lastrowid
    except Exception as e:
        print(f"create_section error: {e}")
        raise


def update_section(section_id, year_level, section_name, room_id=None):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE sections SET year_level=?, section_name=?, room_id=? WHERE id=?",
                (year_level, section_name, room_id, section_id)
            )
    except Exception as e:
        print(f"update_section error: {e}")
        raise


def delete_section(section_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM sections WHERE id=?", (section_id,))
    except Exception as e:
        print(f"delete_section error: {e}")


# ── Subjects ──────────────────────────────────────────────────────────────────

def get_all_subjects():
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM subjects ORDER BY subject_name").fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_all_subjects error: {e}")
        return []


def get_subject_by_id(subject_id):
    try:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM subjects WHERE id=?", (subject_id,)).fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"get_subject_by_id error: {e}")
        return None


def get_subjects_by_year_level(year_level):
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM subjects WHERE year_level=? ORDER BY subject_name",
                (year_level,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_subjects_by_year_level error: {e}")
        return []


def create_subject(subject_name, subject_code, lecture_hours, lab_hours, has_lab,
                   teacher_id=None, year_level=None):
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO subjects "
                "(subject_name, subject_code, lecture_hours, lab_hours, has_lab, teacher_id, year_level) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (subject_name, subject_code, lecture_hours, lab_hours, int(has_lab),
                 teacher_id, year_level)
            )
            return cur.lastrowid
    except Exception as e:
        print(f"create_subject error: {e}")
        raise


def update_subject(subject_id, subject_name, subject_code, lecture_hours, lab_hours, has_lab,
                   teacher_id=None, year_level=None):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE subjects SET subject_name=?, subject_code=?, lecture_hours=?, "
                "lab_hours=?, has_lab=?, teacher_id=?, year_level=? WHERE id=?",
                (subject_name, subject_code, lecture_hours, lab_hours, int(has_lab),
                 teacher_id, year_level, subject_id)
            )
    except Exception as e:
        print(f"update_subject error: {e}")
        raise


def delete_subject(subject_id):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
    except Exception as e:
        print(f"delete_subject error: {e}")


# ── Schedules ─────────────────────────────────────────────────────────────────

def get_schedule_by_section(section_id):
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT sc.*, s.subject_name, s.subject_code, t.name AS teacher_name
                FROM schedules sc
                LEFT JOIN subjects s ON sc.subject_id = s.id
                LEFT JOIN teachers t ON sc.teacher_id = t.id
                WHERE sc.section_id = ?
                ORDER BY sc.day_of_week, sc.start_slot
                """,
                (section_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_schedule_by_section error: {e}")
        return []


def get_schedule_by_teacher(teacher_id):
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT sc.*, s.subject_name, s.subject_code, sec.section_name, sec.year_level
                FROM schedules sc
                LEFT JOIN subjects s ON sc.subject_id = s.id
                LEFT JOIN sections sec ON sc.section_id = sec.id
                WHERE sc.teacher_id = ?
                ORDER BY sc.day_of_week, sc.start_slot
                """,
                (teacher_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_schedule_by_teacher error: {e}")
        return []


def get_schedule_by_room(room_id):
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT sc.*, s.subject_name, s.subject_code, t.name AS teacher_name,
                       sec.section_name, sec.year_level
                FROM schedules sc
                LEFT JOIN subjects s ON sc.subject_id = s.id
                LEFT JOIN teachers t ON sc.teacher_id = t.id
                LEFT JOIN sections sec ON sc.section_id = sec.id
                WHERE sc.room_id = ?
                ORDER BY sc.day_of_week, sc.start_slot
                """,
                (room_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_schedule_by_room error: {e}")
        return []


def clear_schedules():
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM schedules")
    except Exception as e:
        print(f"clear_schedules error: {e}")


def save_schedule_entry(section_id, subject_id, teacher_id, room_id,
                        day_of_week, start_slot, duration=1, is_lab=False):
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO schedules
                    (section_id, subject_id, teacher_id, room_id,
                     day_of_week, start_slot, duration, is_lab)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (section_id, subject_id, teacher_id, room_id,
                 day_of_week, start_slot, duration, int(is_lab))
            )
    except Exception as e:
        print(f"save_schedule_entry error: {e}")
        raise


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key, default=None):
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
            return row["value"] if row else default
    except Exception as e:
        print(f"get_setting error: {e}")
        return default


def set_setting(key, value):
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value))
            )
    except Exception as e:
        print(f"set_setting error: {e}")
