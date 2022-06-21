import csv

import flexible_assessment.class_views as flex
import flexible_assessment.models as models
import flexible_assessment.utils as utils
from canvasapi import Canvas
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.forms import BaseModelFormSet, ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from flexible_assessment.view_roles import Instructor
from oauth.oauth import get_oauth_token

import grader
from forms import (AssessmentFormSet, AssessmentGroupForm, DateForm,
                   StudentBaseForm)


class InstructorHome(flex.TemplateView):
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


class FlexAssessmentListView(flex.ListView):
    """Extends Django generic ListView and authentication mixins for
    listing student flex allocations
    """
    allowed_view_role = Instructor
    model = models.UserProfile
    context_object_name = 'student_list'
    template_name = 'instructor/percentage_list.html'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if self.kwargs.get('csv', False):
            students = self.get_queryset()
            course_id = self.kwargs['course_id']
            course = models.Course.objects.get(pk=course_id)

            csv_response = self.export_csv(students, course)
            return csv_response
        else:
            return response

    def get_queryset(self):
        """QuerySet is students for current course"""

        user_id = self.request.session.get('user_id', '')
        course_id = self.kwargs['course_id']
        if not user_id:
            raise PermissionDenied
        return models.UserProfile.objects.filter(
            role=models.Roles.STUDENT, usercourse__course__id=course_id)

    def export_csv(self, students, course):
        assessments = [
            assessment for assessment in course.assessment_set.all()]
        fields = ['Student'] + \
            [assessment.title for assessment in assessments] + ['Comment']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename="{}_{}_{}.csv"'\
            .format('Students',
                    course.title.replace(' ', '-'),
                    timezone.localtime().strftime("%Y-%m-%dT%H%M"))

        writer = csv.writer(response, delimiter=",")
        writer.writerow(fields)

        for student in students:
            values = []
            values.append('{}, {}'.format(
                student.display_name, student.login_id))

            for assessment in assessments:
                flex = student.flexassessment_set.get(
                    assessment=assessment).flex
                values.append(flex)

            comment = student.usercomment_set.get(course=course).comment
            values.append(comment)

            writer.writerow(values)

        return response


class FinalGradeListView(flex.ListView):
    allowed_view_role = Instructor
    model = models.UserProfile
    context_object_name = 'student_list'
    template_name = 'instructor/final_grade_list.html'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if self.kwargs.get('csv', False):
            students = self.get_queryset()
            course_id = self.kwargs['course_id']
            course = models.Course.objects.get(pk=course_id)
            groups = self.get_context_data().get('groups')

            csv_response = self.export_csv(students, course, groups)
            return csv_response

        else:
            return response

    def post(self, request, *args, **kwargs):
        course_id = self.kwargs['course_id']

        if self.kwargs.get('submit', False):
            access_token = get_oauth_token(self.request)
            canvas = Canvas(settings.CANVAS_DOMAIN, access_token)

            query = """query AllowOverrideQuery($course_id: ID) {
                course(id: $course_id) {
                    allowFinalGradeOverride
                    } }"""
            query_response = canvas.graphql(
                query, variables={
                    "course_id": course_id})

            if query_response['data']['course']['allowFinalGradeOverride']:
                messages.error(
                    request,
                    "Check 'Allow Final Grade Override' under"
                    " Gradebook Settings")
                return HttpResponseRedirect(
                    reverse(
                        'instructor:final_grades',
                        kwargs={'course_id': course_id}))

            course = models.Course.objects.get(pk=course_id)
            groups, enrollments = self.get_groups_and_enrollments()
            for student_id, enrollment_id in enrollments.items():
                student = models.UserProfile.objects.get(pk=student_id)
                override = grader.get_override_total(
                    groups, student, course) or grader.get_default_total(
                    groups, student)

                mutation = """mutation OverrideFinalScore($enrollment_id: ID!, $override: Float) {
                    setOverrideScore(input: { enrollmentId: $enrollment_id,
                                              overrideScore: $override }) {
                        grades {
                            overrideScore
                            } } }"""

                canvas.graphql(
                    mutation,
                    variables={"enrollment_id": enrollment_id,
                               "override": override})

        return HttpResponseRedirect(
            reverse(
                'instructor:instructor_home',
                kwargs={'course_id': course_id}))

    def get_context_data(self, **kwargs):
        context = super(FinalGradeListView, self).get_context_data(**kwargs)
        groups, _ = self.get_groups_and_enrollments()
        context['groups'] = groups
        return context

    def get_queryset(self):
        user_id = self.request.session.get('user_id', '')
        course_id = self.kwargs['course_id']
        if not user_id:
            raise PermissionDenied
        return models.UserProfile.objects.filter(
            role=models.Roles.STUDENT, usercourse__course__id=course_id)

    def get_groups_and_enrollments(self):
        course_id = self.kwargs['course_id']
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
              }
              _id
            } } } } } } }"""

        access_token = get_oauth_token(self.request)
        query_response = Canvas(
            settings.CANVAS_DOMAIN, access_token).graphql(
            query, variables={
                "course_id": course_id})

        query_flattened = utils.flatten_dict(query_response)
        groups = query_flattened.get(
            'data.course.assignment_groups.groups', None)
        if groups is None:
            raise PermissionDenied

        group_dict = {}
        user_enrollment_dict = {}
        for group in groups:
            id = group['group_id']
            group.pop('group_id', None)
            group_dict[id] = group

        for group_data in group_dict.values():
            group_flattened = utils.flatten_dict(group_data)
            grades = group_flattened.get('grade_list.grades', None)
            if grades is None:
                raise PermissionDenied

            updated_grades = []
            for grade in grades:
                grade_flattened = utils.flatten_dict(grade)
                user_id = grade_flattened.get('enrollment.user.user_id', None)
                enrollment_id = grade_flattened.get('enrollment._id', None)
                if user_id is None:
                    raise PermissionDenied

                user_enrollment_dict[user_id] = enrollment_id

                score = grade_flattened['currentScore']
                updated_grades.append((user_id, score))

            group_data['grade_list']['grades'] = updated_grades

        return group_dict, user_enrollment_dict

    def export_csv(self, students, course, groups):
        assessments = [
            assessment for assessment in course.assessment_set.all()]

        titles = [
            "{} ({}%)".format(
                assessment.title,
                grader.get_group_weight(
                    groups,
                    assessment.group.id)) for assessment in assessments]
        fields = ['Student'] + titles + \
            ['Override Final Grade', 'Default Total', 'Difference']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename="{}_{}_{}.csv"'\
            .format('Grades',
                    course.title.replace(' ', '-'),
                    timezone.localtime().strftime("%Y-%m-%dT%H%M"))

        writer = csv.writer(response, delimiter=",")
        writer.writerow(fields)

        for student in students:
            values = []
            values.append(
                '{}, {}'.format(
                    student.display_name,
                    student.login_id))

            for assessment in assessments:
                score = grader.get_score(groups, assessment.group.id, student)
                values.append(score)

            override_total = grader.get_override_total(groups, student, course)
            default_total = grader.get_default_total(groups, student)

            if override_total != '':
                values.append(round(override_total, 2))
                values.append(round(default_total, 2))
                diff = override_total - default_total
                values.append(round(diff, 2))
            else:
                values.append(round(default_total, 2))
                values.append(round(default_total, 2))
                values.append('')

            writer.writerow(values)

        writer.writerow(
            ['Average Override', 'Average Default', 'Average Difference'])
        writer.writerow(grader.get_averages(groups, course))

        return response


class AssessmentGroupView(flex.FormView):
    """Extends Django generic FormView and authentication mixins for
    matching assessments in the app to assignment groups on Canvas
    """

    allowed_view_role = Instructor
    template_name = 'instructor/assessment_group_form.html'
    form_class = AssessmentGroupForm

    def get_success_url(self):
        return reverse_lazy(
            'instructor:final_grades',
            kwargs={'course_id': self.kwargs['course_id']})

    def get_form_kwargs(self):
        """Adds course_id and assessment as keyword arguments for making form fields

        Returns
        -------
        kwargs : kwargs
            Form keyword arguments
        """

        kwargs = super(AssessmentGroupView, self).get_form_kwargs()
        course_id = self.kwargs['course_id']
        kwargs['course_id'] = course_id
        kwargs['assessments'] = models.Assessment.objects.filter(
            course_id=course_id)
        kwargs['request'] = self.request

        return kwargs

    def form_valid(self, form):
        """Validates matched groups are unique and adds
        AssignmentGroup as Foreign Key to Assessment

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

        course_id = self.kwargs['course_id']

        access_token = get_oauth_token(self.request)
        canvas_course = Canvas(
            settings.CANVAS_DOMAIN,
            access_token).get_course(course_id)

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

        response = super(AssessmentGroupView, self).form_valid(form)
        return response


class InstructorFormView(flex.FormView):
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
        response = super().get(request, *args, **kwargs)
        if self.kwargs.get('csv', False):
            course_id = self.kwargs['course_id']
            course = models.Course.objects.get(pk=course_id)

            csv_response = self.export_csv(course)
            return csv_response
        else:
            return response

    def post(self, request, *args, **kwargs):
        """Defines the formset and date form for validation"""

        course_id = self.kwargs['course_id']
        date_form = DateForm(
            request.POST,
            instance=models.Course.objects.get(
                pk=course_id),
            prefix='date')

        formset = AssessmentFormSet(request.POST, prefix='assessment')

        if formset.is_valid() and date_form.is_valid():
            access_token = get_oauth_token(request)
            Canvas(settings.CANVAS_DOMAIN, access_token) \
                .get_course(course_id).update_settings(hide_final_grades=True)

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

    def export_csv(self, course):
        assessments = [
            assessment for assessment in course.assessment_set.all()]
        fields = ('Assessment', 'Default', 'Min', 'Max')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename="{}_{}_{}.csv"'\
            .format('Assessments',
                    course.title.replace(' ', '-'),
                    timezone.localtime().strftime("%Y-%m-%dT%H%M"))

        writer = csv.writer(response, delimiter=",")
        writer.writerow(fields)

        for assessment in assessments:
            values = (assessment.title, assessment.default,
                      assessment.min, assessment.max)
            writer.writerow(values)

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


class OverrideStudentFormView(flex.FormView):
    allowed_view_role = Instructor
    template_name = 'instructor/override_student_form.html'
    form_class = StudentBaseForm

    def get_success_url(self):
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
        for assessment_id, flex_allocation in assessment_fields:
            assessment = models.Assessment.objects.get(pk=assessment_id)
            if flex_allocation > assessment.max:
                form.add_error(assessment_id, ValidationError(
                    'Flex should be less than or equal to max'))
            elif flex_allocation < assessment.min:
                form.add_error(assessment_id, ValidationError(
                    'Flex should be greater than or equal to min'))

        if form.errors:
            response = super(OverrideStudentFormView, self).form_invalid(form)
            return response

        for assessment_id, flex_allocation in assessment_fields:
            assessment = models.Assessment.objects.get(pk=assessment_id)
            flex_assessment = assessment.flexassessment_set.filter(
                user__user_id=user_id).first()
            flex_assessment.flex = flex_allocation
            flex_assessment.save()

        response = super(OverrideStudentFormView, self).form_valid(form)
        return response


class ImportAssessmentsView(flex.FormView):
    pass
