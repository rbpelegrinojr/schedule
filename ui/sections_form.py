from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QSpinBox, QComboBox, QAbstractItemView,
)
from PySide6.QtCore import Qt
import db.database as db


class SectionDialog(QDialog):
    def __init__(self, parent=None, section_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add Section" if section_data is None else "Edit Section")
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.year_level_spin = QSpinBox()
        self.year_level_spin.setRange(1, 4)
        self.section_name_edit = QLineEdit()
        self.room_combo = QComboBox()
        self.room_combo.addItem("-- No Room --", None)
        for room in db.get_all_rooms():
            label = f"{room['room_number']} (Yr{room['year_level']} - {room['section']})"
            self.room_combo.addItem(label, room["id"])

        form.addRow("Year Level (1-4):", self.year_level_spin)
        form.addRow("Section Name:", self.section_name_edit)
        form.addRow("Room:", self.room_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if section_data:
            self.year_level_spin.setValue(section_data.get("year_level", 1))
            self.section_name_edit.setText(section_data.get("section_name", ""))
            room_id = section_data.get("room_id")
            if room_id:
                for i in range(self.room_combo.count()):
                    if self.room_combo.itemData(i) == room_id:
                        self.room_combo.setCurrentIndex(i)
                        break

    def validate_and_accept(self):
        if not self.section_name_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Section Name is required.")
            return
        self.accept()

    def get_data(self):
        return {
            "year_level": self.year_level_spin.value(),
            "section_name": self.section_name_edit.text().strip(),
            "room_id": self.room_combo.currentData(),
        }


class SectionsForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add Section")
        self.edit_btn = QPushButton("Edit Section")
        self.delete_btn = QPushButton("Delete Section")
        self.add_btn.clicked.connect(self.add_section)
        self.edit_btn.clicked.connect(self.edit_section)
        self.delete_btn.clicked.connect(self.delete_section)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Year Level", "Section Name", "Room"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        sections = db.get_all_sections()
        rooms = {r["id"]: r for r in db.get_all_rooms()}
        self.table.setRowCount(0)
        for s in sections:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(s["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(str(s["year_level"])))
            self.table.setItem(row, 2, QTableWidgetItem(s["section_name"]))
            room_id = s.get("room_id")
            room_label = ""
            if room_id and room_id in rooms:
                r = rooms[room_id]
                room_label = f"{r['room_number']} - {r['section']}"
            self.table.setItem(row, 3, QTableWidgetItem(room_label))

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def add_section(self):
        dialog = SectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                db.create_section(data["year_level"], data["section_name"], data["room_id"])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_section(self):
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "Select", "Please select a section to edit.")
            return
        section = db.get_section_by_id(sid)
        if section is None:
            return
        dialog = SectionDialog(self, section_data=section)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                db.update_section(
                    sid, data["year_level"], data["section_name"], data["room_id"]
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_section(self):
        sid = self._selected_id()
        if sid is None:
            QMessageBox.information(self, "Select", "Please select a section to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm", "Delete this section?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_section(sid)
            self.refresh()
