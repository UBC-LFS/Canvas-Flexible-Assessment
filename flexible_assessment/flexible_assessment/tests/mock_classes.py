class MockAssignmentGroup(object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.group_weight = 25
        self.grade_list = [
            {'grades': 12}
        ]
        
class MockCanvasCourse(object):
    def get_settings(self):
        response = {'hide_final_grades': True}
        return response

    def get_assignment_groups(self):
        groups = [MockAssignmentGroup("test_group1", 1),
                       MockAssignmentGroup("test_group2", 2),
                       MockAssignmentGroup("test_group3", 3),
                       MockAssignmentGroup("test_group4", 4)]
        return groups
    
class MockCanvas(object):
    def get_course(course, use_sis_id=False, **kwargs):
        return MockCanvasCourse()
    
class MockFlexCanvas(MockCanvas):
    def __init__(self, request):
        super().__init__()
    
    def get_groups_and_enrollments(course_id):
        groups_dict = {'1': {
            'grade_list': 
                {'grades':
                    [(1, 50), (2, 25), (3, 30), (4, 50)]}
        }}
        return groups_dict, []