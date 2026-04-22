from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QLabel,
    QButtonGroup, QRadioButton, QGroupBox, QProgressDialog, QAbstractItemView,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
import db.database as db
from scheduler.engine import ScheduleEngine


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIOD_LABELS = [f"Period {i}" for i in range(1, 9)]


class GenerateWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            engine = ScheduleEngine()
            result = engine.generate()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ScheduleView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # ── Top controls ──────────────────────────────────────────────────────
        controls = QHBoxLayout()

        mode_group = QGroupBox("View By")
        mode_layout = QHBoxLayout(mode_group)
        self.btn_group = QButtonGroup(self)
        self.radio_section = QRadioButton("Section")
        self.radio_teacher = QRadioButton("Teacher")
        self.radio_room = QRadioButton("Room")
        self.radio_section.setChecked(True)
        self.btn_group.addButton(self.radio_section, 0)
        self.btn_group.addButton(self.radio_teacher, 1)
        self.btn_group.addButton(self.radio_room, 2)
        mode_layout.addWidget(self.radio_section)
        mode_layout.addWidget(self.radio_teacher)
        mode_layout.addWidget(self.radio_room)
        controls.addWidget(mode_group)

        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select:"))
        self.selector_combo = QComboBox()
        self.selector_combo.setMinimumWidth(200)
        selector_layout.addWidget(self.selector_combo)
        controls.addLayout(selector_layout)

        self.generate_btn = QPushButton("Generate Schedule")
        self.generate_btn.setMinimumWidth(150)
        self.clear_btn = QPushButton("Clear Schedule")
        self.view_btn = QPushButton("View")
        controls.addStretch()
        controls.addWidget(self.view_btn)
        controls.addWidget(self.generate_btn)
        controls.addWidget(self.clear_btn)
        layout.addLayout(controls)

        # ── Schedule grid ─────────────────────────────────────────────────────
        self.table = QTableWidget(8, 5)
        self.table.setHorizontalHeaderLabels(DAY_NAMES)
        self.table.setVerticalHeaderLabels(PERIOD_LABELS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setMinimumHeight(400)
        layout.addWidget(self.table)

        # ── Signals ───────────────────────────────────────────────────────────
        self.btn_group.idClicked.connect(self.on_mode_changed)
        self.selector_combo.currentIndexChanged.connect(self.load_schedule)
        self.view_btn.clicked.connect(self.load_schedule)
        self.generate_btn.clicked.connect(self.generate_schedule)
        self.clear_btn.clicked.connect(self.clear_schedule)

        self.worker = None
        self.refresh()

    def refresh(self):
        self.populate_selector()

    def on_mode_changed(self, _mode_id):
        self.populate_selector()

    def populate_selector(self):
        self.selector_combo.blockSignals(True)
        self.selector_combo.clear()

        if self.radio_section.isChecked():
            for s in db.get_all_sections():
                label = f"Year {s['year_level']} - {s['section_name']}"
                self.selector_combo.addItem(label, s["id"])
        elif self.radio_teacher.isChecked():
            for t in db.get_all_teachers():
                self.selector_combo.addItem(f"{t['name']} ({t['employee_id']})", t["id"])
        else:
            for r in db.get_all_rooms():
                self.selector_combo.addItem(f"{r['room_number']} - {r['section']}", r["id"])

        self.selector_combo.blockSignals(False)
        self.load_schedule()

    def load_schedule(self):
        self.clear_table()
        selected_id = self.selector_combo.currentData()
        if selected_id is None:
            return

        if self.radio_section.isChecked():
            entries = db.get_schedule_by_section(selected_id)
        elif self.radio_teacher.isChecked():
            entries = db.get_schedule_by_teacher(selected_id)
        else:
            entries = db.get_schedule_by_room(selected_id)

        teachers = {t["id"]: t["name"] for t in db.get_all_teachers()}
        subjects = {s["id"]: s for s in db.get_all_subjects()}
        sec_map = {s["id"]: s["section_name"] for s in db.get_all_sections()}

        for entry in entries:
            day = entry["day_of_week"]   # 1-5
            period = entry["period"]      # 1-8
            col = day - 1
            row = period - 1

            subject_id = entry.get("subject_id")
            teacher_id = entry.get("teacher_id")

            if subject_id:
                subj = subjects.get(subject_id)
                subj_name = subj["subject_name"] if subj else f"Subject #{subject_id}"
                teacher_name = teachers.get(teacher_id, "")

                if self.radio_teacher.isChecked():
                    cell_text = f"{subj_name}\n[{sec_map.get(entry.get('section_id'), '')}]"
                else:
                    cell_text = f"{subj_name}\n{teacher_name}"

                item = QTableWidgetItem(cell_text)
                item.setBackground(QColor(200, 230, 200))
            else:
                item = QTableWidgetItem("VACANT")
                item.setBackground(QColor(245, 245, 245))
                item.setForeground(QColor(150, 150, 150))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, col, item)

    def clear_table(self):
        for r in range(8):
            for c in range(5):
                item = QTableWidgetItem("")
                item.setBackground(QColor(255, 255, 255))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)

    def generate_schedule(self):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "Busy", "Schedule generation is already in progress.")
            return

        reply = QMessageBox.question(
            self, "Generate Schedule",
            "This will replace the existing schedule. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.generate_btn.setEnabled(False)
        self.progress = QProgressDialog("Generating schedule...", None, 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.show()

        self.worker = GenerateWorker()
        self.worker.finished.connect(self.on_generate_done)
        self.worker.error.connect(self.on_generate_error)
        self.worker.start()

    def on_generate_done(self, result):
        self.progress.close()
        self.generate_btn.setEnabled(True)
        if self.worker:
            self.worker.wait()

        assigned = result.get("assigned", 0)
        sections = result.get("sections", [])
        errors = result.get("errors", [])

        lines = [
            "Schedule generated successfully!",
            "",
            f"Total assigned periods: {assigned}",
            "",
        ]
        if sections:
            lines.append("Sections processed:")
            for s in sections:
                lines.append(f"  • Year {s['year_level']} - {s['section']}: {s['assigned']} periods")
        if errors:
            lines += ["", f"Warnings/Errors ({len(errors)}):"]
            for e in errors[:10]:
                lines.append(f"  ⚠ {e}")
            if len(errors) > 10:
                lines.append(f"  ... and {len(errors) - 10} more.")

        QMessageBox.information(self, "Schedule Generated", "\n".join(lines))
        self.load_schedule()

    def on_generate_error(self, error_msg):
        self.progress.close()
        self.generate_btn.setEnabled(True)
        if self.worker:
            self.worker.wait()
        QMessageBox.critical(self, "Error", f"Failed to generate schedule:\n{error_msg}")

    def clear_schedule(self):
        reply = QMessageBox.question(
            self, "Clear Schedule",
            "Clear all schedule entries?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.clear_schedules()
            self.clear_table()
            QMessageBox.information(self, "Cleared", "All schedule entries have been cleared.")
