from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from flexible_assessment.models import UserProfile, FlexAssessment
from django.urls import reverse
from student.views import StudentHome, StudentAssessmentView
from django.test import Client, tag
import time
from flexible_assessment.tests.test_data import DATA

from flexible_assessment.tests.mock_classes import *
from unittest.mock import patch

class TestStudentViews(StaticLiveServerTestCase):
    fixtures = DATA
        
    def setUp(self):
        self.browser = webdriver.Chrome("functional_tests/chromedriver.exe")
        user = UserProfile.objects.get(login_id="test_student1")
        self.client = Client()
        self.client.force_login(user)

    def tearDown(self):
        self.browser.close()
    
    @tag('slow', 'view')
    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_view_page(self, mock_flex_canvas):
        session_id = self.client.session.session_key
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[1])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})
        
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[4])) 
        
        time.sleep(500)
    
    @tag('slow')
    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_student_first_time_input_flexes(self, mock_flex_canvas):
        """ In course 4 the teacher has set up flexes. The student should:
            1. Be redirected to student_form page
            2. Submit a valid desired % (40 and 60)
            3. Database should save the desired % and comment
            4. They should be redirected to the home page and see their chosen percentages
        """
        print("---------------------test_student_first_time_input_flexes-------------------------------")
        
        session_id = self.client.session.session_key
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[4])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})
        
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[4])) 
        
        # 1
        self.assertIn('form', self.browser.current_url)
        
        # 2
        submit = self.browser.find_element(By.TAG_NAME, 'button')
        inputs = self.browser.find_elements(By.TAG_NAME, 'input')
        inputs[1].send_keys("40")
        self.assertFalse(submit.is_enabled())
        inputs[2].send_keys("60")
        self.assertFalse(submit.is_enabled())
        inputs[3].click()
        self.assertTrue(submit.is_enabled())
        
        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.send_keys("SELENIUM COMMENT")
        
        submit.click()
        
        # 3 and 4
        self.assertNotIn('form', self.browser.current_url)
        
        bodyText = self.browser.find_element(By.TAG_NAME, 'body').text
        self.assertIn('40', bodyText)
        self.assertIn('60', bodyText)

    @tag('slow')
    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_student_change_flexes(self, mock_flex_canvas):
        """ In course 1 the teacher has set up flexes and the student has already inputed choices. The student should:
            1. Start from the home page
            2. Should see their choices (all 25.00%)
            3. Navigate to Assessments
            4. Change their desired %
            5. Be redirected back to the home page with their updated percentages
        """
        print("---------------------test_student_change_flexes-------------------------------")

        session_id = self.client.session.session_key
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[1])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})
        
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[1])) 
        
        # 1
        self.assertNotIn('form', self.browser.current_url)
        
        # 2
        bodyText = self.browser.find_element(By.TAG_NAME, 'body').text
        self.assertIn('25.00', bodyText)
        
        # 3
        tabs = self.browser.find_elements(By.CLASS_NAME, 'nav-link')
        tabs[1].click()
        self.assertIn('form', self.browser.current_url)
        
        # 4
        inputs = self.browser.find_elements(By.TAG_NAME, 'input')
        submit = self.browser.find_element(By.TAG_NAME, 'button')
        
        inputs[1].clear()
        inputs[2].clear()
        inputs[3].clear()
        inputs[4].clear()
        
        inputs[1].send_keys("25.01")
        inputs[2].send_keys("25.02")
        inputs[3].send_keys("24.99")
        inputs[4].send_keys("24.98")
        self.assertFalse(submit.is_enabled())
        inputs[5].click()
        self.assertTrue(submit.is_enabled())

        submit.click()

        # 5
        self.assertNotIn('form', self.browser.current_url)
        bodyText = self.browser.find_element(By.TAG_NAME, 'body').text
        self.assertIn('25.01', bodyText)
        self.assertIn('25.02', bodyText)
        self.assertIn('24.99', bodyText)
        self.assertIn('24.98', bodyText)
        
    @tag('slow')
    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_student_course_not_setup(self, mock_flex_canvas):
        """ In course 2 the teacher has not set up flexes
        1. Student should be on the homepage and see a special message
        2. Student should not see the Assessments tab
        """
        print("---------------------test_student_course_not_setup-------------------------------")
        
        session_id = self.client.session.session_key
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[2])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})
        
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[2])) 
        
        # 1
        self.assertNotIn('form', self.browser.current_url)
        bodyText = self.browser.find_element(By.TAG_NAME, 'body').text
        self.assertIn('Your instructor is not using this tool at the moment', bodyText)
    
        # 2
        tabs = self.browser.find_elements(By.CLASS_NAME, 'nav-link')
        self.assertEqual(len(tabs), 1)

    @tag('slow')
    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_student_deadline_past(self, mock_flex_canvas):
        """ In course 5 the deadline has passed and the student has not made any choices
        1. Student should be on the homepage
        2. Student should not see the Assessments tab
        3. They should see their Chosen % as 'Default'
        """
        print("---------------------test_student_deadline_past-------------------------------")
        
        session_id = self.client.session.session_key
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[5])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})
        
        self.browser.get(self.live_server_url + reverse('student:student_home', args=[5])) 
        
        # 1
        self.assertNotIn('form', self.browser.current_url)
        
        # 2
        tabs = self.browser.find_elements(By.CLASS_NAME, 'nav-link')
        self.assertEqual(len(tabs), 1)
        
        # 3
        self.assertNotIn('form', self.browser.current_url)
        bodyText = self.browser.find_element(By.TAG_NAME, 'body').text
        self.assertIn('Default', bodyText)
        