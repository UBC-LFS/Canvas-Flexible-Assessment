import time
import requests
from collections.abc import MutableMapping

from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from django.conf import settings
from django.core.exceptions import PermissionDenied
from oauth.oauth import get_oauth_token
from decimal import Decimal, ROUND_HALF_UP

from dateutil import parser
from django.utils.timezone import get_current_timezone


def round_half_up(value, digits=2):
    """Rounds a float to the specified number of digits using ROUND_HALF_UP"""
    d = Decimal(str(value))  # Convert the float to a Decimal
    return d.quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP)


def readable_time_limit(minutes):
    if not minutes:
        return None
    if minutes < 60:
        return str(minutes) + "m"
    else:
        hours = minutes // 60
        remainder_minutes = minutes % 60
        if remainder_minutes == 0:
            return str(hours) + "h"
        else:
            return str(hours) + "h " + str(remainder_minutes) + "m"


def readable_datetime(iso_string):
    if not iso_string:
        return None
    try:
        dt = parser.isoparse(iso_string)
        dt = dt.astimezone(get_current_timezone())
        return dt.strftime("%Y-%m-%d - %-I:%M%p")
    except Exception:
        return iso_string


class AccommodationsCanvas(Canvas):
    """Extends Canvas class for handling a Canvas course within
    an Accommodations context
    """

    def __init__(self, request):
        """Creates AccommodationsCanvas instance using Canvas OAuth
        token of instructor using the application
        """

        base_url = settings.CANVAS_DOMAIN
        access_token = get_oauth_token(request)

        self.base_url = base_url
        self.access_token = access_token
        super().__init__(base_url, access_token)

    def get_quiz_data(self, course_id):
        # TODO - extended this to work with New Quizzes as well, add field in quiz data specifying if quiz is New

        course = self.get_course(course_id)  # You'll need the course ID
        quizzes = course.get_quizzes()

        quiz_list = []

        for quiz in quizzes:
            quiz_data = {
                "id": quiz.id,
                "title": quiz.title,
                "time_limit": quiz.time_limit,  # in minutes, or None
                "due_at": quiz.due_at,  # ISO8601 string or None
                "unlock_at": quiz.unlock_at,  # when quiz becomes available
                "lock_at": quiz.lock_at,  # when quiz is no longer available,
                "published": quiz.published,
                "points_possible": quiz.points_possible,
                "time_limit_readable": readable_time_limit(quiz.time_limit),
                "due_at_readable": readable_datetime(quiz.due_at),
                "unlock_at_readable": readable_datetime(quiz.unlock_at),
                "lock_at_readable": readable_datetime(quiz.lock_at),
            }
            quiz_list.append(quiz_data)

        quiz_list = sorted(
            quiz_list, key=lambda quiz: (quiz["title"] or "").strip().lower()
        )

        return quiz_list

    def get_multiplier_groups(self, accommodations, students):
        multiplier_groups = {}
        student_names_by_id = {s.login_id: s.display_name for s in students}

        for student_id, multiplier in accommodations:
            student = (student_id, student_names_by_id[student_id])
            multiplier_groups.setdefault(multiplier, []).append(student)

        # Sort each student list by name
        for multiplier in multiplier_groups:
            multiplier_groups[multiplier] = sorted(
                multiplier_groups[multiplier], key=lambda student: student[1]
            )

        # Return as sorted list of tuples
        return sorted(multiplier_groups.items(), key=lambda item: item[0])
