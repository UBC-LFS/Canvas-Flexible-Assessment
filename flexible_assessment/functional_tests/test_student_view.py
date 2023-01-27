from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from flexible_assessment.models import UserProfile
from django.urls import reverse
from student.views import StudentHome, StudentAssessmentView
from django.test import Client
import time
from flexible_assessment.tests.test_data import DATA

class TestStudentViews(StaticLiveServerTestCase):
    fixtures = DATA
        
    def setUp(self):
        self.browser =  webdriver.Chrome("functional_tests/chromedriver.exe")
        user = UserProfile.objects.get(login_id="test_student1")
        self.client = Client()
        self.client.force_login(user)
        

    def tearDown(self):
        self.browser.close()
    
    def test_start(self):
        session_id = self.client.session.session_key
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[1])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})
        
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[1])) 
        
        time.sleep(10)