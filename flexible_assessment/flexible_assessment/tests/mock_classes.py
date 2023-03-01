from unittest.mock import patch

def use_mock_canvas(func):
    """ Decorate a function that replaces FlexCanvas with MockFlexCanvas and pass the instance of MockFlexCanvas to the function 
        Note: Since this passes in MockClass.return_value, you must add this argument to your function signature"""
    def wrapper(*args, **kwargs):
        with patch("instructor.views.FlexCanvas") as MockClass:
            MockClass.return_value = MockFlexCanvas()
            func(*args, MockClass.return_value, **kwargs)
    return wrapper

class MockAssignmentGroup(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.group_weight = 25.2
        self.grade_list = {'grades': [('1', 50), ('2', 25), ('3', 30), ('4', 50)]}
    
    def edit(self, group_weight):
        self.group_weight = group_weight
    
    def asdict(self):
        return {'group_weight': float(self.group_weight), # Convert so it returns as a float instead of Decimal
                'grade_list': self.grade_list}
        
class MockCanvasCourse(object):
    name = "MOCK COURSE"

    def __init__(self):
        self.groups = [MockAssignmentGroup("test_group1", 1),
                MockAssignmentGroup("test_group2", 2),
                MockAssignmentGroup("test_group3", 3),
                MockAssignmentGroup("test_group4", 4)]
    
    def get_settings(self):
        response = {'hide_final_grades': True}
        return response

    def get_assignment_groups(self):
        return self.groups
    
    def get_assignment_group(self, group_id):
        # Find and return the mock assignment group that matches the group_id, or None if not found
        group =  next(filter(lambda group: str(group.id) == group_id, self.groups), None)
        return group

    def update_settings(self, hide_final_grades):
        return
        
class MockCanvas(object):
    def __init__(self):
        self.canvas_course = MockCanvasCourse()
    
    def get_course(self, course_id, use_sis_id=False, **kwargs):
        return self.canvas_course
    
class MockFlexCanvas(MockCanvas):
    """ This is used to mock FlexCanvas since FlexCanvas requires Canvas authentication to use the Canvas api"""
    
    def __init__(self):
        super().__init__()
        self.groups_dict = {str(group.id): group for group in self.get_course(1).groups}

    def get_groups_and_enrollments(self, course_id):
        dict = {k: v.asdict() for k, v in self.groups_dict.items()}
        return dict, []