import os

from canvasapi import Canvas
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.forms import BaseModelFormSet, ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic

import flex.models as models
import flex.utils as utils

from .forms import (AssessmentFormSet, AssessmentGroupForm,
                    DateForm, StudentBaseForm, StudentForm)

CANVAS_API_URL = os.getenv('CANVAS_API_URL')
CANVAS_API_KEY = os.getenv('CANVAS_API_KEY')


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


class InstructorFormView(
        LoginRequiredMixin, UserPassesTestMixin, generic.FormView):
    template_name = 'flex/instructor/instructor_form.html'
    form_class = BaseModelFormSet
    raise_exception = True
    success_url = reverse_lazy('flex:instructor_home')

    def get_context_data(self, **kwargs):
        context = super(InstructorFormView, self).get_context_data(**kwargs)
        course_id = self.request.session.get('course_id', None)

        if self.request.POST:
            context['date_form'] = DateForm(
                self.request.POST, instance=models.Course.objects.get(
                    pk=course_id), prefix='date')
            context['formset'] = AssessmentFormSet(
                self.request.POST, prefix='assessment')
        else:
            context['date_form'] = DateForm(
                instance=models.Course.objects.get(
                    pk=course_id), prefix='date')
            context['formset'] = AssessmentFormSet(
                queryset=models.Assessment.objects.filter(
                    course_id=course_id), prefix='assessment')

        return context

    def post(self, request, *args, **kwargs):
        course_id = request.session.get('course_id', None)
        date_form = DateForm(
            request.POST,
            instance=models.Course.objects.get(
                pk=course_id),
            prefix='date')

        formset = AssessmentFormSet(request.POST, prefix='assessment')

        if formset.is_valid() and date_form.is_valid():
            return self.forms_valid(formset, date_form)
        elif not formset.is_valid():
            print(formset.errors)
            return self.form_invalid(formset)
        else:
            return self.form_invalid(date_form)

    def forms_valid(self, formset, date_form):
        date_form.save()

        formset.clean()

        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)

        assessment_ids = []
        for form in formset.forms:
            assessment = form.save(commit=False)
            assessment.course = course
            assessment.save()
            self._set_flex_assessments(course, assessment)
            assessment_ids.append(assessment.id)

        to_delete = course.assessment_set.all().exclude(id__in=assessment_ids)
        to_delete.delete()

        response = HttpResponseRedirect(self.get_success_url())

        return response

    def _set_flex_assessments(self, course, assessment):
        """Creates flex assessment objects for new assessments"""

        user_courses = course.usercourse_set.filter(
            user__role=models.Roles.STUDENT)
        users = [user_course.user for user_course in user_courses]
        flex_assessments = [
            models.FlexAssessment(user=user, assessment=assessment)
            for user in users
            if not models.FlexAssessment.objects.filter(user=user, assessment=assessment).exists()]
        models.FlexAssessment.objects.bulk_create(flex_assessments)

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)


# TODO: Create helpers for student form and override student form
class OverrideStudentFormView(
        LoginRequiredMixin, UserPassesTestMixin, generic.FormView):
    template_name = 'flex/instructor/override_student_form.html'
    form_class = StudentBaseForm
    raise_exception = True
    success_url = reverse_lazy('flex:percentage_list')

    def get_context_data(self, **kwargs):
        context = super(
            OverrideStudentFormView,
            self).get_context_data(
            **kwargs)
        student_name = models.UserProfile.objects.get(
            pk=self.kwargs['pk']).display_name
        context['student_name'] = student_name
        return context

    def get_form_kwargs(self):
        """Adds course_id as keyword arguments for making form fields

        Returns
        -------
            kwargs : kwargs
                Form keyword arguments
        """
        kwargs = super(OverrideStudentFormView, self).get_form_kwargs()
        user_id = self.kwargs['pk']
        course_id = self.request.session.get('course_id', '')

        if not user_id or not course_id:
            raise PermissionDenied

        kwargs['user_id'] = user_id
        kwargs['course_id'] = course_id

        return kwargs

    def form_valid(self, form):
        user_id = self.kwargs['pk']
        course_id = self.request.session.get('course_id', '')

        if not user_id or not course_id:
            raise PermissionDenied

        assessment_fields = list(form.cleaned_data.items())
        for assessment_id, flex in assessment_fields:
            assessment = models.Assessment.objects.get(pk=assessment_id)
            if flex > assessment.max:
                form.add_error(assessment_id, ValidationError(
                    'Flex should be less than or equal to max'))
            elif flex < assessment.min:
                form.add_error(assessment_id, ValidationError(
                    'Flex should be greater than or equal to min'))

        if form.errors:
            response = super(OverrideStudentFormView, self).form_invalid(form)
            return response

        for assessment_id, flex in assessment_fields:
            assessment = models.Assessment.objects.get(pk=assessment_id)
            flex_assessment = assessment.flexassessment_set.filter(
                user__user_id=user_id).first()
            flex_assessment.flex = flex
            flex_assessment.save()

        response = super(OverrideStudentFormView, self).form_valid(form)
        return response

    def test_func(self):
        return utils.is_teacher_admin(self.request.user)
