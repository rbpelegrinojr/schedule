import random
from db import database as db


class ScheduleEngine:
    DAYS = [1, 2, 3, 4, 5]
    PERIODS = list(range(1, 9))

    def generate(self):
        """
        Greedy constraint-based schedule generator.
        Returns dict: {"assigned": int, "sections": list, "errors": list}
        """
        db.clear_schedules()

        sections = db.get_all_sections()
        if not sections:
            return {"assigned": 0, "sections": [], "errors": ["No sections found."]}

        teacher_conflicts = {}
        room_conflicts = {}

        total_assigned = 0
        section_summaries = []
        errors = []

        for section in sections:
            section_id = section["id"]
            year_level = section["year_level"]
            room_id = section["room_id"]

            if not room_id:
                errors.append(
                    f"Section {section['section_name']} has no room assigned. Skipping."
                )
                continue

            subjects = db.get_subjects_by_year_level(year_level)
            if not subjects:
                errors.append(
                    f"No subjects for year level {year_level} "
                    f"(section {section['section_name']})."
                )
                continue

            all_slots = [(day, period) for day in self.DAYS for period in self.PERIODS]
            random.shuffle(all_slots)

            # Expand each subject by its periods_per_week
            assignments = []
            for subj in subjects:
                for _ in range(subj["periods_per_week"]):
                    assignments.append(subj)
            random.shuffle(assignments)

            # Build preferred-vacant lookup per teacher
            teacher_preferred_vacant = {}
            for t in db.get_all_teachers():
                pv = set()
                for combo in t.get("preferred_vacant", []):
                    pv.add((combo["day"], combo["period"]))
                teacher_preferred_vacant[t["id"]] = pv

            section_used = set()
            assigned_count = 0

            for subj in assignments:
                teacher_id = subj.get("teacher_id")
                preferred_avoid = (
                    teacher_preferred_vacant.get(teacher_id, set())
                    if teacher_id
                    else set()
                )

                # Non-preferred-vacant slots come first
                sorted_slots = sorted(
                    all_slots,
                    key=lambda s: (1 if s in preferred_avoid else 0, random.random()),
                )

                assigned = False
                for day, period in sorted_slots:
                    if (day, period) in section_used:
                        continue
                    if teacher_id and (teacher_id, day, period) in teacher_conflicts:
                        continue
                    if (room_id, day, period) in room_conflicts:
                        continue

                    db.save_schedule_entry(
                        section_id=section_id,
                        subject_id=subj["id"],
                        teacher_id=teacher_id,
                        room_id=room_id,
                        day_of_week=day,
                        period=period,
                    )
                    section_used.add((day, period))
                    if teacher_id:
                        teacher_conflicts[(teacher_id, day, period)] = True
                    room_conflicts[(room_id, day, period)] = True
                    assigned_count += 1
                    assigned = True
                    break

                if not assigned:
                    errors.append(
                        f"Could not assign subject '{subj['subject_name']}' "
                        f"for section {section['section_name']} (year {year_level})."
                    )

            # Fill remaining slots as vacant
            for day, period in all_slots:
                if (day, period) not in section_used:
                    db.save_schedule_entry(
                        section_id=section_id,
                        subject_id=None,
                        teacher_id=None,
                        room_id=room_id,
                        day_of_week=day,
                        period=period,
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
