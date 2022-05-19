from datetime import datetime
from zoneinfo import ZoneInfo
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from .models import Assessment, Course, FlexAssessment, UserComment


class AddAssessmentForm(ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        default = cleaned_data.get('default')
        min = cleaned_data.get('min')
        max = cleaned_data.get('max')

        allocations = [('Default', default),
                       ('Maximum', max), ('Minimum', min)]
        validation_errors = []

        for name, allocation in allocations:
            if allocation and (allocation > 100.0 or allocation < 0.0):
                validation_errors.append(
                    ValidationError(
                        '{} must be within 0.0 and 100.0'.format(name)))

        if default and min and max:
            if min > default:
                validation_errors.append(
                    ValidationError('Minimum must be lower than default'))
            if default > max:
                validation_errors.append(
                    ValidationError('Maximum must be higher than default'))
            if min > max:
                validation_errors.append(
                    ValidationError('Maximum must be higher than minimum'))

        if validation_errors:
            raise ValidationError(validation_errors)

    class Meta:
        model = Assessment
        fields = ['title', 'default', 'min', 'max']
        help_texts = {'title': 'Enter assessment title',
                      'default': 'Default grade allocation',
                      'min': 'Minimum possible grade allocation set by student',
                      'max': 'Maximum possible grade allocation set by student'}


class UpdateAssessmentForm(AddAssessmentForm):
    reset_flex = forms.BooleanField(
        label='Reset flex',
        required=False,
        initial=False)


class DateForm(ModelForm):
    def clean_deadline(self):
        data = self.cleaned_data['deadline']
        return data

    class Meta:
        model = Course
        fields = ['deadline']
        widgets = {
            'deadline': forms.DateTimeInput(format='%m/%d/%y %H:%M',
                                            attrs={
                                                'placeholder': 'mm/dd/yy hh:mm'})}
        help_texts = {
            'deadline': 'Due date for students to add or change grade allocation for assessments'}


class FlexForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: verify deadline after submitting as well
        flex_assessment = kwargs.get('instance', None)
        if flex_assessment:
            deadline = flex_assessment.assessment.course.deadline
            if datetime.now(ZoneInfo('America/Vancouver')) > deadline:
                self.fields['flex'].disabled = True

    def clean_flex(self):
        cleaned_data = super().clean()
        flex = cleaned_data.get('flex')

        validation_errors = []

        if flex and (flex > 100.0 or flex < 0.0):
            validation_errors.append(
                ValidationError('Flex must be within 0.0 and 100.0'))

        if validation_errors:
            raise ValidationError(validation_errors)

        return flex

    class Meta:
        model = FlexAssessment
        fields = ['flex']
        help_texts = {'flex': 'Grade allocation for assessment'}


class CommentForm(ModelForm):
    class Meta:
        model = UserComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'cols': 25})
        }
