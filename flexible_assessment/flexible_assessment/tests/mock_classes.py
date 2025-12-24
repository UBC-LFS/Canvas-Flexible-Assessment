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
        self.grade_list = {'grades': [('1', 50), ('2', 25), ('3', 30), ('4', 50), ('201', 17), ('202', 64), ('203', 39), ('204', 85), ('205', 95), ('206', 29), ('207', 27), ('208', 77), ('209', 26), ('210', 68), ('211', 14), ('212', 58), ('213', 55), ('214', 39), ('215', 69), ('216', 0), ('217', 99), ('218', 17), ('219', 42), ('220', 80), ('221', 70), ('222', 73), ('223', 75), ('224', 14), ('225', 67), ('226', 15), ('227', 3), ('228', 31), ('229', 96), ('230', 89), ('231', 80), ('232', 97), ('233', 7), ('234', 52), ('235', 13), ('236', 34), ('237', 40), ('238', 6), ('239', 92), ('240', 12), ('241', 2), ('242', 35), ('243', 100), ('244', 44), ('245', 39), ('246', 11), ('247', 81), ('248', 42), ('249', 8), ('250', 33), ('251', 52), ('252', 98), ('253', 19), ('254', 6), ('255', 67), ('256', 28), ('257', 3), ('258', 8), ('259', 85), ('260', 95), ('261', 75), ('262', 33), ('263', 89), ('264', 51), ('265', 63), ('266', 86), ('267', 44), ('268', 97), ('269', 72), ('270', 2), ('271', 62), ('272', 21), ('273', 29), ('274', 41), ('275', 58), ('276', 83), ('277', 17), ('278', 15), ('279', 88), ('280', 15), ('281', 30), ('282', 77), ('283', 34), ('284', 55), ('285', 21), ('286', 60), ('287', 85), ('288', 30), ('289', 64), ('290', 100), ('291', 50), ('292', 45), ('293', 44), ('294', 54), ('295', 67), ('296', 44), ('297', 26), ('298', 15), ('299', 88), ('300', 53), ('301', 52), ('302', 9), ('303', 69), ('304', 28), ('305', 69), ('306', 45), ('307', 72), ('308', 53), ('309', 64), ('310', 95), ('311', 94), ('312', 49), ('313', 70), ('314', 72), ('315', 11), ('316', 6), ('317', 53), ('318', 65), ('319', 30), ('320', 82), ('321', 72), ('322', 11), ('323', 22), ('324', 49), ('325', 60), ('326', 59), ('327', 95), ('328', 21), ('329', 95), ('330', 76), ('331', 14), ('332', 78), ('333', 7), ('334', 72), ('335', 39), ('336', 22), ('337', 55), ('338', 31), ('339', 89), ('340', 63), ('341', 9), ('342', 66), ('343', 45), ('344', 72), ('345', 21), ('346', 86), ('347', 67), ('348', 47), ('349', 14), ('350', 32), ('351', 49), ('352', 60), ('353', 98), ('354', 32), ('355', 28), ('356', 15), ('357', 45), ('358', 10), ('359', 55), ('360', 73), ('361', 38), ('362', 3), ('363', 98), ('364', 65), ('365', 19), ('366', 94), ('367', 97), ('368', 93), ('369', 35), ('370', 82), ('371', 60), ('372', 16), ('373', 0), ('374', 76), ('375', 60), ('376', 10), ('377', 93), ('378', 62), ('379', 68), ('380', 40), ('381', 43), ('382', 92), ('383', 10), ('384', 6), ('385', 55), ('386', 7), ('387', 94), ('388', 50), ('389', 93), ('390', 14), ('391', 61), ('392', 53), ('393', 40), ('394', 11), ('395', 54), ('396', 8), ('397', 82), ('398', 58), ('399', 89), ('400', 50), ('401', 14), ('402', 88), ('403', 76), ('404', 20), ('405', 96),
        ('406', 43), ('407', 64), ('408', 59), ('409', 35), ('410', 3),
        ('411', 70), ('412', 95), ('413', 82), ('414', 25), ('415', 67),
        ('416', 60), ('417', 49), ('418', 78), ('419', 85), ('420', 7),
        ('421', 39), ('422', 11), ('423', 50), ('424', 71), ('425', 33),
        ('426', 29), ('427', 81), ('428', 46), ('429', 92), ('430', 17),
        ('431', 64), ('432', 57), ('433', 8), ('434', 100), ('435', 61),
        ('436', 36), ('437', 79), ('438', 12), ('439', 52), ('440', 41),
        ('441', 65), ('442', 24), ('443', 83), ('444', 47), ('445', 91),
        ('446', 54), ('447', 9), ('448', 73), ('449', 28), ('450', 56),
        ('451', 100), ('452', 40), ('453', 84), ('454', 63), ('455', 16),
        ('456', 99), ('457', 34), ('458', 20), ('459', 82), ('460', 45),
        ('461', 13), ('462', 31), ('463', 75), ('464', 88), ('465', 94),
        ('466', 70), ('467', 32), ('468', 27), ('469', 53), ('470', 22),
        ('471', 48), ('472', 92), ('473', 19), ('474', 62), ('475', 87),
        ('476', 43), ('477', 60), ('478', 28), ('479', 66), ('480', 35),
        ('481', 15), ('482', 57), ('483', 68), ('484', 39), ('485', 25),
        ('486', 90), ('487', 5), ('488', 83), ('489', 14), ('490', 100),
        ('491', 64), ('492', 72), ('493', 9), ('494', 77), ('495', 51),
        ('496', 48), ('497', 96), ('498', 58), ('499', 44), ('500', 88)]}

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
            MockAssignmentGroup("test_group5", 5),
            MockAssignmentGroup("test_group6", 6),
            MockAssignmentGroup("test_group7", 7),
            MockAssignmentGroup("test_group8", 8),
            MockAssignmentGroup("test_group9", 9),
            MockAssignmentGroup("test_group10", 10),
            MockAssignmentGroup("test_group11", 11),
            MockAssignmentGroup("test_group12", 12),
            MockAssignmentGroup("test_group13", 13),
            MockAssignmentGroup("test_group14", 14),
            MockAssignmentGroup("test_group15", 15),
            MockAssignmentGroup("test_group16", 16),
            MockAssignmentGroup("test_group17", 17),
            MockAssignmentGroup("test_group18", 18),
            MockAssignmentGroup("test_group19", 19),
            MockAssignmentGroup("test_group20", 20),
            MockAssignmentGroup("test_group21", 21),
            MockAssignmentGroup("test_group22", 22),
            MockAssignmentGroup("test_group23", 23),
            MockAssignmentGroup("test_group24", 24),
            MockAssignmentGroup("test_group25", 25),
            MockAssignmentGroup("test_group26", 26),
            MockAssignmentGroup("test_group27", 27),
            MockAssignmentGroup("test_group28", 28),
            MockAssignmentGroup("test_group29", 29),
            MockAssignmentGroup("test_group30", 30),
            MockAssignmentGroup("test_group31", 31),
            MockAssignmentGroup("test_group32", 32),
            MockAssignmentGroup("test_group33", 33),
            MockAssignmentGroup("test_group34", 34),
            MockAssignmentGroup("test_group35", 35),
            MockAssignmentGroup("test_group36", 36),
            MockAssignmentGroup("test_group37", 37),
            MockAssignmentGroup("test_group38", 38),
            MockAssignmentGroup("test_group39", 39),
            MockAssignmentGroup("test_group40", 40),
            MockAssignmentGroup("test_group41", 41),
            MockAssignmentGroup("test_group42", 42),
            MockAssignmentGroup("test_group43", 43),
            MockAssignmentGroup("test_group44", 44),
            MockAssignmentGroup("test_group45", 45),
            MockAssignmentGroup("test_group46", 46),
            MockAssignmentGroup("test_group47", 47),
            MockAssignmentGroup("test_group48", 48),
            MockAssignmentGroup("test_group49", 49),
            MockAssignmentGroup("test_group50", 50)
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
