import csv
import json
import logging
from io import TextIOWrapper
from threading import Thread

import flexible_assessment.class_views as views
import flexible_assessment.models as models
import flexible_assessment.utils as utils
import pytz

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Case, When
from django.forms import BaseModelFormSet, ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404

from instructor.canvas_api import FlexCanvas

from . import grader, writer
from .forms import (AssessmentFileForm, AssessmentGroupForm, CourseSettingsForm,
                    OptionsForm, StudentAssessmentBaseForm,
                    get_assessment_formset)

logger = logging.getLogger(__name__)


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

        if self.kwargs.get('csv', ''):
            response = writer.students_csv(course, students)

            logger.info('Percentage view exported',
                        extra={'course': str(course),
                               'user': self.request.session['display_name']})
        elif self.kwargs.get('log', ''):
            response = writer.course_log(course)

            logger.info('Course log exported',
                        extra={'course': str(course),
                               'user': self.request.session['display_name']})

        return response


class FinalGradeListView(views.ExportView, views.InstructorListView):
    """ListView for student final grades with default and override scores"""

    template_name = 'instructor/final_grade_list.html'

    def export_list(self):
        students = self.get_queryset()
        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)
        groups = self.get_context_data().get('groups')

        csv_response = writer.grades_csv(course, students, groups)

        logger.info('Final list view exported',
                    extra={'course': str(course),
                           'user': self.request.session['display_name']})

        return csv_response

    def post(self, request, *args, **kwargs):
        """Sets override grades for students on Canvas"""

        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)

        log_extra = {'course': str(course),
                     'user': request.session['display_name']}

        if self.kwargs.get('submit', False):
            canvas = FlexCanvas(request)

            if not canvas.is_allow_override(course_id):
                messages.error(
                    request,
                    "Check 'Allow Final Grade Override' under"
                    " Gradebook Settings")

                logger.info('Allow Final Grade Override setting'
                            'not checked in Canvas',
                            extra=log_extra)

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

                logger.info('Error in submitting final grades',
                            extra=log_extra)

                return HttpResponseRedirect(
                    reverse(
                        'instructor:final_grades',
                        kwargs={'course_id': course_id}))

            logger.info('Completed final grades submission to Canvas',
                        extra=log_extra)

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

        def _set_override(student_name, enrollment_id, override, incomplete):
            canvas.set_override(enrollment_id, override, incomplete)
            logger.info('Submitted %s final grade to Canvas', student_name,
                        extra={'course': str(course),
                               'user': self.request.session['display_name']})

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

            t = Thread(target=_set_override,
                       args=(student.display_name,
                             enrollment_id,
                             override,
                             incomplete))
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
        course_name = canvas_course.__getattribute__('name')

        for assessment_id, group_id in form.cleaned_data.items():
            assessment = models.Assessment.objects.get(pk=assessment_id)
            assessment.group = int(group_id)
            assessment.save()

            group = canvas_course.get_assignment_group(group_id)
            group.edit(group_weight=assessment.default)
            group_name = group.__getattribute__('name')

            logger.info('Matched %s to Canvas %s group',
                        assessment.title,
                        group_name,
                        extra={'course': course_name,
                               'user': self.request.session['display_name']})

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

        context['date_form'] = CourseSettingsForm(
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
        date_form = CourseSettingsForm(request.POST,
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

        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)

        self._set_flex_availability(date_form, course)

        options_form.clean()

        hide_total = options_form.cleaned_data['hide_total']
        ignore_conflicts = options_form.cleaned_data['ignore_conflicts']

        formset.clean()

        assessments, conflict_students = self._save_assessments(
            formset.forms, course, ignore_conflicts)

        if conflict_students and not ignore_conflicts:
            return super().form_invalid(formset)

        assessment_created = self._create_assessments(course, assessments)
        assessment_deleted = self._delete_assessments(course, assessments)

        if assessment_created or assessment_deleted:
            self._reset_all_students(course)
        else:
            self._reset_conflict_students(course, conflict_students)

        FlexCanvas(self.request)\
            .get_course(course_id)\
            .update_settings(hide_final_grades=hide_total)

        return HttpResponseRedirect(self.get_success_url())

    def _set_flex_availability(self, date_form, course):
        old_dts = tuple(map(
            lambda dt: dt.astimezone(pytz.timezone('America/Vancouver'))
            if dt is not None else 'None',
            (course.open, course.close)))

        date_form.save()

        new_dts = (date_form.cleaned_data['open'],
                   date_form.cleaned_data['close'])

        if old_dts != new_dts:
            logger.info('Updated flex availability '
                        'from %s - %s to %s - %s',
                        *old_dts,
                        *new_dts,
                        extra={'course': str(course),
                               'user': self.request.session['display_name']})

    def _save_assessments(self, forms, course, ignore_conflicts):
        assessments = []
        conflict_students = set()
        for form in forms:
            assessment = form.save(commit=False)
            assessments.append(assessment)
            assessment.course = course

            curr_conflict_students = assessment.check_valid_flex()
            conflict_students = conflict_students.union(curr_conflict_students)

            if curr_conflict_students and not ignore_conflicts:
                messages.warning(
                    self.request,
                    '{} flex allocations are out of range for {}'
                        .format(len(curr_conflict_students), assessment.title))

        return assessments, conflict_students

    def _create_assessments(self, course, assessments):
        log_extra = {'course': str(course),
                     'user': self.request.session['display_name']}
        assessment_created = False

        for assessment in assessments:
            old_assessment = models.Assessment.objects \
                .filter(pk=assessment.id).first()

            assessment.save()

            course.set_flex_assessments(assessment)

            if not old_assessment:
                assessment_created = True
                logger.info('%s created (default %s%%, min %s%%, max %s%%)',
                            assessment.title,
                            assessment.default,
                            assessment.min,
                            assessment.max,
                            extra=log_extra)
            else:
                log_allocations = (old_assessment.default,
                                   old_assessment.min,
                                   old_assessment.max,
                                   assessment.default,
                                   assessment.min,
                                   assessment.max)
                if log_allocations[:3] != log_allocations[3:]:
                    logger.info('%s updated '
                                '(default %s%%, min %s%%, max %s%%) '
                                'to (default %s%%, min %s%%, max %s%%)',
                                assessment.title,
                                *log_allocations,
                                extra=log_extra)

        return assessment_created

    def _delete_assessments(self, course, assessments):
        assessments_to_delete = course.assessment_set \
            .exclude(id__in=[assessment.id for assessment in assessments])

        assessment_deleted = False

        if assessments_to_delete:
            assessment_deleted = True
            logger.info('Deleted assessments: %s',
                        ', '.join(assessments_to_delete.values_list(
                            'title', flat=True)),
                        extra={'course': str(course),
                               'user': self.request.session['display_name']})
            assessments_to_delete.delete()

        return assessment_deleted

    def _reset_conflict_students(self, course, conflict_students):
        course.reset_students(conflict_students)

        for student in conflict_students:
            logger.info('Reset flex allocations and comment for %s '
                        'due to out of range allocations',
                        student.display_name,
                        extra={'course': str(course),
                               'user': self.request.session['display_name']})

    def _reset_all_students(self, course):
        course.reset_all_students()

        logger.info('Reset all student flex allocations and comments '
                    'due to new or deleted assessment(s)',
                    extra={'course': str(course),
                           'user': self.request.session['display_name']})

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
        student_name = get_object_or_404(models.UserProfile, pk=self.kwargs['pk']).display_name
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
        course = models.Course.objects.get(pk=course_id)

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

        log_extra = {'course': str(course),
                     'user': self.request.session['display_name']}

        for assessment_id, flex in assessment_fields:
            assessment = models.Assessment.objects.get(pk=assessment_id)
            flex_assessment = assessment.flexassessment_set.filter(
                user__user_id=user_id).first()
            old_flex = flex_assessment.flex
            flex_assessment.flex = flex
            flex_assessment.save()

            if old_flex is None:
                logger.info('Set %s flex for %s to %s%%',
                            flex_assessment.user.display_name,
                            assessment.title,
                            flex,
                            extra=log_extra)
            elif old_flex != flex:
                logger.info('Updated %s flex for %s '
                            'from %s%% to %s%%',
                            flex_assessment.user.display_name,
                            assessment.title,
                            old_flex,
                            flex,
                            extra=log_extra)

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

        course_id = self.kwargs['course_id']
        course = models.Course.objects.get(pk=course_id)

        logger.info('Successfully imported assessments (not yet saved)',
                    extra={'course': str(course),
                           'user': self.request.session['display_name']})

        return super().form_valid(form)
