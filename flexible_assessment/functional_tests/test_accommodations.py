from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver import ActionChains
import flexible_assessment.models as models
import instructor.writer as writer
from django.urls import reverse
from django.test import Client, tag
from django.http import HttpResponseRedirect
from datetime import datetime, timedelta
import dateutil
from flexible_assessment.tests.test_data import ACCOMMODATIONS_DATA
from unittest.mock import patch, MagicMock, ANY
import instructor.views as views
import time

import flexible_assessment.tests.mock_classes as mock_classes
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

import os
import pandas as pd
import shutil


class TestInstructorViews(StaticLiveServerTestCase):
    fixtures = ACCOMMODATIONS_DATA

    def setUp(self):
        chromeOptions = webdriver.ChromeOptions()
        chromeOptions.add_experimental_option(
            "prefs", {"profile.managed_default_content_settings.images": 2}
        )
        chromeOptions.add_argument("--no-sandbox")
        chromeOptions.add_argument("--disable-setuid-sandbox")
        chromeOptions.add_argument("--remote-debugging-port=9222")
        chromeOptions.add_argument("--disable-dev-shm-using")
        chromeOptions.add_argument("--disable-extensions")
        chromeOptions.add_argument("--disable-gpu")
        chromeOptions.add_argument("start-maximized")
        chromeOptions.add_argument("disable-infobars")

        # for testing csv download
        self.download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)

        chromeOptions.add_experimental_option(
            "prefs",
            {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
            },
        )

        # Use Selenium's automatic driver management
        self.browser = webdriver.Chrome(options=chromeOptions)

        user = models.UserProfile.objects.get(login_id="10000007")
        self.client = Client()
        self.client.force_login(user)
        self.launch_url = reverse("launch_accommodations")
        self.login_url = reverse("login")

    def tearDown(self):
        shutil.rmtree(self.download_dir, ignore_errors=True)
        self.browser.close()

    def launch_new_user(self, course_data):
        client = Client()
        launch_data = {"https://purl.imsglobal.org/spec/lti/claim/custom": course_data}

        message_launch_instance = MagicMock()
        message_launch_instance.get_launch_data.return_value = launch_data

        with patch(
            "flexible_assessment.lti.get_tool_conf"
        ) as mock_get_tool_conf, patch(
            "flexible_assessment.views.DjangoMessageLaunch",
            return_value=message_launch_instance,
        ), patch(
            "flexible_assessment.models.Course.objects.get"
        ) as mock_course_get:
            response = client.post(reverse("launch_accommodations"))

        session_id = client.session.session_key
        chromeOptions = webdriver.ChromeOptions()
        chromeOptions.add_experimental_option(
            "prefs", {"profile.managed_default_content_settings.images": 2}
        )
        chromeOptions.add_argument("--no-sandbox")
        chromeOptions.add_argument("--disable-setuid-sandbox")

        chromeOptions.add_argument("--remote-debugging-port=9222")  # this

        chromeOptions.add_argument("--disable-dev-shm-using")
        chromeOptions.add_argument("--disable-extensions")
        chromeOptions.add_argument("--disable-gpu")
        chromeOptions.add_argument("start-maximized")
        chromeOptions.add_argument("disable-infobars")
        chromeOptions.add_argument(r"user-data-dir=.\cookies\\test")
        browser = webdriver.Chrome(options=chromeOptions)

        browser.get(self.live_server_url + response.url)
        browser.add_cookie({"name": "sessionid", "value": session_id})
        browser.get(self.live_server_url + response.url)
        return browser

    @tag("slow", "view", "accommodations")
    @mock_classes.use_mock_canvas_in_accommodations()
    @patch.object(views.FinalGradeListView, "_submit_final_grades")
    def test_view_page(self, mocked_flex_canvas_instance, mock_submit_final_grades):
        """Note, this is designed to work with the fixture data for course 1."""
        mock_submit_final_grades.return_value = (
            True  # When submitting final grades, just return True for that function
        )
        session_id = self.client.session.session_key

        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_home", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_home", args=[1])
        )

        input("Press Enter in this terminal to continue\n")
