from django.test import TestCase, Client
from flexible_assessment.models import (
    UserProfile,
    Course,
    UserCourse,
    Roles,
    Assessment,
)
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
from flexible_assessment.tests.test_data import DATA

from django.utils import timezone
import datetime


class TestViews(TestCase):
    fixtures = DATA

    def setUp(self):
        self.client = Client()
        user = UserProfile.objects.get(login_id="test_student1")
        self.client.force_login(user)

    """ Begin tests for StudentAssessmentView. For a form to be valid it must also be within the flex range set by the instructor and is within the deadline """

    def test_StudentAssessmentView_form_valid(self):
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        data = {
            assessments[0].id.hex: 30,
            assessments[1].id.hex: 30,
            assessments[2].id.hex: 10,
            assessments[3].id.hex: 30,
            "agreement": True,
            "comment": "My test_student_form_valid comment",
        }

        # Get student_home first to set up display_name session data
        student_home = reverse("student:student_home", args=[course_id])
        response = self.client.get(student_home)

        response = self.client.post(
            reverse("student:student_form", args=[course_id]), data=data
        )
        # A successful form post should redirect the user to the home page
        self.assertEqual(type(response), HttpResponseRedirect)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("student:student_home", args=[course_id])
        )

    def test_StudentAssessmentView_form_invalid_out_of_range(self):
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        # See "./flexible_assessment/fixtures/assessments.json". All the flex ranges are between 10 and 30
        data = {
            assessments[0].id.hex: 31,
            assessments[1].id.hex: 30,
            assessments[2].id.hex: 9,
            assessments[3].id.hex: 30,
            "agreement": True,
            "comment": "My test_student_form_valid comment",
        }

        response = self.client.post(
            reverse("student:student_form", args=[course_id]), data=data
        )

        self.assertEqual(type(response), TemplateResponse)
        self.assertEqual(response.status_code, 200)
        # print(response.context['form'].errors)
        self.assertContains(response, "Flex should be less than or equal to max")
        self.assertContains(response, "Flex should be greater than or equal to min")

    def test_StudentAssessmentView_form_invalid_before_deadline(self):
        course_id = 1
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        course = Course.objects.filter(id=course_id).update(open=tomorrow)
        assessments = Assessment.objects.filter(course_id=course_id)
        # See "./flexible_assessment/fixtures/assessments.json". All the flex ranges are between 10 and 30
        data = {
            assessments[0].id.hex: 25,
            assessments[1].id.hex: 25,
            assessments[2].id.hex: 25,
            assessments[3].id.hex: 25,
            "agreement": True,
            "comment": "My test_student_form_valid comment",
        }

        response = self.client.post(
            reverse("student:student_form", args=[course_id]), data=data
        )

        self.assertEqual(type(response), TemplateResponse)
        self.assertEqual(response.status_code, 200)

    def test_StudentAssessmentView_form_invalid_after_deadline(self):
        course_id = 1
        course = Course.objects.filter(id=course_id).update(close=timezone.now())
        assessments = Assessment.objects.filter(course_id=course_id)
        # See "./flexible_assessment/fixtures/assessments.json". All the flex ranges are between 10 and 30
        data = {
            assessments[0].id.hex: 25,
            assessments[1].id.hex: 25,
            assessments[2].id.hex: 25,
            assessments[3].id.hex: 25,
            "agreement": True,
            "comment": "My test_student_form_valid comment",
        }

        response = self.client.post(
            reverse("student:student_form", args=[course_id]), data=data
        )

        self.assertEqual(type(response), TemplateResponse)
        self.assertEqual(response.status_code, 200)

    def test_StudentAssessmentView_comment_format_on_log(self):
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        data = {
            assessments[0].id.hex: 30,
            assessments[1].id.hex: 30,
            assessments[2].id.hex: 10,
            assessments[3].id.hex: 30,
            "agreement": True,
            "comment": "My\nMultiline\nComment",
        }

        # Get student_home first to set up display_name session data
        student_home = reverse("student:student_home", args=[course_id])
        response = self.client.get(student_home)

        response = self.client.post(
            reverse("student:student_form", args=[course_id]), data=data
        )
        # A successful form post should redirect the user to the home page
        self.assertEqual(type(response), HttpResponseRedirect)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("student:student_home", args=[course_id])
        )

        # insert test here checking last log entry for comment
        import os
        from django.conf import settings

        log_file_path = os.path.join(settings.BASE_DIR, "log", "info.log")
        with open(log_file_path) as f:
            for line in f:
                pass
            last_line = line
            self.assertTrue(
                "- Updated comment to 'My\\nMultiline\\nComment' | test_student1"
                in last_line
            )
