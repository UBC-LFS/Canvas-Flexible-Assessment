import flexible_assessment.class_views as views
import flexible_assessment.models as models
from django.forms import ValidationError
from django.utils import timezone

from .forms import StudentAssessmentForm


class StudentHome(views.StudentTemplateView):
    template_name = 'student/student_home.html'


class StudentAssessmentView(views.StudentFormView):
    """FormView for student flexible allocations"""

    template_name = 'student/student_form.html'
    form_class = StudentAssessmentForm
    success_reverse_name = 'student:student_home'

    def get_form_kwargs(self):
        """Adds user id and course id as keyword arguments for making form fields

        Returns
        -------
        kwargs : kwargs
            Form keyword arguments
        """

        kwargs = super().get_form_kwargs()
        user_id = self.request.session.get('user_id', '')
        course_id = self.kwargs['course_id']

        kwargs['user_id'] = user_id
        kwargs['course_id'] = course_id

        return kwargs

    def form_valid(self, form):
        """Validates form by checking if flex allocation is within range
        and form is submitted within allowed flexible assessment time frame,
        updates flex assessments for student

        Parameters
        ----------
        form : StudentAssessmentForm
            Flexible allocation data for assessments in course

        Returns
        -------
        response : Union[HttpResponseRedirect, TemplateResponse]
            HttpResponseRedirect if form is valid,
            TemplateResponse if error in form
        """

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
            response = super().form_invalid(form)
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

        response = super().form_valid(form)
        return response
