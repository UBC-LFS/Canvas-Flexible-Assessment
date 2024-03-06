import time
from collections.abc import MutableMapping

from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from django.conf import settings
from django.core.exceptions import PermissionDenied
from oauth.oauth import get_oauth_token


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
        super().__init__(base_url, access_token)

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
        assignment_list assignmentsConnection {
          assignments: nodes {
            assignment_name: name
            assignment_grade_list: submissionsConnection {
              assignment_grades: nodes {
                score
                user_id: userId
              }
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

    def _flatten_dict_gen(self, d, parent_key, sep):
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, MutableMapping):
                yield from self._flatten_dict(v, new_key, sep=sep).items()
            else:
                yield new_key, v

    def _flatten_dict(self, d: MutableMapping, parent_key: str = "", sep: str = "."):
        return dict(self._flatten_dict_gen(d, parent_key, sep))
