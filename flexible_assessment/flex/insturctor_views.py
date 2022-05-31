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

from .forms import (AddAssessmentForm, AssessmentFormSet, AssessmentGroupForm,
                    DateForm, UpdateAssessmentForm)

CANVAS_API_URL = os.getenv('CANVAS_API_URL')
CANVAS_API_KEY = os.getenv('CANVAS_API_KEY')


class DateUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Extends Django UpdateView and authentication mixins for changing flex deadline.
    Uses DateForm as form_class. Redirects to instructor assessment page on success.
    """

    model = models.Course
    template_name = 'flex/instructor/date_form.html'
    form_class = DateForm
    success_url = reverse_lazy('flex:instructor_form')

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
    form_class = AddAssessmentForm
    raise_exception = True
    success_url = reverse_lazy('flex:instructor_home')

    def get_context_data(self, **kwargs):
        context = super(InstructorFormView, self).get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = AssessmentFormSet(self.request.POST)
        else:
            course_id = self.request.session.get('course_id', None)
            context['formset'] = AssessmentFormSet(
                queryset=models.Assessment.objects.filter(
                    course_id=course_id))

        return context

    def post(self, request, *args, **kwargs):
        formset = AssessmentFormSet(request.POST)
        if formset.is_valid():
            return self.form_valid(formset)
        else:
            return self.form_invalid(formset)

    def form_valid(self, formset):
        course_id = self.request.session['course_id']
        course = models.Course.objects.get(pk=course_id)

        formset.clean()

        for form in formset.forms:
            assessment = form.save(commit=False)
            if form.cleaned_data.get('DELETE', False):
                form.cleaned_data['id'].delete()
            else:
                assessment.course = course
                assessment.save()
                self._set_flex_assessments(course, assessment)

        response = super(InstructorFormView, self).form_valid(form)

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
