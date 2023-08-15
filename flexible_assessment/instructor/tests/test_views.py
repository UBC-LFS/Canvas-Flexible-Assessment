from django.test import TestCase, Client, tag
from django.urls import reverse
from django.template.response import TemplateResponse
from flexible_assessment.models import Assessment, UserProfile
from instructor.forms import *
from instructor.views import *
from flexible_assessment.tests.test_data import DATA
import datetime

import flexible_assessment.tests.mock_classes as mock_classes


class TestViews(TestCase):
    fixtures = DATA

    def setUp(self):
        self.client = Client()
        self.user = UserProfile.objects.get(login_id="test_instructor1")
        self.client.force_login(self.user)

    """ BEGIN TESTS FOR ASSESSMENT GROUP VIEW (instructor:group_form -> /final/match) """

    @mock_classes.use_mock_canvas()
    def test_AssessmentGroupView_valid_form(self, mocked_flex_canvas_instance):
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        data = {
            assessments[0].id.hex: 1,
            assessments[1].id.hex: 2,
            assessments[2].id.hex: 3,
            assessments[3].id.hex: 4,
            "fdsfds": 5,  # This doesn't raise an error, but it shouldn't matter since the form data gets cleaned before sending to canvas
        }

        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)

        response = self.client.post(
            reverse("instructor:group_form", args=[course_id]), data=data
        )
        # A successful form post should redirect the user to AssessmentGroupView.success_reverse_name = instructor:final_grades
        self.assertEqual(type(response), HttpResponseRedirect)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("instructor:final_grades", args=[course_id])
        )

        # Make sure the Canvas course group weights are now updated to match the default for each assessment
        canvas_groups = mocked_flex_canvas_instance.get_course(
            1
        ).get_assignment_groups()
        for index, assessment in enumerate(assessments):
            # Indexes were matched when we set up the data
            self.assertEqual(assessment.default, canvas_groups[index].group_weight)

    @mock_classes.use_mock_canvas()
    def test_AssessmentGroupView_invalid_form(self, mocked_flex_canvas_instance):
        """This form is invalid as some assessments are not matched and one is invalid"""
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        data = {
            assessments[1].id.hex: 2,
            assessments[2].id.hex: 3,
            assessments[3].id.hex: "-",
        }

        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)
        response = self.client.post(
            reverse("instructor:group_form", args=[course_id]), data=data
        )
        errors = response.context["form"].errors

        self.assertEqual(type(response), TemplateResponse)
        self.assertFormError(
            response, "form", assessments[0].id.hex, "This field is required."
        )
        self.assertFormError(
            response,
            "form",
            assessments[3].id.hex,
            "Select a valid choice. - is not one of the available choices.",
        )
        self.assertFalse(assessments[1].id.hex in errors.keys())
        self.assertFalse(assessments[2].id.hex in errors.keys())

    @mock_classes.use_mock_canvas()
    def test_AssessmentGroupView_invalid_form(self, mocked_flex_canvas_instance):
        """This form is invalid as some assessments are duplicated"""
        course_id = 1
        assessments = Assessment.objects.filter(course_id=course_id)
        data = {
            assessments[0].id.hex: 2,
            assessments[1].id.hex: 2,
            assessments[2].id.hex: 3,
            assessments[3].id.hex: 4,
        }
        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)

        response = self.client.post(
            reverse("instructor:group_form", args=[course_id]), data=data
        )
        errors = response.context["form"].errors

        self.assertEqual(type(response), TemplateResponse)
        self.assertFormError(
            response, "form", assessments[0].id.hex, "Matched groups must be unique"
        )
        self.assertFormError(
            response, "form", assessments[1].id.hex, "Matched groups must be unique"
        )
        self.assertFalse(assessments[2].id.hex in errors.keys())
        self.assertFalse(assessments[3].id.hex in errors.keys())

    """ BEGIN TESTS FOR INSTRUCTOR ASSESSMENT VIEW (instructor:instructor_form -> /form/) """

    # Begin code copied: https://stackoverflow.com/a/62744916 This code just makes it easier to set up the formset data
    def build_formset_form_data(self, form_number, **data):
        form = {}
        for key, value in data.items():
            form_key = f"assessment-{form_number}-{key}"
            form[form_key] = value
        return form

    def build_formset_data(self, forms, **common_data):
        formset_dict = {
            "assessment-TOTAL_FORMS": f"{len(forms)}",
            "assessment-MAX_NUM_FORMS": "1000",
            "assessment-INITIAL_FORMS": "1",
        }
        formset_dict.update(common_data)
        for i, form_data in enumerate(forms):
            form_dict = self.build_formset_form_data(form_number=i, **form_data)
            formset_dict.update(form_dict)
        return formset_dict

    # End copied code

    @mock_classes.use_mock_canvas()
    def test_InstructorAssessmentView_valid_form(self, mocked_flex_canvas_instance):
        course_id = 1

        # id matches uuids in fixtures/assessments.json
        forms = [
            {
                "title": "TITLE 1",
                "default": 0,
                "min": 0,
                "max": 50,
                "id": "123e4567-e89b-12d3-a456-426655440001",
            },
            {
                "title": "TITLE 2",
                "default": 50,
                "min": 50,
                "max": 50,
                "id": "123e4567-e89b-12d3-a456-426655440002",
            },
            {
                "title": "TITLE 3",
                "default": 1,
                "min": 0,
                "max": 50,
                "id": "123e4567-e89b-12d3-a456-426655440003",
            },
            {
                "title": "TITLE 4",
                "default": 49,
                "min": 0,
                "max": 50,
                "id": "123e4567-e89b-12d3-a456-426655440004",
            },
        ]

        payload = self.build_formset_data(forms=forms, global_param=100)

        # add date- infront of open/close because DateForm has prefix='date' inside post
        payload["date-open"] = "2023-01-01T01:00"
        payload["date-close"] = "3000-01-01T00:59"

        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)
        response = self.client.post(
            reverse("instructor:instructor_form", args=[course_id]), data=payload
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(type(response), HttpResponseRedirect)
        self.assertEqual(
            response.url, reverse("instructor:instructor_home", args=[course_id])
        )

    @mock_classes.use_mock_canvas()
    def test_InstructorAssessmentView_invalid_does_not_add_to_100(
        self, mocked_flex_canvas_instance
    ):
        course_id = 1

        # id matches uuids in fixtures/assessments.json
        forms = [
            {
                "title": "TITLE 1",
                "default": 24,
                "min": 10,
                "max": 30,
                "id": "123e4567-e89b-12d3-a456-426655440001",
            },
            {
                "title": "TITLE 2",
                "default": 25,
                "min": 10,
                "max": 30,
                "id": "123e4567-e89b-12d3-a456-426655440002",
            },
            {
                "title": "TITLE 3",
                "default": 25,
                "min": 10,
                "max": 30,
                "id": "123e4567-e89b-12d3-a456-426655440003",
            },
            {
                "title": "TITLE 4",
                "default": 25,
                "min": 10,
                "max": 30,
                "id": "123e4567-e89b-12d3-a456-426655440004",
            },
        ]

        payload = self.build_formset_data(forms=forms, global_param=100)

        # add date- infront of open/close because DateForm has prefix='date' inside post
        payload["date-open"] = "2023-01-01T01:00"
        payload["date-close"] = "3000-01-01T00:59"

        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)
        response = self.client.post(
            reverse("instructor:instructor_form", args=[course_id]), data=payload
        )

        self.assertEqual(type(response), TemplateResponse)
        self.assertContains(response, "Default assessments should add up to 100%")

    @mock_classes.use_mock_canvas()
    def test_InstructorAssessmentView_invalid_out_of_range(
        self, mocked_flex_canvas_instance
    ):
        course_id = 1

        # id matches uuids in fixtures/assessments.json
        forms = [
            {
                "title": "TITLE 1",
                "default": 31,
                "min": 0,
                "max": 30,
                "id": "123e4567-e89b-12d3-a456-426655440001",
            },
            {
                "title": "TITLE 2",
                "default": 25,
                "min": 10,
                "max": 30,
                "id": "123e4567-e89b-12d3-a456-426655440002",
            },
            {
                "title": "TITLE 3",
                "default": 25,
                "min": 10,
                "max": 30,
                "id": "123e4567-e89b-12d3-a456-426655440003",
            },
            {
                "title": "TITLE 4",
                "default": 19,
                "min": 20,
                "max": 30,
                "id": "123e4567-e89b-12d3-a456-426655440004",
            },
        ]

        payload = self.build_formset_data(forms=forms, global_param=100)

        # add date- infront of open/close because DateForm has prefix='date' inside post
        payload["date-open"] = "2023-01-01T01:00"
        payload["date-close"] = "3000-01-01T00:59"

        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)
        response = self.client.post(
            reverse("instructor:instructor_form", args=[course_id]), data=payload
        )

        self.assertEqual(type(response), TemplateResponse)
        self.assertContains(response, "Minimum must be lower than default")
        self.assertContains(response, "Maximum must be higher than default")

    @mock_classes.use_mock_canvas()
    def test_InstructorAssessmentView_invalid_min_max_ranges(
        self, mocked_flex_canvas_instance
    ):
        course_id = 1

        # id matches uuids in fixtures/assessments.json
        forms = [
            {
                "title": "TITLE 1",
                "default": -21,
                "min": -35,
                "max": -1,
                "id": "123e4567-e89b-12d3-a456-426655440001",
            },
            {
                "title": "TITLE 2",
                "default": 101,
                "min": 101,
                "max": 102,
                "id": "123e4567-e89b-12d3-a456-426655440002",
            },
            {
                "title": "TITLE 3",
                "default": 0,
                "min": 0,
                "max": 30,
                "id": "123e4567-e89b-12d3-a456-426655440003",
            },
            {
                "title": "TITLE 4",
                "default": 20,
                "min": 20,
                "max": 50,
                "id": "123e4567-e89b-12d3-a456-426655440004",
            },
        ]

        payload = self.build_formset_data(forms=forms, global_param=100)

        # add date- infront of open/close because DateForm has prefix='date' inside post
        payload["date-open"] = "2023-01-01T01:00"
        payload["date-close"] = "3000-01-01T00:59"

        # Get instructor_home first to set up display_name session data
        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)
        response = self.client.post(
            reverse("instructor:instructor_form", args=[course_id]), data=payload
        )

        self.assertEqual(type(response), TemplateResponse)
        self.assertContains(response, "must be within 0.0 and 100.0", count=6)

    @mock_classes.use_mock_canvas()
    def test_FinalGradeListView_correct_csv(self, mocked_flex_canvas_instance):
        course_id = 1

        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)
        response = self.client.get(
            reverse("instructor:final_grades_export", args=[course_id])
        )

        self.assertContains(response, "Override Total", count=1)
        self.assertContains(response, "Default Total", count=1)
        self.assertContains(response, "Difference", count=2)
        self.assertContains(response, "Average Override", count=1)
        self.assertContains(response, "Average Default", count=1)
        self.assertContains(response, "Average Difference", count=1)

    @mock_classes.use_mock_canvas()
    def test_InstructorAssessmentView_correct_csv(self, mocked_flex_canvas_instance):
        course_id = 1

        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)
        response = self.client.get(
            reverse("instructor:assessments_export", args=[course_id])
        )

        self.assertContains(response, "Assessment", count=1)
        self.assertContains(response, "Default", count=1)
        self.assertContains(response, "Minimum", count=1)
        self.assertContains(response, "Maximum", count=1)

    @mock_classes.use_mock_canvas()
    def test_FlexAssessmentListView_correct_csv(self, mocked_flex_canvas_instance):
        course_id = 1

        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)
        response = self.client.get(
            reverse("instructor:percentage_list_export", args=[course_id])
        )

        self.assertContains(response, "Student", count=1)
        self.assertContains(response, "Comment", count=1)

    @mock_classes.use_mock_canvas()
    def test_csv_exports_chained(self, mocked_flex_canvas_instance):
        course_id = 1

        instructor_home_url = reverse("instructor:instructor_home", args=[course_id])
        response = self.client.get(instructor_home_url)
        response = self.client.get(
            reverse("instructor:final_grades_export", args=[course_id])
        )

        self.assertContains(response, "Override Total", count=1)
        self.assertContains(response, "Default Total", count=1)
        self.assertContains(response, "Difference", count=2)
        self.assertContains(response, "Average Override", count=1)
        self.assertContains(response, "Average Default", count=1)
        self.assertContains(response, "Average Difference", count=1)

        response = self.client.get(
            reverse("instructor:assessments_export", args=[course_id])
        )

        self.assertContains(response, "Assessment", count=1)
        self.assertContains(response, "Default", count=1)
        self.assertContains(response, "Minimum", count=1)
        self.assertContains(response, "Maximum", count=1)

        response = self.client.get(
            reverse("instructor:percentage_list_export", args=[course_id])
        )

        self.assertContains(response, "Student", count=1)
        self.assertContains(response, "Comment", count=1)
