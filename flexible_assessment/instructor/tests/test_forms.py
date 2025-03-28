from django.test import TestCase, tag
from instructor.forms import *
from flexible_assessment.tests.test_data import DATA

from flexible_assessment.tests.mock_classes import *
from unittest.mock import patch


class TestForms(TestCase):
    fixtures = DATA

    def test_DateForm_invalid_close_before_open(self):
        form_data = {"open": "2023-01-01T01:00", "close": "2023-01-01T00:59"}
        form = CourseSettingsForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_DateForm_valid_close_equal_open(self):
        form_data = {"open": "2023-01-01T01:00", "close": "2023-01-01T01:00"}
        form = CourseSettingsForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_DateForm_valid_close_after_open(self):
        form_data = {"open": "2023-01-01T01:00", "close": "2023-01-01T01:01"}
        form = CourseSettingsForm(data=form_data)
        self.assertTrue(form.is_valid())

    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_AssessmentGroupForm_valid(self, mock_flex_canvas):
        """An AssessmentGroupForm is valid if it has data/selection associated with each assessment"""
        course_id = 1
        course = MockCanvasCourse()
        assessments = Assessment.objects.filter(course_id=course_id)
        data = {
            assessments[0].id.hex: 1,
            assessments[1].id.hex: 3,
            assessments[2].id.hex: 3,
            assessments[3].id.hex: 4,
            "weight_option": "default",  # Had to add this to avoid error
        }
        form = AssessmentGroupForm(
            canvas_course=course, assessments=assessments, data=data
        )
        self.assertTrue(form.is_valid())

        assessments_2 = []
        data_2 = {
            "weight_option": "default",  # Had to add this to avoid error
        }
        form = AssessmentGroupForm(
            canvas_course=course, assessments=assessments_2, data=data_2
        )
        self.assertTrue(form.is_valid())

    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_AssessmentGroupForm_invalid(self, mock_flex_canvas):
        """An AssessmentGroupForm is invalid if each assessment does not have a choice made"""
        course_id = 1
        course = MockCanvasCourse()
        assessments = Assessment.objects.filter(course_id=course_id)
        data = {
            assessments[0].id.hex: 1,
            assessments[1].id.hex: 3,
            assessments[3].id.hex: "-",
        }

        form = AssessmentGroupForm(
            canvas_course=course, assessments=assessments, data=data
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors[assessments[2].id.hex][0], "This field is required."
        )
        self.assertEqual(
            form.errors[assessments[3].id.hex][0],
            "Select a valid choice. - is not one of the available choices.",
        )

    @patch("instructor.views.FlexCanvas", return_value=MockFlexCanvas)
    def test_AssessmentGroupForm_correct_order(self, mock_flex_canvas):
        """Make sure Assessment Groups from Cavnas are ordered correctly"""
        course_id = 1
        course = MockCanvasCourse()
        course.groups = [
            MockAssignmentGroup("A1", 1),
            MockAssignmentGroup("b1", 2),
            MockAssignmentGroup("a2", 3),
            MockAssignmentGroup("B2", 4),
        ]

        assessments = Assessment.objects.filter(course_id=course_id)
        data = {
            assessments[0].id.hex: 1,
            assessments[1].id.hex: 2,
            assessments[2].id.hex: 3,
            assessments[3].id.hex: 4,
        }

        form = AssessmentGroupForm(
            canvas_course=course, assessments=assessments, data=data
        )

        choices = form.fields[assessments[0].id.hex].choices
        group_names = [item[1] for item in choices[1:]]
        expected_names = ["A1", "a2", "b1", "B2"]

        self.assertListEqual(group_names, expected_names, "Names are not equal")
