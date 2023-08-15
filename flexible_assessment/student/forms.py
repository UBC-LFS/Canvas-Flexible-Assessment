from django import forms
from django.utils import timezone
from django.utils.html import format_html
from flexible_assessment.models import Course, UserComment
from instructor.forms import StudentAssessmentBaseForm


class CharacterCountTextarea(forms.Textarea):
    def __init__(self, max_length, *args, **kwargs):
        self.max_length = max_length
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        rendered = super().render(name, value, attrs, renderer)
        count_html = format_html(
            '<p class="mb-0 text-muted">Maximum of {} characters</p>', self.max_length
        )
        return rendered + count_html


class StudentAssessmentForm(StudentAssessmentBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_comment = UserComment.objects.filter(
            user__user_id=self.user_id, course__id=self.course_id
        ).first()

        fields = {}
        if user_comment:
            initial_comment = user_comment.comment
        else:
            initial_comment = None

        comment_length = 350
        fields["comment"] = forms.CharField(
            max_length=comment_length,
            initial=initial_comment,
            widget=CharacterCountTextarea(
                max_length=comment_length,
                attrs={
                    "rows": 3,
                    "class": "form-control",
                    "placeholder": "Enter your comment here",
                },
            ),
            required=False,
        )

        fields["agreement"] = forms.BooleanField(
            required=True,
            label="I agree that my final grade will "
            "be calculated as indicated above",
        )

        self.fields.update(fields)
        self.set_field_status()

    def set_field_status(self):
        course = Course.objects.get(pk=self.course_id)
        open_datetime = course.open
        close_datetime = course.close
        now = timezone.now()
        if course.close != None and (now > close_datetime or now < open_datetime):
            for field in self.fields.values():
                field.disabled = True
