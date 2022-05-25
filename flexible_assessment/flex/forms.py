from datetime import datetime
import pprint
from zoneinfo import ZoneInfo
from canvasapi import Canvas
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from .models import Assessment, Course, FlexAssessment, UserComment, AssignmentGroup
import os

CANVAS_API_URL = os.getenv('CANVAS_API_URL')
CANVAS_API_KEY = os.getenv('CANVAS_API_KEY')


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


class AssessmentGroupForm(forms.Form):
    def __init__(self, *args, **kwargs):
        assessments = kwargs.pop('assessments')
        course_id = kwargs.pop('course_id')
        super().__init__(*args, **kwargs)

        if assessments:
            canvas_course = Canvas(
                CANVAS_API_URL,
                CANVAS_API_KEY).get_course(course_id)
            model_course = Course.objects.filter(pk=course_id).first()
            
            asgn_groups = []
            for canvas_group in canvas_course.get_assignment_groups():
                id = canvas_group.__getattribute__('id')
                name = canvas_group.__getattribute__('name')
                allocation = canvas_group.__getattribute__('group_weight')
                asgn_group = AssignmentGroup.objects.filter(pk=id)
                if not asgn_group.exists():
                    asgn_groups.append(
                        AssignmentGroup(
                            id=id,
                            name=name,
                            course=model_course,
                            allocation=allocation))
            AssignmentGroup.objects.bulk_create(asgn_groups)

            assessment_fields = {}
            for assessment in assessments:
                if assessment.group:
                    initial = assessment.group
                else:
                    initial = None
                assessment_fields[assessment.id.hex] = forms.ModelChoiceField(
                    AssignmentGroup.objects.filter(course_id=course_id), label=assessment.title, initial=initial)
            self.fields.update(assessment_fields)
