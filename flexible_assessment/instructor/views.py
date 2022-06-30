import flexible_assessment.class_views as views
import flexible_assessment.models as models
import flexible_assessment.utils as utils
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.forms import BaseModelFormSet, ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from instructor.canvas_api import FlexCanvas
from flexible_assessment.view_roles import Instructor

from . import grader
from . import writer
from .forms import (AssessmentFormSet, AssessmentGroupForm, DateForm,
                    StudentBaseForm)


class InstructorHome(views.TemplateView):
    allowed_view_role = Instructor
    template_name = 'instructor/instructor_home.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        login_redirect = request.GET.get('login_redirect')
        if login_redirect:
            course = self.get_context_data().get('course', '')
            utils.update_students(request, course)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['display_name'] = self.request.session.get('display_name', '')
        return context


class FlexAssessmentListView(views.ListView):
    """Extends ListView for student flex allocations"""

    allowed_view_role = Instructor
    model = models.UserProfile
    context_object_name = 'student_list'
    template_name = 'instructor/percentage_list.html'
    paginate_by = 30

    def get(self, request, *args, **kwargs):
        """Gets list page view or csv response of students """

        response = super().get(request, *args, **kwargs)
        if self.kwargs.get('csv', False):
            students = self.get_queryset()
            course_id = self.kwargs['course_id']
            course = models.Course.objects.get(pk=course_id)

            csv_response = writer.students_csv(course, students)
            return csv_response
        else:
            return response

    def get_queryset(self):
        """QuerySet is students for current course"""

        user_id = self.request.session.get('user_id', '')
        course_id = self.kwargs['course_id']
        if not user_id:
            raise PermissionDenied
        queryset = models.UserProfile.objects.filter(
            role=models.Roles.STUDENT, usercourse__course__id=course_id)
        return queryset


class FinalGradeListView(views.ListView):
    """Extends ListView for student grades with default and override scores"""

    allowed_view_role = Instructor
    model = models.UserProfile
    context_object_name = 'student_list'
    template_name = 'instructor/final_grade_list.html'
    paginate_by = 30

    def get(self, request, *args, **kwargs):
        """Gets list page view or csv response of final grades"""

        response = super().get(request, *args, **kwargs)
        if self.kwargs.get('csv', False):
            students = self.get_queryset()
            course_id = self.kwargs['course_id']
            course = models.Course.objects.get(pk=course_id)
            groups = self.get_context_data().get('groups')

            csv_response = writer.grades_csv(course, students, groups)
            return csv_response

        else:
            return response

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

            course = models.Course.objects.get(pk=course_id)
            groups, enrollments = canvas.get_groups_and_enrollments(course_id)

            for student_id, enrollment_id in enrollments.items():
                student = models.UserProfile.objects\
                    .filter(pk=student_id)\
                    .first()
                if not student:
                    continue
                override = grader.get_override_total(groups, student, course) \
                    or grader.get_default_total(groups, student)

                canvas.set_override(enrollment_id, override)

        return HttpResponseRedirect(
            reverse('instructor:instructor_home',
                    kwargs={'course_id': course_id}))

    def get_context_data(self, **kwargs):
        context = super(FinalGradeListView, self).get_context_data(**kwargs)
        course_id = self.kwargs['course_id']
        groups, _ = FlexCanvas(self.request)\
            .get_groups_and_enrollments(course_id)
        context['groups'] = groups
        return context

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        course_id = self.kwargs['course_id']
        if not user_id:
            raise PermissionDenied
        return models.UserProfile.objects.filter(
            role=models.Roles.STUDENT, usercourse__course__id=course_id)


class AssessmentGroupView(views.FormView):
    """Extends FormView for matching assessments in the app
    to assignment groups on Canvas
    """

    allowed_view_role = Instructor
    template_name = 'instructor/assessment_group_form.html'
    form_class = AssessmentGroupForm

    def get_success_url(self):
        return reverse_lazy(
            'instructor:final_grades',
            kwargs={'course_id': self.kwargs['course_id']})

    def get_form_kwargs(self):
        """Adds course_id, FlexCanvas instance, and assessments as keyword
        arguments for making form fields

        Returns
        -------
        kwargs : kwargs
            Form keyword arguments
        """

        kwargs = super(AssessmentGroupView, self).get_form_kwargs()

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
            response = super(AssessmentGroupView, self).form_invalid(form)
            return response

        self._update_assessments_and_groups(form)

        response = super(AssessmentGroupView, self).form_valid(form)
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


class InstructorFormView(views.FormView):
    allowed_view_role = Instructor
    template_name = 'instructor/instructor_form.html'
    form_class = BaseModelFormSet

    def get_success_url(self):
        return reverse_lazy(
            'instructor:instructor_home',
            kwargs={'course_id': self.kwargs['course_id']})

    def get_context_data(self, **kwargs):
        """Populates assignment formset and date form according to POST or GET request

        Returns
        -------
        context : context
            Request context
        """

        context = super(InstructorFormView, self).get_context_data(**kwargs)
        course = context['course']

        if self.request.POST:
            context['date_form'] = DateForm(
                self.request.POST, instance=course, prefix='date')
            context['formset'] = AssessmentFormSet(
                self.request.POST, prefix='assessment')
        else:
            context['date_form'] = DateForm(
                instance=course, prefix='date')
            context['formset'] = AssessmentFormSet(
                queryset=models.Assessment.objects.filter(
                    course=course), prefix='assessment')

        return context

    def get(self, request, *args, **kwargs):
        """Gets form page or csv response of assessments"""

        response = super().get(request, *args, **kwargs)
        if self.kwargs.get('csv', False):
            course_id = self.kwargs['course_id']
            course = models.Course.objects.get(pk=course_id)

            csv_response = writer.assessments_csv(course)
            return csv_response
        else:
            return response

    def post(self, request, *args, **kwargs):
        """Defines the formset and date form for validation.
        Sets Canvas course setting to hide final grades to True"""

        course_id = self.kwargs['course_id']
        date_form = DateForm(request.POST,
                             instance=models.Course.objects.get(pk=course_id),
                             prefix='date')

        formset = AssessmentFormSet(request.POST, prefix='assessment')

        if formset.is_valid() and date_form.is_valid():
            FlexCanvas(request)\
                .get_course(course_id)\
                .update_settings(hide_final_grades=True)

            return self.forms_valid(formset, date_form)

        elif not formset.is_valid():
            return self.form_invalid(formset)
        else:
            return self.form_invalid(date_form)

    def forms_valid(self, formset, date_form):
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

        formset.clean()

        course_id = self.kwargs['course_id']
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
        """Creates flex assessment objects for new assessments in the course"""

        user_courses = course.usercourse_set.filter(
            user__role=models.Roles.STUDENT)
        users = [user_course.user for user_course in user_courses]
        flex_assessments = [
            models.FlexAssessment(user=user, assessment=assessment)
            for user in users
            if not models.FlexAssessment.objects.filter(
                user=user, assessment=assessment).exists()]
        models.FlexAssessment.objects.bulk_create(flex_assessments)


class OverrideStudentFormView(views.FormView):
    allowed_view_role = Instructor
    template_name = 'instructor/override_student_form.html'
    form_class = StudentBaseForm

    def get_success_url(self):
        if self.kwargs.get('previous', '') == 'final':
            return reverse_lazy(
                'instructor:final_grades',
                kwargs={'course_id': self.kwargs['course_id']})

        return reverse_lazy(
            'instructor:percentage_list',
            kwargs={'course_id': self.kwargs['course_id']})

    def get_context_data(self, **kwargs):
        """Adds the student name whose allocations are being overriden to the context

        Returns
        -------
        context : context
            Request context
        """

        context = super(
            OverrideStudentFormView,
            self).get_context_data(
            **kwargs)
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

        kwargs = super(OverrideStudentFormView, self).get_form_kwargs()
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


class ImportAssessmentsView(views.FormView):
    pass
