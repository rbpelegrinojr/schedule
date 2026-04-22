from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QSpinBox, QAbstractItemView,
)
from PySide6.QtCore import Qt
import db.database as db


class RoomDialog(QDialog):
    def __init__(self, parent=None, room_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add Room" if room_data is None else "Edit Room")
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.room_number_edit = QLineEdit()
        self.room_name_edit = QLineEdit()
        self.year_level_spin = QSpinBox()
        self.year_level_spin.setRange(1, 4)
        self.section_edit = QLineEdit()

        form.addRow("Room Number:", self.room_number_edit)
        form.addRow("Room Name:", self.room_name_edit)
        form.addRow("Year Level (1-4):", self.year_level_spin)
        form.addRow("Section:", self.section_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if room_data:
            self.room_number_edit.setText(room_data.get("room_number", ""))
            self.room_name_edit.setText(room_data.get("room_name", ""))
            self.year_level_spin.setValue(room_data.get("year_level", 1))
            self.section_edit.setText(room_data.get("section", ""))

    def validate_and_accept(self):
        if not self.room_number_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Room Number is required.")
            return
        if not self.section_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Section is required.")
            return
        self.accept()

    def get_data(self):
        return {
            "room_number": self.room_number_edit.text().strip(),
            "room_name": self.room_name_edit.text().strip(),
            "year_level": self.year_level_spin.value(),
            "section": self.section_edit.text().strip(),
        }


class RoomsForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add Room")
        self.edit_btn = QPushButton("Edit Room")
        self.delete_btn = QPushButton("Delete Room")
        self.add_btn.clicked.connect(self.add_room)
        self.edit_btn.clicked.connect(self.edit_room)
        self.delete_btn.clicked.connect(self.delete_room)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Room Number", "Room Name", "Year Level", "Section"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        rooms = db.get_all_rooms()
        self.table.setRowCount(0)
        for r in rooms:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(r["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(r["room_number"]))
            self.table.setItem(row, 2, QTableWidgetItem(r.get("room_name", "")))
            self.table.setItem(row, 3, QTableWidgetItem(str(r["year_level"])))
            self.table.setItem(row, 4, QTableWidgetItem(r["section"]))

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def add_room(self):
        dialog = RoomDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                db.create_room(
                    data["room_number"], data["room_name"],
                    data["year_level"], data["section"],
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_room(self):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "Select", "Please select a room to edit.")
            return
        room = db.get_room_by_id(rid)
        if room is None:
            return
        dialog = RoomDialog(self, room_data=room)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                db.update_room(
                    rid, data["room_number"], data["room_name"],
                    data["year_level"], data["section"],
                )
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_room(self):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "Select", "Please select a room to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm", "Delete this room?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_room(rid)
            self.refresh()
