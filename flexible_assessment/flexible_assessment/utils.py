from collections.abc import MutableMapping
from canvasapi import Canvas
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

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
    set_user_group(user)


def set_user_comment(user, course):
    if not user.usercomment_set.filter(
            course__id=course.id).exists() and user.role == models.Roles.STUDENT:
        user_comment = models.UserComment(user=user, course=course)
        user_comment.save()


def set_user_group(user):
    if not user.groups.all():
        roles = dict(models.Roles.choices)
        role = roles[user.role]
        group = Group.objects.get(name=role)
        user.groups.add(group)


def create_groups(sender, **kwargs):
    from django.contrib.auth.models import Group

    from .models import Roles

    current_role_names = list(
        Group.objects.all().values_list('name', flat=True))

    role_names = list(dict(Roles.choices).values())

    if role_names != current_role_names:
        groups = [Group(name=role) for role in role_names]
        Group.objects.bulk_create(groups)


def add_permissions():
    teacher_admin_groups = Group.objects.filter(
        name='Admin') | Group.objects.filter(
        name='Teacher')

    assessment_content_type = ContentType.objects.get_for_model(models.Assessment)
    assessment_perm_set = Permission.objects.filter(
        content_type=assessment_content_type)
    course_content_type = ContentType.objects.get_for_model(models.Course)
    course_perm_set = Permission.objects.filter(
        content_type=course_content_type)

    assessment_course_perm_set = assessment_perm_set | course_perm_set

    student_group = Group.objects.filter(name='Student')
    flex_assessment_content_type = ContentType.objects.get_for_model(
        models.FlexAssessment)
    student_flex_perm_set = Permission.objects.filter(
        codename__in=['change_flexassessment', 'view_flexassessment'],
        content_type=flex_assessment_content_type)

    add_permissions_helper(
        teacher_admin_groups,
        assessment_course_perm_set)
    add_permissions_helper(student_group, student_flex_perm_set)


def add_permissions_helper(groups, permissions_set):
    for group in groups:
        current_perms = list(
            group.permissions.all().values_list(
                'id', flat=True))
        perms = list(
            permissions_set.values_list(
                'id', flat=True))
        current_perms.sort()
        perms.sort()
        if current_perms != perms:
            group.permissions.add(*perms)


def is_teacher_admin(user):
    return user.groups.filter(name__in=['Teacher', 'Admin', 'Ta']).exists()


def is_student(user):
    return user.groups.filter(name='Student').exists()


def _flatten_dict_gen(d, parent_key, sep):
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            yield from flatten_dict(v, new_key, sep=sep).items()
        else:
            yield new_key, v


def flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '.'):
    return dict(_flatten_dict_gen(d, parent_key, sep))
