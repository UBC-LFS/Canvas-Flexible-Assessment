from django.test import TestCase, Client
from django.urls import reverse
from flexible_assessment.models import UserProfile, Course, UserCourse, Roles
from instructor.views import *
from flexible_assessment.tests.test_data import DATA
from flexible_assessment.tests.mock_classes import *

from unittest.mock import patch

class TestUrls(TestCase):
    fixtures = DATA

    def setUp(self):
        self.client = Client()
    
    def login_instructor(self, id, course_title):
        self.user = UserProfile.objects.get(login_id=id)
        course = Course.objects.get(title=course_title)
        self.client.force_login(self.user)
        self.client.session['display_name'] = "DISPLAY_NAME"
        return course.id
        
    def test_instructor_home_url_valid_for_admins(self):
        user = UserProfile.objects.get(login_id="admin")
        course = Course.objects.get(title="test_course1")
        self.client.force_login(user)
        instructor_home_url = reverse('instructor:instructor_home', args=[course.id])
        
        response = self.client.get(instructor_home_url)
        self.assertEquals(response.status_code, 200)
    
    def test_instructor_home_url_valid_for_tas(self):
        user = UserProfile.objects.get(login_id="test_ta1")
        course = Course.objects.get(title="test_course1")
        self.client.force_login(user)
        instructor_home_url = reverse('instructor:instructor_home', args=[course.id])
        
        response = self.client.get(instructor_home_url)
        self.assertEquals(response.status_code, 200)
        
    def test_instructor_home_url_valid_for_students(self):
        user = UserProfile.objects.get(login_id="test_student1")
        course = Course.objects.get(title="test_course1")
        self.client.force_login(user)
        instructor_home_url = reverse('instructor:instructor_home', args=[course.id])
        
        response = self.client.get(instructor_home_url)
        self.assertEquals(response.status_code, 403)
        
    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_instructor_form_url_valid_for_instructor(self, mock_flex_canvas):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse('instructor:instructor_form', args=[course_id])
        
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        
    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_instructor_form_url_invalid_for_students(self, mock_flex_canvas):
        user = UserProfile.objects.get(login_id="test_student1")
        course = Course.objects.get(title="test_course1")
        self.client.force_login(user)
        

        url = reverse('instructor:instructor_form', args=[course.id])
        response = self.client.get(url)
        self.assertEquals(response.status_code, 403)

    
    def test_instructor_home_url_valid_for_instructor(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        instructor_home_url = reverse('instructor:instructor_home', args=[course_id])
        
        response = self.client.get(instructor_home_url)
        self.assertEquals(response.status_code, 200)
    
    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_instructor_assessments_export_valid_for_instructor(self, mock_flex_canvas):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse('instructor:assessments_export', args=[course_id])

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        
    def test_instructor_file_upload_valid_for_instructor(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse('instructor:file_upload', args=[course_id])
        
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
    
    def test_instructor_percentage_list_valid_for_instructor(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse('instructor:percentage_list', args=[course_id])
        
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        
    def test_instructor_percentage_list_export_valid_for_instructor(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        
        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse('instructor:instructor_home', args=[course_id])
        response = self.client.get(instructor_home_url)
        
        url = reverse('instructor:percentage_list_export', args=[course_id])
        
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        
    def test_override_student_form_percentage_url_valid_for_instructor(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse('instructor:override_student_form_percentage', args=[course_id, 1])
        
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        
    def test_override_student_form_percentage_url_valid_for_instructor(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse('instructor:override_student_form_percentage', args=[course_id, 1])
        
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)