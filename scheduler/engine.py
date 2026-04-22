import random
from db import database as db


def _valid_starts(duration):
    """Return valid start slots for a block of given duration.

    Slots 1-4 are the morning session (7:30-11:30).
    Slots 5-8 are the afternoon session (1:00-5:00).
    A block must not cross the lunch break between the two sessions.
    """
    valid = []
    for start in range(1, 9):
        end = start + duration - 1
        if end <= 4:          # morning block
            valid.append(start)
        elif start >= 5 and end <= 8:  # afternoon block
            valid.append(start)
    return valid


def _is_occupied(occupied, entity_id, day, start_slot, duration):
    return any(
        (entity_id, day, start_slot + i) in occupied
        for i in range(duration)
    )


def _mark_occupied(occupied, entity_id, day, start_slot, duration):
    for i in range(duration):
        occupied[(entity_id, day, start_slot + i)] = True


class ScheduleEngine:

    def generate(self):
        """
        Time-slot based schedule generator.
        - Lab subjects are assigned first: 3-hour block in a lab room.
        - Lecture hours are placed on a DIFFERENT day from the lab.
        - Non-lab subjects get a lecture block of the configured hours.
        - Days per week is configurable via Settings.

        Returns dict: {"assigned": int, "sections": list, "errors": list}
        """
        db.clear_schedules()

        sections = db.get_all_sections()
        if not sections:
            return {"assigned": 0, "sections": [], "errors": ["No sections found."]}

        days_per_week = int(db.get_setting("days_per_week", 5))
        active_days = list(range(1, days_per_week + 1))

        lab_rooms = db.get_lab_rooms()

        # Global conflict tracking: (entity_id, day, slot) -> True
        teacher_occupied = {}
        room_occupied = {}

        total_assigned = 0
        section_summaries = []
        errors = []

        for section in sections:
            section_id = section["id"]
            year_level = section["year_level"]
            room_id = section["room_id"]

            if not room_id:
                errors.append(
                    f"Section '{section['section_name']}' has no classroom assigned. Skipping."
                )
                continue

            subjects = db.get_subjects_by_year_level(year_level)
            if not subjects:
                errors.append(
                    f"No subjects found for Year {year_level} "
                    f"(section '{section['section_name']}')."
                )
                continue

            # Per-section slot occupancy
            section_occupied = {}
            assigned_count = 0

            # Process lab subjects first so lab rooms are allocated before lecture rooms
            lab_subjects = [s for s in subjects if s.get("has_lab")]
            non_lab_subjects = [s for s in subjects if not s.get("has_lab")]
            random.shuffle(lab_subjects)
            random.shuffle(non_lab_subjects)

            for subj in lab_subjects + non_lab_subjects:
                teacher_id = subj.get("teacher_id")
                lecture_hours = subj.get("lecture_hours") or 2
                lab_hours = subj.get("lab_hours") or 3
                has_lab = bool(subj.get("has_lab", 0))

                lab_day = None  # the day this subject's lab is scheduled

                # ── Assign lab block ─────────────────────────────────────────
                if has_lab and lab_rooms and lab_hours > 0:
                    valid_starts = _valid_starts(lab_hours)
                    days_shuffled = active_days[:]
                    random.shuffle(days_shuffled)
                    lab_rooms_shuffled = lab_rooms[:]
                    random.shuffle(lab_rooms_shuffled)

                    lab_assigned = False
                    for day in days_shuffled:
                        if lab_assigned:
                            break
                        for lab_room in lab_rooms_shuffled:
                            if lab_assigned:
                                break
                            lab_room_id = lab_room["id"]
                            starts_shuffled = valid_starts[:]
                            random.shuffle(starts_shuffled)
                            for start in starts_shuffled:
                                if _is_occupied(section_occupied, section_id, day, start, lab_hours):
                                    continue
                                if teacher_id and _is_occupied(teacher_occupied, teacher_id, day, start, lab_hours):
                                    continue
                                if _is_occupied(room_occupied, lab_room_id, day, start, lab_hours):
                                    continue
                                db.save_schedule_entry(
                                    section_id=section_id,
                                    subject_id=subj["id"],
                                    teacher_id=teacher_id,
                                    room_id=lab_room_id,
                                    day_of_week=day,
                                    start_slot=start,
                                    duration=lab_hours,
                                    is_lab=True,
                                )
                                _mark_occupied(section_occupied, section_id, day, start, lab_hours)
                                if teacher_id:
                                    _mark_occupied(teacher_occupied, teacher_id, day, start, lab_hours)
                                _mark_occupied(room_occupied, lab_room_id, day, start, lab_hours)
                                lab_day = day
                                assigned_count += 1
                                lab_assigned = True
                                break

                    if not lab_assigned:
                        errors.append(
                            f"Could not assign lab for '{subj['subject_name']}' "
                            f"(section '{section['section_name']}')."
                        )

                # ── Assign lecture block ─────────────────────────────────────
                if lecture_hours > 0:
                    valid_starts = _valid_starts(lecture_hours)
                    # Exclude the lab day so lecture is on a different day
                    days_for_lecture = [d for d in active_days if d != lab_day]
                    random.shuffle(days_for_lecture)

                    lec_assigned = False
                    for day in days_for_lecture:
                        starts_shuffled = valid_starts[:]
                        random.shuffle(starts_shuffled)
                        for start in starts_shuffled:
                            if _is_occupied(section_occupied, section_id, day, start, lecture_hours):
                                continue
                            if teacher_id and _is_occupied(teacher_occupied, teacher_id, day, start, lecture_hours):
                                continue
                            if _is_occupied(room_occupied, room_id, day, start, lecture_hours):
                                continue
                            db.save_schedule_entry(
                                section_id=section_id,
                                subject_id=subj["id"],
                                teacher_id=teacher_id,
                                room_id=room_id,
                                day_of_week=day,
                                start_slot=start,
                                duration=lecture_hours,
                                is_lab=False,
                            )
                            _mark_occupied(section_occupied, section_id, day, start, lecture_hours)
                            if teacher_id:
                                _mark_occupied(teacher_occupied, teacher_id, day, start, lecture_hours)
                            _mark_occupied(room_occupied, room_id, day, start, lecture_hours)
                            assigned_count += 1
                            lec_assigned = True
                            break
                        if lec_assigned:
                            break

                    if not lec_assigned:
                        errors.append(
                            f"Could not assign lecture for '{subj['subject_name']}' "
                            f"(section '{section['section_name']}')."
                        )

            total_assigned += assigned_count
            section_summaries.append(
                {
                    "section": section["section_name"],
                    "year_level": year_level,
                    "assigned": assigned_count,
                }
            )

        return {
            "assigned": total_assigned,
            "sections": section_summaries,
            "errors": errors,
        }
