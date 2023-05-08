from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from flexible_assessment.models import UserProfile
from django.urls import reverse
from django.test import Client, tag
from datetime import datetime, timedelta
from flexible_assessment.tests.test_data import DATA

import flexible_assessment.tests.mock_classes as mock_classes

class TestStudentViews(StaticLiveServerTestCase):
    fixtures = DATA
        
    def setUp(self):
        self.browser =  webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
        user = UserProfile.objects.get(login_id="test_instructor1")
        self.client = Client()
        self.client.force_login(user)

    def tearDown(self):
        self.browser.close()

    @tag('slow', 'view')
    @mock_classes.use_mock_canvas()
    def test_view_page(self, mocked_flex_canvas_instance):
        session_id = self.client.session.session_key
        
        mocked_flex_canvas_instance.groups_dict['2'].grade_list = {'grades': [('1', 50), ('2', 10), ('3', 50), ('4', 60)]}
        
        self.browser.get(self.live_server_url + reverse('instructor:instructor_home', args=[1])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})

        self.browser.get(self.live_server_url + reverse('instructor:instructor_home', args=[1])) 
        
        input("Press Enter in this terminal to continue")
        
    @tag('slow')
    @mock_classes.use_mock_canvas()
    def test_setup_course(self, mocked_flex_canvas_instance):
        """ In course 2 the teacher is setting up flexible assessment for the first time
            1. Navigate to Course Setup and create 3 assessments
            2. Update MockFlexCanvas grade_list to just have grades for student 1
            3. Match up Assignment Groups
            4. Click on test_student1 and edit their flexes
        """
        print("---------------------test_setup_course-------------------------------")
        
        session_id = self.client.session.session_key
        self.browser.get(self.live_server_url + reverse('instructor:instructor_home', args=[2])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})
        
        self.browser.get(self.live_server_url + reverse('instructor:instructor_home', args=[2])) 
        
        # 1
        self.browser.find_element(By.LINK_TEXT, "Course Setup").click()
        self.browser.find_element(By.XPATH, '//button[contains(text(), "Assessment")]').click()
        self.browser.find_element(By.XPATH, '//button[contains(text(), "Assessment")]').click()
        self.browser.find_element(By.XPATH, '//button[contains(text(), "Assessment")]').click()
        
        inputs = self.browser.find_elements(By.TAG_NAME, 'input')
        values = ["Welcome to the test course", "A1", "33", "30", "50", "A2", "33", "10", "50", "A3", "34", "0", "100"]
        for index, value in enumerate(values):
            inputs[index + 5].send_keys(value)
        
        date_field = self.browser.find_element(By.NAME, 'date-close')
        
        tomorrow = datetime.now() + timedelta(1)
        date_field.send_keys(datetime.strftime(tomorrow, '%m-%d-%Y'))
        date_field.send_keys(Keys.TAB)
        date_field.send_keys("0245PM")
        
        self.browser.fullscreen_window()
        update_button = self.browser.find_element(By.XPATH, '//button[contains(text(), "Save")]')
        self.browser.execute_script("arguments[0].scrollIntoView();", update_button)
        update_button.click()
        
        # 2
        mocked_flex_canvas_instance.canvas_course.groups.pop(0)
        mocked_flex_canvas_instance.groups_dict['2'].grade_list = {'grades': [('1', 40)]}
        mocked_flex_canvas_instance.groups_dict['3'].grade_list = {'grades': [('1', 60)]}
        mocked_flex_canvas_instance.groups_dict['4'].grade_list = {'grades': [('1', 80)]}

        # 3
        self.browser.find_element(By.LINK_TEXT, "Final Grades").click()
        select_tags = self.browser.find_elements(By.TAG_NAME, "select")
        Select(select_tags[0]).select_by_visible_text('test_group2')
        Select(select_tags[1]).select_by_visible_text('test_group4')
        Select(select_tags[2]).select_by_visible_text('test_group3')
        
        self.browser.find_element(By.XPATH, '//button[contains(text(), "Continue")]').click()
        
        # 4 
        bodyText = self.browser.find_element(By.TAG_NAME, 'body').text
        self.assertNotIn('+', bodyText) # With only the default flexes, there is no difference in the totals
        
        self.browser.find_element(By.LINK_TEXT, "test_student1").click()
        inputs = self.browser.find_elements(By.TAG_NAME, 'input')
        inputs[1].send_keys("30")
        inputs[2].send_keys("50")
        inputs[3].send_keys("20")
        inputs[2].click() # This is so the input is registered
        self.browser.find_element(By.XPATH, '//button[contains(text(), "Submit")]').click()
        
        bodyText = self.browser.find_element(By.TAG_NAME, 'body').text
        self.assertIn('+', bodyText)  # Check there is a difference in the totals now
    
    @tag('slow')
    @mock_classes.use_mock_canvas()
    def test_final_grades_matched_then_canvas_group_deleted(self, mocked_flex_canvas_instance):
        """ In course 1 the teacher has matched the flexible assessments to the canvas assignment groups, but then deletes one of the canvas assignment groups
            1. Go to Final Match page and click continue
            2. Delete a canvas assignment group
            3. Go back to the Final Match page. That assignment should no longer be matched
            4. Add back a canvas assignment group and match it then continue
        """
        print("---------------------test_final_grades_matched_then_canvas_group_deleted-------------------------------")
        session_id = self.client.session.session_key
        self.browser.get(self.live_server_url + reverse('instructor:instructor_home', args=[1])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})
        
        self.browser.get(self.live_server_url + reverse('instructor:instructor_home', args=[1])) 
        # 1
        self.browser.find_element(By.LINK_TEXT, "Final Grades").click()
        self.browser.find_element(By.XPATH, '//button[contains(text(), "Continue")]').click()
        
        # 2
        mocked_flex_canvas_instance.canvas_course.groups.pop(1) # Remove at first element
        
        # 3
        self.browser.find_element(By.LINK_TEXT, "Final Grades").click()
        bodyText = self.browser.find_element(By.TAG_NAME, 'body').text
        self.assertIn('---------', bodyText)
        
        # 4
        mocked_flex_canvas_instance.canvas_course.groups.append(mock_classes.MockAssignmentGroup("NEW GROUP", 2))
        self.browser.refresh()
        self.browser.find_element(By.XPATH, '//*[@id="id_123e4567e89b12d3a456426655440002"]/option[5]').click()
        self.browser.find_element(By.XPATH, '//button[contains(text(), "Continue")]').click()
        
        self.assertIn('final/list', self.browser.current_url)
        