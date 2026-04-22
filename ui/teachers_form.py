from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QListWidget, QListWidgetItem, QDialogButtonBox,
    QLabel, QGroupBox, QSpinBox, QComboBox, QAbstractItemView,
)
from PySide6.QtCore import Qt
import db.database as db


class PreferredVacantEditor(QWidget):
    """Manages a list of preferred-vacant day/period combos for a teacher."""

    DAY_NAMES = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday"}

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Day", "Time Slot", "Remove"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(150)
        layout.addWidget(self.table)

        add_row = QHBoxLayout()
        self.day_combo = QComboBox()
        for d, name in self.DAY_NAMES.items():
            self.day_combo.addItem(name, d)
        self.period_spin = QSpinBox()
        self.period_spin.setRange(1, 8)
        self.add_btn = QPushButton("Add Vacant Time")
        self.add_btn.clicked.connect(self.add_entry)
        add_row.addWidget(QLabel("Day:"))
        add_row.addWidget(self.day_combo)
        add_row.addWidget(QLabel("Time Slot (1-8):"))
        add_row.addWidget(self.period_spin)
        add_row.addWidget(self.add_btn)
        layout.addLayout(add_row)

    def add_entry(self):
        day = self.day_combo.currentData()
        period = self.period_spin.value()
        # Prevent duplicates
        for r in range(self.table.rowCount()):
            d_item = self.table.item(r, 0)
            p_item = self.table.item(r, 1)
            if d_item and p_item:
                if (
                    int(d_item.data(Qt.ItemDataRole.UserRole)) == day
                    and int(p_item.text()) == period
                ):
                    return
        row = self.table.rowCount()
        self.table.insertRow(row)
        day_item = QTableWidgetItem(self.DAY_NAMES[day])
        day_item.setData(Qt.ItemDataRole.UserRole, day)
        day_item.setFlags(day_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        period_item = QTableWidgetItem(str(period))
        period_item.setFlags(period_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        remove_btn = QPushButton("X")
        remove_btn.clicked.connect(self._make_remove_handler())
        self.table.setItem(row, 0, day_item)
        self.table.setItem(row, 1, period_item)
        self.table.setCellWidget(row, 2, remove_btn)

    def _make_remove_handler(self):
        """Return a slot that removes the row containing the clicked button."""
        def handler():
            btn = self.sender()
            for r in range(self.table.rowCount()):
                if self.table.cellWidget(r, 2) is btn:
                    self.table.removeRow(r)
                    return
        return handler

    def get_vacant_list(self):
        result = []
        for r in range(self.table.rowCount()):
            d_item = self.table.item(r, 0)
            p_item = self.table.item(r, 1)
            if d_item and p_item:
                result.append(
                    {
                        "day": int(d_item.data(Qt.ItemDataRole.UserRole)),
                        "period": int(p_item.text()),
                    }
                )
        return result

    def set_vacant_list(self, vacant_list):
        self.table.setRowCount(0)
        for combo in vacant_list:
            day = combo.get("day", 1)
            period = combo.get("period", 1)
            row = self.table.rowCount()
            self.table.insertRow(row)
            day_item = QTableWidgetItem(self.DAY_NAMES.get(day, str(day)))
            day_item.setData(Qt.ItemDataRole.UserRole, day)
            day_item.setFlags(day_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            period_item = QTableWidgetItem(str(period))
            period_item.setFlags(period_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            remove_btn = QPushButton("X")
            remove_btn.clicked.connect(self._make_remove_handler())
            self.table.setItem(row, 0, day_item)
            self.table.setItem(row, 1, period_item)
            self.table.setCellWidget(row, 2, remove_btn)


class TeacherDialog(QDialog):
    def __init__(self, parent=None, teacher_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add Teacher" if teacher_data is None else "Edit Teacher")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.emp_id_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)
        form.addRow("Employee ID:", self.emp_id_edit)
        layout.addLayout(form)

        # Subjects group
        subj_group = QGroupBox("Assigned Subjects")
        subj_layout = QVBoxLayout(subj_group)
        self.subjects_list = QListWidget()
        self.subjects_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for s in db.get_all_subjects():
            item = QListWidgetItem(f"{s['subject_code']} - {s['subject_name']}")
            item.setData(Qt.ItemDataRole.UserRole, s["id"])
            item.setCheckState(Qt.CheckState.Unchecked)
            self.subjects_list.addItem(item)
        subj_layout.addWidget(self.subjects_list)
        layout.addWidget(subj_group)

        # Preferred vacant times
        vacant_group = QGroupBox("Preferred Vacant Times")
        vacant_layout = QVBoxLayout(vacant_group)
        self.vacant_editor = PreferredVacantEditor()
        vacant_layout.addWidget(self.vacant_editor)
        layout.addWidget(vacant_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if teacher_data:
            self.name_edit.setText(teacher_data.get("name", ""))
            self.emp_id_edit.setText(teacher_data.get("employee_id", ""))
            assigned_ids = set(teacher_data.get("subjects", []))
            for i in range(self.subjects_list.count()):
                item = self.subjects_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) in assigned_ids:
                    item.setCheckState(Qt.CheckState.Checked)
            self.vacant_editor.set_vacant_list(teacher_data.get("preferred_vacant", []))

    def validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required.")
            return
        if not self.emp_id_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Employee ID is required.")
            return
        self.accept()

    def get_data(self):
        subjects = [
            self.subjects_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.subjects_list.count())
            if self.subjects_list.item(i).checkState() == Qt.CheckState.Checked
        ]
        return {
            "name": self.name_edit.text().strip(),
            "employee_id": self.emp_id_edit.text().strip(),
            "subjects": subjects,
            "preferred_vacant": self.vacant_editor.get_vacant_list(),
        }


class TeachersForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add Teacher")
        self.edit_btn = QPushButton("Edit Teacher")
        self.delete_btn = QPushButton("Delete Teacher")
        self.add_btn.clicked.connect(self.add_teacher)
        self.edit_btn.clicked.connect(self.edit_teacher)
        self.delete_btn.clicked.connect(self.delete_teacher)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Employee ID", "Subjects Assigned"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        teachers = db.get_all_teachers()
        all_subjects = {s["id"]: s["subject_name"] for s in db.get_all_subjects()}
        self.table.setRowCount(0)
        for t in teachers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(t["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(t["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(t["employee_id"]))
            subj_names = [all_subjects.get(sid, f"#{sid}") for sid in t.get("subjects", [])]
            self.table.setItem(row, 3, QTableWidgetItem(", ".join(subj_names)))

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def add_teacher(self):
        dialog = TeacherDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                db.create_teacher(
                    data["name"], data["employee_id"],
                    data["subjects"], data["preferred_vacant"],
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_teacher(self):
        tid = self._selected_id()
        if tid is None:
            QMessageBox.information(self, "Select", "Please select a teacher to edit.")
            return
        teacher = db.get_teacher_by_id(tid)
        if teacher is None:
            return
        dialog = TeacherDialog(self, teacher_data=teacher)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                db.update_teacher(
                    tid, data["name"], data["employee_id"],
                    data["subjects"], data["preferred_vacant"],
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_teacher(self):
        tid = self._selected_id()
        if tid is None:
            QMessageBox.information(self, "Select", "Please select a teacher to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm", "Delete this teacher?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_teacher(tid)
            self.refresh()
