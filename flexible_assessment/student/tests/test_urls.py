from django.test import SimpleTestCase
from django.urls import reverse, resolve
from student.views import StudentHome, StudentAssessmentView

class TestUrls(SimpleTestCase):
    def test_student_home_url_resolves(self):
        url = reverse('student:student_home', args=[1124])
        self.assertEquals(resolve(url).func.view_class, StudentHome)
    
    def test_student_form_url_resolves(self):
        url = reverse('student:student_form', args=[223])
        self.assertEquals(resolve(url).func.view_class, StudentAssessmentView)