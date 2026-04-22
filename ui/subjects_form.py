from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QSpinBox, QComboBox, QCheckBox,
    QAbstractItemView,
)
from PySide6.QtCore import Qt
import db.database as db


class SubjectDialog(QDialog):
    def __init__(self, parent=None, subject_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add Subject" if subject_data is None else "Edit Subject")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.subject_name_edit = QLineEdit()
        self.subject_code_edit = QLineEdit()

        self.lecture_hours_spin = QSpinBox()
        self.lecture_hours_spin.setRange(0, 8)
        self.lecture_hours_spin.setValue(2)

        self.has_lab_check = QCheckBox("This subject has a laboratory component")
        self.has_lab_check.toggled.connect(self._on_has_lab_toggled)

        self.lab_hours_spin = QSpinBox()
        self.lab_hours_spin.setRange(1, 8)
        self.lab_hours_spin.setValue(3)
        self.lab_hours_spin.setEnabled(False)

        self.teacher_combo = QComboBox()
        self.teacher_combo.addItem("-- No Teacher --", None)
        for t in db.get_all_teachers():
            self.teacher_combo.addItem(f"{t['name']} ({t['employee_id']})", t["id"])

        self.year_level_combo = QComboBox()
        self.year_level_combo.addItem("-- All Levels --", None)
        for y in range(1, 5):
            self.year_level_combo.addItem(f"Year {y}", y)

        form.addRow("Subject Name:", self.subject_name_edit)
        form.addRow("Subject Code:", self.subject_code_edit)
        form.addRow("Lecture Hours/Week:", self.lecture_hours_spin)
        form.addRow("Has Lab:", self.has_lab_check)
        form.addRow("Lab Hours/Week:", self.lab_hours_spin)
        form.addRow("Teacher:", self.teacher_combo)
        form.addRow("Year Level:", self.year_level_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if subject_data:
            self.subject_name_edit.setText(subject_data.get("subject_name", ""))
            self.subject_code_edit.setText(subject_data.get("subject_code", ""))
            self.lecture_hours_spin.setValue(subject_data.get("lecture_hours", 2))
            has_lab = bool(subject_data.get("has_lab", 0))
            self.has_lab_check.setChecked(has_lab)
            self.lab_hours_spin.setValue(subject_data.get("lab_hours", 3))
            self.lab_hours_spin.setEnabled(has_lab)
            teacher_id = subject_data.get("teacher_id")
            if teacher_id:
                for i in range(self.teacher_combo.count()):
                    if self.teacher_combo.itemData(i) == teacher_id:
                        self.teacher_combo.setCurrentIndex(i)
                        break
            year_level = subject_data.get("year_level")
            if year_level:
                for i in range(self.year_level_combo.count()):
                    if self.year_level_combo.itemData(i) == year_level:
                        self.year_level_combo.setCurrentIndex(i)
                        break

    def _on_has_lab_toggled(self, checked):
        self.lab_hours_spin.setEnabled(checked)

    def validate_and_accept(self):
        if not self.subject_name_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Subject Name is required.")
            return
        if not self.subject_code_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Subject Code is required.")
            return
        if self.lecture_hours_spin.value() == 0 and not self.has_lab_check.isChecked():
            QMessageBox.warning(self, "Validation",
                                "A subject must have at least 1 lecture hour or a lab component.")
            return
        self.accept()

    def get_data(self):
        has_lab = self.has_lab_check.isChecked()
        return {
            "subject_name": self.subject_name_edit.text().strip(),
            "subject_code": self.subject_code_edit.text().strip(),
            "lecture_hours": self.lecture_hours_spin.value(),
            "lab_hours": self.lab_hours_spin.value() if has_lab else 0,
            "has_lab": has_lab,
            "teacher_id": self.teacher_combo.currentData(),
            "year_level": self.year_level_combo.currentData(),
        }


class SubjectsForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add Subject")
        self.edit_btn = QPushButton("Edit Subject")
        self.delete_btn = QPushButton("Delete Subject")
        self.add_btn.clicked.connect(self.add_subject)
        self.edit_btn.clicked.connect(self.edit_subject)
        self.delete_btn.clicked.connect(self.delete_subject)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Subject Name", "Code", "Lec Hrs", "Lab Hrs", "Teacher", "Year Level"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        subjects = db.get_all_subjects()
        teachers = {t["id"]: t["name"] for t in db.get_all_teachers()}
        self.table.setRowCount(0)
        for s in subjects:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(s["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(s["subject_name"]))
            self.table.setItem(row, 2, QTableWidgetItem(s["subject_code"]))
            self.table.setItem(row, 3, QTableWidgetItem(str(s.get("lecture_hours", 2))))
            lab_hrs = s.get("lab_hours", 0)
            lab_label = str(lab_hrs) if s.get("has_lab") else "—"
            self.table.setItem(row, 4, QTableWidgetItem(lab_label))
            teacher_name = teachers.get(s.get("teacher_id"), "")
            self.table.setItem(row, 5, QTableWidgetItem(teacher_name))
            yr = s.get("year_level")
            self.table.setItem(row, 6, QTableWidgetItem(f"Year {yr}" if yr else "All"))

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def add_subject(self):
        dialog = SubjectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                db.create_subject(
                    data["subject_name"], data["subject_code"],
                    data["lecture_hours"], data["lab_hours"], data["has_lab"],
                    data["teacher_id"], data["year_level"],
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_subject(self):
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "Select", "Please select a subject to edit.")
            return
        subject = db.get_subject_by_id(sid)
        if subject is None:
            return
        dialog = SubjectDialog(self, subject_data=subject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                db.update_subject(
                    sid, data["subject_name"], data["subject_code"],
                    data["lecture_hours"], data["lab_hours"], data["has_lab"],
                    data["teacher_id"], data["year_level"],
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_subject(self):
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "Select", "Please select a subject to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm", "Delete this subject?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_subject(sid)
            self.refresh()
