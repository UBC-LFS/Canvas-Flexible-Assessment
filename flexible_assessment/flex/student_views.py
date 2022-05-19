from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.forms import ValidationError
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic.edit import UpdateView

import flex.models as models
import flex.utils as utils

from .forms import FlexForm


class StudentListView(
        LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    model = models.FlexAssessment
    context_object_name = 'flex_list'
    template_name = 'flex/student/student_list.html'
    raise_exception = True
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super(StudentListView, self).get_context_data(**kwargs)

        flex_sum = self._get_flex_sum()
        context['flex_remainder'] = 100 - flex_sum
        user_id = self.request.session['user_id']
        course_id = self.request.session['course_id']
        user_comment = models.UserComment.objects.filter(
            user__user_id=user_id, course__id=course_id).first()
        context['user_comment_id'] = user_comment.id
        context['comment'] = user_comment.comment

        return context

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        course_id = self.request.session.get('course_id', '')
        if not (user_id and course_id):
            raise PermissionDenied
        return models.FlexAssessment.objects.filter(
            user__user_id=user_id,
            assessment__course_id=course_id)

    def _get_flex_sum(self):
        user_id = self.request.session['user_id']
        course_id = self.request.session['course_id']

        user = models.UserProfile.objects.get(pk=user_id)
        course = models.Course.objects.get(pk=course_id)

        def flex_filter(flex_assessment):
            assessment = flex_assessment.assessment
            flex_course = assessment.course

            return flex_assessment.flex and flex_course == course

        user_flex_assessments = user.flexassessment_set.all()
        flex_assessments = list(filter(flex_filter, user_flex_assessments))
        flex_allocations = [
            flex_asessment.flex for flex_asessment in flex_assessments]

        return sum(flex_allocations)

    def test_func(self):
        return utils.is_teacher_admin(
            self.request.user) or utils.is_student(self.request.user)


class FlexAssessmentUpdate(
        LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.FlexAssessment
    form_class = FlexForm
    template_name = 'flex/flex_assessment_form.html'
    success_url = reverse_lazy('flex:student_list')

    def get_context_data(self, **kwargs):
        context = super(FlexAssessmentUpdate, self).get_context_data(**kwargs)

        flex_sum = self._get_flex_sum()
        context['flex_sum'] = flex_sum
        context['flex_remainder'] = 100 - flex_sum

        return context

    def form_valid(self, form):
        flex_sum = self.get_context_data().get('flex_sum', '')

        error_response = self._check_allocation_total(form, flex_sum)
        if error_response:
            return error_response

        self._flex_within_range(form)

        if form.has_error('flex'):
            response = super(FlexAssessmentUpdate, self).form_invalid(form)
            return response

        response = super(FlexAssessmentUpdate, self).form_valid(form)

        return response

    def _get_flex_sum(self):
        user_id = self.request.session['user_id']
        course_id = self.request.session['course_id']
        curr_flex_assessment_id = self.object.id

        user = models.UserProfile.objects.get(pk=user_id)
        course = models.Course.objects.get(pk=course_id)

        def flex_filter(flex_assessment):
            assessment = flex_assessment.assessment
            flex_course = assessment.course
            form_flex_assessment_id = curr_flex_assessment_id

            return flex_assessment.flex and flex_course == course and flex_assessment.id != form_flex_assessment_id

        user_flex_assessments = user.flexassessment_set.all()
        flex_assessments = list(filter(flex_filter, user_flex_assessments))
        flex_allocations = [
            flex_asessment.flex for flex_asessment in flex_assessments]

        return sum(flex_allocations)

    def _check_allocation_total(self, form, flex_sum):
        if flex_sum and form.cleaned_data['flex'] + flex_sum > 100.0:
            form.add_error('flex', ValidationError(
                'Flex assessment allocations add up to over 100%'))
            response = super(FlexAssessmentUpdate, self).form_invalid(form)
            return response
        else:
            return None

    def _flex_within_range(self, form):
        flex_assessment = models.FlexAssessment.objects.get(pk=self.object.id)
        assessment = flex_assessment.assessment
        print(form.cleaned_data)
        if form.cleaned_data['flex'] > assessment.max:
            form.add_error('flex', ValidationError(
                'Flex should be less than or equal to max'))
        elif form.cleaned_data['flex'] < assessment.min:
            form.add_error('flex', ValidationError(
                'Flex should be greater than or equal to min'))

    def test_func(self):
        return utils.is_teacher_admin(
            self.request.user) or utils.is_student(self.request.user)


class CommentUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = models.UserComment
    fields = ['comment']
    template_name = 'flex/student/student_comment.html'
    success_url = reverse_lazy('flex:student_list')

    def test_func(self):
        return utils.is_teacher_admin(
            self.request.user) or utils.is_student(self.request.user)
