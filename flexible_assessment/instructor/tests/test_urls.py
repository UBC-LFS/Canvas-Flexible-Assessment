from django.test import TestCase, Client
from django.urls import reverse
from flexible_assessment.models import UserProfile, Course, UserCourse, Roles
from instructor.views import *
from flexible_assessment.tests.test_data import DATA
import flexible_assessment.tests.mock_classes as mock_classes

from unittest.mock import patch


class TestUrls(TestCase):
    fixtures = DATA

    def setUp(self):
        self.client = Client()

    def login_instructor(self, id, course_title):
        self.user = UserProfile.objects.get(login_id=id)
        course = Course.objects.get(title=course_title)
        self.client.force_login(self.user)
        return course.id

    # Helper function to log in a student and try to access the url, students should be redirected home
    def url_invalid_for_student(self, url_name):
        user = UserProfile.objects.get(login_id="test_student1")
        course = Course.objects.get(title="test_course1")
        self.client.force_login(user)

        url = reverse(f"instructor:{url_name}", args=[course.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("student:student_home", args=[course.id])
        )

    # Helper function to log in an instructor and try to access the url
    def url_valid_for_instructor(self, url_name):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse(f"instructor:{url_name}", args=[course_id])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_instructor_home_url_valid_for_admins(self):
        user = UserProfile.objects.get(login_id="admin")
        course = Course.objects.get(title="test_course1")
        self.client.force_login(user)
        instructor_home_url = reverse("instructor:instructor_home", args=[course.id])

        response = self.client.get(instructor_home_url)
        self.assertEqual(response.status_code, 200)

    def test_instructor_home_url_valid_for_tas(self):
        user = UserProfile.objects.get(login_id="test_ta1")
        course = Course.objects.get(title="test_course1")
        self.client.force_login(user)
        instructor_home_url = reverse("instructor:instructor_home", args=[course.id])

        response = self.client.get(instructor_home_url)
        self.assertEqual(response.status_code, 200)

    def test_instructor_home_url_invalid_for_students(self):
        self.url_invalid_for_student("instructor_home")

    @mock_classes.use_mock_canvas()
    def test_instructor_form_url_valid_for_instructor(
        self, mocked_flex_canvas_instance
    ):
        self.url_valid_for_instructor("instructor_form")

    @mock_classes.use_mock_canvas()
    def test_instructor_form_url_invalid_for_students(
        self, mocked_flex_canvas_instance
    ):
        self.url_invalid_for_student("instructor_form")

    def test_instructor_home_url_valid_for_instructor(self):
        self.url_valid_for_instructor("instructor_home")

    @mock_classes.use_mock_canvas()
    def test_instructor_assessments_export_valid_for_instructor(
        self, mocked_flex_canvas_instance
    ):
        self.url_valid_for_instructor("assessments_export")

    @mock_classes.use_mock_canvas()
    def test_instructor_assessments_export_invalid_for_students(
        self, mocked_flex_canvas_instance
    ):
        self.url_invalid_for_student("assessments_export")

    def test_instructor_file_upload_valid_for_instructor(self):
        self.url_valid_for_instructor("file_upload")

    def test_instructor_file_upload_invalid_for_students(self):
        self.url_invalid_for_student("file_upload")

    def test_instructor_percentage_list_valid_for_instructor(self):
        self.url_valid_for_instructor("percentage_list")

    def test_instructor_percentage_list_invalid_for_students(self):
        self.url_invalid_for_student("percentage_list")

    def test_instructor_percentage_list_export_valid_for_instructor(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)

        self.url_valid_for_instructor("percentage_list_export")

    def test_override_student_form_percentage_url_valid_for_instructor(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse(
            "instructor:override_student_form_percentage", args=[course_id, 1]
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_override_student_form_final_url_valid_for_instructor(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse("instructor:override_student_form_final", args=[course_id, 1])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @mock_classes.use_mock_canvas()
    def test_group_form_url_valid_for_instructor(self, mocked_flex_canvas_instance):
        self.url_valid_for_instructor("group_form")

    @mock_classes.use_mock_canvas()
    def test_final_grades_url_valid_for_instructor(self, mocked_flex_canvas_instance):
        self.url_valid_for_instructor("final_grades")

    @mock_classes.use_mock_canvas()
    def test_final_grades_export_url_valid_for_instructor(
        self, mocked_flex_canvas_instance
    ):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)

        self.url_valid_for_instructor("final_grades_export")

    @mock_classes.use_mock_canvas()
    def test_final_grades_submit_url_valid_for_instructor(
        self, mocked_flex_canvas_instance
    ):
        self.url_valid_for_instructor("final_grades_submit")

    @mock_classes.use_mock_canvas()
    def test_final_grades_submit_url_invalid_for_students(
        self, mocked_flex_canvas_instance
    ):
        self.url_invalid_for_student("final_grades_submit")

    def test_instructor_tries_access_course_id_they_are_not_instructing(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse("instructor:instructor_home", args=[1000])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_instructor_tries_access_nonexistant_course(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        instructor_home_url = reverse("instructor:instructor_home", args=[999])
        response = self.client.get(instructor_home_url)
        self.assertEqual(response.status_code, 404)

    def test_instructor_tries_override_student_nonexistant_student(self):
        course_id = self.login_instructor("test_instructor1", "test_course1")
        url = reverse(
            "instructor:override_student_form_percentage", args=[course_id, 9999]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # # TODO: They should probably be routed to course_setup page instead of being able to access these pages
    # def test_accessing_urls_when_course_setup_not_complete(self):
    #     course_id = self.login_instructor("test_instructor1", "test_course2")
    #     url = reverse('instructor:file_upload', args=[course_id])
    #     response = self.client.get(url)

    #     self.assertEqual(response.status_code, 302)
