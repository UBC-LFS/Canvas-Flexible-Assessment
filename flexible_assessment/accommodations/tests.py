from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.conf import settings
from django.test import TestCase, tag

from accommodations.canvas_api import ACCOMMODATION_MULTIPLIERS, AccommodationsCanvas
from flexible_assessment.models import Roles, UserProfile
from flexible_assessment.tests.test_data import ACCOMMODATIONS_DATA


class TestAccommodationsCanvas(TestCase):
    fixtures = ACCOMMODATIONS_DATA

    def setUp(self):
        self.canvas = AccommodationsCanvas.__new__(AccommodationsCanvas)
        self.canvas.base_url = "https://canvas.example.test/"
        self.canvas.access_token = "mock-token"
        self.students = UserProfile.objects.filter(
            usercourse__role=Roles.STUDENT, usercourse__course__id=1
        )

    @tag("accommodations", "canvas_api", "init")
    @patch("accommodations.canvas_api.Canvas.__init__", return_value=None)
    @patch("accommodations.canvas_api.get_oauth_token", return_value="mock-token")
    def test_init_uses_canvas_domain_and_oauth_token(
        self, mock_get_oauth_token, mock_canvas_init
    ):
        mock_request = MagicMock()

        canvas = AccommodationsCanvas(mock_request)

        mock_get_oauth_token.assert_called_once_with(mock_request)
        mock_canvas_init.assert_called_once_with(settings.CANVAS_DOMAIN, "mock-token")
        self.assertEqual(canvas.base_url, settings.CANVAS_DOMAIN)
        self.assertEqual(canvas.access_token, "mock-token")

    @tag("accommodations", "canvas_api", "student_groups")
    def test_get_multiplier_student_groups_groups_and_sorts_students(self):
        accommodations = [
            ("10000001", "1.5", 1, "Jason Zheng", ""),
            ("10000002", "2.0", 2, "Albert Einstein", ""),
            ("10000003", "1.5", 3, "Marie Curie", "notes"),
        ]

        groups = self.canvas.get_multiplier_student_groups(
            accommodations, self.students
        )

        self.assertEqual(
            groups,
            [
                (
                    "1.5",
                    [
                        ("10000001", "Jason Zheng", 1, ""),
                        ("10000003", "Marie Curie", 3, "notes"),
                    ],
                ),
                ("2.0", [("10000002", "Albert Einstein", 2, "")]),
            ],
        )

    @tag("accommodations", "canvas_api", "quiz_groups")
    def test_get_multiplier_quiz_groups_calculates_time_and_window_extensions(self):
        quizzes = [
            {
                "id": 101,
                "title": "Timed Quiz",
                "time_limit": 60,
                "due_at": "2026-08-01T18:00:00Z",
                "unlock_at": "2026-08-01T17:00:00Z",
                "lock_at": "2026-08-01T18:00:00Z",
                "add_time_after": True,
                "add_buffer": False,
                "is_new_quiz": False,
            }
        ]

        groups = self.canvas.get_multiplier_quiz_groups(quizzes)

        self.assertEqual(
            set(groups.keys()), {str(m) for m in ACCOMMODATION_MULTIPLIERS}
        )
        self.assertEqual(groups["1.5"][0]["time_limit_new"], 90)
        self.assertEqual(groups["1.5"][0]["time_limit_new_readable"], "1h 30m")
        self.assertIsNotNone(groups["1.5"][0]["lock_at_new"])
        self.assertEqual(
            groups["1.5"][0]["due_at_new"], groups["1.5"][0]["lock_at_new"]
        )
        self.assertIsNone(groups["1.5"][0]["unlock_at_new"])

    @tag("accommodations", "canvas_api", "overwrite_student_groups")
    def test_get_overwrite_student_groups_groups_additional_accommodations_by_type(
        self,
    ):
        accommodations = [
            (
                "10000001",
                "1.5",
                1,
                "Jason Zheng",
                "1.75^2.0^^3.0^Needs quiet room",
            ),
            ("10000002", "2.0", 2, "Albert Einstein", "^3.5^2.25^^"),
            ("10000003", "1.25", 3, "Marie Curie", None),
        ]

        groups = self.canvas.get_overwrite_student_groups(accommodations, self.students)

        self.assertEqual(
            groups,
            [
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
                            "new_multiplier": "3.5",
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
                    "students": [
                        {
                            "id": "10000001",
                            "name": "Jason Zheng",
                            "def_multiplier": "1.5",
                            "new_multiplier": "3.0",
                        }
                    ],
                    "description": "exams involving fine maniplations",
                },
                {
                    "key": "notes",
                    "students": [
                        {
                            "id": "10000001",
                            "name": "Jason Zheng",
                            "def_multiplier": "1.5",
                            "new_multiplier": "Needs quiet room",
                        }
                    ],
                    "description": "CFA Notes",
                },
            ],
        )

    @tag("accommodations", "canvas_api", "overwrite_by_student")
    def test_get_overwrite_by_student_uses_highest_multiplier_for_overlapping_quizzes(
        self,
    ):
        overwrite_student_groups = [
            {
                "key": "essay",
                "students": [
                    {
                        "id": "10000001",
                        "name": "Jason Zheng",
                        "def_multiplier": "1.5",
                        "new_multiplier": "1.75",
                    },
                    {
                        "id": "10000002",
                        "name": "Albert Einstein",
                        "def_multiplier": "2.0",
                        "new_multiplier": "1.25",
                    },
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
                    }
                ],
                "description": "multiple choice format",
            },
        ]
        override_quizzes = {"essay": ["101", "102"], "mult_choice": ["101"]}
        multiplier_quiz_groups = {
            "1.25": [
                self.quiz_dict(101, "Quiz 101 for 1.25", 1.25),
                self.quiz_dict(102, "Quiz 102 for 1.25", 1.25),
            ],
            "1.75": [
                self.quiz_dict(101, "Quiz 101 for 1.75", 1.75),
                self.quiz_dict(102, "Quiz 102 for 1.75", 1.75),
            ],
            "2.0": [
                self.quiz_dict(101, "Quiz 101 for 2.0", 2.0),
                self.quiz_dict(102, "Quiz 102 for 2.0", 2.0),
            ],
        }

        overwrite_by_student = self.canvas.get_overwrite_by_student(
            overwrite_student_groups,
            override_quizzes,
            self.students,
            multiplier_quiz_groups,
        )

        self.assertEqual(
            overwrite_by_student,
            {
                "10000001": {
                    "name": "Jason Zheng",
                    "quizzes": [
                        self.quiz_dict(101, "Quiz 101 for 2.0", 2.0),
                        self.quiz_dict(102, "Quiz 102 for 1.75", 1.75),
                    ],
                },
                "10000002": {
                    "name": "Albert Einstein",
                    "quizzes": [
                        self.quiz_dict(101, "Quiz 101 for 1.25", 1.25),
                        self.quiz_dict(102, "Quiz 102 for 1.25", 1.25),
                    ],
                },
            },
        )

    @tag("accommodations", "canvas_api", "add_time_extensions")
    def test_add_time_extensions_sets_extensions_for_standard_and_new_quizzes(self):
        course = MagicMock()
        standard_quiz = MagicMock()
        new_quiz = SimpleNamespace(id=202)
        course.get_quiz.return_value = standard_quiz
        course.get_new_quiz.return_value = new_quiz
        self.canvas.get_course = MagicMock(return_value=course)
        self.canvas.set_extensions_for_new_quiz = MagicMock()

        quiz_groups, status = self.canvas.add_time_extensions(
            student_groups=[
                (
                    "1.5",
                    [
                        ("10000001", "Jason Zheng", 1, ""),
                        ("10000002", "Albert Einstein", 2, ""),
                    ],
                )
            ],
            quiz_groups={
                "1.5": [
                    self.extension_quiz(101, False, 60, 90),
                    self.extension_quiz(202, True, 30, 45),
                ]
            },
            course_id=1,
        )

        self.assertTrue(status)
        standard_quiz.set_extensions.assert_called_once_with(
            [{"user_id": 1, "extra_time": 30}, {"user_id": 2, "extra_time": 30}]
        )
        self.canvas.set_extensions_for_new_quiz.assert_called_once_with(
            new_quiz,
            [{"user_id": 1, "extra_time": 15}, {"user_id": 2, "extra_time": 15}],
            1,
        )
        self.assertEqual(quiz_groups["1.5"][0]["time_limit_status"], "success")
        self.assertEqual(quiz_groups["1.5"][1]["time_limit_status"], "success")

    @tag("accommodations", "canvas_api", "add_time_extensions")
    def test_add_time_extensions_applies_per_student_override_multiplier(self):
        course = MagicMock()
        standard_quiz = MagicMock()
        course.get_quiz.return_value = standard_quiz
        self.canvas.get_course = MagicMock(return_value=course)

        self.canvas.add_time_extensions(
            student_groups=[
                (
                    "1.5",
                    [
                        ("10000001", "Jason Zheng", 1, ""),
                        ("10000002", "Albert Einstein", 2, ""),
                    ],
                )
            ],
            quiz_groups={
                "1.5": [self.extension_quiz(101, False, 60, 90)],
                "2.0": [self.extension_quiz(101, False, 60, 120)],
            },
            course_id=1,
            student_quiz_data={
                "10000002": {
                    "name": "Albert Einstein",
                    "quizzes": [{"id": 101, "multiplier": 2.0}],
                }
            },
        )

        standard_quiz.set_extensions.assert_called_once_with(
            [{"user_id": 1, "extra_time": 30}, {"user_id": 2, "extra_time": 60}]
        )

    @tag("accommodations", "canvas_api", "override_logic", "add_time_extensions")
    def test_add_time_extensions_uses_full_additional_accommodation_override_flow(self):
        accommodations = [
            ("10000001", "1.5", 1, "Jason Zheng", "1.75^2.0^^^"),
            ("10000002", "1.5", 2, "Albert Einstein", "^2.5^^^"),
            ("10000003", "1.5", 3, "Marie Curie", ""),
        ]
        student_groups = self.canvas.get_multiplier_student_groups(
            accommodations, self.students
        )
        overwrite_student_groups = self.canvas.get_overwrite_student_groups(
            accommodations, self.students
        )
        quiz_groups = self.override_extension_quiz_groups([101, 102])
        overwrite_by_student = self.canvas.get_overwrite_by_student(
            overwrite_student_groups,
            {"essay": ["101"], "mult_choice": ["101", "102"]},
            self.students,
            quiz_groups,
        )

        course = MagicMock()
        canvas_quizzes = {101: MagicMock(), 102: MagicMock()}
        course.get_quiz.side_effect = lambda quiz_id: canvas_quizzes[quiz_id]
        self.canvas.get_course = MagicMock(return_value=course)

        quiz_groups, status = self.canvas.add_time_extensions(
            student_groups=student_groups,
            quiz_groups=quiz_groups,
            course_id=1,
            student_quiz_data=overwrite_by_student,
        )

        self.assertTrue(status)
        canvas_quizzes[101].set_extensions.assert_called_once_with(
            [
                {"user_id": 2, "extra_time": 90},
                {"user_id": 1, "extra_time": 60},
                {"user_id": 3, "extra_time": 30},
            ]
        )
        canvas_quizzes[102].set_extensions.assert_called_once_with(
            [
                {"user_id": 2, "extra_time": 90},
                {"user_id": 1, "extra_time": 60},
                {"user_id": 3, "extra_time": 30},
            ]
        )
        self.assertEqual(quiz_groups["1.5"][0]["time_limit_status"], "success")
        self.assertEqual(quiz_groups["1.5"][1]["time_limit_status"], "success")
        self.assertEqual(
            [
                quiz["multiplier"]
                for quiz in overwrite_by_student["10000001"]["quizzes"]
            ],
            [2.0, 2.0],
        )
        self.assertEqual(
            [
                quiz["multiplier"]
                for quiz in overwrite_by_student["10000002"]["quizzes"]
            ],
            [2.5, 2.5],
        )

    @tag("accommodations", "canvas_api", "add_time_extensions")
    def test_add_time_extensions_marks_quizzes_without_time_limit_as_not_applicable(
        self,
    ):
        course = MagicMock()
        self.canvas.get_course = MagicMock(return_value=course)

        quiz_groups, status = self.canvas.add_time_extensions(
            student_groups=[("1.5", [("10000001", "Jason Zheng", 1, "")])],
            quiz_groups={"1.5": [self.extension_quiz(101, False, 60, None)]},
            course_id=1,
        )

        self.assertTrue(status)
        self.assertEqual(quiz_groups["1.5"][0]["time_limit_status"], "N/A")
        course.get_quiz.assert_not_called()
        course.get_new_quiz.assert_not_called()

    @tag("accommodations", "canvas_api", "add_time_extensions")
    def test_add_time_extensions_marks_failure_when_canvas_call_fails(self):
        course = MagicMock()
        course.get_quiz.side_effect = Exception("Canvas API failed")
        self.canvas.get_course = MagicMock(return_value=course)

        quiz_groups, status = self.canvas.add_time_extensions(
            student_groups=[("1.5", [("10000001", "Jason Zheng", 1, "")])],
            quiz_groups={"1.5": [self.extension_quiz(101, False, 60, 90)]},
            course_id=1,
        )

        self.assertFalse(status)
        self.assertEqual(quiz_groups["1.5"][0]["time_limit_status"], "failure")

    @tag("accommodations", "canvas_api", "override_logic", "add_availabilities")
    def test_add_availabilities_overwrites_existing_canvas_overrides(self):
        partial_overlap = self.assignment_override(
            [1, 99],
            due_at="2026-08-01T18:00:00Z",
            unlock_at="2026-08-01T17:00:00Z",
            lock_at="2026-08-01T18:00:00Z",
        )
        full_overlap = self.assignment_override([2])
        no_overlap = self.assignment_override([88])
        assignment = MagicMock()
        assignment.get_overrides.return_value = [
            partial_overlap,
            full_overlap,
            no_overlap,
        ]
        course = self.course_for_availability_assignment(assignment)
        self.canvas.get_course = MagicMock(return_value=course)
        quiz_groups = {
            "1.5": [
                self.availability_quiz(
                    101,
                    lock_at_new="2026-08-01T18:30:00Z",
                    due_at_new="2026-08-01T18:30:00Z",
                )
            ]
        }

        quiz_groups, status = self.canvas.add_availabilities(
            student_groups=[
                (
                    "1.5",
                    [
                        ("10000001", "Jason Zheng", 1, ""),
                        ("10000002", "Albert Einstein", 2, ""),
                    ],
                )
            ],
            quiz_groups=quiz_groups,
            existing_accommodations=[{"id": 101, "user_id": 1}],
            should_override=True,
            course_id=1,
        )

        self.assertTrue(status)
        partial_overlap.delete.assert_called_once()
        full_overlap.delete.assert_called_once()
        no_overlap.delete.assert_not_called()
        assignment.create_override.assert_has_calls(
            [
                call(
                    assignment_override={
                        "student_ids": [99],
                        "due_at": "2026-08-01T18:00:00Z",
                        "unlock_at": "2026-08-01T17:00:00Z",
                        "lock_at": "2026-08-01T18:00:00Z",
                    }
                ),
                call(
                    assignment_override={
                        "unlock_at": "2026-08-01T17:00:00Z",
                        "lock_at": "2026-08-01T18:30:00Z",
                        "due_at": "2026-08-01T18:30:00Z",
                        "student_ids": [1, 2],
                    }
                ),
            ]
        )
        self.assertEqual(quiz_groups["1.5"][0]["lock_at_status"], "success")
        self.assertEqual(quiz_groups["1.5"][0]["unlock_at_status"], "N/A")

    @tag("accommodations", "canvas_api", "override_logic", "add_availabilities")
    def test_add_availabilities_preserves_existing_overrides_when_not_overwriting(self):
        assignment = MagicMock()
        course = self.course_for_availability_assignment(assignment)
        self.canvas.get_course = MagicMock(return_value=course)
        quiz_groups = {
            "1.5": [
                self.availability_quiz(
                    101,
                    lock_at_new="2026-08-01T18:30:00Z",
                    due_at_new="2026-08-01T18:30:00Z",
                )
            ]
        }

        quiz_groups, status = self.canvas.add_availabilities(
            student_groups=[
                (
                    "1.5",
                    [
                        ("10000001", "Jason Zheng", 1, ""),
                        ("10000002", "Albert Einstein", 2, ""),
                        ("10000003", "Marie Curie", 3, ""),
                    ],
                )
            ],
            quiz_groups=quiz_groups,
            existing_accommodations=[
                {"id": 101, "user_id": 1},
                {"id": 101, "user_id": 2},
                {"id": 999, "user_id": 3},
            ],
            should_override=False,
            course_id=1,
        )

        self.assertTrue(status)
        assignment.get_overrides.assert_not_called()
        assignment.create_override.assert_called_once_with(
            assignment_override={
                "unlock_at": "2026-08-01T17:00:00Z",
                "lock_at": "2026-08-01T18:30:00Z",
                "due_at": "2026-08-01T18:30:00Z",
                "student_ids": [3],
            }
        )
        self.assertEqual(quiz_groups["1.5"][0]["lock_at_status"], "success")
        self.assertEqual(quiz_groups["1.5"][0]["unlock_at_status"], "N/A")

    @staticmethod
    def quiz_dict(quiz_id, title, multiplier):
        return {
            "multiplier": multiplier,
            "id": quiz_id,
            "title": title,
            "is_new_quiz": False,
            "url": f"https://example.test/quizzes/{quiz_id}",
        }

    @staticmethod
    def extension_quiz(quiz_id, is_new_quiz, time_limit, time_limit_new):
        return {
            "id": quiz_id,
            "title": f"Quiz {quiz_id}",
            "is_new_quiz": is_new_quiz,
            "time_limit": time_limit,
            "time_limit_new": time_limit_new,
        }

    @classmethod
    def override_extension_quiz_groups(cls, quiz_ids):
        groups = {}
        for multiplier in ("1.5", "1.75", "2.0", "2.5"):
            groups[multiplier] = [
                {
                    **cls.extension_quiz(
                        quiz_id,
                        is_new_quiz=False,
                        time_limit=60,
                        time_limit_new=int(60 * float(multiplier)),
                    ),
                    "multiplier": float(multiplier),
                }
                for quiz_id in quiz_ids
            ]
        return groups

    @staticmethod
    def availability_quiz(
        quiz_id,
        lock_at_new=None,
        unlock_at_new=None,
        due_at_new=None,
        is_new_quiz=False,
    ):
        return {
            "id": quiz_id,
            "title": f"Quiz {quiz_id}",
            "is_new_quiz": is_new_quiz,
            "unlock_at": "2026-08-01T17:00:00Z",
            "lock_at": "2026-08-01T18:00:00Z",
            "unlock_at_new": unlock_at_new,
            "lock_at_new": lock_at_new,
            "due_at_new": due_at_new,
        }

    @staticmethod
    def assignment_override(student_ids, due_at=None, unlock_at=None, lock_at=None):
        override = MagicMock()
        override.student_ids = student_ids
        override.due_at = due_at
        override.unlock_at = unlock_at
        override.lock_at = lock_at
        return override

    @staticmethod
    def course_for_availability_assignment(assignment):
        course = MagicMock()
        canvas_quiz = MagicMock()
        canvas_quiz.assignment_id = 1001
        course.get_quiz.return_value = canvas_quiz
        course.get_assignment.return_value = assignment
        return course
