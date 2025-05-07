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


def use_mock_canvas_in_accommodations():
    return use_mock_canvas(location="accommodations.views.FlexCanvas")


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
