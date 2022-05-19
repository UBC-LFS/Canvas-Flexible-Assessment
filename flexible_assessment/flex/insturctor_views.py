from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.forms import ValidationError
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView

import flex.models as models
import flex.utils as utils

from .forms import AddAssessmentForm, DateForm, UpdateAssessmentForm


class AssessmentCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = models.Assessment
    form_class = AddAssessmentForm
    template_name = 'flex/assessment/assessment_form.html'
    success_url = reverse_lazy('flex:instructor_list')

    def get_context_data(self, **kwargs):
        context = super(AssessmentCreate, self).get_context_data(**kwargs)

        assessment_default_sum = self._get_assessment_sum()
        context['default_sum'] = assessment_default_sum
        context['default_remainder'] = 100 - assessment_default_sum
        context['reset_confirm'] = False

        return context

    def form_valid(self, form):
        assessment_default_sum = self.get_context_data().get('default_sum')

        error_response = self._check_allocation_total(
            form, assessment_default_sum)
        if error_response:
            return error_response

        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)

        assessment = form.save(commit=False)
        assessment.course = course
        response = super(AssessmentCreate, self).form_valid(form)

        assessment_id = self.object.id
        assessment = models.Assessment.objects.get(pk=assessment_id)

        self._set_flex_assessments(course, assessment)

        return response

    def _get_assessment_sum(self):
        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)
        assessments = course.assessment_set.all()
        return sum([assessment.default for assessment in assessments])

    def _check_allocation_total(self, form, assessment_default_sum):
        if form.cleaned_data['default'] + assessment_default_sum > 100.0:
            form.add_error('default', ValidationError(
                'Default assessment allocations add up to over 100%'))
            response = super(AssessmentCreate, self).form_invalid(form)
            return response
        else:
            return None

    def _set_flex_assessments(self, course, assessment):
        user_courses = course.usercourse_set.all()
        users = [user_course.user for user_course in user_courses]
        flex_assessments = [
            models.FlexAssessment(
                user=user,
                assessment=assessment) for user in users if user.role == models.Roles.STUDENT]
        models.FlexAssessment.objects.bulk_create(flex_assessments)

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class AssessmentUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.Assessment
    form_class = UpdateAssessmentForm
    template_name = 'flex/assessment/assessment_form.html'
    success_url = reverse_lazy('flex:instructor_list')

    def get_context_data(self, **kwargs):
        context = super(AssessmentUpdate, self).get_context_data(**kwargs)

        assessment_default_sum = self._get_assessment_sum()
        context['default_sum'] = assessment_default_sum
        context['default_remainder'] = 100 - assessment_default_sum

        return context

    def form_valid(self, form):
        assessment_default_sum = self.get_context_data().get('default_sum')

        allocation_response = self._check_allocation_total(
            form, assessment_default_sum)
        if allocation_response:
            return allocation_response

        flex_range_response = self._handle_flex_out_of_range(form)
        if flex_range_response:
            return flex_range_response

        response = super(AssessmentUpdate, self).form_valid(form)
        return response

    def _get_assessment_sum(self):
        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)

        assessments = course.assessment_set.all()
        return sum(
            [assessment.default for assessment in assessments if assessment.id != self.object.id])

    def _check_allocation_total(self, form, assessment_default_sum):
        if form.cleaned_data['default'] + assessment_default_sum > 100.0:
            form.add_error('default', ValidationError(
                'Default assessment allocations add up to over 100%'))
            response = super(AssessmentUpdate, self).form_invalid(form)
            return response
        else:
            return None

    def _handle_flex_out_of_range(self, form):
        new_min = form.cleaned_data.get('min', '')
        new_max = form.cleaned_data.get('max', '')
        assessment = models.Assessment.objects.get(pk=self.object.id)
        flex_assessments = assessment.flexassessment_set.all()

        def out_of_range_filter(flex_assessment):
            flex = flex_assessment.flex
            return flex and (flex < new_min or flex > new_max)

        invalid_flexes = list(filter(out_of_range_filter, flex_assessments))

        reset_flex = form.cleaned_data.get('reset_flex', False)
        if invalid_flexes and not reset_flex:
            if len(invalid_flexes) > 10:
                form.add_error(None, ValidationError(
                    'Warning: {} students have flex allocation out of new range '.format(len(invalid_flex))))
            else:
                for invalid_flex in invalid_flexes:
                    login_id = invalid_flex.user.login_id
                    display_name = invalid_flex.user.display_name
                    flex = invalid_flex.flex

                    form.add_error(None, ValidationError(
                        '{} ({}) has flex allocation out of range ({}%)'.format(display_name, login_id, flex)))

            response = super(AssessmentUpdate, self).form_invalid(form)
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
    paginate_by = 5

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        course_id = self.request.session.get('course_id', '')
        if not user_id:
            raise PermissionDenied
        return models.Assessment.objects.filter(course__id=course_id)

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class FlexAssessmentListView(
        LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    model = models.UserProfile
    context_object_name = 'student_list'
    template_name = 'flex/instructor/percentage_list.html'
    raise_exception = True
    paginate_by = 5

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        course_id = self.request.session.get('course_id', '')
        if not user_id:
            raise PermissionDenied
        return models.UserProfile.objects.filter(
            role=models.Roles.STUDENT, usercourse__course__id=course_id)

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class AssessmentDetailView(
        LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    model = models.Assessment
    template_name = 'flex/assessment/assessment_detail.html'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assessment = context['assessment']
        flex_assessments = list(
            filter(
                lambda fa: fa.flex,
                assessment.flexassessment_set.all()))
        context['response_count'] = len(flex_assessments)
        return context

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)
