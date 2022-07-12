from threading import Thread

import flexible_assessment.class_views as views
import flexible_assessment.models as models
import flexible_assessment.utils as utils
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Case, When
from django.forms import BaseModelFormSet, ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse

from instructor.canvas_api import FlexCanvas

from . import grader, writer
from .forms import (AssessmentFormSet, AssessmentGroupForm, DateForm,
                    OptionsForm, StudentAssessmentBaseForm)


class InstructorHome(views.InstructorTemplateView):
    template_name = 'instructor/instructor_home.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        login_redirect = request.GET.get('login_redirect')
        if login_redirect:
            course = self.get_context_data().get('course', '')
            utils.update_students(request, course)
        return response


class FlexAssessmentListView(views.ExportView, views.InstructorListView):
    """Extends ListView for student flex allocations"""

    template_name = 'instructor/percentage_list.html'

    def export_list(self):
        students = self.get_queryset()
        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)

        csv_response = writer.students_csv(course, students)
        return csv_response


class FinalGradeListView(views.ExportView, views.InstructorListView):
    """Extends ListView for student grades with default and override scores"""

    template_name = 'instructor/final_grade_list.html'

    def export_list(self):
        students = self.get_queryset()
        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)
        groups = self.get_context_data().get('groups')

        csv_response = writer.grades_csv(course, students, groups)
        return csv_response

    def post(self, request, *args, **kwargs):
        """Sets override grades for students on Canvas"""

        course_id = self.kwargs['course_id']

        if self.kwargs.get('submit', False):
            canvas = FlexCanvas(request)

            if not canvas.is_allow_override(course_id):
                messages.error(
                    request,
                    "Check 'Allow Final Grade Override' under"
                    " Gradebook Settings")
                return HttpResponseRedirect(
                    reverse(
                        'instructor:final_grades',
                        kwargs={'course_id': course_id}))

            success = self._submit_final_grades(course_id, canvas)

            if not success:
                messages.error(
                    request,
                    "Something went wrong when submitting grades!"
                    "Please try again.")
                return HttpResponseRedirect(
                    reverse(
                        'instructor:final_grades',
                        kwargs={'course_id': course_id}))

        return HttpResponseRedirect(
            reverse('instructor:instructor_home',
                    kwargs={'course_id': course_id}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs['course_id']
        groups, _ = FlexCanvas(self.request)\
            .get_groups_and_enrollments(course_id)
        context['groups'] = groups
        return context

    def _submit_final_grades(self, course_id, canvas):
        course = models.Course.objects.get(pk=course_id)
        groups, enrollments = canvas.get_groups_and_enrollments(course_id)

        threads = []
        incomplete = [False]
        batch_size = 64
        for student_id, enrollment_id in enrollments.items():
            student = models.UserProfile.objects\
                .filter(pk=student_id)\
                .first()
            if not student:
                continue
            override = grader.get_override_total(groups, student, course) \
                or grader.get_default_total(groups, student)

            t = Thread(target=canvas.set_override,
                       args=(enrollment_id, override, incomplete))
            threads.append(t)

            if len(threads) >= batch_size:
                [t.start() for t in threads]
                [t.join() for t in threads]
                threads = []

        [t.start() for t in threads]
        [t.join() for t in threads]

        return not incomplete[0]


class AssessmentGroupView(views.InstructorFormView):
    """Extends FormView for matching assessments in the app
    to assignment groups on Canvas
    """

    template_name = 'instructor/assessment_group_form.html'
    form_class = AssessmentGroupForm
    success_reverse_name = 'instructor:final_grades'

    def get_form_kwargs(self):
        """Adds course_id, FlexCanvas instance, and assessments as keyword
        arguments for making form fields

        Returns
        -------
        kwargs : kwargs
            Form keyword arguments
        """

        kwargs = super().get_form_kwargs()

        course_id = self.kwargs['course_id']

        kwargs['course_id'] = course_id
        kwargs['canvas'] = FlexCanvas(self.request)
        kwargs['assessments'] = models.Assessment.objects.filter(
            course_id=course_id)

        return kwargs

    def form_valid(self, form):
        """Validates matched groups are unique and adds AssignmentGroup as
        Foreign Key to Assessment. Changes group weights on Canvas to
        match default allocations. Unmatched group weights are set to zero.

        Parameters
        ----------
        form : form
            Contains Django form fields and submitted field data

        Returns
        -------
        response : Union[HttpResponseRedirect, TemplateResponse]
            HttpResponseRedirect if form is valid,
            TemplateResponse if error in form
        """

        matched_groups = form.cleaned_data.values()

        duplicates = []
        seen = set()
        for group in matched_groups:
            if group in seen:
                duplicates.append(group)
            else:
                seen.add(group)

        items = list(form.cleaned_data.items())
        for field, group in items:
            if group in duplicates:
                form.add_error(field, ValidationError(
                    'Matched groups must be unique'))

        if form.errors:
            response = super().form_invalid(form)
            return response

        self._update_assessments_and_groups(form)

        response = super().form_valid(form)
        return response

    def _update_assessments_and_groups(self, form):
        """Adds assignment group to assessment and updates
        Canvas group weights
        """

        course_id = self.kwargs['course_id']

        canvas_course = FlexCanvas(self.request).get_course(course_id)

        for id, group in form.cleaned_data.items():
            assessment = models.Assessment.objects.filter(pk=id).first()
            assessment.group = group
            assessment.save()

            canvas_course.get_assignment_group(
                group.id).edit(
                group_weight=assessment.default)

        matched_group_ids = [group.id for group in form.cleaned_data.values()]
        canvas_group_ids = [
            group.id for group in canvas_course.get_assignment_groups()]

        unmatched_group_ids = list(
            filter(
                lambda id: id not in matched_group_ids,
                canvas_group_ids))
        for id in unmatched_group_ids:
            canvas_course.get_assignment_group(id).edit(group_weight=0)


class InstructorAssessmentView(views.ExportView, views.InstructorFormView):
    template_name = 'instructor/instructor_form.html'
    form_class = BaseModelFormSet
    success_reverse_name = 'instructor:instructor_home'

    def get_context_data(self, **kwargs):
        """Populates assignment formset and date form according to POST or GET request

        Returns
        -------
        context : context
            Request context
        """
        context = super().get_context_data(**kwargs)
        course = context['course']

        course_settings = FlexCanvas(self.request) \
            .get_course(course.id) \
            .get_settings()

        if not course.open:
            hide_total = True
        else:
            hide_total = course_settings['hide_final_grades']

        context['date_form'] = DateForm(
            self.request.POST or None, instance=course, prefix='date')
        context['options_form'] = OptionsForm(
            self.request.POST or None, prefix='options', hide_total=hide_total)

        if self.request.POST:
            context['formset'] = AssessmentFormSet(
                self.request.POST, prefix='assessment')
        else:
            qs = models.Assessment.objects.filter(
                    course=course)
            ids = qs.values_list('id', flat=True)
            original_order = Case(*[When(id=id, then=pos)
                                    for pos, id in enumerate(ids)])
            context['formset'] = AssessmentFormSet(
                queryset=qs.order_by(original_order), prefix='assessment')

        return context

    def export_list(self):
        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)

        csv_response = writer.assessments_csv(course)
        return csv_response

    def post(self, request, *args, **kwargs):
        """Defines the formset and date form for validation.
        Sets Canvas course setting to hide final grades to True"""

        course_id = self.kwargs['course_id']
        date_form = DateForm(request.POST,
                             instance=models.Course.objects.get(pk=course_id),
                             prefix='date')

        formset = AssessmentFormSet(request.POST, prefix='assessment')
        options_form = OptionsForm(request.POST, prefix='options')

        if formset.is_valid() \
                and date_form.is_valid() \
                and options_form.is_valid():
            return self.forms_valid(formset, date_form, options_form)

        elif not formset.is_valid():
            return self.form_invalid(formset)
        elif not date_form.is_valid():
            return self.form_invalid(date_form)
        else:
            return self.form_invalid(options_form)

    def forms_valid(self, formset, date_form, options_form):
        """Validates and saves assignment formset and date form

        Parameters
        ----------
        formset : formset
            Contains assignment forms and their submitted form data
        date_form : form
            Contains flex assessment open and close datetime

        Returns
        -------
        response : Union[HttpResponseRedirect, TemplateResponse]
            HttpResponseRedirect if formset and date form is valid,
            TemplateResponse if error
        """

        date_form.save()

        options_form.clean()

        hide_total = options_form.cleaned_data['hide_total']
        ignore_conflicts = options_form.cleaned_data['ignore_conflicts']

        formset.clean()

        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)

        assessments = []
        conflict_students = set()
        for form in formset.forms:
            assessment = form.save(commit=False)
            assessments.append(assessment)
            assessment.course = course

            curr_conflict_students = self._check_valid_flex(assessment)
            conflict_students = conflict_students.union(curr_conflict_students)

            if curr_conflict_students and not ignore_conflicts:
                messages.warning(
                    self.request,
                    '{} flex allocations are out of range for {}'
                        .format(len(curr_conflict_students), assessment.title))

        if conflict_students and not ignore_conflicts:
            return super().form_invalid(formset)

        assessment_created = False
        for assessment in assessments:
            assessment.save()
            curr_assessment_created = self._set_flex_assessments(course,
                                                                 assessment)
            if curr_assessment_created:
                assessment_created = curr_assessment_created

        FlexCanvas(self.request)\
            .get_course(course_id)\
            .update_settings(hide_final_grades=hide_total)

        assessments_to_delete = course.assessment_set \
            .exclude(id__in=[assessment.id for assessment in assessments])

        if assessment_created or assessments_to_delete:
            if assessments_to_delete:
                assessments_to_delete.delete()
            self._reset_all_students(course)
        else:
            self._reset_conflict_students(course, conflict_students)

        return HttpResponseRedirect(self.get_success_url())

    def _set_flex_assessments(self, course, assessment):
        """Creates flex assessment objects for new assessments in the course"""

        user_courses = course.usercourse_set.filter(
            user__role=models.Roles.STUDENT).select_related('user')
        users = [user_course.user for user_course in user_courses]
        flex_assessments = [
            models.FlexAssessment(user=user, assessment=assessment)
            for user in users
            if not models.FlexAssessment.objects.filter(
                user=user, assessment=assessment).exists()]
        models.FlexAssessment.objects.bulk_create(flex_assessments)
        return True if flex_assessments else False

    def _check_valid_flex(self, assessment):
        flex_assessments = assessment.flexassessment_set \
            .exclude(flex__isnull=True)

        conflict_fas = flex_assessments.filter(flex__lt=assessment.min) \
            | flex_assessments.filter(flex__gt=assessment.max)
        conflict_fas = conflict_fas.select_related('user')

        conflict_students = {fa.user for fa in conflict_fas}

        return conflict_students

    def _reset_conflict_students(self, course, conflict_students):
        for student in conflict_students:
            fas_to_reset = student.flexassessment_set \
                .filter(assessment__course=course)
            fas_to_reset.update(flex=None)
            student.usercomment_set.filter(course=course).update(comment="")

    def _reset_all_students(self, course):
        fas_to_reset = models.FlexAssessment.objects \
            .filter(assessment__course=course)
        fas_to_reset.update(flex=None)


class OverrideStudentAssessmentView(views.InstructorFormView):
    template_name = 'instructor/override_student_form.html'
    form_class = StudentAssessmentBaseForm

    def get_success_url(self):
        if self.kwargs.get('previous', '') == 'final':
            self.success_reverse_name = 'instructor:final_grades'
        else:
            self.success_reverse_name = 'instructor:percentage_list',

        return super().get_success_url()

    def get_context_data(self, **kwargs):
        """Adds the student name whose allocations are being overriden to the context

        Returns
        -------
        context : context
            Request context
        """

        context = super().get_context_data(**kwargs)
        student_name = models.UserProfile.objects.get(
            pk=self.kwargs['pk']).display_name
        context['student_name'] = student_name

        previous = self.kwargs.get('previous', '')
        context['previous'] = previous

        return context

    def get_form_kwargs(self):
        """Adds course_id as keyword argument for making form fields

        Returns
        -------
        kwargs : kwargs
            Form keyword arguments
        """

        kwargs = super().get_form_kwargs()
        user_id = self.kwargs['pk']
        course_id = self.kwargs['course_id']

        if not user_id or not course_id:
            raise PermissionDenied

        kwargs['user_id'] = user_id
        kwargs['course_id'] = course_id

        return kwargs

    def form_valid(self, form):
        """Validates form by checking if flex allocation is within range
        and updates flex assessments for student

        Parameters
        ----------
        form : form
            Contains Django form fields and submitted field data

        Returns
        -------
        response : Union[HttpResponseRedirect, TemplateResponse]
            HttpResponseRedirect if form is valid,
            TemplateResponse if error in form
        """

        user_id = self.kwargs['pk']
        course_id = self.kwargs['course_id']

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
            response = super().form_invalid(form)
            return response

        for assessment_id, flex in assessment_fields:
            assessment = models.Assessment.objects.get(pk=assessment_id)
            flex_assessment = assessment.flexassessment_set.filter(
                user__user_id=user_id).first()
            flex_assessment.flex = flex
            flex_assessment.save()

        response = super().form_valid(form)
        return response


class ImportAssessmentsView(views.InstructorFormView):
    pass
