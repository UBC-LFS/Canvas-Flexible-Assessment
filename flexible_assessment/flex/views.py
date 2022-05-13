import pprint

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from pylti1p3.contrib.django import DjangoMessageLaunch, DjangoOIDCLogin

import flex.auth as auth
import flex.lti as lti
import flex.models as models
import flex.utils as utils

from django.views import generic


def index(request):
    return HttpResponse('Home page')


def login(request):
    tool_conf = lti.get_tool_conf()
    launch_data_storage = lti.get_launch_data_storage()
    pprint.pprint(request)

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

    custom_fields = message_launch_data['https://purl.imsglobal.org/spec/lti/claim/custom']

    utils.add_permissions()

    # TODO: TAEnrollement view
    if 'TeacherEnrollment' in custom_fields['role']:
        utils.set_user_course(request, custom_fields, models.Roles.TEACHER)
        auth.authenticate_login(request)
        return HttpResponseRedirect(reverse('flex:instructor_home'))

    elif 'StudentEnrollment' in custom_fields['role']:
        utils.set_user_course(request, custom_fields, models.Roles.STUDENT)
        auth.authenticate_login(request)
        return HttpResponseRedirect(reverse('flex:student_view'))


def get_jwks(request):
    tool_conf = utils.get_tool_conf()
    return JsonResponse(tool_conf.get_jwks(), safe=False)


@login_required
@user_passes_test(utils.is_student)
def student(request):
    response_string = 'Student Page, your user id: {} and name: {}'
    user_id = request.session.get('user_id', '')
    display_name = request.session.get('display_name', '')
    if not user_id:
        raise Http404

    return HttpResponse(response_string.format(user_id, display_name))


def instructor_home(request):
    return render(request, 'flex/instructor_home.html')


def add_assessment(request):
    return HttpResponse('Add Assessment Page')


class InstructorListView(
        LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    model = models.Assessment
    context_object_name = 'assessment_list'
    template_name = 'flex/instructor_list.html'
    raise_exception = True

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        if not user_id:
            raise PermissionDenied
        return models.Assessment.objects.filter(
            assessmentcourse__course__id=self.request.session['course_id'])

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)
