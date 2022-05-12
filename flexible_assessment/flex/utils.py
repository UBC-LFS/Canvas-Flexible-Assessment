import os

from django.conf import settings
from pylti1p3.contrib.django import DjangoCacheDataStorage
from pylti1p3.tool_config import ToolConfJsonFile

from .models import Course, UserCourse, UserProfile


def set_user_profile(request, user_id, login_id, display_name, role):
    user_set = UserProfile.objects.filter(pk=user_id)
    if not user_set.exists():
        user = UserProfile.objects.create_user(user_id, login_id, display_name, role)
    else:
        user = user_set.first()
    request.session['user_id'] = user.user_id
    request.session['display_name'] = user.display_name
    return user


def set_course(course_id, course_name):
    course_set = Course.objects.filter(pk=course_id)
    if not course_set.exists():
        course = Course(id=course_id, title=course_name)
        course.save()
    else:
        course = course_set.first()
    # TODO: check request.session['course_id'] for when adding assessments
    return course


def set_user_course_enrollment(user, course):
    user_course_set = UserCourse.objects.filter(user_id = user.user_id, course_id = course.id)
    if not user_course_set.exists():
        user_course = UserCourse(user = user, course = course)
        user_course.save()


def set_user_course(request, custom_fields, role):
    user_id = custom_fields['user_id']
    login_id = custom_fields['login_id']
    display_name = custom_fields['user_display_name']
    course_id = custom_fields['course_id']
    course_name = custom_fields['course_name']

    user = set_user_profile(request, user_id, login_id, display_name, role)
    course = set_course(course_id, course_name)

    set_user_course_enrollment(user, course)


def get_launch_data_storage():
    return DjangoCacheDataStorage()


def get_launch_url(request):
    target_link_uri = request.POST.get('target_link_uri', request.GET.get('target_link_uri'))
    if not target_link_uri:
        raise Exception('Missing "target_link_uri" param')

    return target_link_uri


def get_lti_config_path():
    return os.path.join(settings.BASE_DIR, 'configs', 'flexible_assessment.json')


def get_tool_conf():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    return tool_conf
    