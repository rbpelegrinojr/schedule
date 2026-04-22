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
        # When running as a frozen windowed exe there is no console, so surface
        # the error in a dialog box so the user is not left wondering.
        import traceback
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Setup Warning")
        msg.setText(
            "Sample data could not be loaded automatically.\n\n"
            "The application will still open, but you may need to add\n"
            "teachers, rooms, sections, and subjects manually.\n\n"
            f"Details: {exc}"
        )
        msg.setDetailedText(traceback.format_exc())
        msg.exec()


if __name__ == "__main__":
    init_db()
    _seed_if_empty()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
