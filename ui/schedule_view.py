from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QLabel,
    QButtonGroup, QRadioButton, QGroupBox, QProgressDialog, QAbstractItemView,
    QSpinBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
import db.database as db
from scheduler.engine import ScheduleEngine


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# 8 one-hour slots: morning 7:30–11:30, afternoon 1:00–5:00
TIME_SLOT_LABELS = db.TIME_SLOT_LABELS

COLOR_LAB = QColor(173, 216, 230)    # light blue  – laboratory block
COLOR_LEC = QColor(200, 230, 200)    # light green – lecture block


def _slot_range_text(start_slot, duration):
    start_idx = max(0, min(start_slot - 1, len(db.TIME_SLOT_STARTS) - 1))
    end_idx = max(0, min(start_slot + duration - 2, len(db.TIME_SLOT_ENDS) - 1))
    s = db.TIME_SLOT_STARTS[start_idx]
    e = db.TIME_SLOT_ENDS[end_idx]
    return f"{s} – {e}"


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

        # Days per week setting
        days_layout = QHBoxLayout()
        days_layout.addWidget(QLabel("Days/Week:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 5)
        self.days_spin.setValue(int(db.get_setting("days_per_week", 5)))
        self.days_spin.setToolTip(
            "Number of school days per week.\n"
            "If fewer than 5, the remaining days are not scheduled\n"
            "(teachers/students hold online classes on those days)."
        )
        days_layout.addWidget(self.days_spin)
        controls.addLayout(days_layout)

        self.generate_btn = QPushButton("Generate Schedule")
        self.generate_btn.setMinimumWidth(150)
        self.clear_btn = QPushButton("Clear Schedule")
        self.view_btn = QPushButton("View")
        controls.addStretch()
        controls.addWidget(self.view_btn)
        controls.addWidget(self.generate_btn)
        controls.addWidget(self.clear_btn)
        layout.addLayout(controls)

        # ── Legend ────────────────────────────────────────────────────────────
        legend_layout = QHBoxLayout()
        lab_lbl = QLabel("  Lab  ")
        lab_lbl.setAutoFillBackground(True)
        p = lab_lbl.palette()
        p.setColor(lab_lbl.backgroundRole(), COLOR_LAB)
        lab_lbl.setPalette(p)
        lec_lbl = QLabel("  Lecture  ")
        lec_lbl.setAutoFillBackground(True)
        p2 = lec_lbl.palette()
        p2.setColor(lec_lbl.backgroundRole(), COLOR_LEC)
        lec_lbl.setPalette(p2)
        legend_layout.addWidget(QLabel("Legend:"))
        legend_layout.addWidget(lab_lbl)
        legend_layout.addWidget(lec_lbl)
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        # ── Schedule grid ─────────────────────────────────────────────────────
        self.table = QTableWidget(8, 5)
        self.table.setHorizontalHeaderLabels(DAY_NAMES)
        self.table.setVerticalHeaderLabels(TIME_SLOT_LABELS)
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
        self.days_spin.valueChanged.connect(self._on_days_changed)

        self.worker = None
        self.refresh()

    def _on_days_changed(self, value):
        db.set_setting("days_per_week", value)
        self._resize_table_columns(value)

    def _resize_table_columns(self, days_per_week):
        self.table.setColumnCount(days_per_week)
        self.table.setHorizontalHeaderLabels(DAY_NAMES[:days_per_week])
        self.load_schedule()

    def refresh(self):
        days = int(db.get_setting("days_per_week", 5))
        self.days_spin.blockSignals(True)
        self.days_spin.setValue(days)
        self.days_spin.blockSignals(False)
        self._resize_table_columns(days)
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
                label = r["room_number"]
                if r.get("room_name"):
                    label += f" – {r['room_name']}"
                if r.get("is_lab"):
                    label += " [Lab]"
                self.selector_combo.addItem(label, r["id"])

        self.selector_combo.blockSignals(False)
        self.load_schedule()

    def load_schedule(self):
        self._reset_spans()
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
        rooms = {r["id"]: r for r in db.get_all_rooms()}

        days_per_week = self.table.columnCount()

        for entry in entries:
            day = entry["day_of_week"]        # 1-5
            start_slot = entry["start_slot"]  # 1-8
            duration = entry.get("duration", 1)
            is_lab = bool(entry.get("is_lab", 0))

            col = day - 1
            row = start_slot - 1

            if col >= days_per_week:
                continue  # day is outside active range

            subject_id = entry.get("subject_id")
            teacher_id = entry.get("teacher_id")
            room_id = entry.get("room_id")

            if subject_id:
                subj = subjects.get(subject_id)
                subj_name = subj["subject_name"] if subj else f"Subject #{subject_id}"
                time_range = _slot_range_text(start_slot, duration)
                room_info = rooms.get(room_id)
                room_label = room_info["room_number"] if room_info else ""

                if self.radio_teacher.isChecked():
                    cell_text = (
                        f"{subj_name}\n"
                        f"[{sec_map.get(entry.get('section_id'), '')}]\n"
                        f"{time_range}"
                    )
                elif self.radio_room.isChecked():
                    teacher_name = teachers.get(teacher_id, "")
                    cell_text = (
                        f"{subj_name}\n"
                        f"{teacher_name}\n"
                        f"[{sec_map.get(entry.get('section_id'), '')}]\n"
                        f"{time_range}"
                    )
                else:
                    teacher_name = teachers.get(teacher_id, "")
                    block_type = "LAB" if is_lab else "Lec"
                    cell_text = (
                        f"{subj_name}\n"
                        f"{teacher_name}\n"
                        f"{room_label}  [{block_type}]\n"
                        f"{time_range}"
                    )

                item = QTableWidgetItem(cell_text)
                item.setBackground(COLOR_LAB if is_lab else COLOR_LEC)
            else:
                item = QTableWidgetItem("")
                item.setBackground(QColor(255, 255, 255))

            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            if duration > 1:
                self.table.setSpan(row, col, duration, 1)

            self.table.setItem(row, col, item)

    def _reset_spans(self):
        for r in range(8):
            for c in range(self.table.columnCount()):
                self.table.setSpan(r, c, 1, 1)

    def clear_table(self):
        for r in range(8):
            for c in range(self.table.columnCount()):
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
            f"Total assigned blocks: {assigned}",
            "",
        ]
        if sections:
            lines.append("Sections processed:")
            for s in sections:
                lines.append(f"  • Year {s['year_level']} - {s['section']}: {s['assigned']} blocks")
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
            self._reset_spans()
            self.clear_table()
            QMessageBox.information(self, "Cleared", "All schedule entries have been cleared.")
