import csv
import json
from io import TextIOWrapper
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
from .forms import (AssessmentFileForm, AssessmentGroupForm, DateForm,
                    OptionsForm, StudentAssessmentBaseForm,
                    get_assessment_formset)


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
    """ListView for student flexible allocations"""

    template_name = 'instructor/percentage_list.html'

    def export_list(self):
        students = self.get_queryset()
        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)

        csv_response = writer.students_csv(course, students)
        return csv_response


class FinalGradeListView(views.ExportView, views.InstructorListView):
    """ListView for student final grades with default and override scores"""

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
        """Adds Canvas Assignment Groups to context for rendering grades

        Returns
        -------
        context : context
            Request context
        """

        context = super().get_context_data(**kwargs)
        course_id = self.kwargs['course_id']
        groups, _ = FlexCanvas(self.request)\
            .get_groups_and_enrollments(course_id)
        context['groups'] = groups
        return context

    def _submit_final_grades(self, course_id, canvas):
        """Uploads final override grades in batches to Canvas"""

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
    """FormView for matching assessments in the app
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

        canvas_course = FlexCanvas(self.request).get_course(course_id)

        kwargs['canvas_course'] = canvas_course
        kwargs['assessments'] = models.Assessment.objects.filter(
            course_id=course_id)

        return kwargs

    def form_valid(self, form):
        """Validates that each assessment is matched to one Canvas assignment group
        and each Canvas assignment group is matched to zero or one assessments.
        Adds AssignmentGroup from form as Foreign Key to Assessment. Changes
        group weights on Canvas to match default allocations and unmatched
        group weights are set to zero.

        Parameters
        ----------
        form : AssessmentGroupForm
            Matched flexible assessments and Canvas assignment groups

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

        for assessment_id, group_id in form.cleaned_data.items():
            assessment = models.Assessment.objects.get(pk=assessment_id)
            assessment.group = int(group_id)
            assessment.save()

            canvas_course.get_assignment_group(
                group_id).edit(
                group_weight=assessment.default)

        matched_group_ids = [int(id) for id in form.cleaned_data.values()]
        canvas_group_ids = [
            group.id for group in canvas_course.get_assignment_groups()]

        unmatched_group_ids = list(
            filter(
                lambda id: id not in matched_group_ids,
                canvas_group_ids))
        for id in unmatched_group_ids:
            canvas_course.get_assignment_group(id).edit(group_weight=0)


class InstructorAssessmentView(views.ExportView, views.InstructorFormView):
    """FormView for instructor setup of flexible assessment for a course"""

    template_name = 'instructor/instructor_form.html'
    form_class = BaseModelFormSet
    success_reverse_name = 'instructor:instructor_home'

    def get_context_data(self, **kwargs):
        """Populates and adds assessment formset, date form, and options
        form to context

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
            AssessmentFormSet = get_assessment_formset()
            context['formset'] = AssessmentFormSet(
                self.request.POST, prefix='assessment')

        elif self.request.GET.get('initial', False):
            fields_str = self.request.GET.get('initial', '')
            initial = self._to_initial_dict(fields_str)

            AssessmentFormSet = get_assessment_formset(extra=len(initial))
            context['formset'] = AssessmentFormSet(
                queryset=models.Assessment.objects.none(),
                initial=initial,
                prefix='assessment')
            context['populated'] = True

        else:
            qs = models.Assessment.objects.filter(
                    course=course)
            if len(qs) > 0:
                ids = qs.values_list('id', flat=True)
                original_order = Case(*[When(id=id, then=pos)
                                        for pos, id in enumerate(ids)])
                qs = qs.order_by(original_order)

            AssessmentFormSet = get_assessment_formset()
            context['formset'] = AssessmentFormSet(
                queryset=qs, prefix='assessment')

        return context

    def export_list(self):
        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)

        csv_response = writer.assessments_csv(course)
        return csv_response

    def post(self, request, *args, **kwargs):
        """Defines the assessment formset, date form, and options form
        for validation
        """

        course_id = self.kwargs['course_id']
        date_form = DateForm(request.POST,
                             instance=models.Course.objects.get(pk=course_id),
                             prefix='date')

        AssessmentFormSet = get_assessment_formset()

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
        """Validates and saves assessment formset and date form and creates
        or removes related flexible assessments, and updates relevant Canvas
        course settings using options form

        Parameters
        ----------
        formset : AssessmentFormSet
            Contains assignment forms and their submitted form data
        date_form : DateForm
            Contains flex assessment open and close datetime
        options_form : OptionsForm
            Contains options for the course setup

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
        """Returns students with flex allocations
        out of allowed assessment range i.e. have conflicts
        """

        flex_assessments = assessment.flexassessment_set \
            .exclude(flex__isnull=True)

        conflict_fas = flex_assessments.filter(flex__lt=assessment.min) \
            | flex_assessments.filter(flex__gt=assessment.max)
        conflict_fas = conflict_fas.select_related('user')

        conflict_students = {fa.user for fa in conflict_fas}

        return conflict_students

    def _reset_conflict_students(self, course, conflict_students):
        """Resets flex allocations and comments for students with conflicts"""

        for student in conflict_students:
            fas_to_reset = student.flexassessment_set \
                .filter(assessment__course=course)
            fas_to_reset.update(flex=None)
            student.usercomment_set.filter(course=course).update(comment="")

    def _reset_all_students(self, course):
        """Resets flex allocations for all students in the course"""

        fas_to_reset = models.FlexAssessment.objects \
            .filter(assessment__course=course)
        fas_to_reset.update(flex=None)

    def _to_initial_dict(self, fields_str):
        """Converts assessment data for formset initial data

        Parameters
        ----------
        fields_str : str
            Assessment data as string

        Returns
        -------
        initial : dict
            Assessment formset initial data
        """

        if not fields_str:
            return []

        fields = json.loads(fields_str)
        initial = []
        names = ('title', 'default', 'min', 'max')
        for values in fields:
            assessment_fields = {}
            for name, value in zip(names, values):
                assessment_fields[name] = value
            initial.append(assessment_fields)

        return initial


class OverrideStudentAssessmentView(views.InstructorFormView):
    """FormView for instructor overriding student flexible allocations"""

    template_name = 'instructor/override_student_form.html'
    form_class = StudentAssessmentBaseForm

    def get_success_url(self):
        previous = self.request.GET.get('previous', '')
        if previous == 'final':
            self.success_reverse_name = 'instructor:final_grades'
        else:
            self.success_reverse_name = 'instructor:percentage_list'

        return super().get_success_url()

    def get_context_data(self, **kwargs):
        """Adds the student name whose allocations are being overriden
        and previous page to the context

        Returns
        -------
        context : context
            Request context
        """

        context = super().get_context_data(**kwargs)
        student_name = models.UserProfile.objects.get(
            pk=self.kwargs['pk']).display_name
        context['student_name'] = student_name

        previous = self.request.GET.get('previous', '')

        context['previous'] = previous

        return context

    def get_form_kwargs(self):
        """Adds user id and course id as keyword argument for making form fields

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
        form : StudentAssessmentBaseForm
            Flexible allocation data for assessments in course

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


class ImportAssessmentView(views.InstructorFormView):
    """FormView for importing assessments"""

    template_name = 'instructor/assessment_upload.html'
    form_class = AssessmentFileForm
    success_reverse_name = 'instructor:instructor_form'

    def get_success_url(self):
        """Appends imported assessment data to url as parameter"""

        fields_str = json.dumps(self.fields, separators=(',', ':'))
        success_url = super().get_success_url() \
            + '?initial={}'.format(fields_str)

        return success_url

    def form_valid(self, form):
        """Validates import assessments form,
        sets url parameter for form data to be used on success callback

        Parameters
        ----------
        form : AssessmentFileForm
            Contains uploaded assessment data file

        Returns
        -------
        response : Union[HttpResponseRedirect, TemplateResponse]
            HttpResponseRedirect if form is valid,
            TemplateResponse if error
        """

        file_header = self.request.FILES.get('assessments', None)
        if file_header is None:
            return super().form_invalid(form)
        encoded_file = TextIOWrapper(file_header.file,
                                     encoding=self.request.encoding)

        with encoded_file as csv_file:
            data = []
            reader = csv.reader(csv_file)
            headers = next(reader, None)
            if headers != ['Assessment', 'Default', 'Minimum', 'Maximum']:
                return super().form_invalid(form)

            for row in reader:
                if len(row) != 4:
                    return super().form_invalid(form)
                try:
                    int(row[1])
                    int(row[2])
                    int(row[3])
                except ValueError:
                    return super().form_invalid(form)

                data.append(row)

        self.fields = data

        return super().form_valid(form)
