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
from datetime import timedelta

import math


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


def calculate_new_time_limit(time_limit, multiplier):
    if time_limit and multiplier:
        time_limit_new = time_limit * float(multiplier)
        time_limit_new_rounded = int(math.ceil(time_limit_new))
        return time_limit_new_rounded
    else:
        return None


def calculate_new_lock_at(unlock_at, lock_at, time_limit_new):
    # unlock_at, lock_at are ISO8601 strings, time_limit_new is int (in minutes)
    if unlock_at and lock_at and time_limit_new:  # only try if all values exist
        unlock_at_parsed = parser.isoparse(unlock_at).astimezone(get_current_timezone())
        lock_at_parsed = parser.isoparse(lock_at).astimezone(get_current_timezone())
        window = lock_at_parsed - unlock_at_parsed
        window_in_minutes = window.total_seconds() / 60

        if window_in_minutes < time_limit_new:
            # Set new lock_at to unlock_at + time_limit_new minutes
            new_lock_at = unlock_at_parsed + timedelta(minutes=time_limit_new)
            return new_lock_at.isoformat()
        return None
    else:
        return None


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

    def get_multiplier_student_groups(self, accommodations, students):
        # returns a dictionary of multipliers, and list of student tuples, where each tuple has the login id, display name, and user id
        multiplier_student_groups = {}
        student_names_by_id = {s.login_id: s.display_name for s in students}

        for student_id, multiplier, user_id in accommodations:
            student = (student_id, student_names_by_id[student_id], user_id)
            multiplier_student_groups.setdefault(multiplier, []).append(student)

        # Sort each student list by name
        for multiplier in multiplier_student_groups:
            multiplier_student_groups[multiplier] = sorted(
                multiplier_student_groups[multiplier], key=lambda student: student[1]
            )

        # Return as sorted list of tuples
        return sorted(multiplier_student_groups.items(), key=lambda item: item[0])

    def get_multiplier_quiz_groups(self, quizzes):
        # returns a dictionary of multipliers, and quiz lists, where each quiz list has the new time limit and locking time calculated
        multiplier_quiz_groups = {}
        for multiplier in ["1.25", "1.5", "2.0"]:
            quizzes_multiplied = (
                []
            )  # the list of quizzes, but with new data from the multiplication
            for quiz in quizzes:
                time_limit_new = calculate_new_time_limit(
                    quiz["time_limit"], multiplier
                )
                lock_at_new = calculate_new_lock_at(
                    quiz["unlock_at"], quiz["lock_at"], time_limit_new
                )

                quizzes_multiplied.append(
                    {
                        "id": quiz["id"],
                        "title": quiz["title"],
                        "time_limit": quiz["time_limit"],  # in minutes, or None
                        "due_at": quiz["due_at"],  # ISO8601 string or None
                        "unlock_at": quiz["unlock_at"],  # when quiz becomes available
                        "lock_at": quiz["lock_at"],  # when quiz is no longer available,
                        "published": quiz["published"],
                        "points_possible": quiz["points_possible"],
                        "time_limit_readable": readable_time_limit(quiz["time_limit"]),
                        "due_at_readable": readable_datetime(quiz["due_at"]),
                        "unlock_at_readable": readable_datetime(quiz["unlock_at"]),
                        "lock_at_readable": readable_datetime(quiz["lock_at"]),
                        # new, multiplier-specific fields added here
                        "time_limit_new": time_limit_new,
                        "time_limit_new_readable": readable_time_limit(time_limit_new),
                        "lock_at_new": lock_at_new,
                        "lock_at_new_readable": readable_datetime(lock_at_new),
                    }
                )
            multiplier_quiz_groups[multiplier] = quizzes_multiplied
        return multiplier_quiz_groups

    def add_time_extensions(self, student_groups, quiz_groups, course_id):
        # pass in final student data, quiz data needed, both are grouped by multiplier
        student_groups = dict(student_groups)  # convert from tuple list to dictionary
        for multiplier in ["1.25", "1.5", "2.0"]:
            student_list = student_groups[multiplier]
            quiz_list = quiz_groups[multiplier]
            for quiz in quiz_list:
                if quiz["time_limit_new"] is None:
                    break
                extensions = []
                # student is a tuple of login id, display name, user id
                for student in student_list:
                    extensions.append(
                        {
                            "user_id": student[2],
                            "extra_time": int(
                                quiz["time_limit_new"] - quiz["time_limit"]
                            ),
                        }
                    )
                canvas_quiz = self.get_course(course_id).get_quiz(quiz["id"])
                canvas_quiz.set_extensions(extensions)

    def add_availabilities():
        pass
