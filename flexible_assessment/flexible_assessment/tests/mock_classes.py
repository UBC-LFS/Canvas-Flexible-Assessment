class MockAssignmentGroup(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.group_weight = 25
        self.grade_list = {'grades': [('1', 50), ('2', 25), ('3', 30), ('4', 50)]}
    
    def edit(self, group_weight):
        self.group_weight = group_weight
    
    def asdict(self):
        return {'group_weight': self.group_weight,
                'grade_list': self.grade_list}
        
class MockCanvasCourse(object):
    name = "MOCK COURSE"
    groups = [MockAssignmentGroup("test_group1", 1),
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
    canvas_course = MockCanvasCourse()
    
    def get_course(course, use_sis_id=False, **kwargs):
        return MockCanvas.canvas_course
    
class MockFlexCanvas(MockCanvas):
    def __init__(self, request):
        super().__init__()
    
    def get_groups_and_enrollments(course_id):
        groups_dict = {'1': MockAssignmentGroup("test_group1", 1).asdict(),
                       '2': MockAssignmentGroup("test_group2", 2).asdict(),
                       '3': MockAssignmentGroup("test_group3", 3).asdict(),
                       '4': MockAssignmentGroup("test_group4", 4).asdict()}
        
        return groups_dict, []