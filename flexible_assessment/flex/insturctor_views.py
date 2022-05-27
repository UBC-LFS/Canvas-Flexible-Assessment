import os

from canvasapi import Canvas
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.forms import ValidationError
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView

import flex.models as models
import flex.utils as utils

from .forms import (AddAssessmentForm, AssessmentGroupForm, DateForm,
                    UpdateAssessmentForm)

CANVAS_API_URL = os.getenv('CANVAS_API_URL')
CANVAS_API_KEY = os.getenv('CANVAS_API_KEY')


class AssessmentCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Extends Django CreateView and authentication mixins for creating assessments.
    Uses AddAssessmentForm as form_class, redirects to instructor assessment page on success.
    """

    # TODO: Create assignment group on Canvas if one doesn't already exist

    model = models.Assessment
    form_class = AddAssessmentForm
    template_name = 'flex/assessment/assessment_form.html'
    success_url = reverse_lazy('flex:instructor_list')

    def get_context_data(self, **kwargs):
        """Adds assessment allocation sum and remainder for UI and allocation total check.

        Returns
        -------
            context : context
                Contains context data for request
        """

        context = super(AssessmentCreate, self).get_context_data(**kwargs)

        assessment_default_sum = self._get_assessment_sum()
        context['default_sum'] = assessment_default_sum
        context['default_remainder'] = 100 - assessment_default_sum

        return context

    def form_valid(self, form):
        """Validates allocation total and creates flex assessment for current assessment

        Parameters
        ----------
            form : form
                Contains Django form fields and submitted field data

        Returns
        -------
            response : Union[HttpResponseRedirect, TemplateResponse]
                HttpResponseRedirect if form is valid, TemplateResponse if invalid form
        """

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
        """Gets sum of default allocations for assessments"""

        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)
        assessments = course.assessment_set.all()

        return sum([assessment.default for assessment in assessments])

    def _check_allocation_total(self, form, assessment_default_sum):
        """Checks if default allocations add up over 100%"""

        if form.cleaned_data['default'] + assessment_default_sum > 100.0:
            form.add_error('default', ValidationError(
                'Default assessment allocations add up to over 100%'))
            response = super(AssessmentCreate, self).form_invalid(form)
            return response
        else:
            return None

    def _set_flex_assessments(self, course, assessment):
        """Creates flex assessment objects for new assessment"""

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
    """Extends Django UpdateView and authentication mixins for updating assessments.
    Uses UpdateAssessmentForm as form_class, redirects to instructor assessment page on success.
    """

    model = models.Assessment
    form_class = UpdateAssessmentForm
    template_name = 'flex/assessment/assessment_form.html'
    success_url = reverse_lazy('flex:instructor_list')

    def get_context_data(self, **kwargs):
        """Adds assessment allocation sum and remainder for UI and allocation total check.

        Returns
        -------
            context : context
                Contains context data for request
        """

        context = super(AssessmentUpdate, self).get_context_data(**kwargs)

        assessment_default_sum = self._get_assessment_sum()
        context['default_sum'] = assessment_default_sum
        context['default_remainder'] = 100 - assessment_default_sum

        return context

    def form_valid(self, form):
        """Validates allocation total and changes flex assessment for related assessment
        if flex is not within max and min.

        Parameters
        ----------
            form : form
                Contains Django form fields and submitted field data

        Returns
        -------
            response : Union[HttpResponseRedirect, TemplateResponse]
                HttpResponseRedirect if form is valid, TemplateResponse if error in form
        """

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
        """Gets sum of default allocations for all other assessments"""

        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)

        assessments = course.assessment_set.all()
        return sum(
            [assessment.default for assessment in assessments if assessment.id != self.object.id])

    def _check_allocation_total(self, form, assessment_default_sum):
        """Checks if default allocations add up over 100%"""

        if form.cleaned_data['default'] + assessment_default_sum > 100.0:
            form.add_error('default', ValidationError(
                'Default assessment allocations add up to over 100%'))
            response = super(AssessmentUpdate, self).form_invalid(form)
            return response
        else:
            return None

    def _handle_flex_out_of_range(self, form):
        """Checks for and handles flex assessments with flex out of range of max and min.
        If reset flex is checked in the form then out of bound flex is reset to None,
        otherwise invalid response returned.
        """

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
    """Extends Django DeleteView and authentication mixins for deleting assessments.
    Redirects to instructor assessment page on success.
    """

    model = models.Assessment
    template_name = 'flex/assessment/assessment_confirm_delete.html'
    success_url = reverse_lazy('flex:instructor_list')

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class DateUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Extends Django UpdateView and authentication mixins for changing flex deadline.
    Uses DateForm as form_class. Redirects to instructor assessment page on success.
    """

    model = models.Course
    template_name = 'flex/date_form.html'
    form_class = DateForm
    success_url = reverse_lazy('flex:instructor_list')

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class InstructorListView(
        LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    """Extends Django generic ListView and authentication mixins for listing assessments added"""

    model = models.Assessment
    context_object_name = 'assessment_list'
    template_name = 'flex/instructor/instructor_list.html'
    raise_exception = True
    paginate_by = 10

    def get_queryset(self):
        """QuerySet is assessments objects for current course"""

        user_id = self.request.session.get('user_id', '')
        course_id = self.request.session.get('course_id', '')
        if not user_id:
            raise PermissionDenied
        return models.Assessment.objects.filter(course__id=course_id)

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class FlexAssessmentListView(
        LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    """Extends Django generic ListView and authentication mixins for
    listing student flex allocations
    """

    model = models.UserProfile
    context_object_name = 'student_list'
    template_name = 'flex/instructor/percentage_list.html'
    raise_exception = True
    paginate_by = 10

    def get_queryset(self):
        """QuerySet is students for current course"""

        user_id = self.request.session.get('user_id', '')
        course_id = self.request.session.get('course_id', '')
        if not user_id:
            raise PermissionDenied
        return models.UserProfile.objects.filter(
            role=models.Roles.STUDENT, usercourse__course__id=course_id)

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class FinalGradeListView(
        LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    model = models.UserProfile
    context_object_name = 'student_list'
    template_name = 'flex/instructor/final_grade_list.html'
    raise_exception = True
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super(FinalGradeListView, self).get_context_data(**kwargs)
        course_id = self.request.session.get('course_id', '')
        query = """query AssignmentGroupQuery($course_id: ID) {
  course(id: $course_id) {
    assignment_groups: assignmentGroupsConnection {
      groups: nodes {
        group_id: _id
        group_name: name
        group_weight: groupWeight
        grade_list: gradesConnection {
          grades: nodes {
            currentScore
            enrollment {
              user {
                user_id: _id
                display_name: name
              } } } } } } } }"""
        query_response = Canvas(
            CANVAS_API_URL, CANVAS_API_KEY).graphql(
            query, variables={
                "course_id": course_id})
        # TODO: Add KeyError handle
        groups = query_response['data']['course']['assignment_groups']['groups']
        group_dict = {}
        for group in groups:
            id = group['group_id']
            group.pop('group_id', None)
            group_dict[id] = group

        for group_data in group_dict.values():
            grades = group_data['grade_list']['grades']
            updated_grades = []
            for grade in grades:
                user_id = grade['enrollment']['user']['user_id']
                score = grade['currentScore']
                updated_grades.append((user_id, score))
            group_data['grade_list']['grades'] = updated_grades

        context['groups'] = group_dict
        return context

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
    """Extends Django generic DetailView and authentication mixins for
    viewing assessment details
    """

    model = models.Assessment
    template_name = 'flex/assessment/assessment_detail.html'
    raise_exception = True

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


class AssessmentGroupView(
        LoginRequiredMixin, UserPassesTestMixin, generic.FormView):
    """Extends Django generic FormView and authentication mixins for
    matching assessments in the app to assignment groups on Canvas
    """

    template_name = 'flex/instructor/assessment_group_form.html'
    form_class = AssessmentGroupForm
    raise_exception = True
    success_url = reverse_lazy('flex:final_grades')

    def get_form_kwargs(self):
        """Adds course_id and assessment as keyword arguments for making form fields

        Returns
        -------
            kwargs : kwargs
                Form keyword arguments
        """

        kwargs = super(AssessmentGroupView, self).get_form_kwargs()
        course_id = self.request.session.get('course_id', '')
        kwargs['course_id'] = course_id
        kwargs['assessments'] = models.Assessment.objects.filter(
            course_id=course_id)

        return kwargs

    def form_valid(self, form):
        """Validates matched groups are unique and adds AssignmentGroup as Foreign Key to Assessment

        Parameters
        ----------
            form : form
                Contains Django form fields and submitted field data

        Returns
        -------
            response : Union[HttpResponseRedirect, TemplateResponse]
                HttpResponseRedirect if form is valid, TemplateResponse if error in form
        """

        matched_groups = form.cleaned_data.values()
        matched_groups_unique = len(set(matched_groups)) == len(matched_groups)
        if not matched_groups_unique:
            form.add_error(None, ValidationError(
                'Matched groups must be unique'))
            response = super(AssessmentGroupView, self).form_invalid(form)
            return response

        for id, group in form.cleaned_data.items():
            assessment = models.Assessment.objects.filter(pk=id).first()
            assessment.group = group
            assessment.save()

        response = super(AssessmentGroupView, self).form_valid(form)
        return response

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)
