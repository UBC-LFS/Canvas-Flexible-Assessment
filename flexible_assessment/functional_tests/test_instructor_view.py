from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver import ActionChains
import flexible_assessment.models as models
from django.urls import reverse
from django.test import Client, tag
from django.http import HttpResponseRedirect
from datetime import datetime, timedelta
import dateutil
from flexible_assessment.tests.test_data import DATA
from unittest.mock import patch, MagicMock, ANY
import instructor.views as views
import time

import flexible_assessment.tests.mock_classes as mock_classes
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

import os
import pandas as pd
import shutil


class TestInstructorViews(StaticLiveServerTestCase):
    fixtures = DATA

    def setUp(self):
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

        # for testing csv download
        self.download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)

        chromeOptions.add_experimental_option(
            "prefs",
            {
                "download.default_directory": self.download_dir,  # Set download location
                "download.prompt_for_download": False,  # Disable prompt
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
            },
        )

        self.browser = webdriver.Chrome(options=chromeOptions)

        user = models.UserProfile.objects.get(login_id="test_instructor1")
        self.client = Client()
        self.client.force_login(user)
        self.launch_url = reverse("launch")
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
            response = client.post(reverse("launch"))

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

    @tag("slow", "view", "instructor_view")
    @mock_classes.use_mock_canvas()
    @patch.object(views.FinalGradeListView, "_submit_final_grades")
    def test_view_page(self, mocked_flex_canvas_instance, mock_submit_final_grades):
        """Note, this is designed to work with the fixture data for course 1."""
        mock_submit_final_grades.return_value = (
            True  # When submitting final grades, just return True for that function
        )
        session_id = self.client.session.session_key

        mocked_flex_canvas_instance.groups_dict["2"].grade_list = {
            "grades": [("1", 50), ("2", 10), ("3", 50), ("4", 60)]
        }

        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[1])
        )

        input("Press Enter in this terminal to continue")

    @tag("slow", "view", "double_view")
    @mock_classes.use_mock_canvas()
    def test_double_view(self, mocked_flex_canvas_instance):
        """See both instructor and student view, this is designed to work with course 1"""
        print("---------------------test_double_view-------------------------------")
        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[1])
        )
        student_data = {
            "course_id": 1,
            "role": "StudentEnrollment",
            "user_display_name": "Test User",
            "user_id": "987664",
            "login_id": "987664",
            "course_name": 1,
        }

        student_browser = self.launch_new_user(student_data)

        while (
            input("Input R to Relaunch the Student, Enter anything else to quit: ")
            == "R"
        ):
            student_browser.close()
            student_browser = self.launch_new_user(student_data)

        student_browser.close()

    @tag("slow")
    def test_login_and_launch_success(self):
        # Mock the lti module functions used in the login view
        with patch(
            "flexible_assessment.lti.get_tool_conf"
        ) as mock_get_tool_conf, patch(
            "flexible_assessment.lti.get_launch_data_storage"
        ) as mock_get_launch_data_storage, patch(
            "flexible_assessment.lti.get_launch_url", return_value=self.launch_url
        ):
            # Mock the DjangoOIDCLogin object and its methods
            with patch(
                "flexible_assessment.views.DjangoOIDCLogin"
            ) as mock_django_oidc_login:
                oidc_login_instance = MagicMock()
                oidc_login_instance.enable_check_cookies.return_value = (
                    oidc_login_instance
                )
                oidc_login_instance.redirect.return_value = HttpResponseRedirect(
                    self.launch_url
                )
                mock_django_oidc_login.return_value = oidc_login_instance

                response = self.client.get(self.login_url)

                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(self.launch_url))

                course_data = {
                    "course_id": "12345",
                    "role": "StudentEnrollment",
                    "user_display_name": "Test User",
                    "user_id": "987664",
                    "login_id": "987664",
                    "course_name": "Test Course",
                }

        self.browser = self.launch_new_user(course_data)
        body_text = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("Test User", body_text)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_setup_course(self, mocked_flex_canvas_instance):
        """In course 2 the teacher is setting up flexible assessment for the first time
        1. Navigate to Course Setup and create 3 assessments
        2. Update MockFlexCanvas grade_list to just have grades for student 1
        3. Match up Assignment Groups
        4. Click on test_student1 and edit their flexes
        """
        print("---------------------test_setup_course-------------------------------")

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[2])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[2])
        )

        # 1
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()
        self.browser.find_element(By.ID, "add").click()
        self.browser.find_element(By.ID, "add").click()
        self.browser.find_element(By.ID, "add").click()

        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        values = ["A1", "33", "30", "50", "A2", "33", "10", "50", "A3", "34", "0", "60"]
        for index, value in enumerate(values):
            inputs[index + 6].send_keys(
                value
            )  # There are 6 hidden inputs we need to skip over

        open_date_field = self.browser.find_element(By.NAME, "date-open")
        date_field = self.browser.find_element(By.NAME, "date-close")

        tomorrow = datetime.now() + timedelta(1)

        open_date_field.send_keys(datetime.strftime(tomorrow, "%m-%d-%Y"))
        open_date_field.send_keys(Keys.TAB)
        open_date_field.send_keys("0245PM")

        date_field.send_keys(datetime.strftime(tomorrow, "%m-%d-%Y"))
        date_field.send_keys(Keys.TAB)
        date_field.send_keys("0245PM")

        self.browser.fullscreen_window()
        update_button = self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Save")]'
        )
        update_button.send_keys(Keys.ENTER)

        wait = WebDriverWait(self.browser, 5)
        wait.until_not(EC.url_contains("form"))  # Wait for changes to be made

        # 2
        mocked_flex_canvas_instance.canvas_course.groups.pop(0)
        mocked_flex_canvas_instance.groups_dict["2"].grade_list = {
            "grades": [("1", 40)]
        }
        mocked_flex_canvas_instance.groups_dict["3"].grade_list = {
            "grades": [("1", 60)]
        }
        mocked_flex_canvas_instance.groups_dict["4"].grade_list = {
            "grades": [("1", 80)]
        }

        # 3
        self.browser.find_element(By.LINK_TEXT, "Final Grades").click()
        select_tags = self.browser.find_elements(By.TAG_NAME, "select")
        Select(select_tags[0]).select_by_visible_text("test_group2")
        Select(select_tags[1]).select_by_visible_text("test_group4")
        Select(select_tags[2]).select_by_visible_text("test_group3")

        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Continue")]'
        ).click()

        # 4
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertNotIn(
            "+", bodyText
        )  # With only the default flexes, there is no difference in the totals

        self.browser.find_element(By.LINK_TEXT, "test_student1").click()
        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        inputs[1].send_keys("30")
        inputs[2].send_keys("50")
        inputs[3].send_keys("20")
        inputs[2].click()  # This is so the input is registered
        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Submit")]'
        ).click()

        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("+", bodyText)  # Check there is a difference in the totals now

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_final_grades_matched_then_canvas_group_deleted(
        self, mocked_flex_canvas_instance
    ):
        """In course 1 the teacher has matched the flexible assessments to the canvas assignment groups, but then deletes one of the canvas assignment groups
        1. Go to Final Match page and click continue
        2. Delete a canvas assignment group
        3. Go back to the Final Match page. That assignment should no longer be matched
        4. Add back a canvas assignment group and match it then continue
        """
        print(
            "---------------------test_final_grades_matched_then_canvas_group_deleted-------------------------------"
        )
        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[1])
        )
        # 1
        self.browser.find_element(By.LINK_TEXT, "Final Grades").click()
        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Continue")]'
        ).click()

        # 2
        mocked_flex_canvas_instance.canvas_course.groups.pop(
            1
        )  # Remove at first element

        # 3
        self.browser.find_element(By.LINK_TEXT, "Final Grades").click()
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("---------", bodyText)

        # 4
        mocked_flex_canvas_instance.canvas_course.groups.append(
            mock_classes.MockAssignmentGroup("NEW GROUP", 2)
        )
        self.browser.refresh()
        self.browser.find_element(
            By.XPATH, '//*[@id="id_123e4567e89b12d3a456426655440002"]/option[2]'
        ).click()
        self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Continue")]'
        ).click()

        self.assertIn("final/list", self.browser.current_url)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_reset_course(self, mocked_flex_canvas_instance):
        """In course 1 the teacher goes to the assessments view, and deleting all assessments will reset the course
        1. Go to assessments view, make sure there are assessments, student responses, etc.
        2. Delete all the assessments, and submit
        3. Make sure all the data is deleted
        4. Make sure other course data is not deleted
        5. Make sure a student can log in and sets up data correctly
        """
        print("---------------------test_reset_course-------------------------------")
        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[1])
        )

        # 1
        course = models.Course.objects.get(id=1)
        old_course_id = course.id
        old_course_title = course.title
        userprofiles_before_length = models.UserProfile.objects.all().count()
        course_count_before = models.Course.objects.all().count()
        assessment_count_before = models.Assessment.objects.all().count()
        expected_assessment_count = (
            assessment_count_before - course.assessment_set.all().count()
        )
        comment_count_before = models.UserComment.objects.all().count()
        expected_comment_count = (
            comment_count_before - course.usercomment_set.all().count()
        )
        flexes_count_before = models.FlexAssessment.objects.all().count()
        course_flexes_count = models.FlexAssessment.objects.filter(
            assessment__course__id=old_course_id
        ).count()
        expected_flex_count_after = flexes_count_before - course_flexes_count

        # 2
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "delete"))
        )
        buttons = self.browser.find_elements(By.CLASS_NAME, "delete")

        # Iterate through each button and click it
        for button in buttons:
            if button.is_displayed():
                button.send_keys(Keys.ENTER)

        update_button = self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)
        alert = self.browser.switch_to.alert
        alert.accept()
        wait = WebDriverWait(self.browser, 5)
        wait.until_not(EC.url_contains("form"))  # Wait for changes to be made

        # 3
        course_after = models.Course.objects.get(id=1)
        user_courses_after = course_after.usercourse_set.all()
        assessments_after = course_after.assessment_set.all()
        comments_after = course_after.usercomment_set.all()
        userprofiles_after = models.UserProfile.objects.all()
        flex_assessments_after = models.FlexAssessment.objects.all()
        self.assertEqual(
            course_after.id, old_course_id
        )  # Make sure course correctly reset
        self.assertEqual(course_after.title, old_course_title)
        self.assertEqual(
            course_after.welcome_instructions,
            models.Course._meta.get_field("welcome_instructions").default,
        )
        self.assertEqual(
            course_after.comment_instructions,
            models.Course._meta.get_field("comment_instructions").default,
        )
        self.assertEqual(course_after.open, None)
        self.assertEqual(course_after.close, None)
        self.assertEqual(course_after.id, 1)
        self.assertEqual(
            user_courses_after.count(), 1
        )  # only one user left (the instructor who made the deletion)

        # 4
        self.assertEqual(assessments_after.count(), 0)
        self.assertEqual(comments_after.count(), 0)
        self.assertEqual(
            userprofiles_after.count(), userprofiles_before_length
        )  # no user profiles should be deleted
        self.assertEqual(
            flex_assessments_after.filter(
                assessment__course__id=course_after.id
            ).count(),
            0,
        )
        self.assertEqual(
            models.FlexAssessment.objects.all().count(), expected_flex_count_after
        )  # Other flexes should not be deleted
        self.assertEqual(models.Course.objects.all().count(), course_count_before)
        self.assertEqual(
            models.Assessment.objects.all().count(), expected_assessment_count
        )
        self.assertEqual(
            models.UserComment.objects.all().count(), expected_comment_count
        )

        # 5
        student_data = {
            "course_id": course_after.id,
            "role": "StudentEnrollment",
            "user_display_name": "Test User",
            "user_id": "987664",
            "login_id": "987664",
            "course_name": course_after.title,
        }

        student_browser = self.launch_new_user(student_data)
        wait = WebDriverWait(student_browser, 5)
        wait.until_not(EC.url_contains("launch"))  # Wait for changes to be made
        body_text = student_browser.find_element(By.TAG_NAME, "body").text
        self.assertIn(course_after.title, body_text)

        # Try logging in old student
        student1_data = {
            "course_id": course_after.id,
            "role": "StudentEnrollment",
            "user_display_name": "test_student1",
            "user_id": "1",
            "login_id": "1",
            "course_name": course_after.title,
        }
        student_browser = self.launch_new_user(student1_data)
        wait = WebDriverWait(student_browser, 5)
        wait.until_not(EC.url_contains("launch"))  # Wait for changes to be made
        body_text = student_browser.find_element(By.TAG_NAME, "body").text
        self.assertIn(course_after.title, body_text)
        student_browser.close()

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_reordering(self, mocked_flex_canvas_instance):
        """In course 3 the teacher is setting up flexible assessment for the first time
        The teacher will set up assessments and reorder them
        1. Navigate to Course Setup and create 3 assessments
        2. Switch positions of the 2nd and 3rd assessments
        3. Check that the updated positions are correct
        4. Add a new assessment and move it to the top
        5. Check that the order of all assessments has changed
        6. Check that the assessment order is reflected in the front-end
        7. Check that the assessment order is reflected in the csv download
        """
        print("---------------------test_reordering-------------------------------")

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[3])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[3])
        )
        # 1
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()
        self.browser.find_element(By.ID, "add").click()
        self.browser.find_element(By.ID, "add").click()
        self.browser.find_element(By.ID, "add").click()

        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        values = [
            "A1",
            "25",
            "10",
            "40",
            "A2",
            "25",
            "10",
            "40",
            "A3",
            "50",
            "50",
            "50",
        ]
        for index, value in enumerate(values):
            inputs[index + 6].send_keys(
                value
            )  # There are 6 hidden inputs we need to skip over

        open_date_field = self.browser.find_element(By.NAME, "date-open")
        date_field = self.browser.find_element(By.NAME, "date-close")

        tomorrow = datetime.now() + timedelta(1)

        open_date_field.send_keys(datetime.strftime(tomorrow, "%m-%d-%Y"))
        open_date_field.send_keys(Keys.TAB)
        open_date_field.send_keys("0245PM")

        date_field.send_keys(datetime.strftime(tomorrow, "%m-%d-%Y"))
        date_field.send_keys(Keys.TAB)
        date_field.send_keys("0245PM")

        # 2
        self.browser.fullscreen_window()
        actions = ActionChains(self.browser)
        handle_elements = self.browser.find_elements(By.CLASS_NAME, "handle-td")
        source_element = handle_elements[2]
        target_element = handle_elements[1]
        actions.drag_and_drop(source_element, target_element).perform()

        update_button = self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)

        wait = WebDriverWait(self.browser, 5)
        wait.until_not(EC.url_contains("form"))

        # 3
        A3_order = models.Assessment.objects.get(title="A3").order
        A2_order = models.Assessment.objects.get(title="A2").order
        A1_order = models.Assessment.objects.get(title="A1").order
        self.assertEqual(A3_order, 1)
        self.assertEqual(A2_order, 2)
        self.assertEqual(A1_order, 0)

        # 4
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()
        self.browser.find_element(By.ID, "add").click()

        handle_elements = self.browser.find_elements(By.CLASS_NAME, "handle-td")
        source_element = handle_elements[3]
        target_element = handle_elements[0]
        actions.drag_and_drop(source_element, target_element).perform()

        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        values = ["A4", "0", "0", "0"]
        for index, value in enumerate(values):
            inputs[index + 6].send_keys(
                value
            )  # There are 6 hidden inputs we need to skip over

        update_button = self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)

        wait = WebDriverWait(self.browser, 5)
        wait.until_not(EC.url_contains("form"))

        # 5
        A4_order = models.Assessment.objects.get(title="A4").order
        A3_order = models.Assessment.objects.get(title="A3").order
        A2_order = models.Assessment.objects.get(title="A2").order
        A1_order = models.Assessment.objects.get(title="A1").order
        self.assertEqual(A3_order, 2)
        self.assertEqual(A2_order, 3)
        self.assertEqual(A1_order, 1)
        self.assertEqual(A4_order, 0)

        print("OK")

        # front-end test begins here

        final_grades_button = self.browser.find_element(
            By.XPATH, '//a[contains(text(), "Final Grades")]'
        )
        final_grades_button.send_keys(Keys.ENTER)

        # Locate all <select> elements and enter appropriate assignment
        select_elements = self.browser.find_elements(By.TAG_NAME, "select")

        select_1 = Select(select_elements[1])
        select_1.select_by_visible_text("test_group1")

        select_2 = Select(select_elements[3])
        select_2.select_by_visible_text("test_group2")

        select_3 = Select(select_elements[2])
        select_3.select_by_visible_text("test_group3")

        select_4 = Select(select_elements[0])
        select_4.select_by_visible_text("test_group4")

        continue_button = self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Continue")]'
        )
        continue_button.send_keys(Keys.ENTER)

        thead_element = self.browser.find_element(By.TAG_NAME, "thead")

        th_elements = thead_element.find_elements(By.TAG_NAME, "th")

        assessment_list = []

        for index in range(5, len(th_elements), 2):
            th = th_elements[index]
            aria_label = th.get_attribute("aria-label").strip()
            assessment_list.append(aria_label)

        self.assertIn("A4", assessment_list[0], "A4 not in order")
        self.assertIn("A1", assessment_list[1], "A1 not in order")
        self.assertIn("A3", assessment_list[2], "A3 not in order")
        self.assertIn("A2", assessment_list[3], "A2 not in order")

        table_element = self.browser.find_element(By.ID, "final")
        td_elements = table_element.find_elements(By.TAG_NAME, "td")

        student_weights = []

        for index in range(10, len(td_elements), 2):
            td = td_elements[index]
            student_weights.append(td.text)

        self.assertEqual(
            "0.00%", student_weights[0], "student choice for A4 not in order"
        )
        self.assertEqual(
            "25.00%", student_weights[1], "student choice for A1 not in order"
        )
        self.assertEqual(
            "50.00%", student_weights[2], "student choice for A3 not in order"
        )
        self.assertEqual(
            "25.00%", student_weights[3], "student choice for A2 not in order"
        )

        # download csv and compare with pandas
        download_button = self.browser.find_element(
            By.CLASS_NAME, "btn-outline-primary"
        )

        filename = os.path.join(
            self.download_dir,
            f"Grades_test_course3_{datetime.now().strftime("%Y-%m-%dT%H%M")}.csv",
        )

        download_button.click()

        timeout = 5

        while not os.path.exists(filename) and timeout > 0:
            time.sleep(1)
            timeout -= 1

        self.assertTrue(os.path.exists(filename), "CSV file was not downloaded")

        df = pd.read_csv(filename, header=0)

        # Drop extra rows that might not match the expected structure
        df = df[df["Student"].notna()]

        # Strip spaces in column names (just in case)
        df.columns = df.columns.str.strip()

        # Select only columns from "A4 Grade %" onwards
        start_col = "A4 Grade %"
        df_filtered = df.loc[:, start_col:]

        expected_data_filtered = pd.DataFrame(
            {
                "A4 Grade %": [50, None, None],
                "A4 Weight % (0.0%)": [0.0, None, None],
                "A1 Grade %": [50, None, None],
                "A1 Weight % (25.0%)": [25.0, None, None],
                "A3 Grade %": [50, None, None],
                "A3 Weight % (50.0%)": [50.0, None, None],
                "A2 Grade %": [50, None, None],
                "A2 Weight % (25.0%)": [25.0, None, None],
            }
        )

        # Ensure NaNs are treated consistently
        df_filtered = df_filtered.fillna("")
        expected_data_filtered = expected_data_filtered.fillna("")

        # Compare the DataFrames
        pd.testing.assert_frame_equal(
            df_filtered.reset_index(drop=True),
            expected_data_filtered.reset_index(drop=True),
        )

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_min_max_auto(self, mocked_flex_canvas_instance):
        """In course 3 the teacher is setting up flexible assessment for the first time
        The teacher will set up a course and leave the min and max for one of them empty
        The fields should be filled in as per the default value automatically
        1. Navigate to Course Setup and create 3 assessments with one having empty fields
        2. Check that the value of the min and max are correct
        """
        print("---------------------test_min_max_auto-------------------------------")

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[3])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[3])
        )

        # 1
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()
        self.browser.find_element(By.ID, "add").click()
        self.browser.find_element(By.ID, "add").click()
        self.browser.find_element(By.ID, "add").click()

        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        # empty fields are represented by empty strings
        values = ["A1", "25", "10", "40", "A2", "25", "10", "40", "A3", "50", "", ""]
        for index, value in enumerate(values):
            inputs[index + 6].send_keys(
                value
            )  # There are 6 hidden inputs we need to skip over

        open_date_field = self.browser.find_element(By.NAME, "date-open")
        date_field = self.browser.find_element(By.NAME, "date-close")

        tomorrow = datetime.now() + timedelta(1)

        open_date_field.send_keys(datetime.strftime(tomorrow, "%m-%d-%Y"))
        open_date_field.send_keys(Keys.TAB)
        open_date_field.send_keys("0245PM")

        date_field.send_keys(datetime.strftime(tomorrow, "%m-%d-%Y"))
        date_field.send_keys(Keys.TAB)
        date_field.send_keys("0245PM")

        self.browser.fullscreen_window()

        update_button = self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)

        wait = WebDriverWait(self.browser, 5)
        wait.until_not(EC.url_contains("form"))

        # 2
        A3_min = models.Assessment.objects.get(title="A3").min
        A3_max = models.Assessment.objects.get(title="A3").max

        self.assertEqual(A3_min, 50)
        self.assertEqual(A3_max, 50)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_calendar(self, mocked_flex_canvas_instance):
        """In course 3 the teacher is setting up flexible assessment
        The calendar should match the open and close dates and provide an option if the dates do not match
        1. Navigate to Course Setup and create 3 assessments
        2. Check that the calendar dates are correct
        3. Change the calendar date
        4. Select the option to change the calendar dates
        5. Check that the calendar dates are correct
        6. Change the calendar date
        7. Select the option to change the close date of flex assessment
        8. Check that the close date is different to the original close date
        """
        print("---------------------test_calendar-------------------------------")

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[3])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[3])
        )

        # 1
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()
        self.browser.find_element(By.ID, "add").click()
        self.browser.find_element(By.ID, "add").click()
        self.browser.find_element(By.ID, "add").click()

        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        values = [
            "A1",
            "25",
            "10",
            "40",
            "A2",
            "25",
            "10",
            "40",
            "A3",
            "50",
            "50",
            "50",
        ]
        for index, value in enumerate(values):
            inputs[index + 6].send_keys(
                value
            )  # There are 6 hidden inputs we need to skip over

        open_date_field = self.browser.find_element(By.NAME, "date-open")
        date_field = self.browser.find_element(By.NAME, "date-close")

        tomorrow = datetime.now() + timedelta(1)

        open_date_field.send_keys(datetime.strftime(tomorrow, "%m-%d-%Y"))
        open_date_field.send_keys(Keys.TAB)
        open_date_field.send_keys("0245PM")

        date_field.send_keys(datetime.strftime(tomorrow, "%m-%d-%Y"))
        date_field.send_keys(Keys.TAB)
        date_field.send_keys("0245PM")

        update_button = self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)

        wait = WebDriverWait(self.browser, 5)
        wait.until_not(EC.url_contains("form"))

        # 2
        calendar_id = models.Course.objects.get(id=3).calendar_id
        canvas_calendar = mocked_flex_canvas_instance.get_calendar_event(
            str(calendar_id)
        )
        self.assertEqual(calendar_id, canvas_calendar.id)
        start_at = dateutil.parser.parse(canvas_calendar.start_at).replace(tzinfo=None)
        end_at = dateutil.parser.parse(canvas_calendar.end_at).replace(tzinfo=None)
        self.assertTrue(abs((end_at - tomorrow).days) <= 1)
        self.assertTrue(abs((start_at - tomorrow).days) <= 1)

        # 3
        canvas_calendar.edit(
            calendar_event={
                "title": "Flexible Assessment",
                "end_at": models.Course.objects.get(id=3).close + timedelta(2),
            }
        )

        # 4
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()
        time.sleep(5)
        self.browser.find_element(By.CLASS_NAME, "btn-secondary").click()

        # 5
        start_at = dateutil.parser.parse(canvas_calendar.start_at).replace(tzinfo=None)
        end_at = dateutil.parser.parse(canvas_calendar.end_at).replace(tzinfo=None)
        self.assertTrue(abs((end_at - tomorrow).days) <= 1)
        self.assertTrue(abs((start_at - tomorrow).days) <= 1)

        update_button = self.browser.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)

        wait = WebDriverWait(self.browser, 5)
        wait.until_not(EC.url_contains("form"))

        # 6
        canvas_calendar.edit(
            calendar_event={
                "title": "Flexible Assessment",
                "end_at": models.Course.objects.get(id=3).close + timedelta(2),
            }
        )

        # 7
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()
        time.sleep(5)
        self.browser.find_element(By.CLASS_NAME, "btn-primary").click()

        # 8
        c_close = models.Course.objects.get(id=3).close.replace(tzinfo=None)
        c_open = models.Course.objects.get(id=3).open.replace(tzinfo=None)
        self.assertTrue(abs((c_close - tomorrow).days) > 1)
        self.assertTrue(abs((c_open - tomorrow).days) <= 1)
