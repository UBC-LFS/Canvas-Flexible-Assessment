from collections.abc import MutableMapping
from canvasapi import Canvas
from django.conf import settings

from oauth.oauth import get_oauth_token

import flexible_assessment.models as models

def update_students(request, course):
    access_token = get_oauth_token(request)
    students_canvas = Canvas(settings.CANVAS_DOMAIN, access_token).get_course(course.id).get_users(enrollment_type='student')
    students_db = models.UserProfile.objects.filter(role=models.Roles.STUDENT)

    students_canvas_ids = [student.__getattribute__('id') for student in students_canvas]
    students_db_ids = [student.user_id for student in students_db]

    students_to_add = list(filter(lambda student: student.__getattribute__('id') not in students_db_ids, students_canvas))
    students_to_delete = students_db.exclude(user_id__in=students_canvas_ids)

    for student in students_to_add:
        canvas_fields = {}
        canvas_fields['user_id'] = student.__getattribute__('id')
        canvas_fields['login_id'] = student.__getattribute__('login_id')
        canvas_fields['user_display_name'] = student.__getattribute__('name')
        canvas_fields['course_id'] = course.id
        canvas_fields['course_name'] = course.title
        set_user_course(canvas_fields, models.Roles.STUDENT)
    
    students_to_delete.delete()

def set_user_profile(user_id, login_id, display_name, role):
    user_set = models.UserProfile.objects.filter(pk=user_id)
    if not user_set.exists():
        user = models.UserProfile.objects.create_user(
            user_id, login_id, display_name, role)
    else:
        user = user_set.first()
    return user


def set_course(course_id, course_name):
    course_set = models.Course.objects.filter(pk=course_id)
    if not course_set.exists():
        course = models.Course(id=course_id, title=course_name)
        course.save()
    else:
        course = course_set.first()
    return course


def set_user_course_enrollment(user, course):
    user_course_set = models.UserCourse.objects.filter(
        user_id=user.user_id, course_id=course.id)
    if not user_course_set.exists():
        user_course = models.UserCourse(user=user, course=course)
        user_course.save()


def set_user_course(canvas_fields, role):
    user_id = canvas_fields['user_id']
    login_id = canvas_fields['login_id']
    display_name = canvas_fields['user_display_name']
    course_id = canvas_fields['course_id']
    course_name = canvas_fields['course_name']

    user = set_user_profile(user_id, login_id, display_name, role)
    course = set_course(course_id, course_name)

    set_user_course_enrollment(user, course)
    set_user_comment(user, course)


def set_user_comment(user, course):
    if not user.usercomment_set.filter(
            course__id=course.id).exists() and user.role == models.Roles.STUDENT:
        user_comment = models.UserComment(user=user, course=course)
        user_comment.save()


def _flatten_dict_gen(d, parent_key, sep):
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            yield from flatten_dict(v, new_key, sep=sep).items()
        else:
            yield new_key, v


def flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '.'):
    return dict(_flatten_dict_gen(d, parent_key, sep))
