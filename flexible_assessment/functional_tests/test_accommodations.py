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
        try:
            self.browser.quit()
        except Exception:
            pass  # Browser may already be closed

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

    @tag("slow", "view", "accommodations", "summary")
    @mock_classes.use_mock_canvas_in_accommodations()
    def test_accommodations_summary_page(self, mocked_canvas_instance):
        """Test the accommodations summary page displays correctly with session data."""
        session_id = self.client.session.session_key

        # Set up required session data for the summary page
        session = self.client.session
        # Required auth/display data
        session["display_name"] = "Test Instructor"
        session["user_id"] = "10000007"
        session["login_id"] = "10000007"
        # Summary page data
        session["multiplier_student_groups"] = [
            ("1.5", [
                ("10000001", "Jason Zheng", "user_1", "^2.0^"),
                ("10000002", "Albert Einstein", "user_2", "^1.5^"),
            ]),
            ("2.0", [
                ("10000003", "Jon Snow", "user_3", "2.0^^Exam Accommodation: Exams to begin only after 11:00 a.m."),
            ]),
        ]
        session["multiplier_quiz_groups_results"] = {
            "1.5": [
                {
                    "id": 101,
                    "title": "Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "Dec 15, 2025 10:00 AM",
                    "lock_at_readable": "Dec 15, 2025 11:00 AM",
                    "time_limit_readable": "1h",
                    "unlock_at_new_readable": "Dec 15, 2025 9:30 AM",
                    "lock_at_new_readable": "Dec 15, 2025 11:30 AM",
                    "time_limit_new_readable": "1h 30m",
                    "unlock_at_status": "success",
                    "lock_at_status": "success",
                    "time_limit_status": "success",
                }
            ],
            "2.0": [
                {
                    "id": 102,
                    "title": "Quiz 2",
                    "is_new_quiz": True,
                    "url": "https://example.com/quiz/102",
                    "unlock_at_readable": "Dec 20, 2025 2:00 PM",
                    "lock_at_readable": "Dec 20, 2025 3:00 PM",
                    "time_limit_readable": "30m",
                    "unlock_at_new_readable": "Dec 20, 2025 1:00 PM",
                    "lock_at_new_readable": "Dec 20, 2025 4:00 PM",
                    "time_limit_new_readable": "1h",
                    "unlock_at_status": "success",
                    "lock_at_status": "success",
                    "time_limit_status": "success",
                }
            ],
        }
        session["selected_quizzes"] = [
            {"id": 101, "title": "Quiz 1"},
            {"id": 102, "title": "Quiz 2"},
        ]
        session.save()

        # First, test with Django test client to verify view works
        response = self.client.get(
            reverse("accommodations:accommodations_summary", args=[1])
        )
        self.assertEqual(response.status_code, 200, f"View returned {response.status_code}")

        # Navigate to the summary page with Selenium
        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_summary", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})
        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_summary", args=[1])
        )

        # Wait for page to load
        wait = WebDriverWait(self.browser, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h2")))

        # Verify page title
        page_title = self.browser.find_element(By.TAG_NAME, "h2")
        self.assertEqual(page_title.text, "Accommodations")

        # Verify multiplier groups are displayed
        cards = self.browser.find_elements(By.CLASS_NAME, "card")
        self.assertGreaterEqual(len(cards), 2)  # At least warning card + multiplier groups

        # Verify the restart button exists
        restart_button = self.browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.assertIn("Restart", restart_button.text)

        # Verify back button exists
        back_button = self.browser.find_element(By.CSS_SELECTOR, "button.btn-secondary")
        self.assertIn("Back", back_button.text)

        input("Press Enter in this terminal to continue\n")

    @tag("slow", "view", "accommodations", "summary")
    @mock_classes.use_mock_canvas_in_accommodations()
    def test_accommodations_summary_redirect_without_data(self, mocked_canvas_instance):
        """Test that accessing summary page without required session data redirects to home."""
        session_id = self.client.session.session_key

        # Set auth session data but not the page-specific data - should redirect to home
        session = self.client.session
        session["display_name"] = "Test Instructor"
        session["user_id"] = "10000007"
        session["login_id"] = "10000007"
        session.save()
        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_summary", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})
        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_summary", args=[1])
        )

        # Wait for redirect and page load
        wait = WebDriverWait(self.browser, 10)
        wait.until(EC.url_contains("accommodations"))

        # Should be redirected to accommodations home
        current_url = self.browser.current_url
        expected_home_url = reverse("accommodations:accommodations_home", args=[1])
        self.assertIn(expected_home_url.rstrip("/"), current_url)

    @tag("slow", "view", "accommodations", "summary")
    @mock_classes.use_mock_canvas_in_accommodations()
    def test_accommodations_summary_restart_clears_session(self, mocked_canvas_instance):
        """Test that clicking restart button clears session data and redirects to home."""
        session_id = self.client.session.session_key

        # Set up required session data
        session = self.client.session
        # Required auth/display data
        session["display_name"] = "Test Instructor"
        session["user_id"] = "10000007"
        session["login_id"] = "10000007"
        session["multiplier_student_groups"] = [
            ("1.5", [("10000001", "Test Student", "user_1", "")]),
        ]
        session["multiplier_quiz_groups_results"] = {
            "1.5": [
                {
                    "id": 101,
                    "title": "Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": None,
                    "lock_at_readable": None,
                    "time_limit_readable": "60 minutes",
                    "unlock_at_new_readable": None,
                    "lock_at_new_readable": None,
                    "time_limit_new_readable": "90 minutes",
                    "unlock_at_status": "success",
                    "lock_at_status": "success",
                    "time_limit_status": "success",
                }
            ],
        }
        session["selected_quizzes"] = [{"id": 101, "title": "Quiz 1"}]
        session["accommodations"] = [("10000001", "1.5", "user_1", "Test Student", "")]
        session.save()

        # Navigate to summary page
        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_summary", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})
        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_summary", args=[1])
        )

        # Wait for page to load
        wait = WebDriverWait(self.browser, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']")))

        # Click restart button
        restart_button = self.browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        restart_button.click()

        # Wait for redirect
        wait.until(EC.url_contains("accommodations"))

        # Should be redirected to accommodations home
        current_url = self.browser.current_url
        expected_home_url = reverse("accommodations:accommodations_home", args=[1])
        self.assertIn(expected_home_url.rstrip("/"), current_url)

    @tag("slow", "view", "accommodations", "summary")
    @mock_classes.use_mock_canvas_in_accommodations()
    def test_accommodations_summary_displays_unique_accommodations_warning(self, mocked_canvas_instance):
        """Test that unique accommodations (with special notes) are displayed in warning table."""
        session_id = self.client.session.session_key

        # Set up session data with unique accommodations (additional_info with notes)
        session = self.client.session
        # Required auth/display data
        session["display_name"] = "Test Instructor"
        session["user_id"] = "10000007"
        session["login_id"] = "10000007"
        session["multiplier_student_groups"] = [
            ("1.5", [
                ("10000001", "Test Student 1", "user_1", "1.5^^"),  # Has current extended time
                ("10000002", "Test Student 2", "user_2", "^2.0^"),  # Essay only
                ("10000003", "Test Student 3", "user_3", "^^MC Only"),  # MC only notes
            ]),
        ]
        session["multiplier_quiz_groups_results"] = {
            "1.5": [
                {
                    "id": 101,
                    "title": "Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "Dec 15, 2025 10:00 AM",
                    "lock_at_readable": "Dec 15, 2025 11:00 AM",
                    "time_limit_readable": "60 minutes",
                    "unlock_at_new_readable": None,
                    "lock_at_new_readable": None,
                    "time_limit_new_readable": "90 minutes",
                    "unlock_at_status": "success",
                    "lock_at_status": "success",
                    "time_limit_status": "success",
                }
            ],
        }
        session["selected_quizzes"] = [{"id": 101, "title": "Quiz 1"}]
        session.save()

        # Navigate to summary page
        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_summary", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})
        self.browser.get(
            self.live_server_url
            + reverse("accommodations:accommodations_summary", args=[1])
        )

        # Wait for page to load
        wait = WebDriverWait(self.browser, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h3")))

        # Verify warning section exists
        warning_header = self.browser.find_element(By.XPATH, "//h3[contains(text(), 'Warning')]")
        self.assertIsNotNone(warning_header)

        input("Press Enter in this terminal to continue\n")
