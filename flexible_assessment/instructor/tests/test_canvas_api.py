from django.test import TestCase
from unittest.mock import patch, MagicMock
from instructor.canvas_api import FlexCanvas
from django.core.exceptions import PermissionDenied


class TestFlexCanvas(TestCase):

    @patch("instructor.canvas_api.FlexCanvas.graphql")  # Mock the GraphQL call
    @patch("instructor.canvas_api.get_oauth_token")  # Mock OAuth token retrieval
    def test_get_flat_groups_and_enrollments(self, mock_get_oauth_token, mock_graphql):
        # Mock request
        mock_request = MagicMock()
        mock_request.session = {}  # If get_oauth_token accesses session
        mock_request.user = MagicMock()  # If user-related data is needed

        # Mock OAuth token retrieval
        mock_get_oauth_token.return_value = "mock_token"

        # Mock the API response
        mock_graphql.return_value = {
            "data": {
                "course": {
                    "assignment_groups": {
                        "groups": [
                            {
                                "rules": {
                                    "dropHighest": None,
                                    "dropLowest": None,
                                    "neverDrop": None,
                                },
                                "group_id": "537054",
                                "group_name": "Quizzes",
                                "group_weight": 10,
                                "assignment_list": {
                                    "assignments": [
                                        {
                                            "_id": "2088526",
                                            "max_score": 5,
                                            "name": "Q1",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {
                                                "submissions": [
                                                    {"score": 4, "user_id": "357363"},
                                                    {"score": 3, "user_id": "357381"},
                                                    {"score": 2, "user_id": "357399"},
                                                    {"score": 4, "user_id": "357480"},
                                                    {"score": 1, "user_id": "357495"},
                                                ]
                                            },
                                        },
                                        {
                                            "_id": "2088527",
                                            "max_score": 10,
                                            "name": "Q2",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {
                                                "submissions": [
                                                    {"score": 9, "user_id": "357363"},
                                                    {"score": 6, "user_id": "357381"},
                                                    {"score": 7, "user_id": "357399"},
                                                    {"score": 7, "user_id": "357480"},
                                                    {"score": 8, "user_id": "357495"},
                                                ]
                                            },
                                        },
                                        {
                                            "_id": "2088528",
                                            "max_score": 30,
                                            "name": "Q3",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {
                                                "submissions": [
                                                    {"score": 18, "user_id": "357363"},
                                                    {"score": 23, "user_id": "357381"},
                                                    {"score": 26, "user_id": "357399"},
                                                    {"score": 13, "user_id": "357480"},
                                                    {"score": 27, "user_id": "357495"},
                                                ]
                                            },
                                        },
                                        {
                                            "_id": "2088552",
                                            "max_score": 30,
                                            "name": "Q4 - unpublished, graded",
                                            "published": False,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {"submissions": []},
                                        },
                                    ]
                                },
                                "grade_list": {
                                    "grades": [
                                        {
                                            "current_score": 68.89,
                                            "enrollment": {
                                                "_id": "9432892",
                                                "user": {
                                                    "user_id": "357363",
                                                    "display_name": "Jane Doe",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 77.78,
                                            "enrollment": {
                                                "_id": "9432891",
                                                "user": {
                                                    "user_id": "357399",
                                                    "display_name": "John Smith",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 53.33,
                                            "enrollment": {
                                                "_id": "9432893",
                                                "user": {
                                                    "user_id": "357480",
                                                    "display_name": "Demi Demo",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 71.11,
                                            "enrollment": {
                                                "_id": "9432894",
                                                "user": {
                                                    "user_id": "357381",
                                                    "display_name": "Demitri Demokovsky",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 80,
                                            "enrollment": {
                                                "_id": "9432895",
                                                "user": {
                                                    "user_id": "357495",
                                                    "display_name": "Zoe Zemo",
                                                },
                                            },
                                        },
                                    ]
                                },
                            },
                            {
                                "rules": {
                                    "dropHighest": None,
                                    "dropLowest": None,
                                    "neverDrop": None,
                                },
                                "group_id": "537053",
                                "group_name": "Assignments",
                                "group_weight": 25,
                                "assignment_list": {
                                    "assignments": [
                                        {
                                            "_id": "2088529",
                                            "max_score": 10,
                                            "name": "A1",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {
                                                "submissions": [
                                                    {"score": 8, "user_id": "357363"},
                                                    {"score": 6, "user_id": "357381"},
                                                    {"score": 5, "user_id": "357399"},
                                                    {"score": 7, "user_id": "357480"},
                                                    {"score": 6, "user_id": "357495"},
                                                ]
                                            },
                                        },
                                        {
                                            "_id": "2088530",
                                            "max_score": 20,
                                            "name": "A2",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {
                                                "submissions": [
                                                    {"score": 16, "user_id": "357363"},
                                                    {"score": 12, "user_id": "357381"},
                                                    {"score": 15, "user_id": "357399"},
                                                    {"score": 20, "user_id": "357480"},
                                                    {"score": 17, "user_id": "357495"},
                                                ]
                                            },
                                        },
                                        {
                                            "_id": "2088553",
                                            "max_score": None,
                                            "name": "A3 - Published, not graded",
                                            "published": True,
                                            "gradingType": "not_graded",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {"submissions": []},
                                        },
                                        {
                                            "_id": "2088554",
                                            "max_score": 5,
                                            "name": "A4 - Published, do not count towards final grade",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": True,
                                            "submission_list": {"submissions": []},
                                        },
                                    ]
                                },
                                "grade_list": {
                                    "grades": [
                                        {
                                            "current_score": 66.67,
                                            "enrollment": {
                                                "_id": "9432891",
                                                "user": {
                                                    "user_id": "357399",
                                                    "display_name": "John Smith",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 80,
                                            "enrollment": {
                                                "_id": "9432892",
                                                "user": {
                                                    "user_id": "357363",
                                                    "display_name": "Jane Doe",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 90,
                                            "enrollment": {
                                                "_id": "9432893",
                                                "user": {
                                                    "user_id": "357480",
                                                    "display_name": "Demi Demo",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 60,
                                            "enrollment": {
                                                "_id": "9432894",
                                                "user": {
                                                    "user_id": "357381",
                                                    "display_name": "Demitri Demokovsky",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 76.67,
                                            "enrollment": {
                                                "_id": "9432895",
                                                "user": {
                                                    "user_id": "357495",
                                                    "display_name": "Zoe Zemo",
                                                },
                                            },
                                        },
                                    ]
                                },
                            },
                            {
                                "rules": {
                                    "dropHighest": None,
                                    "dropLowest": None,
                                    "neverDrop": None,
                                },
                                "group_id": "537055",
                                "group_name": "Midterms",
                                "group_weight": 25,
                                "assignment_list": {
                                    "assignments": [
                                        {
                                            "_id": "2088531",
                                            "max_score": 25,
                                            "name": "MT1",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {
                                                "submissions": [
                                                    {"score": 21, "user_id": "357363"},
                                                    {"score": 14, "user_id": "357381"},
                                                    {"score": 23, "user_id": "357399"},
                                                    {"score": 17, "user_id": "357480"},
                                                    {"score": 16, "user_id": "357495"},
                                                ]
                                            },
                                        },
                                        {
                                            "_id": "2088532",
                                            "max_score": 25,
                                            "name": "MT2",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {
                                                "submissions": [
                                                    {"score": 8, "user_id": "357363"},
                                                    {"score": 24, "user_id": "357381"},
                                                    {"score": 15, "user_id": "357399"},
                                                    {"score": 21, "user_id": "357480"},
                                                    {"score": 17, "user_id": "357495"},
                                                ]
                                            },
                                        },
                                    ]
                                },
                                "grade_list": {
                                    "grades": [
                                        {
                                            "current_score": 58,
                                            "enrollment": {
                                                "_id": "9432892",
                                                "user": {
                                                    "user_id": "357363",
                                                    "display_name": "Jane Doe",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 76,
                                            "enrollment": {
                                                "_id": "9432893",
                                                "user": {
                                                    "user_id": "357480",
                                                    "display_name": "Demi Demo",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 76,
                                            "enrollment": {
                                                "_id": "9432894",
                                                "user": {
                                                    "user_id": "357381",
                                                    "display_name": "Demitri Demokovsky",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 66,
                                            "enrollment": {
                                                "_id": "9432895",
                                                "user": {
                                                    "user_id": "357495",
                                                    "display_name": "Zoe Zemo",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 76,
                                            "enrollment": {
                                                "_id": "9432891",
                                                "user": {
                                                    "user_id": "357399",
                                                    "display_name": "John Smith",
                                                },
                                            },
                                        },
                                    ]
                                },
                            },
                            {
                                "rules": {
                                    "dropHighest": None,
                                    "dropLowest": None,
                                    "neverDrop": None,
                                },
                                "group_id": "537056",
                                "group_name": "Final",
                                "group_weight": 40,
                                "assignment_list": {
                                    "assignments": [
                                        {
                                            "_id": "2088533",
                                            "max_score": 50,
                                            "name": "Final",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {
                                                "submissions": [
                                                    {"score": 41, "user_id": "357363"},
                                                    {"score": 29, "user_id": "357381"},
                                                    {"score": 17, "user_id": "357399"},
                                                    {"score": 37, "user_id": "357480"},
                                                    {"score": 46, "user_id": "357495"},
                                                ]
                                            },
                                        }
                                    ]
                                },
                                "grade_list": {
                                    "grades": [
                                        {
                                            "current_score": 34,
                                            "enrollment": {
                                                "_id": "9432891",
                                                "user": {
                                                    "user_id": "357399",
                                                    "display_name": "John Smith",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 82,
                                            "enrollment": {
                                                "_id": "9432892",
                                                "user": {
                                                    "user_id": "357363",
                                                    "display_name": "Jane Doe",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 74,
                                            "enrollment": {
                                                "_id": "9432893",
                                                "user": {
                                                    "user_id": "357480",
                                                    "display_name": "Demi Demo",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 58,
                                            "enrollment": {
                                                "_id": "9432894",
                                                "user": {
                                                    "user_id": "357381",
                                                    "display_name": "Demitri Demokovsky",
                                                },
                                            },
                                        },
                                        {
                                            "current_score": 92,
                                            "enrollment": {
                                                "_id": "9432895",
                                                "user": {
                                                    "user_id": "357495",
                                                    "display_name": "Zoe Zemo",
                                                },
                                            },
                                        },
                                    ]
                                },
                            },
                        ]
                    }
                }
            }
        }

        # Initialize FlexCanvas
        flex_canvas = FlexCanvas(mock_request)

        # Call function
        group_dict, user_enrollment_dict = flex_canvas.get_flat_groups_and_enrollments(
            123
        )

        # Assertions

        # check user_enrollment_dict is correct
        self.assertEqual(user_enrollment_dict["357363"], "9432892")
        self.assertEqual(user_enrollment_dict["357381"], "9432894")
        self.assertEqual(user_enrollment_dict["357399"], "9432891")
        self.assertEqual(user_enrollment_dict["357480"], "9432893")
        self.assertEqual(user_enrollment_dict["357495"], "9432895")
        self.assertEqual(len(user_enrollment_dict), 5)

        # check group_dict is correct
        self.assertIn("537053", group_dict)
        self.assertIn("537054", group_dict)
        self.assertIn("537055", group_dict)
        self.assertIn("537056", group_dict)
        self.assertEqual(len(group_dict), 4)

        # check calculated grades are correct
        # John Smith's grade for assignments, which have published but ungraded assignments
        self.assertEqual(
            round(group_dict["537053"]["grade_list"]["grades"][0][1], 2), 62.5
        )
        # John Smith's grade for quizzes,  with an unpublished assignment
        self.assertEqual(
            round(group_dict["537054"]["grade_list"]["grades"][1][1], 2), 65.56
        )
        # John Smith's grade for midterms, which have only published, graded assignments
        self.assertEqual(
            round(group_dict["537055"]["grade_list"]["grades"][4][1], 2), 76
        )

        import pprint

        pprint.pprint(user_enrollment_dict)
        pprint.pprint(group_dict)

    @patch("instructor.canvas_api.FlexCanvas.graphql")  # Mock the GraphQL call
    @patch("instructor.canvas_api.get_oauth_token")  # Mock OAuth token retrieval
    def test_get_groups_and_enrollments(self, mock_get_oauth_token, mock_graphql):
        # Mock request
        mock_request = MagicMock()
        mock_request.session = {}  # If get_oauth_token accesses session
        mock_request.user = MagicMock()  # If user-related data is needed

        # Mock OAuth token retrieval
        mock_get_oauth_token.return_value = "mock_token"

        # Mock the API response
        mock_graphql.return_value = {
            "data": {
                "course": {
                    "assignment_groups": {
                        "groups": [
                            {
                                "group_id": "537054",
                                "group_name": "Quizzes",
                                "group_weight": 10,
                                "grade_list": {
                                    "grades": [
                                        {
                                            "current_score": 68.89,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357363",
                                                    "display_name": "Jane Doe",
                                                },
                                                "_id": "9432892",
                                            },
                                        },
                                        {
                                            "current_score": 77.78,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357399",
                                                    "display_name": "John Smith",
                                                },
                                                "_id": "9432891",
                                            },
                                        },
                                        {
                                            "current_score": 53.33,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357480",
                                                    "display_name": "Demi Demo",
                                                },
                                                "_id": "9432893",
                                            },
                                        },
                                        {
                                            "current_score": 71.11,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357381",
                                                    "display_name": "Demitri Demokovsky",
                                                },
                                                "_id": "9432894",
                                            },
                                        },
                                        {
                                            "current_score": 80,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357495",
                                                    "display_name": "Zoe Zemo",
                                                },
                                                "_id": "9432895",
                                            },
                                        },
                                    ]
                                },
                            },
                            {
                                "group_id": "537053",
                                "group_name": "Assignments",
                                "group_weight": 25,
                                "grade_list": {
                                    "grades": [
                                        {
                                            "current_score": 66.67,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357399",
                                                    "display_name": "John Smith",
                                                },
                                                "_id": "9432891",
                                            },
                                        },
                                        {
                                            "current_score": 80,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357363",
                                                    "display_name": "Jane Doe",
                                                },
                                                "_id": "9432892",
                                            },
                                        },
                                        {
                                            "current_score": 90,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357480",
                                                    "display_name": "Demi Demo",
                                                },
                                                "_id": "9432893",
                                            },
                                        },
                                        {
                                            "current_score": 60,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357381",
                                                    "display_name": "Demitri Demokovsky",
                                                },
                                                "_id": "9432894",
                                            },
                                        },
                                        {
                                            "current_score": 76.67,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357495",
                                                    "display_name": "Zoe Zemo",
                                                },
                                                "_id": "9432895",
                                            },
                                        },
                                    ]
                                },
                            },
                            {
                                "group_id": "537055",
                                "group_name": "Midterms",
                                "group_weight": 25,
                                "grade_list": {
                                    "grades": [
                                        {
                                            "current_score": 58,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357363",
                                                    "display_name": "Jane Doe",
                                                },
                                                "_id": "9432892",
                                            },
                                        },
                                        {
                                            "current_score": 76,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357480",
                                                    "display_name": "Demi Demo",
                                                },
                                                "_id": "9432893",
                                            },
                                        },
                                        {
                                            "current_score": 76,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357381",
                                                    "display_name": "Demitri Demokovsky",
                                                },
                                                "_id": "9432894",
                                            },
                                        },
                                        {
                                            "current_score": 66,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357495",
                                                    "display_name": "Zoe Zemo",
                                                },
                                                "_id": "9432895",
                                            },
                                        },
                                        {
                                            "current_score": 76,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357399",
                                                    "display_name": "John Smith",
                                                },
                                                "_id": "9432891",
                                            },
                                        },
                                    ]
                                },
                            },
                            {
                                "group_id": "537056",
                                "group_name": "Final",
                                "group_weight": 40,
                                "grade_list": {
                                    "grades": [
                                        {
                                            "current_score": 34,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357399",
                                                    "display_name": "John Smith",
                                                },
                                                "_id": "9432891",
                                            },
                                        },
                                        {
                                            "current_score": 82,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357363",
                                                    "display_name": "Jane Doe",
                                                },
                                                "_id": "9432892",
                                            },
                                        },
                                        {
                                            "current_score": 74,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357480",
                                                    "display_name": "Demi Demo",
                                                },
                                                "_id": "9432893",
                                            },
                                        },
                                        {
                                            "current_score": 58,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357381",
                                                    "display_name": "Demitri Demokovsky",
                                                },
                                                "_id": "9432894",
                                            },
                                        },
                                        {
                                            "current_score": 92,
                                            "enrollment": {
                                                "user": {
                                                    "user_id": "357495",
                                                    "display_name": "Zoe Zemo",
                                                },
                                                "_id": "9432895",
                                            },
                                        },
                                    ]
                                },
                            },
                        ]
                    }
                }
            }
        }

        # Initialize FlexCanvas
        flex_canvas = FlexCanvas(mock_request)

        # Call function
        group_dict, user_enrollment_dict = flex_canvas.get_groups_and_enrollments(123)

        # Assertions

        # check user_enrollment_dict is correct
        self.assertEqual(user_enrollment_dict["357363"], "9432892")
        self.assertEqual(user_enrollment_dict["357381"], "9432894")
        self.assertEqual(user_enrollment_dict["357399"], "9432891")
        self.assertEqual(user_enrollment_dict["357480"], "9432893")
        self.assertEqual(user_enrollment_dict["357495"], "9432895")
        self.assertEqual(len(user_enrollment_dict), 5)

        # check group_dict is correct
        self.assertIn("537053", group_dict)
        self.assertIn("537054", group_dict)
        self.assertIn("537055", group_dict)
        self.assertIn("537056", group_dict)
        self.assertEqual(len(group_dict), 4)

        # check calculated grades are correct
        # John Smith's grade for assignments
        self.assertEqual(
            round(group_dict["537053"]["grade_list"]["grades"][0][1], 2), 66.67
        )
        # John Smith's grade for quizzes
        self.assertEqual(
            round(group_dict["537054"]["grade_list"]["grades"][1][1], 2), 77.78
        )

        # John Smith's grade for midterms
        self.assertEqual(
            round(group_dict["537055"]["grade_list"]["grades"][4][1], 2), 76
        )

    @patch("instructor.canvas_api.FlexCanvas.graphql")  # Mock the GraphQL call
    @patch("instructor.canvas_api.get_oauth_token")  # Mock OAuth token retrieval
    def test_get_flat_groups_and_enrollments_no_groups(
        self, mock_get_oauth_token, mock_graphql
    ):
        # Mock request
        mock_request = MagicMock()
        mock_request.session = {}  # If get_oauth_token accesses session
        mock_request.user = MagicMock()  # If user-related data is needed

        # Mock OAuth token retrieval
        mock_get_oauth_token.return_value = "mock_token"

        # Mock the API response with no assignment groups
        mock_graphql.return_value = {
            "data": {"course": {"assignment_groups": {"groups": None}}}
        }

        # Initialize FlexCanvas
        flex_canvas = FlexCanvas(mock_request)

        # test when value is None
        with self.assertRaises(PermissionDenied):
            group_dict, user_enrollment_dict = (
                flex_canvas.get_flat_groups_and_enrollments(123)
            )

        # test when value is empty list
        mock_graphql.return_value = {
            "data": {"course": {"assignment_groups": {"groups": []}}}
        }

        group_dict, user_enrollment_dict = flex_canvas.get_flat_groups_and_enrollments(
            123
        )

        # Assertions
        self.assertEqual(len(group_dict), 0)
        self.assertEqual(len(user_enrollment_dict), 0)

    @patch("instructor.canvas_api.FlexCanvas.graphql")  # Mock the GraphQL call
    @patch("instructor.canvas_api.get_oauth_token")  # Mock OAuth token retrieval
    def test_get_flat_groups_and_enrollments_invalid_assignments(
        self, mock_get_oauth_token, mock_graphql
    ):
        # Mock request
        mock_request = MagicMock()
        mock_request.session = {}  # If get_oauth_token accesses session
        mock_request.user = MagicMock()  # If user-related data is needed

        # Mock OAuth token retrieval
        mock_get_oauth_token.return_value = "mock_token"

        # Mock the API response with invalid assignments
        mock_graphql.return_value = {
            "data": {
                "course": {
                    "assignment_groups": {
                        "groups": [
                            {
                                "rules": {
                                    "dropHighest": None,
                                    "dropLowest": None,
                                    "neverDrop": None,
                                },
                                "group_id": "537054",
                                "group_name": "Quizzes",
                                "group_weight": 10,
                                "assignment_list": {
                                    "assignments": [
                                        {
                                            "_id": "2088526",
                                            "max_score": None,  # Invalid max_score
                                            "name": "Q1",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {"submissions": []},
                                        }
                                    ]
                                },
                                "grade_list": {"grades": []},
                            }
                        ]
                    }
                }
            }
        }

        # Initialize FlexCanvas
        flex_canvas = FlexCanvas(mock_request)

        # Call function
        group_dict, user_enrollment_dict = flex_canvas.get_flat_groups_and_enrollments(
            123
        )

        # Assertions
        self.assertEqual(len(group_dict), 1)
        self.assertEqual(len(user_enrollment_dict), 0)
        self.assertEqual(group_dict["537054"]["grade_list"]["grades"], [])

    @patch("instructor.canvas_api.FlexCanvas.graphql")  # Mock the GraphQL call
    @patch("instructor.canvas_api.get_oauth_token")  # Mock OAuth token retrieval
    def test_get_flat_groups_and_enrollments_no_grades(
        self, mock_get_oauth_token, mock_graphql
    ):
        # Mock request
        mock_request = MagicMock()
        mock_request.session = {}  # If get_oauth_token accesses session
        mock_request.user = MagicMock()  # If user-related data is needed

        # Mock OAuth token retrieval
        mock_get_oauth_token.return_value = "mock_token"

        # Mock the API response with invalid assignments
        mock_graphql.return_value = {
            "data": {
                "course": {
                    "assignment_groups": {
                        "groups": [
                            {
                                "rules": {
                                    "dropHighest": None,
                                    "dropLowest": None,
                                    "neverDrop": None,
                                },
                                "group_id": "537054",
                                "group_name": "Quizzes",
                                "group_weight": 10,
                                "assignment_list": {
                                    "assignments": [
                                        {
                                            "_id": "2088526",
                                            "max_score": None,  # Invalid max_score
                                            "name": "Q1",
                                            "published": True,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": False,
                                            "submission_list": {"submissions": []},
                                        }
                                    ]
                                },
                                "grade_list": {"grades": None},
                            }
                        ]
                    }
                }
            }
        }

        # Initialize FlexCanvas
        flex_canvas = FlexCanvas(mock_request)

        # Assertions
        with self.assertRaises(PermissionDenied):
            group_dict, user_enrollment_dict = (
                flex_canvas.get_flat_groups_and_enrollments(123)
            )
