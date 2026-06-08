from unittest.mock import patch
from functools import wraps
from canvasapi.calendar_event import CalendarEvent


def use_mock_canvas(location="instructor.views.FlexCanvas"):
    """Decorate a function that replaces FlexCanvas with MockFlexCanvas and pass the instance of MockFlexCanvas to the function
    Note: Since this passes in MockClass.return_value, you must add this argument to your function signature
    See https://stackoverflow.com/a/42581103 for an explanation of this code"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with patch(location) as MockClass:
                MockClass.return_value = MockFlexCanvas()
                func(*args, MockClass.return_value, **kwargs)

        return wrapper

    return decorator


def use_mock_canvas_in_accommodations(
    location="accommodations.views.AccommodationsCanvas",
):
    """Decorate a function that replaces AccommodationsCanvas with MockAccommodationsCanvas and pass the instance of MockAccommodationsCanvas to the function
    Note: Since this passes in MockClass.return_value, you must add this argument to your function signature
    See https://stackoverflow.com/a/42581103 for an explanation of this code"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with patch(location) as MockClass:
                MockClass.return_value = MockAccommodationsCanvas()
                func(*args, MockClass.return_value, **kwargs)

        return wrapper

    return decorator


class MockUser(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.sis_user_id = id


class MockAssignmentGroup(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.group_weight = 25.2
        self.grade_list = {"grades": [("1", 50), ("2", 25), ("3", 30), ("4", 50)]}

    def edit(self, group_weight):
        self.group_weight = group_weight

    def asdict(self):
        return {
            "group_weight": float(
                self.group_weight
            ),  # Convert so it returns as a float instead of Decimal
            "grade_list": self.grade_list,
        }


class MockCanvasCourse(object):
    name = "MOCK COURSE"
    apply_assignment_group_weights = True

    def __init__(self):
        self.groups = [
            MockAssignmentGroup("test_group1", 1),
            MockAssignmentGroup("test_group2", 2),
            MockAssignmentGroup("test_group3", 3),
            MockAssignmentGroup("test_group4", 4),
        ]

    def get_settings(self):
        response = {"hide_final_grades": True}
        return response

    def get_assignment_groups(self):
        return self.groups

    def get_assignment_group(self, group_id):
        # Find and return the mock assignment group that matches the group_id, or None if not found
        for group in self.groups:
            if int(group.id) == int(group_id):
                return group

        return None

    def update_settings(self, hide_final_grades):
        return

    def update(self, course):
        return


class MockCanvas(object):
    def __init__(self):
        self.canvas_course = MockCanvasCourse()
        self.calendar_item = None

    def get_course(self, course_id, use_sis_id=False, **kwargs):
        return self.canvas_course

    def create_calendar_event(self, calendar_event):
        self.calendar_item = MockCalendarEvent(calendar_event)
        return self.calendar_item

    def get_calendar_event(self, calendar_event):
        return self.calendar_item


class MockCalendarEvent(object):
    def __init__(self, dict):
        self.id = 12345
        self.title = dict["title"]
        self.start_at = dict["start_at"]
        self.end_at = dict["end_at"]

    def edit(self, calendar_event):
        for k, v in calendar_event.items():
            setattr(self, k, str(v))
        return self


class MockFlexCanvas(MockCanvas):
    """This is used to mock FlexCanvas since FlexCanvas requires Canvas authentication to use the Canvas api"""

    def __init__(self):
        super().__init__()
        self.groups_dict = {str(group.id): group for group in self.get_course(1).groups}
        self.calendar_item = None
        self.allow_override = False

    def get_groups_and_enrollments(self, course_id):
        dict = {k: v.asdict() for k, v in self.groups_dict.items()}
        return dict, {}

    # TODO: Make this work legit in the Mock Canvas enviroment
    def get_flat_groups_and_enrollments(self, course_id):
        dict = {k: v.asdict() for k, v in self.groups_dict.items()}
        return dict, {}

    def set_override_true(self, course_id):
        self.allow_override = True

    def is_allow_override(self, course_id):
        return self.allow_override

    def create_calendar_event(self, calendar_event):
        self.calendar_item = MockCalendarEvent(calendar_event)
        return self.calendar_item

    def get_calendar_event(self, calendar_event):
        return self.calendar_item


class MockAccommodationsCanvas(MockCanvas):
    """This is used to mock AccommodationsCanvas since AccommodationsCanvas requires Canvas authentication to use the Canvas api"""

    def __init__(self):
        super().__init__()

    def get_quiz_data(self, course_id):
        """Mock the quiz data method"""
        quiz_list = [
            {
                "id": 101,
                "title": "Mock Quiz 1",
                "is_new_quiz": False,
                "url": "https://example.com/quiz/101",
                "unlock_at_readable": "2026-06-01 - 12:00PM",
                "lock_at_readable": "2026-06-01 - 1:00PM",
                "time_limit_readable": "No time limit set",
            },
            {
                "id": 102,
                "title": "Mock Quiz 2",
                "is_new_quiz": True,
                "url": "https://example.com/quiz/102",
                "unlock_at_readable": "2026-07-05 - 9:00AM",
                "lock_at_readable": "2026-08-10 - 11:59PM",
                "time_limit_readable": "2h",
            },
        ]
        unavailable_quiz_list = [
            {
                "id": 103,
                "title": "Mock Quiz 3",
                "is_new_quiz": False,
                "url": "https://example.com/quiz/103",
                "unlock_at_readable": "2026-04-05 - 9:00AM",
                "lock_at_readable": "2026-04-05 - 11:59PM",
                "time_limit_readable": "1h",
            }
        ]
        return quiz_list, unavailable_quiz_list

    def get_multiplier_student_groups(self, accommodations, students):
        """Mock method that groups students by multiplier"""
        multiplier_groups = {}
        for accommodation in accommodations:
            student_id, multiplier, user_id, student_string, additional_info = (
                accommodation
            )
            if multiplier not in multiplier_groups:
                multiplier_groups[multiplier] = []

            # Find matching student name from students
            student_name = "Test Student"
            for student in students:
                if str(student.login_id) == student_id:
                    student_name = student.display_name
                    break

            multiplier_groups[multiplier].append(
                (student_id, student_name, user_id, additional_info)
            )

        # Convert dict to list of tuples sorted by multiplier
        return sorted(
            [(k, v) for k, v in multiplier_groups.items()],
            key=lambda x: float(x[0]),
            reverse=True,
        )

    def get_multiplier_quiz_groups(self, selected_quizzes):
        """Mock method that groups quizzes by multiplier"""
        if selected_quizzes[0]:
            selected_quizzes[0]["lock_at_new_readable"] = "2026-06-01 - 1:30PM"
        if selected_quizzes[1]:
            selected_quizzes[1]["time_limit_new_readable"] = "3h"
        multipliers = [4.0, 3.5, 3.0, 2.5, 2.0, 1.75, 1.5, 1.25]
        result = {}
        for multiplier in multipliers:
            result[str(multiplier)] = selected_quizzes
        return result

    def get_existing_accommodations(
        self, accommodations, students, multiplier_quiz_groups, course_id
    ):
        """Mock method that returns existing accommodations"""
        return []

    def add_time_extensions(self, student_groups, quiz_groups, course_id):
        for multiplier, quiz_list in quiz_groups.items():
            for quiz in quiz_list:
                quiz["time_limit_status"] = "success"
        return quiz_groups, True

    def add_availabilities(
        self,
        student_groups,
        quiz_groups,
        existing_accommodations,
        should_override,
        course_id,
    ):
        for multiplier, quiz_list in quiz_groups.items():
            for quiz in quiz_list:
                quiz["lock_at_status"] = "success"
                quiz["unlock_at_status"] = "success"
        return quiz_groups, True

    def get_additional_accommodations_groups(self, accommodations, students):
        """Mock method that groups students by additional accommodation type"""
        additional_accommodations_groups = {
            "essay": [],
            "mult_choice": [],
            "short_ans": [],
            "fine_manip": [],
            "notes": [],
        }
        accommodations_keys = [
            "essay",
            "mult_choice",
            "short_ans",
            "fine_manip",
            "notes",
        ]
        student_names_by_id = {s.login_id: s.display_name for s in students}

        for student_id, _, _, _, student_note in accommodations:
            if isinstance(student_note, str):
                split_parts = student_note.split("^")
                for i in range(min(5, len(split_parts))):
                    if split_parts[i]:
                        additional_accommodations_groups[accommodations_keys[i]].append(
                            {
                                "id": student_id,
                                "name": student_names_by_id.get(
                                    student_id, "Test Student"
                                ),
                                "multiplier": split_parts[i],
                            }
                        )
        return additional_accommodations_groups
