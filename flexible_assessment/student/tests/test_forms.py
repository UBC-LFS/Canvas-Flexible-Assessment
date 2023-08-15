from django.test import TestCase
from student.forms import StudentAssessmentForm
from flexible_assessment.models import Assessment
from flexible_assessment.tests.test_data import DATA


class TestForms(TestCase):
    fixtures = DATA

    def test_student_form_valid(self):
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        form_data = {
            assessments[0].id.hex: 50,
            assessments[1].id.hex: 20,
            assessments[2].id.hex: 10,
            assessments[3].id.hex: 20,
            "agreement": True,
        }

        form = StudentAssessmentForm(user_id=1, course_id=1, data=form_data)
        self.assertTrue(form.is_valid())

    def test_student_form_invalid_does_not_add_to_100(self):
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        form_data = {
            assessments[0].id.hex: 50,
            assessments[1].id.hex: 20,
            assessments[2].id.hex: 11,
            assessments[3].id.hex: 20,
            "agreement": True,
        }

        form = StudentAssessmentForm(user_id=1, course_id=1, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["__all__"][0],
            "Total flex has to add up to 100%, currently it is (101)%",
        )

    def test_student_form_invalid_invalid_argument(self):
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        form_data = {
            assessments[0].id.hex: -1,
            assessments[1].id.hex: 12.2,
            assessments[2].id.hex: 101,
            assessments[3].id.hex: 70,
            "agreement": True,
        }

        form = StudentAssessmentForm(user_id=1, course_id=1, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["__all__"][0],
            "Total flex has to add up to 100%, currently it is (82.2)%",
        )
        self.assertEqual(
            form.errors[assessments[0].id.hex][0],
            "Ensure this value is greater than or equal to 0.",
        )
        self.assertEqual(
            form.errors[assessments[2].id.hex][0],
            "Ensure this value is less than or equal to 100.",
        )

    def test_student_form_invalid_did_not_agree(self):
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        form_data = {
            assessments[0].id.hex: 50,
            assessments[1].id.hex: 20,
            assessments[2].id.hex: 11,
            assessments[3].id.hex: 20,
        }

        form = StudentAssessmentForm(user_id=1, course_id=1, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["agreement"][0], "This field is required.")

    def test_student_form_invalid_missing_field(self):
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        form_data = {
            assessments[0].id.hex: 50,
            assessments[2].id.hex: 30,
            assessments[3].id.hex: 20,
            "agreement": True,
        }

        form = StudentAssessmentForm(user_id=1, course_id=1, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors[assessments[1].id.hex][0], "This field is required."
        )
