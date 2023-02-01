from django.test import TestCase, Client
from django.urls import reverse, resolve
from flexible_assessment.models import UserProfile, Course, UserCourse, Roles
from student.views import StudentHome, StudentAssessmentView
from flexible_assessment.tests.test_data import DATA

class TestUrls(TestCase):
    fixtures = DATA

    def setUp(self):
        self.client = Client()
    
    def get_user_and_course_object(self, user_id, course_title):
        user = UserProfile.objects.get(login_id=user_id)
        course = Course.objects.get(title=course_title)
        return (user, course)
        
    def test_student_home_url_resolves(self):
        url = reverse('student:student_home', args=[1124])
        self.assertEquals(resolve(url).func.view_class, StudentHome)
    
    def test_student_form_url_resolves(self):
        url = reverse('student:student_form', args=[223])
        self.assertEquals(resolve(url).func.view_class, StudentAssessmentView)
        
    
    def test_student_home_url_valid_for_student(self):
        [user, course] = self.get_user_and_course_object("test_student1", "test_course1")
        self.client.force_login(user)
        
        student_home_url = reverse('student:student_home', args=[course.id])
        response = self.client.get(student_home_url)
        self.assertEquals(response.status_code, 200)
    
    def test_student_home_url_invalid_for_instructor(self):
        [user, course] = self.get_user_and_course_object("test_instructor1", "test_course1")
        self.client.force_login(user)
        student_home_url = reverse('student:student_home', args=[course.id])
        
        response = self.client.get(student_home_url)
        self.assertEquals(response.status_code, 403)
    
    def test_student_form_url_valid_for_student(self):
        [user, course] = self.get_user_and_course_object("test_student1", "test_course1")
        self.client.force_login(user)
        
        student_url = reverse('student:student_form', args=[course.id])
        response = self.client.get(student_url, args=[course.id])
        self.assertEquals(response.status_code, 200)
        
    def test_student_home_invalid_if_not_logged_in(self):
        [user, course] = self.get_user_and_course_object("test_student1", "test_course1")
        
        student_url = reverse('student:student_home', args=[course.id])
        response = self.client.get(student_url, args=[course.id])
        self.assertEquals(response.status_code, 403)
    
    def test_student_form_invalid_if_not_logged_in(self):
        [user, course] = self.get_user_and_course_object("test_student1", "test_course1")
        
        student_url = reverse('student:student_form', args=[course.id])
        response = self.client.get(student_url, args=[course.id])
        self.assertEquals(response.status_code, 403)
    
    def test_student_home_url_invalid_for_student_not_in_course(self):
        user = UserProfile.objects.get(login_id="test_student1")
        course = Course.objects.get(title="test_course1000")
        self.client.force_login(user)
        student_home_url = reverse('student:student_home', args=[course.id])
        
        response = self.client.get(student_home_url)
        self.assertEquals(response.status_code, 403)
    
    def test_student_tries_access_nonexistant_course(self):
        user, course = self.get_user_and_course_object("test_student1", "test_course1")
        self.client.force_login(user)
        student_home_url = reverse('student:student_home', args=[99999])

        response = self.client.get(student_home_url)
        self.assertEquals(response.status_code, 404)
    