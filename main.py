import sys
from PySide6.QtWidgets import QApplication
from db.database import init_db, get_all_teachers
from ui.main_window import MainWindow


def _seed_if_empty():
    """Seed sample records on the very first launch (empty database)."""
    if get_all_teachers():
        return  # data already present – nothing to do
    try:
        from seed_data import (
            seed_teachers,
            seed_rooms,
            seed_sections,
            seed_subjects,
            link_teacher_subjects,
        )
        seed_teachers()
        seed_rooms()
        seed_sections()
        _, subject_id_map = seed_subjects()
        link_teacher_subjects(subject_id_map)
    except Exception as exc:
        print(f"Auto-seed warning: {exc}")


if __name__ == "__main__":
    init_db()
    _seed_if_empty()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
