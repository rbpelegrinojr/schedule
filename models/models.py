from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Teacher:
    id: Optional[int] = None
    name: str = ""
    employee_id: str = ""
    subjects: List[int] = field(default_factory=list)
    preferred_vacant: List[dict] = field(default_factory=list)


@dataclass
class Room:
    id: Optional[int] = None
    room_number: str = ""
    room_name: str = ""
    year_level: int = 0
    section: str = ""
    is_lab: bool = False


@dataclass
class Section:
    id: Optional[int] = None
    year_level: int = 1
    section_name: str = ""
    room_id: Optional[int] = None


@dataclass
class Subject:
    id: Optional[int] = None
    subject_name: str = ""
    subject_code: str = ""
    lecture_hours: int = 2
    lab_hours: int = 0
    has_lab: bool = False
    teacher_id: Optional[int] = None
    year_level: Optional[int] = None


@dataclass
class ScheduleEntry:
    id: Optional[int] = None
    section_id: int = 0
    subject_id: Optional[int] = None
    teacher_id: Optional[int] = None
    room_id: int = 0
    day_of_week: int = 1
    start_slot: int = 1
    duration: int = 1
    is_lab: bool = False


@dataclass
class Settings:
    days_per_week: int = 5
