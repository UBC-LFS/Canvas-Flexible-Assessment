from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from flexible_assessment.models import UserProfile
from django.urls import reverse
from django.test import Client, tag
from flexible_assessment.tests.test_data import DATA
import flexible_assessment.tests.mock_classes as mock_classes
from unittest.mock import patch

class TestStudentViews(StaticLiveServerTestCase):
    fixtures = DATA
        
    def setUp(self):
        self.browser = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
        user = UserProfile.objects.get(login_id="admin")
        self.client = Client()
        self.client.force_login(user)
        
    def tearDown(self):
        self.browser.close()
    
    @tag('slow', 'view')
    @mock_classes.use_mock_canvas()
    def test_start(self, mocked_flex_canvas_instance):
        session_id = self.client.session.session_key
        self.client.session['display_name'] = "HEllo"
        self.browser.get(self.live_server_url + reverse('instructor:instructor_home', args=[1])) 
        self.browser.add_cookie({'name': 'sessionid', 'value': session_id})
        self.browser.add_cookie({'name': 'display_name', 'value': "TEST"})

        self.browser.get(self.live_server_url + reverse('instructor:instructor_home', args=[1])) 
        
        input("Press Enter in this terminal to continue")
    