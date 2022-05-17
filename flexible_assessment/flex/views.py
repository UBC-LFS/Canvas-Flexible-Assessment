import pprint

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.forms import ValidationError
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from pylti1p3.contrib.django import DjangoMessageLaunch, DjangoOIDCLogin

import flex.auth as auth
import flex.lti as lti
import flex.models as models
import flex.utils as utils

from .forms import AddAssessmentForm, DateForm


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

    # utils.add_permissions()

    # TODO: TAEnrollement view
    if 'TeacherEnrollment' in custom_fields['role']:
        utils.set_user_course(request, custom_fields, models.Roles.TEACHER)
        auth.authenticate_login(request)
        return HttpResponseRedirect(reverse('flex:instructor_home'))

    elif 'StudentEnrollment' in custom_fields['role']:
        utils.set_user_course(request, custom_fields, models.Roles.STUDENT)
        auth.authenticate_login(request)
        return HttpResponseRedirect(reverse('flex:student_home'))


def get_jwks(request):
    tool_conf = utils.get_tool_conf()
    return JsonResponse(tool_conf.get_jwks(), safe=False)


@login_required
@user_passes_test(utils.is_student)
def student_home(request):
    return render(request, 'flex/student/student_home.html')


@login_required
@user_passes_test(utils.is_teacher_admin)
def instructor_home(request):
    return render(request, 'flex/instructor/instructor_home.html')


class AssessmentCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = models.Assessment
    form_class = AddAssessmentForm
    template_name = 'flex/assessment/assessment_form.html'
    success_url = reverse_lazy('flex:instructor_list')

    def form_valid(self, form):
        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)

        assessments = course.assessment_set.all()
        assessment_default_sum = sum([assessment.default for assessment in assessments])

        if form.cleaned_data['default'] + assessment_default_sum > 100.0:
            form.add_error('default', ValidationError(
                'Default assessment allocations add up to over 100%'))
            response = super(AssessmentCreate, self).form_invalid(form)
            return response

        assessment = form.save(commit=False)
        assessment.course = course
        response = super(AssessmentCreate, self).form_valid(form)

        assessment_id = self.object.id
        assessment = models.Assessment.objects.get(pk=assessment_id)

        user_courses = course.usercourse_set.all()
        users = [user_course.user for user_course in user_courses]
        flex_assessments = [
            models.FlexAssessment(
                user=user,
                assessment=assessment) for user in users if user.role == models.Roles.STUDENT]
        models.FlexAssessment.objects.bulk_create(flex_assessments)

        return response

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class AssessmentUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.Assessment
    form_class = AddAssessmentForm
    template_name = 'flex/assessment/assessment_form.html'
    success_url = reverse_lazy('flex:instructor_list')

    def form_valid(self, form):
        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)

        assessments = course.assessment_set.all()
        assessment_default_sum = sum(
            [assessment.default for assessment in assessments if assessment.id != self.object.id])

        if form.cleaned_data['default'] + assessment_default_sum > 100.0:
            form.add_error('default', ValidationError(
                'Default assessment allocations add up to over 100%'))
            response = super(AssessmentUpdate, self).form_invalid(form)
            return response

        response = super(AssessmentUpdate, self).form_valid(form)

        return response

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class AssessmentDelete(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = models.Assessment
    template_name = 'flex/assessment/assessment_confirm_delete.html'
    success_url = reverse_lazy('flex:instructor_list')

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class DateUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.Course
    template_name = 'flex/date_form.html'
    form_class = DateForm
    success_url = reverse_lazy('flex:instructor_list')

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class InstructorListView(
        LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    model = models.Assessment
    context_object_name = 'assessment_list'
    template_name = 'flex/instructor/instructor_list.html'
    raise_exception = True

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        course_id = self.request.session.get('course_id', '')
        if not user_id:
            raise PermissionDenied
        return models.Assessment.objects.filter(course__id=course_id)

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class InstructorAssessmentDetailView(
        LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    model = models.Assessment
    template_name = 'flex/assessment/assessment_detail.html'
    raise_exception = True

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class StudentListView(
        LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    model = models.FlexAssessment
    context_object_name = 'flex_list'
    template_name = 'flex/student/student_list.html'
    raise_exception = True

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        course_id = self.request.session.get('course_id', '')
        if not (user_id and course_id):
            raise PermissionDenied
        return models.FlexAssessment.objects.filter(
            user__user_id=user_id,
            assessment__course_id=course_id)

    def test_func(self):
        return utils.is_teacher_admin(
            self.request.user) or utils.is_student(self.request.user)


class FlexAssessmentUpdate(
        LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.FlexAssessment
    # form_class = FlexForm
    fields = ['flex']
    template_name = 'flex/flex_assessment_form.html'
    success_url = reverse_lazy('flex:student_list')

    def form_valid(self, form):
        user_id = self.request.session['user_id']
        user = models.UserProfile.objects.get(pk=user_id)

        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)

        def flex_filter(flex_assessment):
            assessment = flex_assessment.assessment
            flex_course = assessment.course
            form_flex_assessment_id = self.object.id

            return flex_assessment and flex_course == course and flex_assessment.id != form_flex_assessment_id

        user_flex_assessments = user.flexassessment_set.all()
        flex_assessments = list(filter(flex_filter, user_flex_assessments))
        flex_allocations = [fa.flex for fa in flex_assessments]
        flex_sum = sum(flex_allocations)

        if form.cleaned_data['flex'] + flex_sum > 100.0:
            form.add_error('default', ValidationError(
                'Flex assessment allocations add up to over 100%'))
            response = super(FlexAssessmentUpdate, self).form_invalid(form)
            return response

        response = super(FlexAssessmentUpdate, self).form_valid(form)

        return response

    def test_func(self):
        return utils.is_teacher_admin(
            self.request.user) or utils.is_student(self.request.user)
