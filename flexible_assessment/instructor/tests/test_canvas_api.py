from django.test import TestCase
from unittest.mock import patch, MagicMock
from instructor.canvas_api import FlexCanvas


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
                                            "_id": "2088551",
                                            "max_score": 30,
                                            "name": "Q3 Copy",
                                            "published": False,
                                            "gradingType": "points",
                                            "omitFromFinalGrade": True,
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
        self.assertIn("537054", group_dict)
        self.assertEqual(user_enrollment_dict["357363"], "9432892")
        self.assertEqual(group_dict["537053"]["grade_list"]["grades"][0][1], 62.5)
        import pprint

        pprint.pprint(user_enrollment_dict)
        pprint.pprint(group_dict)
