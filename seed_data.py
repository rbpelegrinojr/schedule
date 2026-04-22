"""
seed_data.py – Populate the schedule database with sample records.

Run from the project root:
    python seed_data.py

The script is idempotent: it skips insertion of any record whose unique
key (employee_id / subject_code / room_number+section / section_name+year)
already exists in the database.
"""

import sys
import os

# Allow imports from the project root.
sys.path.insert(0, os.path.dirname(__file__))

import db.database as db

# ---------------------------------------------------------------------------
# Teachers
# ---------------------------------------------------------------------------
# Format: (name, employee_id)
# Teachers marked with *_LAB teach subjects that have a lab component.
TEACHERS = [
    ("Dr. Maria Santos",       "T001"),   # Programming – has lab
    ("Prof. Juan dela Cruz",   "T002"),   # Mathematics – no lab
    ("Ms. Ana Reyes",          "T003"),   # Science – has lab
    ("Mr. Carlo Mendoza",      "T004"),   # English / Communication – no lab
    ("Dr. Rosa Garcia",        "T005"),   # Database Systems – has lab
    ("Prof. Jose Ramos",       "T006"),   # Physics – has lab
    ("Ms. Liza Torres",        "T007"),   # Social Sciences – no lab
    ("Mr. Mark Bautista",      "T008"),   # Computer Networks – has lab
    ("Dr. Elena Villanueva",   "T009"),   # Data Structures / Algorithms – no lab
    ("Prof. Roberto Aquino",   "T010"),   # Web Development – has lab
    ("Ms. Cristina Lim",       "T011"),   # Discrete Mathematics – no lab
    ("Mr. Dennis Tan",         "T012"),   # Operating Systems – has lab
]

# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------
# Format: (room_number, room_name, year_level, section, is_lab)
# Regular classrooms carry a year-level + section so the scheduler can
# assign them to the matching section automatically.  Lab rooms use 0/"".
ROOMS = [
    ("101", "Room 101",          1, "A",  False),
    ("102", "Room 102",          1, "B",  False),
    ("201", "Room 201",          2, "A",  False),
    ("202", "Room 202",          2, "B",  False),
    ("301", "Room 301",          3, "A",  False),
    ("302", "Room 302",          3, "B",  False),
    ("401", "Room 401",          4, "A",  False),
    ("402", "Room 402",          4, "B",  False),
    ("LAB1", "Computer Lab 1",   0, "",   True),
    ("LAB2", "Computer Lab 2",   0, "",   True),
    ("SCILAB", "Science Lab",    0, "",   True),
]

# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
# Format: (year_level, section_name, room_number)
# room_number is looked up after rooms are inserted.
SECTIONS = [
    (1, "1-A", "101"),
    (1, "1-B", "102"),
    (2, "2-A", "201"),
    (2, "2-B", "202"),
    (3, "3-A", "301"),
    (3, "3-B", "302"),
    (4, "4-A", "401"),
    (4, "4-B", "402"),
]

# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------
# Format: (subject_name, subject_code, lecture_hours, lab_hours, has_lab,
#          teacher_employee_id, year_level)
# lecture_hours = 2 hours/week (one 2-hr block)
# lab_hours     = 3 hours/week (one 3-hr block) when has_lab is True
SUBJECTS = [
    # ── Year 1 ────────────────────────────────────────────────────────────
    ("Introduction to Computing", "ITC101", 2, 3, True,  "T001", 1),
    ("Mathematics 1",             "MATH101", 2, 0, False, "T002", 1),
    ("English Communication",     "ENG101",  2, 0, False, "T004", 1),
    ("General Physics",           "PHYS101", 2, 3, True,  "T006", 1),

    # ── Year 2 ────────────────────────────────────────────────────────────
    ("Object-Oriented Programming", "OOP201",  2, 3, True,  "T001", 2),
    ("Mathematics 2",               "MATH201", 2, 0, False, "T002", 2),
    ("Data Structures",             "DSTR201", 2, 0, False, "T009", 2),
    ("Database Management",         "DBMS201", 2, 3, True,  "T005", 2),

    # ── Year 3 ────────────────────────────────────────────────────────────
    ("Web Development",      "WEB301",  2, 3, True,  "T010", 3),
    ("Computer Networks",    "NET301",  2, 3, True,  "T008", 3),
    ("Social Sciences",      "SOC301",  2, 0, False, "T007", 3),
    ("Discrete Mathematics", "DMAT301", 2, 0, False, "T011", 3),

    # ── Year 4 ────────────────────────────────────────────────────────────
    ("Operating Systems",  "OS401",  2, 3, True,  "T012", 4),
    ("Algorithm Design",   "ALG401", 2, 0, False, "T009", 4),
    ("Software Engineering", "SE401", 2, 0, False, "T005", 4),
    ("Professional Ethics", "ETH401", 2, 0, False, "T004", 4),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _existing_employee_ids():
    return {t["employee_id"] for t in db.get_all_teachers()}


def _existing_subject_codes():
    return {s["subject_code"] for s in db.get_all_subjects()}


def _existing_room_keys():
    """Return a set of (room_number, section) tuples already in the DB."""
    return {(r["room_number"], r["section"]) for r in db.get_all_rooms()}


def _existing_section_keys():
    return {(s["year_level"], s["section_name"]) for s in db.get_all_sections()}


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_teachers():
    existing = _existing_employee_ids()
    inserted = 0
    for name, emp_id in TEACHERS:
        if emp_id in existing:
            print(f"  [skip] Teacher {emp_id} ({name}) already exists.")
            continue
        db.create_teacher(name, emp_id)
        print(f"  [+] Teacher: {name} ({emp_id})")
        inserted += 1
    return inserted


def seed_rooms():
    existing = _existing_room_keys()
    inserted = 0
    for room_number, room_name, year_level, section, is_lab in ROOMS:
        if (room_number, section) in existing:
            print(f"  [skip] Room {room_number}/{section!r} already exists.")
            continue
        db.create_room(room_number, room_name, year_level, section, is_lab)
        lab_tag = " [LAB]" if is_lab else ""
        print(f"  [+] Room: {room_number} – {room_name}{lab_tag}")
        inserted += 1
    return inserted


def seed_sections():
    existing = _existing_section_keys()
    # Build a room_number → room_id map (non-lab rooms only).
    room_map = {r["room_number"]: r["id"] for r in db.get_regular_rooms()}
    inserted = 0
    for year_level, section_name, room_number in SECTIONS:
        if (year_level, section_name) in existing:
            print(f"  [skip] Section Year {year_level} {section_name} already exists.")
            continue
        room_id = room_map.get(room_number)
        db.create_section(year_level, section_name, room_id)
        print(f"  [+] Section: Year {year_level} – {section_name} (room {room_number})")
        inserted += 1
    return inserted


def seed_subjects():
    existing_codes = _existing_subject_codes()
    # Build employee_id → teacher_id map.
    teacher_map = {t["employee_id"]: t["id"] for t in db.get_all_teachers()}
    inserted = 0
    new_ids_by_code = {}
    for (subject_name, subject_code, lecture_hours, lab_hours, has_lab,
         teacher_emp_id, year_level) in SUBJECTS:
        if subject_code in existing_codes:
            print(f"  [skip] Subject {subject_code} already exists.")
            # Still track the id for teacher linking.
            for s in db.get_all_subjects():
                if s["subject_code"] == subject_code:
                    new_ids_by_code[subject_code] = s["id"]
                    break
            continue
        teacher_id = teacher_map.get(teacher_emp_id)
        sid = db.create_subject(
            subject_name, subject_code, lecture_hours, lab_hours,
            has_lab, teacher_id, year_level,
        )
        new_ids_by_code[subject_code] = sid
        lab_tag = f" [LAB {lab_hours}h]" if has_lab else ""
        print(f"  [+] Subject: {subject_code} – {subject_name}{lab_tag}  (Year {year_level})")
        inserted += 1
    return inserted, new_ids_by_code


def link_teacher_subjects(new_ids_by_code):
    """
    Update each teacher's subjects list with the IDs of their assigned subjects.
    Only adds IDs that are not already listed (idempotent).
    """
    # Build employee_id → teacher record map.
    teacher_map = {t["employee_id"]: t for t in db.get_all_teachers()}
    # Build (teacher_employee_id) → [subject_codes] from SUBJECTS list.
    from collections import defaultdict
    teacher_codes = defaultdict(list)
    for (_, code, _, _, _, emp_id, _) in SUBJECTS:
        teacher_codes[emp_id].append(code)

    for emp_id, codes in teacher_codes.items():
        teacher = teacher_map.get(emp_id)
        if not teacher:
            continue
        existing_sids = set(teacher.get("subjects") or [])
        new_sids = {new_ids_by_code[c] for c in codes if c in new_ids_by_code}
        merged = sorted(existing_sids | new_sids)
        if merged != sorted(existing_sids):
            db.update_teacher(
                teacher["id"], teacher["name"], teacher["employee_id"],
                merged, teacher.get("preferred_vacant") or [],
            )
            print(f"  [link] {teacher['name']} ← {len(new_sids)} subject(s)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    db.init_db()

    print("\n=== Seeding Teachers ===")
    seed_teachers()

    print("\n=== Seeding Rooms ===")
    seed_rooms()

    print("\n=== Seeding Sections ===")
    seed_sections()

    print("\n=== Seeding Subjects ===")
    _, subject_id_map = seed_subjects()

    print("\n=== Linking Subjects to Teachers ===")
    link_teacher_subjects(subject_id_map)

    print("\nDone.  Sample data is ready.\n")


if __name__ == "__main__":
    main()
