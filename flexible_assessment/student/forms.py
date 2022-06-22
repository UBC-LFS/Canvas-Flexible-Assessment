from django import forms
from django.utils import timezone
from flexible_assessment.models import Course, UserComment
from instructor.forms import StudentBaseForm


class StudentForm(StudentBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_comment = UserComment.objects.filter(
            user__user_id=self.user_id, course__id=self.course_id).first()

        comment_field = {}
        if user_comment.comment:
            initial_comment = user_comment.comment
        else:
            initial_comment = None
        comment_field['comment'] = forms.CharField(
            max_length=100,
            initial=initial_comment,
            widget=forms.Textarea(
                attrs={
                    'rows': 3
                }),
            required=False)

        self.fields.update(comment_field)
        self.set_field_status()

    def set_field_status(self):
        course = Course.objects.get(pk=self.course_id)
        open_datetime = course.open
        close_datetime = course.close
        now = timezone.now()
        if now > close_datetime or now < open_datetime:
            for field in self.fields.values():
                field.disabled = True
