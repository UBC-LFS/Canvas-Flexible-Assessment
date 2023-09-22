from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from flexible_assessment.models import UserProfile
from django.urls import reverse
from django.test import Client, tag
from datetime import datetime, timedelta
from flexible_assessment.tests.test_data import DATA

import flexible_assessment.tests.mock_classes as mock_classes


class TestStudentViews(StaticLiveServerTestCase):
    fixtures = DATA

    def setUp(self):
        self.browser = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install())
        )
        user = UserProfile.objects.get(login_id="test_student1")
        self.client = Client()
        self.client.force_login(user)
        self.browser_teacher = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install())
        )
        self.login_teacher()

    def tearDown(self):
        self.browser.close()
        self.browser_teacher.close()

    def login_teacher(self):
        teacher = UserProfile.objects.get(login_id="test_instructor1")
        self.client_teacher = Client()
        self.client_teacher.force_login(teacher)

    @tag("slow", "view", "student_view")
    @mock_classes.use_mock_canvas()
    def test_view_page(self, mocked_flex_canvas_instance):
        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )

        input("Press Enter in this terminal to continue")

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_student_first_time_input_flexes(self, mocked_flex_canvas_instance):
        """In course 4 the teacher has set up flexes. The student should:
        1. Be redirected to student_form page
        2. Submit a valid desired % (40 and 60)
        3. Database should save the desired % and comment
        4. They should be redirected to the home page and see their chosen percentages
        """
        print(
            "---------------------test_student_first_time_input_flexes-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )

        # 1
        self.assertIn("form", self.browser.current_url)

        # 2
        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        inputs[1].send_keys("40")
        inputs[2].send_keys("60")
        inputs[3].click()

        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.send_keys("SELENIUM COMMENT")

        submit.click()

        # 3 and 4
        self.assertNotIn("form", self.browser.current_url)

        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("40", bodyText)
        self.assertIn("60", bodyText)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_student_change_flexes(self, mocked_flex_canvas_instance):
        """In course 1 the teacher has set up flexes and the student has already inputed choices. The student should:
        1. Start from the home page
        2. Should see their choices (all 25.00%)
        3. Navigate to Assessments
        4. Change their desired %
        5. Be redirected back to the home page with their updated percentages
        """
        print(
            "---------------------test_student_change_flexes-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[1])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[1])
        )

        # 1
        self.assertNotIn("form", self.browser.current_url)

        # 2
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("25.00", bodyText)

        # 3
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()
        self.assertIn("form", self.browser.current_url)

        # 4
        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        submit = self.browser.find_element(By.TAG_NAME, "button")

        inputs[1].clear()
        inputs[2].clear()
        inputs[3].clear()
        inputs[4].clear()

        inputs[1].send_keys("25.01")
        inputs[2].send_keys("25.02")
        inputs[3].send_keys("24.99")
        inputs[4].send_keys("24.98")
        inputs[5].click()

        submit.send_keys(Keys.ENTER)

        # 5
        self.assertNotIn("form", self.browser.current_url)
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("25.01", bodyText)
        self.assertIn("25.02", bodyText)
        self.assertIn("24.99", bodyText)
        self.assertIn("24.98", bodyText)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_student_course_not_setup(self, mocked_flex_canvas_instance):
        """In course 2 the teacher has not set up flexes
        1. Student should be on the homepage and see a special message
        """
        print(
            "---------------------test_student_course_not_setup-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[2])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[2])
        )

        # 1
        self.assertNotIn("form", self.browser.current_url)
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("Your instructor is not using this tool at the moment", bodyText)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_student_deadline_past(self, mocked_flex_canvas_instance):
        """In course 5 the deadline has passed and the student has not made any choices
        1. Student should be on the homepage
        2. They should see their Chosen % as 'Default'
        """
        print(
            "---------------------test_student_deadline_past-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[5])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[5])
        )

        # 1
        self.assertNotIn("form", self.browser.current_url)

        # 2
        self.assertNotIn("form", self.browser.current_url)
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("Default", bodyText)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_student_percentage_gets_reset(self, mocked_flex_canvas_instance):
        """The student in course 4 chooses his flexes, but then the teacher changes the weights thus resetting their weights
        1. Student starts by choosing 20 % and 80 %
        2. Student gets redirected to the homepage and sees their weights
        3. Instructor then changes the minimum of the first assignment to 20%
        4. Student upon refreshing the page sees their weights are now the default
        4.5 Their comment should also be gone
        5. Student goes back to the assessments tab to set their weights to 20% and 80%
        """
        print(
            "---------------------test_student_percentage_gets_reset-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )

        # 1
        self.assertIn("form", self.browser.current_url)
        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")

        inputs[1].send_keys("20")
        inputs[2].send_keys("80")
        inputs[3].click()

        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.send_keys("INITIAL COMMENT")

        submit.click()

        # 2
        self.assertNotIn("form", self.browser.current_url)

        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("20", bodyText)
        self.assertIn("80", bodyText)

        # 3
        session_id_teacher = self.client_teacher.session.session_key
        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.add_cookie(
            {"name": "sessionid", "value": session_id_teacher}
        )

        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.find_element(By.LINK_TEXT, "Assessments").click()

        min_field = self.browser_teacher.find_element(By.NAME, "assessment-0-min")
        min_field.clear()
        min_field.send_keys("21")

        max_field = self.browser_teacher.find_element(By.NAME, "assessment-1-max")
        max_field.clear()
        max_field.send_keys("79")

        self.browser_teacher.fullscreen_window()
        update_button = self.browser_teacher.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)

        alert = (
            self.browser_teacher.switch_to.alert
        )  # Accept the confirmation message that a student will be reset
        alert.accept()

        # 4
        self.browser.refresh()
        self.browser.refresh()  # Double refresh because database takes time to update
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("Default", bodyText)
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()

        # 4.5
        comment_field = self.browser.find_element(By.NAME, "comment")
        self.assertEqual(comment_field.text, "")

        # 5
        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")

        inputs[1].send_keys("20")
        inputs[2].send_keys("80")
        inputs[3].click()

        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.send_keys("NEW COMMENT")

        submit.click()

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_student_page_open_when_deadline_expires(self, mocked_flex_canvas_instance):
        """The student in course 4 opens the assessments page before the deadline, but then the deadline expires before they can submit
        1. Student starts by choosing 40 % and 60 % but doesn't submit
        2. Instructor changes the deadline to yesterday
        3. Student tries to hit submit
        4. Student sees the form not open page
        5. Student goes to the homepage and sees they have the default selection
        """
        print(
            "---------------------test_student_page_open_when_deadline_expires-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )

        # 1
        self.assertIn("form", self.browser.current_url)
        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")

        inputs[1].send_keys("40")
        inputs[2].send_keys("60")
        inputs[3].click()

        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.send_keys(
            "I am so happy to be able to choose my flexes :) I hope nothing goes wrong..."
        )

        # 2
        session_id_teacher = self.client_teacher.session.session_key
        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.add_cookie(
            {"name": "sessionid", "value": session_id_teacher}
        )

        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.find_element(By.LINK_TEXT, "Assessments").click()

        date_field = self.browser_teacher.find_element(By.NAME, "date-close")
        yesterday = datetime.now() - timedelta(1)
        date_field.send_keys(datetime.strftime(yesterday, "%m-%d-%Y"))

        self.browser_teacher.fullscreen_window()
        update_button = self.browser_teacher.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)

        # 3
        self.assertTrue(submit.is_enabled())
        submit.click()

        # 4
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("Form not open", bodyText)

        # 5
        self.browser.find_element(By.LINK_TEXT, "Home").click()
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("Default", bodyText)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_student_editing_when_min_max_changed(self, mocked_flex_canvas_instance):
        """The student in course 4 is choosing their weights according to the current max, but then the teacher changes them so it is now invalid
        1. Student starts by choosing 10 % and 90 % but doesn't submit
        2. Instructor changes min for the first assignment to 20 %
        3. Student tries to hit submit
        4. Student sees form errors
        5. Student redos the form and submits
        """
        print(
            "---------------------test_student_editing_when_min_max_changed-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )

        # 1
        self.assertIn("form", self.browser.current_url)
        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")

        inputs[1].send_keys("20")
        inputs[2].send_keys("80")
        inputs[3].click()

        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.send_keys(
            "I am so glad to choose these weights, I spent so much time coming to this decision"
        )

        # 2
        session_id_teacher = self.client_teacher.session.session_key
        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.add_cookie(
            {"name": "sessionid", "value": session_id_teacher}
        )

        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.find_element(By.LINK_TEXT, "Assessments").click()

        min_field = self.browser_teacher.find_element(By.NAME, "assessment-0-min")
        min_field.clear()
        min_field.send_keys("21")

        max_field = self.browser_teacher.find_element(By.NAME, "assessment-1-max")
        max_field.clear()
        max_field.send_keys("79")
        self.browser_teacher.fullscreen_window()
        update_button = self.browser_teacher.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)

        # 3
        submit.click()

        # 4
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("Flex should be greater than or equal to min", bodyText)

        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        inputs[1].clear()
        inputs[1].send_keys("21")
        inputs[2].clear()
        inputs[2].send_keys("79")
        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.clear()
        comment_field.send_keys("Who changed the minimum from 10% to 20% :'(")
        self.browser.fullscreen_window()
        self.browser.execute_script("arguments[0].scrollIntoView();", submit)
        submit.click()

        self.assertNotIn("form", self.browser.current_url)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_student_editing_when_assessment_deleted(self, mocked_flex_canvas_instance):
        """The student in course 4 is choosing their weights, but then a teacher deletes one of the assessments
        1. Student starts by choosing 10 % and 90 % but doesn't submit
        2. Instructor deletes the second assessment
        3. Student tries to hit submit
        4. Student sees form errors
        """
        print(
            "---------------------test_student_editing_when_assessment_deleted-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )

        # 1
        self.assertIn("form", self.browser.current_url)
        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")

        inputs[1].send_keys("10")
        inputs[2].send_keys("90")
        inputs[3].click()

        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.send_keys("Wow so many awesome assessments")

        # 2
        session_id_teacher = self.client_teacher.session.session_key
        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.add_cookie(
            {"name": "sessionid", "value": session_id_teacher}
        )

        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.find_element(By.LINK_TEXT, "Assessments").click()

        delete_button = self.browser_teacher.find_element(
            By.XPATH, '//*[@id="assessments"]/tbody/tr[2]/td[6]/button'
        ).click()

        default_field = self.browser_teacher.find_element(
            By.NAME, "assessment-0-default"
        )
        default_field.clear()
        default_field.send_keys("80")

        min_field = self.browser_teacher.find_element(By.NAME, "assessment-0-min")
        min_field.click()  # This is so the Update button is enabled

        self.browser_teacher.find_element(By.ID, "add").click()

        title_field = self.browser_teacher.find_element(By.NAME, "assessment-1-title")
        default_field = self.browser_teacher.find_element(
            By.NAME, "assessment-1-default"
        )
        min_field = self.browser_teacher.find_element(By.NAME, "assessment-1-min")
        max_field = self.browser_teacher.find_element(By.NAME, "assessment-1-max")

        title_field.send_keys("AssignmentC")
        default_field.send_keys("20")
        min_field.send_keys("20")
        max_field.send_keys("80")

        self.browser_teacher.fullscreen_window()
        update_button = self.browser_teacher.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)
        wait = WebDriverWait(self.browser_teacher, 5)
        wait.until_not(EC.url_contains("form"))  # Wait for changes to be made

        # 3
        self.assertTrue(submit.is_enabled())
        submit.click()

        # 4
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("Total flex has to add up to 100%", bodyText)

        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        inputs[1].clear()
        inputs[1].send_keys("80")
        inputs[2].send_keys("20")
        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.clear()
        comment_field.send_keys("Where did the second assessment go :'(")
        submit.click()

        self.assertNotIn("form", self.browser.current_url)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_student_editing_when_assessment_added(self, mocked_flex_canvas_instance):
        """The student in course 4 is choosing their weights, but then a teacher adds another assessments
        1. Student starts by choosing 10 % and 90 % but doesn't submit
        2. Instructor adds a third assessment with a minimum
        3. Student tries to hit submit
        4. Student sees form errors
        """
        print(
            "---------------------test_student_editing_when_assessment_deleted-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )

        # 1
        self.assertIn("form", self.browser.current_url)
        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")

        inputs[1].send_keys("10")
        inputs[2].send_keys("90")
        inputs[3].click()

        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.send_keys(
            "I hope there are only two assessments, I get choice paralysis"
        )

        # 2
        session_id_teacher = self.client_teacher.session.session_key
        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.add_cookie(
            {"name": "sessionid", "value": session_id_teacher}
        )

        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.find_element(By.LINK_TEXT, "Assessments").click()

        self.browser_teacher.find_element(By.ID, "add").click()

        title_field = self.browser_teacher.find_element(By.NAME, "assessment-2-title")
        default_field = self.browser_teacher.find_element(
            By.NAME, "assessment-2-default"
        )
        min_field = self.browser_teacher.find_element(By.NAME, "assessment-2-min")
        max_field = self.browser_teacher.find_element(By.NAME, "assessment-2-max")

        title_field.send_keys("AssignmentC")
        default_field.send_keys("10")
        min_field.send_keys("0")
        max_field.send_keys("60")

        old_default_field = self.browser_teacher.find_element(
            By.NAME, "assessment-0-default"
        )
        old_default_field.clear()
        old_default_field.send_keys("40")
        min_field = self.browser_teacher.find_element(By.NAME, "assessment-0-min")
        min_field.click()  # This is so the Update button is enabled

        self.browser_teacher.fullscreen_window()
        update_button = self.browser_teacher.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)
        wait = WebDriverWait(self.browser_teacher, 5)
        wait.until_not(EC.url_contains("form"))  # Wait for changes to be made

        # 3
        self.assertTrue(submit.is_enabled())
        submit.click()

        # 4
        bodyText = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("This field is required", bodyText)

        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")
        inputs[1].clear()
        inputs[1].send_keys("20")
        inputs[2].clear()
        inputs[2].send_keys("70")
        inputs[3].send_keys("10")
        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.clear()
        comment_field.send_keys("I spent 10 hours deciding my weights")
        submit.send_keys(Keys.ENTER)

        self.assertNotIn("form", self.browser.current_url)

    @tag("slow")
    @mock_classes.use_mock_canvas()
    def test_teacher_updates_instruction_comments(self, mocked_flex_canvas_instance):
        """The student in course 4 has set up their weights and sees the default comment that the instructor later updates
        1. Student starts by choosing 10 % and 90 % and submits
        2. Instructor changes the instructions
        3. Student sees the new instructions
        """
        print(
            "---------------------test_student_editing_when_assessment_deleted-------------------------------"
        )

        session_id = self.client.session.session_key
        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )
        self.browser.add_cookie({"name": "sessionid", "value": session_id})

        self.browser.get(
            self.live_server_url + reverse("student:student_home", args=[4])
        )

        # 1
        self.assertIn("form", self.browser.current_url)
        submit = self.browser.find_element(By.TAG_NAME, "button")
        inputs = self.browser.find_elements(By.TAG_NAME, "input")

        inputs[1].send_keys("20")
        inputs[2].send_keys("80")
        inputs[3].click()

        comment_field = self.browser.find_element(By.NAME, "comment")
        comment_field.send_keys(
            "I hope there are only two assessments, I get choice paralysis"
        )
        page_text = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("Welcome to test course 4", page_text)
        self.assertIn("Please explain why you made those choices", page_text)
        submit.send_keys(Keys.ENTER)

        # 2
        session_id_teacher = self.client_teacher.session.session_key
        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.add_cookie(
            {"name": "sessionid", "value": session_id_teacher}
        )

        self.browser_teacher.get(
            self.live_server_url + reverse("instructor:instructor_home", args=[4])
        )
        self.browser_teacher.find_element(By.LINK_TEXT, "Assessments").click()

        welcome_instructions = self.browser_teacher.find_element(
            By.NAME, "date-welcome_instructions"
        )
        comment_instructions = self.browser_teacher.find_element(
            By.NAME, "date-comment_instructions"
        )
        welcome_instructions.clear()
        comment_instructions.clear()
        welcome_instructions.send_keys("NEW WELCOME INSTRUCTIONS")
        comment_instructions.send_keys("NEW COMMENT INSTRUCTIONS")

        update_button = self.browser_teacher.find_element(
            By.XPATH, '//button[contains(text(), "Update")]'
        )
        update_button.send_keys(Keys.ENTER)

        wait = WebDriverWait(self.browser_teacher, 5)
        wait.until_not(EC.url_contains("form"))  # Wait for changes to be made

        # 3
        self.browser.find_element(By.LINK_TEXT, "Assessments").click()

        page_text = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertNotIn("Welcome to test course 4", page_text)
        self.assertNotIn("Please explain why you made those choices", page_text)

        self.assertIn("NEW WELCOME INSTRUCTIONS", page_text)
        self.assertIn("NEW COMMENT INSTRUCTIONS", page_text)
