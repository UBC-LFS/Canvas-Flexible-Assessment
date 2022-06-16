from django import forms
from flexible_assessment.models import UserComment
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
        self.field_status()
