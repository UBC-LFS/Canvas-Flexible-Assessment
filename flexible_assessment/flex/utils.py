from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from .models import Assessment, Course, Roles, UserCourse, UserProfile


def set_user_profile(request, user_id, login_id, display_name, role):
    user_set = UserProfile.objects.filter(pk=user_id)
    if not user_set.exists():
        user = UserProfile.objects.create_user(
            user_id, login_id, display_name, role)
    else:
        user = user_set.first()
    request.session['user_id'] = user.user_id
    request.session['login_id'] = user.login_id
    request.session['display_name'] = user.display_name
    request.session['role'] = user.role
    return user


def set_course(request, course_id, course_name):
    course_set = Course.objects.filter(pk=course_id)
    if not course_set.exists():
        course = Course(id=course_id, title=course_name)
        course.save()
    else:
        course = course_set.first()
    # TODO: check request.session['course_id'] for when adding assessments
    request.session['course_id'] = course.id
    request.session['course_name'] = course.title
    return course


def set_user_course_enrollment(user, course):
    user_course_set = UserCourse.objects.filter(
        user_id=user.user_id, course_id=course.id)
    if not user_course_set.exists():
        user_course = UserCourse(user=user, course=course)
        user_course.save()


def set_user_course(request, custom_fields, role):
    user_id = custom_fields['user_id']
    login_id = custom_fields['login_id']
    display_name = custom_fields['user_display_name']
    course_id = custom_fields['course_id']
    course_name = custom_fields['course_name']

    user = set_user_profile(request, user_id, login_id, display_name, role)
    course = set_course(request, course_id, course_name)

    set_user_course_enrollment(user, course)
    set_user_group(user)


def set_user_group(user):
    if not user.groups.all():
        roles = dict(Roles.choices)
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

    assessment_content_type = ContentType.objects.get_for_model(Assessment)
    assessment_perm_set = Permission.objects.filter(
        content_type=assessment_content_type)
    course_content_type = ContentType.objects.get_for_model(Course)
    course_perm_set = Permission.objects.filter(
        content_type=course_content_type)

    assessment_course_perm_set = assessment_perm_set | course_perm_set

    student_group = Group.objects.filter(name='Student')
    student_assessment_perm_set = Permission.objects.filter(
        codename__in=['change_assessment', 'view_assessment'],
        content_type=assessment_content_type)

    add_permissions_helper(
        teacher_admin_groups,
        assessment_course_perm_set)
    add_permissions_helper(student_group, student_assessment_perm_set)


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
    return user.groups.filter(name__in=['Teacher', 'Admin']).exists()


def is_student(user):
    return user.groups.filter(name='Student').exists()
