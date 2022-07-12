from collections.abc import MutableMapping
from django.core.exceptions import PermissionDenied
from canvasapi import Canvas
from django.conf import settings
from oauth.oauth import get_oauth_token
from canvasapi.exceptions import CanvasException
import time


class FlexCanvas(Canvas):
    def __init__(self, request):
        base_url = settings.CANVAS_DOMAIN
        access_token = get_oauth_token(request)
        super().__init__(base_url, access_token)

    def is_allow_override(self, course_id):
        query = """query AllowOverrideQuery($course_id: ID) {
                course(id: $course_id) {
                    allowFinalGradeOverride
                    } }"""
        query_response = self.graphql(query,
                                      variables={"course_id": course_id})

        return query_response['data']['course']['allowFinalGradeOverride']

    def set_override(self, enrollment_id, override, incomplete, attempt=1):
        mutation = """mutation OverrideFinalScore($enrollment_id: ID!, $override: Float) {
                    setOverrideScore(input: { enrollmentId: $enrollment_id,
                                              overrideScore: $override }) {
                        grades {
                            overrideScore
                            } } }"""
        try:
            if not incomplete[0]:
                self.graphql(mutation,
                             variables={"enrollment_id": enrollment_id,
                                        "override": override})
        except CanvasException:
            if attempt >= 5:
                time.sleep(1)
                self.set_override(enrollment_id,
                                  override,
                                  incomplete,
                                  attempt+1)
            else:
                incomplete[0] = True

    def get_groups_and_enrollments(self, course_id):
        query = """query AssignmentGroupQuery($course_id: ID) {
  course(id: $course_id) {
    assignment_groups: assignmentGroupsConnection {
      groups: nodes {
        group_id: _id
        group_name: name
        group_weight: groupWeight
        grade_list: gradesConnection {
          grades: nodes {
            currentScore
            enrollment {
              user {
                user_id: _id
                display_name: name
              }
              _id
            } } } } } } }"""

        query_response = self.graphql(
            query, variables={"course_id": course_id})

        query_flattened = self._flatten_dict(query_response)
        groups = query_flattened.get(
            'data.course.assignment_groups.groups', None)
        if groups is None:
            raise PermissionDenied

        group_dict = {}
        user_enrollment_dict = {}
        for group in groups:
            id = group['group_id']
            group.pop('group_id', None)
            group_dict[id] = group

        for group_data in group_dict.values():
            group_flattened = self._flatten_dict(group_data)
            grades = group_flattened.get('grade_list.grades', None)
            if grades is None:
                raise PermissionDenied

            updated_grades = []
            for grade in grades:
                grade_flattened = self._flatten_dict(grade)
                user_id = grade_flattened.get('enrollment.user.user_id', None)
                enrollment_id = grade_flattened.get('enrollment._id', None)
                if user_id is None:
                    raise PermissionDenied

                user_enrollment_dict[user_id] = enrollment_id

                score = grade_flattened['currentScore']
                updated_grades.append((user_id, score))

            group_data['grade_list']['grades'] = updated_grades

        return group_dict, user_enrollment_dict

    def _flatten_dict_gen(self, d, parent_key, sep):
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, MutableMapping):
                yield from self._flatten_dict(v, new_key, sep=sep).items()
            else:
                yield new_key, v

    def _flatten_dict(self, d: MutableMapping,
                      parent_key: str = '',
                      sep: str = '.'):
        return dict(self._flatten_dict_gen(d, parent_key, sep))
