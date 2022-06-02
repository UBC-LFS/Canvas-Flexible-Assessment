from datetime import datetime
from zoneinfo import ZoneInfo
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.forms import ValidationError
from django.urls import reverse_lazy
from django.views import generic

import flex.models as models
import flex.utils as utils

from .forms import StudentForm


class StudentFormView(
        LoginRequiredMixin, UserPassesTestMixin, generic.FormView):
    """Extends Django generic FormView and authentication mixins for student form."""

    template_name = 'flex/student/student_form.html'
    form_class = StudentForm
    raise_exception = True
    success_url = reverse_lazy('flex:student_home')

    def get_context_data(self, **kwargs):
        context = super(StudentFormView, self).get_context_data(**kwargs)
        return context

    def get_form_kwargs(self):
        """Adds course_id as keyword arguments for making form fields

        Returns
        -------
            kwargs : kwargs
                Form keyword arguments
        """

        kwargs = super(StudentFormView, self).get_form_kwargs()
        user_id = self.request.session.get('user_id', '')
        course_id = self.request.session.get('course_id', '')

        if not user_id or not course_id:
            raise PermissionDenied

        kwargs['user_id'] = user_id
        kwargs['course_id'] = course_id

        return kwargs

    def form_valid(self, form):
        user_id = self.request.session.get('user_id', '')
        course_id = self.request.session.get('course_id', '')

        if not user_id or not course_id:
            raise PermissionDenied

        course = models.Course.objects.get(pk=course_id)
        open = course.open
        close = course.close
        now = datetime.now(ZoneInfo('America/Vancouver'))
        if now > close:
            form.add_error(None, ValidationError(
                'Past deadline to submit form'))
        elif now < open:
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

    def test_func(self):
        return utils.is_student(self.request.user)
