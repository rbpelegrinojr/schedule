from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar,
)
from ui.teachers_form import TeachersForm
from ui.rooms_form import RoomsForm
from ui.sections_form import SectionsForm
from ui.subjects_form import SubjectsForm
from ui.schedule_view import ScheduleView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("School Schedule Manager")
        self.setMinimumSize(1000, 700)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.teachers_form = TeachersForm()
        self.rooms_form = RoomsForm()
        self.sections_form = SectionsForm()
        self.subjects_form = SubjectsForm()
        self.schedule_view = ScheduleView()

        self.tabs.addTab(self.teachers_form, "Teachers")
        self.tabs.addTab(self.rooms_form, "Rooms")
        self.tabs.addTab(self.sections_form, "Sections")
        self.tabs.addTab(self.subjects_form, "Subjects")
        self.tabs.addTab(self.schedule_view, "Schedule")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()
        self.status_bar.showMessage(f"Viewing: {self.tabs.tabText(index)}")
