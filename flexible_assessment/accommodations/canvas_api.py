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
from datetime import timedelta, datetime, timezone

import math
import json


ACCOMMODATION_MULTIPLIERS = [1.25, 1.5, 2.0]


def is_midnight(query_time):
    """Checks if time is midnight
    Parameters
    ----------
    query_time : datetime.datetime
        datetime object
    """
    return query_time.hour == 0 and query_time.minute == 0


def readable_time_limit(minutes):
    """Formats time in minutes to user-readable format

    Parameters
    ----------
    minutes : int

    Returns
    -------
    result : str or None if nothing passed in
    """
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
    """Formats datetime to user-readable format

    Parameters
    ----------
    minutes : str (formatted as ISO8601 string)

    Returns
    -------
    result : str or None if nothing passed in
    """
    if not iso_string:
        return None
    try:
        dt = parser.isoparse(iso_string)
        dt = dt.astimezone(get_current_timezone())
        return dt.strftime("%Y-%m-%d - %-I:%M%p")
    except Exception:
        return iso_string


def get_time_window(unlock_at, lock_at):
    """
    Get the time window in minutes given the unlock_at and lock_at values of a quiz.

    Parameters
    ----------
    unlock_at : str
        A string representing the time a quiz unlocks (formatted as ISO8601 string)

    lock_at : str
        A string representing the time a quiz locks (formatted as ISO8601 string)

    Returns
    -------
    int
        An integer representing the number of minutes in the time window
    """
    unlock_at_parsed = parser.isoparse(unlock_at).astimezone(get_current_timezone())
    lock_at_parsed = parser.isoparse(lock_at).astimezone(get_current_timezone())
    window = lock_at_parsed - unlock_at_parsed
    window_in_minutes = window.total_seconds() / 60
    return window_in_minutes


def is_quiz_selectable(quiz):
    """
    Determines if a quiz is selectable based on time limit or lock/unlock dates.

    Parameters
    ----------
    quiz : dict
        A dictionary representing a Canvas quiz, containing 'unlock_at', 'lock_at', and 'time_limit'.

    Returns
    -------
    bool
        True if the quiz has a time limit or an unlock date and lock date, where the lock date is in the future;
        otherwise False.
    """
    unlock_at = quiz.get("unlock_at")
    lock_at = quiz.get("lock_at")

    if unlock_at is not None and lock_at is not None:
        try:
            lock_time = datetime.fromisoformat(lock_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if lock_time > now:  # check to make sure quiz locks in the future
                # First case - valid unlock_at, lock_at, existing time limit - should return true
                if quiz.get("time_limit") is not None:
                    return True
                else:
                    # Second case - valid unlock_at, lock_at, no existing time limit - should only return true if time window is <= 3 hours
                    time_window = get_time_window(unlock_at, lock_at)
                    if time_window <= 180:
                        return True
                    else:
                        return False
            else:
                return False
        except ValueError:
            # If the lock_at date is malformed, treat quiz as not selectable
            return False

    # check this both unlock at and lock at are not available
    if quiz.get("time_limit") is not None:
        return True

    return False


def calculate_new_time_limit(time_limit, multiplier):
    """
    Calculates a new time limit by applying an accommodation multiplier.

    Parameters
    ----------
    time_limit : int or float
        Original time limit in minutes.
    multiplier : float or str
        Accommodation multiplier (e.g., 1.5 for 50% extra time).

    Returns
    -------
    int or None
        The new time limit rounded up to the nearest minute, or None if input is invalid.
    """
    if time_limit and multiplier:
        time_limit_new = time_limit * float(multiplier)
        time_limit_new_rounded = int(
            math.ceil(time_limit_new)
        )  # round up instead of truncating
        return time_limit_new_rounded
    else:
        return None


def set_warn(quiz):
    """
    Sets the "should_warn" field in the quiz dictionary passed in

    Parameters
    ----------
    quiz : dict
        A dictionary representing a Canvas quiz
    """
    if (
        quiz["unlock_at"] is not None
        and quiz["lock_at"] is not None
        and quiz["time_limit"] is not None
    ):
        time_window = get_time_window(quiz["unlock_at"], quiz["lock_at"])
        if time_window < quiz["time_limit"]:
            quiz["should_warn"] = True


def calculate_new_lock_at(unlock_at, lock_at, time_limit_new, multiplier):
    """
    Calculates a new lock time if the quiz window is shorter than the new time limit.

    Parameters
    ----------
    unlock_at : str
        ISO8601 formatted unlock datetime string.
    lock_at : str
        ISO8601 formatted lock datetime string.
    time_limit_new : int
        The new time limit in minutes.
    multiplier : float or str
        Accommodation multiplier (e.g., 1.5 for 50% extra time).

    Returns
    -------
    str or None
        The new lock_at time in ISO8601 format, or None if no change is needed.
    """

    if (
        unlock_at is None or lock_at is None
    ):  # both unlock and lock at must exist to set new lock at
        return None

    # unlock_at, lock_at are ISO8601 strings, time_limit_new is int (in minutes)
    unlock_at_parsed = parser.isoparse(unlock_at).astimezone(get_current_timezone())
    window_in_minutes = get_time_window(unlock_at, lock_at)

    if (
        time_limit_new
    ):  # normal case - extend lock at to match new time limit if necessary

        if window_in_minutes < time_limit_new:
            # Set new lock_at to unlock_at + time_limit_new minutes
            new_lock_at = unlock_at_parsed + timedelta(minutes=time_limit_new)
            if is_midnight(new_lock_at):
                # Canvas does not allow setting time to midnight, so we'll set to 12:01 AM
                new_lock_at = new_lock_at + timedelta(minutes=1)
            return new_lock_at.isoformat()
        return None
    elif (
        window_in_minutes <= 180
    ):  # rarer case - no time limit, but unlock, lock at both exist and have a window less than 3 hours
        multiplier = float(multiplier)
        new_window_in_minutes = int(math.ceil(window_in_minutes * multiplier))
        new_lock_at = unlock_at_parsed + timedelta(minutes=new_window_in_minutes)
        if is_midnight(new_lock_at):
            # Canvas does not allow setting time to midnight, so we'll set to 12:01 AM
            new_lock_at = new_lock_at + timedelta(minutes=1)
        return new_lock_at.isoformat()
    else:  # if unlock, lock at both exist, but have a window greater than 3 hours, don't set a new lock at time
        return None


def calculate_new_due_at(due_at, lock_at_new, lock_at):
    """
    Calculates a new due time according to the existing due time and the new lock time.

    Parameters
    ----------
    due_at : str
        ISO8601 formatted due date datetime string.
    lock_at_new : str
        ISO8601 formatted lock datetime string.
    lock_at : str
        ISO8601 formatted lock datetime string.

    Returns
    -------
    str or None
        The new due_at time in ISO8601 format, or None if no change is needed.
    """
    if due_at is None:
        return None
    elif (
        lock_at_new is not None
    ):  # if there is a new lock time and due_at exists, set due_at to the new lock time
        return lock_at_new
    elif (
        lock_at is not None
    ):  # if there is an existing lock time and due_at exists, set due_at to the existing lock time
        return lock_at
    else:
        # if no original lock time but existing due time, keep due at the same
        return due_at


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
        """
        Retrieves quizzes from a Canvas course and classifies them by availability.

        Quizzes are separated into two groups: those that are selectable (i.e., have a time limit or are open)
        and those that are unavailable (e.g., not published or outside availability window).

        Parameters
        ----------
        course_id : int
            The Canvas course ID.

        Returns
        -------
        tuple of list of dict
            A tuple (selectable_quizzes, unavailable_quizzes), where each list contains dictionaries with quiz metadata.
        """
        # TODO - extended this to work with New Quizzes as well, add field in quiz data specifying if quiz is New

        course = self.get_course(course_id)  # You'll need the course ID
        quizzes = course.get_quizzes()

        quiz_list = []
        unavailable_quiz_list = []

        for quiz in quizzes:
            quiz_data = {
                "id": quiz.id,
                "title": quiz.title,
                "time_limit": quiz.time_limit,  # in minutes, or None
                "due_at": quiz.due_at,  # ISO8601 string or None
                "unlock_at": quiz.unlock_at,  # when quiz becomes available
                "lock_at": quiz.lock_at,  # when quiz is no longer available,
                "published": quiz.published,
                "url": quiz.html_url + "/edit",  # send edit link
                "points_possible": quiz.points_possible,
                "time_limit_readable": readable_time_limit(quiz.time_limit),
                "due_at_readable": readable_datetime(quiz.due_at),
                "unlock_at_readable": readable_datetime(quiz.unlock_at),
                "lock_at_readable": readable_datetime(quiz.lock_at),
                "should_warn": False,  # set this to true if the time window between start and end date is less than the time limit
                "is_new_quiz": False,
            }
            if is_quiz_selectable(quiz_data):
                set_warn(quiz_data)
                quiz_list.append(quiz_data)
            else:
                unavailable_quiz_list.append(quiz_data)

        try:
            new_quizzes = course.get_new_quizzes()
            for quiz in new_quizzes:
                quiz_data = {
                    "id": quiz.id,
                    "title": quiz.title,
                    "due_at": quiz.due_at,  # ISO8601 string or None
                    "unlock_at": quiz.unlock_at,  # when quiz becomes available
                    "lock_at": quiz.lock_at,  # when quiz is no longer available,
                    "published": quiz.published,
                    "url": f"{self.base_url}courses/{course_id}/assignments/{quiz.id}/edit?quiz_lti",  # send edit link
                    "points_possible": quiz.points_possible,
                    "due_at_readable": readable_datetime(quiz.due_at),
                    "unlock_at_readable": readable_datetime(quiz.unlock_at),
                    "lock_at_readable": readable_datetime(quiz.lock_at),
                    "should_warn": False,  # set this to true if the time window between start and end date is less than the time limit
                    "is_new_quiz": True,
                }
                if (
                    hasattr(quiz, "quiz_settings")
                    and quiz.quiz_settings["has_time_limit"] == True
                ):  # some new quiz objects may not have this if the instructor hasn't built the quiz yet
                    new_quiz_settings = quiz.quiz_settings

                    quiz_data["time_limit"] = (
                        new_quiz_settings["session_time_limit_in_seconds"] // 60
                    )  # use floor division
                    quiz_data["time_limit_readable"] = readable_time_limit(
                        quiz_data["time_limit"]
                    )
                else:
                    quiz_data["time_limit"] = None
                    quiz_data["time_limit_readable"] = None

                if is_quiz_selectable(quiz_data):
                    set_warn(quiz_data)
                    quiz_list.append(quiz_data)
                else:
                    unavailable_quiz_list.append(quiz_data)
        except:
            print("Unable to get new quizzes")

        quiz_list = sorted(
            quiz_list, key=lambda quiz: (quiz["title"] or "").strip().lower()
        )

        unavailable_quiz_list = sorted(
            unavailable_quiz_list,
            key=lambda quiz: (quiz["title"] or "").strip().lower(),
        )

        return quiz_list, unavailable_quiz_list

    def get_multiplier_student_groups(self, accommodations, students):
        """
        Groups students by time extension multiplier.

        Parameters
        ----------
        accommodations : list of tuple of (str, str, int)
            List of (login_id, multiplier, user_id) tuples.
        students : list
            List of Canvas user objects, each with 'login_id' and 'display_name' attributes.

        Returns
        -------
        list of tuple
            A list of (multiplier, students) tuples, sorted by multiplier. Each students list is sorted by name.
        """
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
        """
        Creates quiz variants with extended time limit and adjusted lock times for common multipliers.

        Parameters
        ----------
        quizzes : list of dict
            A list of quiz dictionaries containing keys like 'time_limit', 'unlock_at', 'lock_at', etc.

        Returns
        -------
        dict of {str: list of dict}
            Dictionary where each key is a multiplier (e.g., '1.5') and the value is a list of modified quiz dicts.
        """
        multiplier_quiz_groups = {}
        for multiplier in ACCOMMODATION_MULTIPLIERS:
            multiplier = str(multiplier)
            quizzes_multiplied = (
                []
            )  # the list of quizzes, but with new data from the multiplication
            for quiz in quizzes:
                time_limit_new = calculate_new_time_limit(
                    quiz["time_limit"], multiplier
                )
                lock_at_new = calculate_new_lock_at(
                    quiz["unlock_at"], quiz["lock_at"], time_limit_new, multiplier
                )

                due_at_new = calculate_new_due_at(
                    quiz["due_at"], lock_at_new, quiz["lock_at"]
                )

                #  due_at_new = calculate_new_due_at(quiz["due_at"], lock_at_new)

                quiz_modified = quiz.copy()
                quiz_modified.update(
                    {
                        "time_limit_new": time_limit_new,
                        "time_limit_new_readable": readable_time_limit(time_limit_new),
                        "lock_at_new": lock_at_new,
                        "lock_at_new_readable": readable_datetime(lock_at_new),
                        "due_at_new": due_at_new,  # no need for readable since we don't display due_at valueu
                    }
                )

                quizzes_multiplied.append(quiz_modified)
            multiplier_quiz_groups[multiplier] = quizzes_multiplied
        return multiplier_quiz_groups

    def get_existing_accommodations(
        self, accommodations, students, multiplier_quiz_groups, course_id
    ):
        """
        Find and return all existing accommodations on Canvas that conflict with the curent accommodations to be applied.

        Parameters
        ----------
        accommodations : list of tuple of (str, str, int)
            List of (login_id, multiplier, user_id) tuples.
        students : list
            List of Canvas user objects, each with 'login_id' and 'display_name' attributes.
        multiplier_quiz_groups : dict of {str: list of dict}
            Dictionary where each key is a multiplier (e.g., '1.5') and the value is a list of modified quiz dicts.
        course_id : int
            The Canvas course ID.

        Returns
        -------
        list of dict
            Each dict represents an existing accommodation override for a student, containing:
            - login_id
            - display_name
            - user_id
            - title
            - url
            - unlock_at
            - unlock_at_readable
            - lock_at
            - lock_at_readable
            - unlock_at_override
            - unlock_at_override_readable
            - lock_at_override
            - lock_at_override_readable
        """
        course = self.get_course(course_id)

        # Create a mapping of user_id to student info
        student_tuples_by_user_id = {
            s.user_id: (s.login_id, s.display_name, s.user_id) for s in students
        }

        # Map user_id to multiplier
        user_id_to_multiplier = {
            user_id: multiplier for _, multiplier, user_id in accommodations
        }

        existing_accommodations = []

        # Use the quiz structure from one multiplier as reference (all groups are parallel)
        reference_quiz_list = next(iter(multiplier_quiz_groups.values()))

        for quiz_index, quiz in enumerate(reference_quiz_list):
            # TODO - fix for new quizzes here
            quiz_assignment = None
            if quiz["is_new_quiz"]:
                quiz_assignment = course.get_assignment(quiz["id"])
            else:
                canvas_quiz = course.get_quiz(quiz["id"])
                quiz_assignment = course.get_assignment(canvas_quiz.assignment_id)
            assignment_overrides = quiz_assignment.get_overrides()

            for override in assignment_overrides:
                for student_id in override.student_ids:
                    if student_id not in user_id_to_multiplier:
                        continue

                    multiplier = user_id_to_multiplier[student_id]
                    planned_quiz_list = multiplier_quiz_groups.get(multiplier)
                    if not planned_quiz_list:
                        continue

                    planned_quiz = planned_quiz_list[quiz_index]
                    if planned_quiz.get("lock_at_new") is None:
                        continue  # App does not plan to override this quiz

                    unlock_at_override = (
                        override.unlock_at if hasattr(override, "unlock_at") else None
                    )

                    lock_at_override = (
                        override.lock_at if hasattr(override, "unlock_at") else None
                    )

                    student_tuple = student_tuples_by_user_id[student_id]
                    override_dict = {
                        "login_id": student_tuple[0],
                        "display_name": student_tuple[1],
                        "user_id": student_tuple[2],
                        "id": quiz["id"],
                        "title": quiz["title"],
                        "url": quiz["url"],
                        "unlock_at": quiz["unlock_at"],
                        "unlock_at_readable": quiz["unlock_at_readable"],
                        "lock_at": quiz["lock_at"],
                        "lock_at_readable": quiz["lock_at_readable"],
                        "unlock_at_override": unlock_at_override,
                        "unlock_at_override_readable": readable_datetime(
                            unlock_at_override
                        ),
                        "lock_at_override": lock_at_override,
                        "lock_at_override_readable": readable_datetime(
                            lock_at_override
                        ),
                    }
                    existing_accommodations.append(override_dict)

        return existing_accommodations

    def set_extensions_for_new_quiz(self, new_quiz, extensions, course_id):
        quiz_url = f"{self.base_url}api/quiz/v1/courses/{course_id}/quizzes/{new_quiz.id}/accommodations"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(quiz_url, headers=headers, data=json.dumps(extensions))
        response.raise_for_status()  # raise exception on HTTP error

    def add_time_extensions(self, student_groups, quiz_groups, course_id):
        """
        Applies extra time limit extensions to quizzes for students with accommodations.

        Uses Canvas API to set `extra_time` for each quiz attempt based on multiplier.

        Parameters
        ----------
        student_groups : list of tuple
            List of (multiplier, students) tuples, where each student is a (login_id, name, user_id) tuple.
        quiz_groups : dict of {str: list of dict}
            Dictionary of quizzes grouped by multiplier, each with new time limits.
        course_id : int
            The Canvas course ID.

        Returns
        -------
        tuple
            A tuple (quiz_groups, status) where:
            - quiz_groups : dict of {str: list of dict}
                Updated quiz group data with 'time_limit_status' keys indicating success or failure.
            - status : bool
                Overall status indicating whether all extensions were applied successfully.
        """
        student_groups = dict(student_groups)  # convert from tuple list to dictionary
        course = self.get_course(course_id)
        status = True  # represents the status of adding - if any adds fail set to false

        for multiplier in ACCOMMODATION_MULTIPLIERS:
            multiplier = str(multiplier)
            student_list = student_groups.get(multiplier, None)
            if student_list is None:
                continue  # if no students for this multiplier, move on to next multiplier
            quiz_list = quiz_groups[multiplier]
            for quiz in quiz_list:
                if quiz["time_limit_new"] is None:
                    quiz["time_limit_status"] = "N/A"
                    continue
                try:
                    # create list of extensions
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

                    # set extensions based on quiz type
                    if quiz["is_new_quiz"]:
                        new_quiz = course.get_new_quiz(quiz["id"])
                        self.set_extensions_for_new_quiz(
                            new_quiz, extensions, course_id
                        )  # use our own custom function
                    else:
                        canvas_quiz = course.get_quiz(quiz["id"])
                        canvas_quiz.set_extensions(extensions)  # use built in function
                except:
                    quiz["time_limit_status"] = "failure"
                    status = False
                else:
                    quiz["time_limit_status"] = "success"

        return quiz_groups, status

    def add_availabilities(
        self,
        student_groups,
        quiz_groups,
        existing_accommodations,
        should_override,
        course_id,
    ):
        """
        Applies availability overrides to extend quiz access windows.

        Removes matching overrides and replaces them with new ones using adjusted `lock_at` times.

        Parameters
        ----------
        student_groups : list of tuple
            List of (multiplier, students) tuples, where each student is a (login_id, name, user_id) tuple.
        quiz_groups : dict of {str: list of dict}
            Dictionary of quizzes grouped by multiplier, each with new lock times.
        existing_accommodations : list of dict
            List of all existing accommodations on Canvas as dictionaries including student and quiz info.
        should_override : boolean
            Whether existing accommodations should be overriden or ignored
        course_id : int
            The Canvas course ID.

        Returns
        -------
        tuple
            A tuple (quiz_groups, status) where:
            - quiz_groups : dict of {str: list of dict}
                Updated quiz group data with 'lock_at_status' keys indicating success or failure.
            - status : bool
                Overall status indicating whether all availability overrides were applied successfully.
        """

        start = time.time()

        student_groups = dict(student_groups)  # convert from tuple list to dictionary
        course = self.get_course(course_id)
        status = True  # represents the status of adding - if any adds fail set to false

        for multiplier in ACCOMMODATION_MULTIPLIERS:
            multiplier = str(multiplier)
            student_list = student_groups.get(multiplier, None)
            if student_list is None:
                continue  # if no students for this multiplier, move on to next multiplier
            student_user_id_list = [student[2] for student in student_list]

            quiz_list = quiz_groups[multiplier]
            for quiz in quiz_list:
                if quiz["lock_at_new"] is None:
                    quiz["lock_at_status"] = "N/A"
                    continue

                try:
                    quiz_assignment = None
                    if quiz["is_new_quiz"]:
                        quiz_assignment = course.get_assignment(quiz["id"])
                    else:
                        canvas_quiz = course.get_quiz(quiz["id"])
                        quiz_assignment = course.get_assignment(
                            canvas_quiz.assignment_id
                        )

                    if (
                        not existing_accommodations
                    ):  # there are no existing accommodations to worry about
                        # Create a new override
                        result = quiz_assignment.create_override(
                            assignment_override={
                                "student_ids": student_user_id_list,
                                "unlock_at": quiz["unlock_at"],
                                "lock_at": quiz["lock_at_new"],
                                "due_at": quiz["due_at_new"],
                            }
                        )
                    elif should_override:
                        # for the quiz, get all existing overrides
                        # for each existing quiz override, remove the students that need to be overridden by the app
                        # assignment_overrides = quiz_assignment.get_overrides()
                        assignment_overrides = quiz_assignment.get_overrides()
                        for override in assignment_overrides:
                            override_student_ids = set(override.student_ids)
                            accommodation_student_ids = set(student_user_id_list)
                            new_override_student_ids = list(
                                override_student_ids.difference(
                                    accommodation_student_ids
                                )
                            )

                            if new_override_student_ids and len(
                                new_override_student_ids
                            ) < len(
                                override_student_ids
                            ):  # case 1 - override should be modified to have less students
                                override_new = {
                                    "student_ids": new_override_student_ids,
                                    "due_at": (
                                        override.due_at
                                        if hasattr(override, "due_at")
                                        else None
                                    ),
                                    "unlock_at": (
                                        override.unlock_at
                                        if hasattr(override, "unlock_at")
                                        else None
                                    ),
                                    "lock_at": (
                                        override.lock_at
                                        if hasattr(override, "lock_at")
                                        else None
                                    ),
                                }
                                # it would be ideal to call override.edit() but it seems to break - deleting and creating the override works as well
                                override.delete()
                                quiz_assignment.create_override(
                                    assignment_override=override_new
                                )
                            elif new_override_student_ids and len(
                                new_override_student_ids
                            ) == len(
                                override_student_ids
                            ):  # case 2 - override doesn't have any overlapping students
                                pass
                            else:
                                override.delete()
                        # create our new override with all the students
                        result = quiz_assignment.create_override(
                            assignment_override={
                                "student_ids": student_user_id_list,
                                "unlock_at": quiz["unlock_at"],
                                "lock_at": quiz["lock_at_new"],
                                "due_at": quiz["due_at_new"],
                            }
                        )
                    else:
                        # remove student user ids from list if there is an entry in the existing accommodations with the current quiz and the student
                        # create new override with the rest of the students
                        list_filtered = student_user_id_list[:]  # shallow copy
                        for acc in existing_accommodations:
                            if acc["id"] == quiz["id"]:
                                if acc["user_id"] in list_filtered:
                                    list_filtered.remove(acc["user_id"])

                        if list_filtered:  # don't create if list is empty
                            result = quiz_assignment.create_override(
                                assignment_override={
                                    "student_ids": list_filtered,
                                    "unlock_at": quiz["unlock_at"],
                                    "lock_at": quiz["lock_at_new"],
                                    "due_at": quiz["due_at_new"],
                                }
                            )
                except:
                    quiz["lock_at_status"] = "failure"
                    status = False
                    # raise Exception("TEST EXCEPTION")
                else:
                    quiz["lock_at_status"] = "success"

        end = time.time()
        print("synchronous execution time for add_availabilities: " + str(end - start))
        return quiz_groups, status
