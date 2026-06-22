from django.test import TestCase, tag
from unittest.mock import patch, MagicMock
from accommodations.canvas_api import AccommodationsCanvas
from flexible_assessment.models import Roles, UserProfile
from flexible_assessment.tests.test_data import ACCOMMODATIONS_DATA


class TestAccommodationsCanvas(TestCase):

    fixtures = ACCOMMODATIONS_DATA

    @tag("accommodations", "canvas_api", "overwrite_by_student")
    @patch("accommodations.canvas_api.get_oauth_token")  # Mock OAuth token retrieval
    def test_get_overwrite_by_student(self, mock_get_oauth_token):
        # Mock request
        mock_request = MagicMock()
        mock_request.session = {}  # If get_oauth_token accesses session
        mock_request.user = MagicMock()  # If user-related data is needed

        # Mock OAuth token retrieval
        mock_get_oauth_token.return_value = "mock_token"

        accommodationsCanvas = AccommodationsCanvas(mock_request)
        students = UserProfile.objects.filter(
            usercourse__role=Roles.STUDENT, usercourse__course__id=1
        )
        overwrite_student_groups = [
            {
                "key": "essay",
                "students": [
                    {
                        "id": "10000001",
                        "name": "Jason Zheng",
                        "def_multiplier": "1.5",
                        "new_multiplier": "1.75",
                    }
                ],
                "description": "essay format",
            },
            {
                "key": "mult_choice",
                "students": [
                    {
                        "id": "10000001",
                        "name": "Jason Zheng",
                        "def_multiplier": "1.5",
                        "new_multiplier": "2.0",
                    },
                    {
                        "id": "10000002",
                        "name": "Albert Einstein",
                        "def_multiplier": "2.0",
                        "new_multiplier": "3.0",
                    },
                ],
                "description": "multiple choice format",
            },
            {
                "key": "short_ans",
                "students": [
                    {
                        "id": "10000002",
                        "name": "Albert Einstein",
                        "def_multiplier": "2.0",
                        "new_multiplier": "2.25",
                    }
                ],
                "description": "short answer format",
            },
            {
                "key": "fine_manip",
                "students": [],
                "description": "exams involving fine maniplations",
            },
            {"key": "notes", "students": [], "description": "CFA Notes"},
        ]

        multiplier_quiz_groups = {
            "4.0": [
                {
                    "id": 101,
                    "title": "Mock Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "2026-06-01 - 12:00PM",
                    "lock_at_readable": "2026-06-01 - 1:00PM",
                    "time_limit_readable": "No time limit set",
                    "lock_at_new_readable": "2026-06-01 - 1:30PM",
                },
                {
                    "id": 102,
                    "title": "Mock Quiz 2",
                    "is_new_quiz": True,
                    "url": "https://example.com/quiz/102",
                    "unlock_at_readable": "2026-07-05 - 9:00AM",
                    "lock_at_readable": "2026-08-10 - 11:59PM",
                    "time_limit_readable": "2h",
                    "time_limit_new_readable": "3h",
                },
            ],
            "3.5": [
                {
                    "id": 101,
                    "title": "Mock Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "2026-06-01 - 12:00PM",
                    "lock_at_readable": "2026-06-01 - 1:00PM",
                    "time_limit_readable": "No time limit set",
                    "lock_at_new_readable": "2026-06-01 - 1:30PM",
                },
                {
                    "id": 102,
                    "title": "Mock Quiz 2",
                    "is_new_quiz": True,
                    "url": "https://example.com/quiz/102",
                    "unlock_at_readable": "2026-07-05 - 9:00AM",
                    "lock_at_readable": "2026-08-10 - 11:59PM",
                    "time_limit_readable": "2h",
                    "time_limit_new_readable": "3h",
                },
            ],
            "3.0": [
                {
                    "id": 101,
                    "title": "Mock Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "2026-06-01 - 12:00PM",
                    "lock_at_readable": "2026-06-01 - 1:00PM",
                    "time_limit_readable": "No time limit set",
                    "lock_at_new_readable": "2026-06-01 - 1:30PM",
                },
                {
                    "id": 102,
                    "title": "Mock Quiz 2",
                    "is_new_quiz": True,
                    "url": "https://example.com/quiz/102",
                    "unlock_at_readable": "2026-07-05 - 9:00AM",
                    "lock_at_readable": "2026-08-10 - 11:59PM",
                    "time_limit_readable": "2h",
                    "time_limit_new_readable": "3h",
                },
            ],
            "2.5": [
                {
                    "id": 101,
                    "title": "Mock Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "2026-06-01 - 12:00PM",
                    "lock_at_readable": "2026-06-01 - 1:00PM",
                    "time_limit_readable": "No time limit set",
                    "lock_at_new_readable": "2026-06-01 - 1:30PM",
                },
                {
                    "id": 102,
                    "title": "Mock Quiz 2",
                    "is_new_quiz": True,
                    "url": "https://example.com/quiz/102",
                    "unlock_at_readable": "2026-07-05 - 9:00AM",
                    "lock_at_readable": "2026-08-10 - 11:59PM",
                    "time_limit_readable": "2h",
                    "time_limit_new_readable": "3h",
                },
            ],
            "2.0": [
                {
                    "id": 101,
                    "title": "Mock Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "2026-06-01 - 12:00PM",
                    "lock_at_readable": "2026-06-01 - 1:00PM",
                    "time_limit_readable": "No time limit set",
                    "lock_at_new_readable": "2026-06-01 - 1:30PM",
                },
                {
                    "id": 102,
                    "title": "Mock Quiz 2",
                    "is_new_quiz": True,
                    "url": "https://example.com/quiz/102",
                    "unlock_at_readable": "2026-07-05 - 9:00AM",
                    "lock_at_readable": "2026-08-10 - 11:59PM",
                    "time_limit_readable": "2h",
                    "time_limit_new_readable": "3h",
                },
            ],
            "1.75": [
                {
                    "id": 101,
                    "title": "Mock Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "2026-06-01 - 12:00PM",
                    "lock_at_readable": "2026-06-01 - 1:00PM",
                    "time_limit_readable": "No time limit set",
                    "lock_at_new_readable": "2026-06-01 - 1:30PM",
                },
                {
                    "id": 102,
                    "title": "Mock Quiz 2",
                    "is_new_quiz": True,
                    "url": "https://example.com/quiz/102",
                    "unlock_at_readable": "2026-07-05 - 9:00AM",
                    "lock_at_readable": "2026-08-10 - 11:59PM",
                    "time_limit_readable": "2h",
                    "time_limit_new_readable": "3h",
                },
            ],
            "1.5": [
                {
                    "id": 101,
                    "title": "Mock Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "2026-06-01 - 12:00PM",
                    "lock_at_readable": "2026-06-01 - 1:00PM",
                    "time_limit_readable": "No time limit set",
                    "lock_at_new_readable": "2026-06-01 - 1:30PM",
                },
                {
                    "id": 102,
                    "title": "Mock Quiz 2",
                    "is_new_quiz": True,
                    "url": "https://example.com/quiz/102",
                    "unlock_at_readable": "2026-07-05 - 9:00AM",
                    "lock_at_readable": "2026-08-10 - 11:59PM",
                    "time_limit_readable": "2h",
                    "time_limit_new_readable": "3h",
                },
            ],
            "1.25": [
                {
                    "id": 101,
                    "title": "Mock Quiz 1",
                    "is_new_quiz": False,
                    "url": "https://example.com/quiz/101",
                    "unlock_at_readable": "2026-06-01 - 12:00PM",
                    "lock_at_readable": "2026-06-01 - 1:00PM",
                    "time_limit_readable": "No time limit set",
                    "lock_at_new_readable": "2026-06-01 - 1:30PM",
                },
                {
                    "id": 102,
                    "title": "Mock Quiz 2",
                    "is_new_quiz": True,
                    "url": "https://example.com/quiz/102",
                    "unlock_at_readable": "2026-07-05 - 9:00AM",
                    "lock_at_readable": "2026-08-10 - 11:59PM",
                    "time_limit_readable": "2h",
                    "time_limit_new_readable": "3h",
                },
            ],
        }

        override_quizzes = {
            "essay": ["101", "102"],
            "mult_choice": ["101"],
            "short_ans": ["102"],
        }

        overwrite_by_student = accommodationsCanvas.get_overwrite_by_student(
            overwrite_student_groups, override_quizzes, students, multiplier_quiz_groups
        )

        print(students)
        print(overwrite_by_student)

        self.assertEqual(
            overwrite_by_student,
            {
                "10000001": {
                    "name": "Jason Zheng",
                    "quizzes": [
                        {
                            "multiplier": 2.0,
                            "id": 101,
                            "title": "Mock Quiz 1",
                            "is_new_quiz": False,
                            "url": "https://example.com/quiz/101",
                            "unlock_at_readable": "2026-06-01 - 12:00PM",
                            "lock_at_readable": "2026-06-01 - 1:00PM",
                            "time_limit_readable": "No time limit set",
                            "lock_at_new_readable": "2026-06-01 - 1:30PM",
                        },
                        {
                            "multiplier": 1.75,
                            "id": 102,
                            "title": "Mock Quiz 2",
                            "is_new_quiz": True,
                            "url": "https://example.com/quiz/102",
                            "unlock_at_readable": "2026-07-05 - 9:00AM",
                            "lock_at_readable": "2026-08-10 - 11:59PM",
                            "time_limit_readable": "2h",
                            "time_limit_new_readable": "3h",
                        },
                    ],
                },
                "10000002": {
                    "name": "Albert Einstein",
                    "quizzes": [
                        {
                            "multiplier": 3.0,
                            "id": 101,
                            "title": "Mock Quiz 1",
                            "is_new_quiz": False,
                            "url": "https://example.com/quiz/101",
                            "unlock_at_readable": "2026-06-01 - 12:00PM",
                            "lock_at_readable": "2026-06-01 - 1:00PM",
                            "time_limit_readable": "No time limit set",
                            "lock_at_new_readable": "2026-06-01 - 1:30PM",
                        },
                        {"multiplier": 2.25},
                    ],
                },
            },
        )
