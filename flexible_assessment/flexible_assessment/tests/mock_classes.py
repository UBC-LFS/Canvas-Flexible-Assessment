class MockCanvasCourse(object):
    def get_settings(self):
        response = {'hide_final_grades': True}
        return response
    
class MockCanvas(object):
    def get_course(course, use_sis_id=False, **kwargs):
        return MockCanvasCourse()
    
class MockFlexCanvas(MockCanvas):
    def __init__(self, request):
        super().__init__()