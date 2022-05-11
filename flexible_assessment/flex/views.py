import pprint

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from pylti1p3.contrib.django import DjangoMessageLaunch, DjangoOIDCLogin

from .view_helpers import (get_launch_data_storage, get_launch_url,
                           get_lti_config_path, get_tool_conf,
                           set_user_profile)


def index(request):
    return HttpResponse('Home page')


def login(request):
    tool_conf = get_tool_conf()
    launch_data_storage = get_launch_data_storage()
    pprint.pprint(request)

    oidc_login = DjangoOIDCLogin(request, tool_conf, launch_data_storage=launch_data_storage)
    target_link_uri = get_launch_url(request)
    return oidc_login.enable_check_cookies().redirect(target_link_uri)


@require_POST
def launch(request):
    tool_conf = get_tool_conf()
    launch_data_storage = get_launch_data_storage()
    message_launch = DjangoMessageLaunch(request, tool_conf, launch_data_storage=launch_data_storage)
    message_launch_data = message_launch.get_launch_data()
    pprint.pprint(message_launch_data)

    custom_fields = message_launch_data['https://purl.imsglobal.org/spec/lti/claim/custom']

    # TODO: TAEnrollement view
    if 'TeacherEnrollment' in custom_fields['role']:
        set_user_profile(request, custom_fields, 'TeacherEnrollment')
        return HttpResponseRedirect(reverse('flex:instructor_view'))

    elif 'StudentEnrollment' in custom_fields['role']:
        set_user_profile(request, custom_fields, 'StudentEnrollment')
        return HttpResponseRedirect(reverse('flex:student_view'))


def get_jwks(request):
    tool_conf = get_tool_conf()
    return JsonResponse(tool_conf.get_jwks(), safe=False)


def instuctor(request):
    response_string = 'Instructor Page, your user id: {} and name: {}'
    user_id = request.session['user_id']
    display_name = request.session['display_name']

    return HttpResponse(response_string.format(user_id, display_name))


def student(request):
    response_string = 'Student Page, your user id: {} and name: {}'
    user_id = request.session['user_id']
    display_name = request.session['display_name']
    
    return HttpResponse(response_string.format(user_id, display_name))
