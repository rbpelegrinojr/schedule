# School Schedule Manager

A Python desktop application for managing school timetables, built with **PySide6** and **SQLite**.

---

## Prerequisites

- Python 3.10 or higher
- pip

---

## Installation

```bash
git clone https://github.com/rbpelegrinojr/schedule.git
cd schedule
pip install -r requirements.txt
python main.py
```

The SQLite database file (`schedule.db`) is created automatically in the working directory on first run.

---

## Usage Guide

### Teachers Tab
Add, edit, and delete teachers. Each teacher record stores:
- **Name** and **Employee ID** (unique).
- **Assigned Subjects** – select from the subject list using checkboxes.
- **Preferred Vacant Times** – day/period combinations the teacher prefers to be unscheduled. The scheduler will avoid assigning the teacher during those slots when possible.

### Rooms Tab
Manage classrooms. Each room has a room number, optional room name, year level, and section label. A room must exist before it can be assigned to a section.

### Sections Tab
Define class sections (e.g. "Year 1 – Section A"). Each section must be linked to a room before the scheduler can generate a timetable for it.

### Subjects Tab
Add subjects with:
- **Subject Name** and unique **Subject Code**.
- **Periods per Week** – how many times the subject appears in the weekly schedule (1–8).
- **Teacher** – the teacher assigned to deliver this subject.
- **Year Level** – limits the subject to a specific year level; subjects without a year level are not used during scheduling.

### Schedule Tab
- **View By** – switch between *Section*, *Teacher*, and *Room* perspectives.
- **Select** – choose the entity to display using the dropdown.
- **View** – reload the grid for the selected entity.
- **Generate Schedule** – runs the scheduling engine and fills the timetable. Existing entries are replaced.
- **Clear Schedule** – removes all schedule entries.

The grid shows 8 periods × 5 days. Assigned periods are highlighted in green; vacant slots are shown in light grey.

---

## Database Schema

| Table | Purpose |
|---|---|
| `teachers` | Staff records with JSON-encoded subject IDs and preferred-vacant slots |
| `rooms` | Classroom definitions linked to a year level and section |
| `sections` | Class groups, each assigned a room |
| `subjects` | Subjects with per-week period count, teacher, and year level |
| `schedules` | Generated timetable entries (section × day × period) |

Unique constraints in `schedules` prevent a teacher, room, or section from being double-booked in the same slot.

---

## Scheduling Algorithm

The `ScheduleEngine` in `scheduler/engine.py` uses a **greedy, constraint-based** approach:

1. **Clear** all existing schedule entries.
2. For each **section** (skipped if it has no room or its year level has no subjects):
   - Build a flat list of assignments by repeating each subject according to its `periods_per_week`.
   - Shuffle the assignment list and all available slots for randomness.
   - For each assignment, iterate over available slots ordered so that teacher-preferred-vacant slots come last.
   - A slot is valid when it is free for the section, teacher, and room simultaneously.
   - Remaining unfilled slots are saved as **VACANT** entries.
3. Returns a summary with counts of assigned periods, per-section details, and any unresolvable conflicts.

---

## Limitations & Future Enhancements

- The greedy algorithm does not backtrack; conflicts that could be resolved by reordering earlier assignments are reported as errors instead.
- No support for split or double periods.
- No export to PDF or spreadsheet (planned).
- No drag-and-drop manual editing of the schedule grid (planned).
- Year levels are currently fixed to 1–4 (junior high / senior high structure).
