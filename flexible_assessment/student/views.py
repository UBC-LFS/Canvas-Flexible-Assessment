from django.forms import ValidationError
from django.urls import reverse_lazy
from django.utils import timezone

import flexible_assessment.class_views as views
import flexible_assessment.models as models
from flexible_assessment.view_roles import Student

from .forms import StudentForm


class StudentHome(views.TemplateView):
    allowed_view_role = Student
    template_name = 'student/student_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['display_name'] = self.request.session.get('display_name', '')
        return context


class StudentFormView(views.FormView):
    """Extends Django generic FormView and authentication mixins
    for student form."""

    allowed_view_role = Student
    template_name = 'student/student_form.html'
    form_class = StudentForm

    def get_success_url(self):
        return reverse_lazy('student:student_home',
                            kwargs={'course_id': self.kwargs['course_id']})

    def get_form_kwargs(self):
        """Adds course_id as keyword arguments for making form fields

        Returns
        -------
        kwargs : kwargs
            Form keyword arguments
        """

        kwargs = super(StudentFormView, self).get_form_kwargs()
        user_id = self.request.session.get('user_id', '')
        course_id = self.kwargs['course_id']

        kwargs['user_id'] = user_id
        kwargs['course_id'] = course_id

        return kwargs

    def form_valid(self, form):
        user_id = self.request.session.get('user_id', '')
        course_id = self.kwargs['course_id']

        course = models.Course.objects.get(pk=course_id)
        open_datetime = course.open
        close_datetime = course.close
        now = timezone.now()
        if now > close_datetime:
            form.add_error(None, ValidationError(
                'Past deadline to submit form'))
        elif now < open_datetime:
            form.add_error(None, ValidationError(
                'Form is not open yet'))

        comment = form.cleaned_data.pop('comment')

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
            response = super(StudentFormView, self).form_invalid(form)
            return response

        for assessment_id, flex in assessment_fields:
            assessment = models.Assessment.objects.get(pk=assessment_id)
            flex_assessment = assessment.flexassessment_set.filter(
                user__user_id=user_id).first()
            flex_assessment.flex = flex
            flex_assessment.save()

        user_comment = models.UserComment.objects.filter(
            user__user_id=user_id, course__id=course_id).first()
        user_comment.comment = comment
        user_comment.save()

        response = super(StudentFormView, self).form_valid(form)
        return response
