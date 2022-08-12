import logging
import pprint

from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from pylti1p3.contrib.django import DjangoMessageLaunch, DjangoOIDCLogin

from . import auth, lti, models, utils

logger = logging.getLogger(__name__)


def login(request):
    tool_conf = lti.get_tool_conf()
    launch_data_storage = lti.get_launch_data_storage()

    oidc_login = DjangoOIDCLogin(
        request,
        tool_conf,
        launch_data_storage=launch_data_storage)
    target_link_uri = lti.get_launch_url(request)
    return oidc_login.enable_check_cookies().redirect(target_link_uri)


@require_POST
def launch(request):
    tool_conf = lti.get_tool_conf()
    launch_data_storage = lti.get_launch_data_storage()
    message_launch = DjangoMessageLaunch(
        request, tool_conf, launch_data_storage=launch_data_storage)
    message_launch_data = message_launch.get_launch_data()
    pprint.pprint(message_launch_data)

    canvas_fields = message_launch_data['https://purl.imsglobal.org'
                                        '/spec/lti/claim/custom']
    course_id = canvas_fields['course_id']

    if 'TeacherEnrollment' in canvas_fields['role']:
        utils.set_user_course(canvas_fields, models.Roles.TEACHER)
        auth.authenticate_login(request, canvas_fields)
        logger.info('Instructor login',
                    extra={'course': canvas_fields['course_name'],
                           'user': canvas_fields['user_display_name']})
        return HttpResponseRedirect(
            reverse('instructor:instructor_home',
                    kwargs={'course_id': course_id}) + '?login_redirect=True')

    elif 'TaEnrollment' in canvas_fields['role']:
        utils.set_user_course(canvas_fields, models.Roles.TA)
        auth.authenticate_login(request, canvas_fields)
        logger.info('TA login',
                    extra={'course': canvas_fields['course_name'],
                           'user': canvas_fields['user_display_name']})
        return HttpResponseRedirect(
            reverse('instructor:instructor_home',
                    kwargs={'course_id': course_id}) + '?login_redirect=True')

    elif 'StudentEnrollment' in canvas_fields['role']:
        utils.set_user_course(canvas_fields, models.Roles.STUDENT)
        auth.authenticate_login(request, canvas_fields)
        logger.info('Student login',
                    extra={'course': canvas_fields['course_name'],
                           'user': canvas_fields['user_display_name']})
        return HttpResponseRedirect(
            reverse('student:student_home',
                    kwargs={'course_id': course_id}))


def get_jwks(request):
    tool_conf = utils.get_tool_conf()
    return JsonResponse(tool_conf.get_jwks(), safe=False)
