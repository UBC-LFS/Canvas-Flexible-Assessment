import time
import requests
from collections.abc import MutableMapping

from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from django.conf import settings
from django.core.exceptions import PermissionDenied
from oauth.oauth import get_oauth_token
from decimal import Decimal, ROUND_HALF_UP


def round_half_up(value, digits=2):
    """Rounds a float to the specified number of digits using ROUND_HALF_UP"""
    d = Decimal(str(value))  # Convert the float to a Decimal
    return d.quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP)


class FlexCanvas(Canvas):
    """Extends Canvas class for handling a Canvas course within
    a Flexible Assessment context
    """

    def __init__(self, request):
        """Creates FlexCanvas instance using Canvas OAuth
        token of instructor using the application
        """

        base_url = settings.CANVAS_DOMAIN
        access_token = get_oauth_token(request)
        self.base_url = base_url
        self.access_token = access_token
        super().__init__(base_url, access_token)

    def set_override_true(self, course_id):
        """Sets 'allow final grade override' in Canvas course

        Parameters
        ----------
        course_id : int
            Canvas course ID
        """

        param = {"allow_final_grade_override": "true"}
        url = f"{self.base_url}/api/v1/courses/{course_id}/settings"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = requests.put(url, headers=headers, params=param)
        response.raise_for_status()

        return response.json()

    def is_allow_override(self, course_id):
        """Checks if Canvas couse with given id has 'allow final grade override'
        enabled

        Parameters
        ----------
        course_id : int
            Canvas course ID

        Returns
        -------
        bool
            True indicates final grade override is enabled,
            False indicates it is disabled
        """

        query = """query AllowOverrideQuery($course_id: ID) {
                course(id: $course_id) {
                    allowFinalGradeOverride
                    } }"""
        query_response = self.graphql(query, variables={"course_id": course_id})

        return query_response["data"]["course"]["allowFinalGradeOverride"]

    def set_override(self, enrollment_id, override, incomplete, attempt=1):
        """ "Sets final grade override for student with given enrollment ID

        Parameters
        ----------
        enrollment_id : str
            Canvas enrollment ID for student in the course
        override : float
            Final grade override for the student
        incomplete : list
            Mutable datatype representing status of submitting final grade,
            contains single element of bool type, True represents a grade
            was not able to be submitted
        attempt : int
            Represents the current attempt of submitting a student grade
        """

        mutation = """mutation OverrideFinalScore($enrollment_id: ID!, $override: Float) {
                    setOverrideScore(input: { enrollmentId: $enrollment_id,
                                              overrideScore: $override }) {
                        grades {
                            overrideScore
                            } } }"""
        try:
            if not incomplete[0]:
                self.graphql(
                    mutation,
                    variables={"enrollment_id": enrollment_id, "override": override},
                )
        except CanvasException:
            if attempt <= 5:
                time.sleep(1)
                self.set_override(enrollment_id, override, incomplete, attempt + 1)
            else:
                incomplete[0] = True

    def get_groups_and_enrollments(self, course_id):
        """Gets Canvas assignment groups and student enrollment data

        Parameters
        ----------
        course_id : int
            Canvas course ID

        Returns
        -------
        group_dict : dict
            Contains assignment group and grades data
        user_enrollment_dict : dict
            Contains enrollment ID for each user
        """

        query = """query AssignmentGroupQuery($course_id: ID) {
                    course(id: $course_id) {
                        assignment_groups: assignmentGroupsConnection {
                        groups: nodes {
                            group_id: _id
                            group_name: name
                            group_weight: groupWeight
                            grade_list: gradesConnection {
                            grades: nodes {
                                current_score: currentScore
                                enrollment {
                                user {
                                    user_id: _id
                                    display_name: name
                                }
                                _id
            } } } } } } }"""

        query_response = self.graphql(query, variables={"course_id": course_id})

        query_flattened = self._flatten_dict(query_response)
        groups = query_flattened.get("data.course.assignment_groups.groups", None)
        if groups is None:
            raise PermissionDenied

        group_dict = {}
        user_enrollment_dict = {}
        for group in groups:
            id = group["group_id"]
            group.pop("group_id", None)
            group_dict[id] = group

        for group_data in group_dict.values():
            group_flattened = self._flatten_dict(group_data)
            grades = group_flattened.get("grade_list.grades", None)
            if grades is None:
                raise PermissionDenied

            updated_grades = []
            for grade in grades:
                grade_flattened = self._flatten_dict(grade)
                user_id = grade_flattened.get("enrollment.user.user_id", None)
                enrollment_id = grade_flattened.get("enrollment._id", None)
                if user_id is None:
                    raise PermissionDenied

                user_enrollment_dict[user_id] = enrollment_id

                score = grade_flattened["current_score"]
                updated_grades.append((user_id, score))

            group_data["grade_list"]["grades"] = updated_grades

        return group_dict, user_enrollment_dict

    def calculate_user_scores(self, data, rules, user_drop_status):
        user_scores = {}

        for user_id, assignments in data.items():
            # Create list of dictionaries (a tuple) out of nested dictionary
            score_dict = {
                list(assignment.keys())[0]: list(assignment.values())[0]
                for assignment in assignments
            }

            # initialize user_drop_status for each user
            user_drop_status[user_id] = 0

            # Extracting scores that should never be dropped
            if rules["neverDrop"]:
                neverdrop = []
                for aid in rules["neverDrop"]:
                    neverdrop.append(aid["_id"])
                never_drop_scores = {
                    aid: score for aid, score in score_dict.items() if aid in neverdrop
                }
                # Extracting scores that can potentially be dropped
                droppable_scores = {
                    aid: score
                    for aid, score in score_dict.items()
                    if aid not in neverdrop
                }
            else:
                never_drop_scores = {}
                droppable_scores = {aid: score for aid, score in score_dict.items()}

            # Sorting droppable scores by score, descending order
            sorted_droppable_scores = sorted(
                droppable_scores.items(), key=lambda item: item[1]
            )

            # Design: if there are rules for dropping highest and lowest scores, only drop if it's possible to satisfy both rules
            # Otherwise, if there is only one rule, drop only if you can satisfy it
            if (
                "dropHighest" in rules
                and rules["dropHighest"]
                and "dropLowest" in rules
                and rules["dropLowest"]
            ):
                highest_drop_count = rules["dropHighest"]
                lowest_drop_count = rules["dropLowest"]
                if highest_drop_count + lowest_drop_count < len(
                    sorted_droppable_scores
                ):
                    sorted_droppable_scores = sorted_droppable_scores[
                        :-highest_drop_count
                    ]
                    user_drop_status[user_id] += highest_drop_count
                    sorted_droppable_scores = sorted_droppable_scores[
                        lowest_drop_count:
                    ]
                    user_drop_status[user_id] += lowest_drop_count
            elif (
                "dropHighest" in rules and rules["dropHighest"]
            ):  # case where dropLowest not found or equals null
                highest_drop_count = rules["dropHighest"]
                if highest_drop_count < len(sorted_droppable_scores):
                    sorted_droppable_scores = sorted_droppable_scores[
                        :-highest_drop_count
                    ]
                    user_drop_status[user_id] += highest_drop_count
            elif "dropLowest" in rules and rules["dropLowest"]:
                lowest_drop_count = rules["dropLowest"]
                if lowest_drop_count < len(sorted_droppable_scores):
                    sorted_droppable_scores = sorted_droppable_scores[
                        lowest_drop_count:
                    ]
                    user_drop_status[user_id] += lowest_drop_count

            # Combine the scores from neverDrop with the remaining droppable scores
            final_scores = list(never_drop_scores.values()) + [
                score for _, score in sorted_droppable_scores
            ]

            # Calculate total_score as the sum of all the undropped scores
            total_score = sum(final_scores)

            # Store the computed total score for each user
            user_scores[user_id] = total_score

        # print(user_scores)
        return user_scores

    def get_flat_groups_and_enrollments(self, course_id):
        """Gets Canvas assignment groups and student enrollment data

        Parameters
        ----------
        course_id : int
            Canvas course ID

        Returns
        -------
        group_dict : dict
            Contains assignment group and grades data
        user_enrollment_dict : dict
            Contains enrollment ID for each user
        """

        query = """
        query AssignmentGroupQuery($course_id: ID!) {
        course(id: $course_id) {
            assignment_groups: assignmentGroupsConnection {
                groups: nodes {
                    rules {
                        dropHighest
                        dropLowest
                        neverDrop {
                            _id
                        }
                    }
                    group_id:_id
                    group_name: name
                    group_weight: groupWeight
                    assignment_list: assignmentsConnection {
                        assignments: nodes {
                            _id
                            max_score: pointsPossible
                            name
                            published   # to check for unpublished assignments to filter out
                            gradingType # to check for assignments with gradingType = not_graded
                            omitFromFinalGrade # to check for assignments that should not be factored into the final grade
                            submission_list: submissionsConnection {
                                submissions: nodes {
                                    score
                                    user_id: userId
                                }
                            }
                        }
                    }
                    grade_list: gradesConnection {
                        grades: nodes {
                            current_score: currentScore
                            enrollment {
                                _id
                                user {
                                    user_id: _id
                                    display_name: name
                                }
                            }
                        }
                    }
                }
            }
        }
    }
        """
        # Makes the API call
        query_response = self.graphql(query, variables={"course_id": course_id})
        query_flattened = self._flatten_dict(query_response)
        groups = query_flattened.get("data.course.assignment_groups.groups", None)
        if groups is None:
            raise PermissionDenied

        group_dict = {}
        # This dict matches grades to enrollment ID, necessary for overriding grade
        user_enrollment_dict = {}
        # Set group id key to group value
        for group in groups:
            id = group.pop("group_id", None)
            group_dict[id] = group

        # Iterate over each assignment group.
        for group_data in group_dict.values():
            # Collect special grading rules for each assignment group
            rules = group_data.pop("rules")
            # If rules = None you skip the extra processing
            if all(rule is None for rule in rules.values()):
                rules = None

            group_flattened = self._flatten_dict(group_data)
            # Get list of assignments for each group
            assignments = group_flattened.pop("assignment_list.assignments", None)
            if assignments is None:
                raise PermissionDenied

            # Have dictionary storing total assignments per user
            user_total_assignments = {}

            # Gets the grades for each assignment, will be editing this to accomodate a flat grading system
            grades = group_flattened.get("grade_list.grades", [])
            if grades is None:
                raise PermissionDenied

            user_scores = {}

            # Add scores for each assignment to user_id, converts them into a percentage.
            for assignment in assignments:
                assignment_flattened = self._flatten_dict(assignment)

                published = assignment_flattened.get("published", True)
                grading_type = assignment_flattened.get("gradingType", None)
                omit_from_final_grade = assignment_flattened.get(
                    "omitFromFinalGrade", False
                )
                not_empty = assignment_flattened.get("submission_list.submissions")
                if (
                    published is False
                    or grading_type == "not_graded"
                    or omit_from_final_grade
                    or not not_empty
                ):  # filter out unpublished assignments
                    continue

                max_score = assignment_flattened.get("max_score", None)
                submissions = assignment_flattened.get(
                    "submission_list.submissions", None
                )

                # If no submissions of max_score == 0, skip assignment and do not factor it into grade
                if max_score == 0 or max_score is None or submissions is None:
                    continue

                assignment_id = assignment["_id"]

                for submission in submissions:
                    score = submission["score"]
                    user_id = submission["user_id"]
                    if user_id is None or score is None:
                        raise PermissionDenied

                    flat_score = score / max_score if max_score else 0
                    if rules:
                        if user_id not in user_scores:
                            user_scores[user_id] = []
                        user_scores[user_id].append({assignment_id: flat_score})
                    else:
                        user_scores[user_id] = user_scores.get(user_id, 0) + flat_score

                    if user_id not in user_total_assignments:
                        user_total_assignments[user_id] = 0
                    user_total_assignments[user_id] += 1

            # If no rules, skip extra processing

            # user_drop_status is a dictionary of user ids, and the number of dropped assignments for that user
            user_drop_status = {}

            if rules:
                user_scores = self.calculate_user_scores(
                    user_scores, rules, user_drop_status
                )
                user_total_assignments = {
                    k: v - user_drop_status[k]
                    for k, v in user_total_assignments.items()
                }

            # Once group scores are calculated, update assignment grades
            updated_grades = []
            for grade in grades:
                grade_flattened = self._flatten_dict(grade)
                user_id = grade_flattened.get("enrollment.user.user_id", None)
                enrollment_id = grade_flattened.get("enrollment._id", None)
                if user_id is None:
                    raise PermissionDenied
                user_enrollment_dict[user_id] = enrollment_id

                if user_id in user_scores:
                    # Calculate the average score and convert it to percentage
                    flat_group_score = (
                        # perhaps here, loop through all assignments and count number of assignments without submission
                        (user_scores[user_id] / user_total_assignments[user_id]) * 100
                        if user_total_assignments[user_id]
                        else 0
                    )
                    # updated_grades.append((user_id, round_half_up(flat_group_score, 3)))
                    updated_grades.append((user_id, flat_group_score))
                else:
                    # Keep the original score if no submissions were found
                    score = grade_flattened["current_score"]
                    updated_grades.append((user_id, score))

            group_data["grade_list"]["grades"] = updated_grades
            group_data.pop(
                "assignment_list", None
            )  # Remove assignment list as requested

        return group_dict, user_enrollment_dict

    def _flatten_dict_gen(self, d, parent_key, sep):
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, MutableMapping):
                yield from self._flatten_dict(v, new_key, sep=sep).items()
            else:
                yield new_key, v

    def _flatten_dict(self, d: MutableMapping, parent_key: str = "", sep: str = "."):
        return dict(self._flatten_dict_gen(d, parent_key, sep))
