from datetime import datetime
from zoneinfo import ZoneInfo
from canvasapi import Canvas
from django import forms
from django.core.exceptions import ValidationError, PermissionDenied
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


class AssessmentGroupForm(forms.Form):
    def __init__(self, *args, **kwargs):
        assessments = kwargs.pop('assessments')
        course_id = kwargs.pop('course_id')
        super().__init__(*args, **kwargs)

        canvas_course = Canvas(
            CANVAS_API_URL,
            CANVAS_API_KEY).get_course(course_id)
        model_course = Course.objects.filter(pk=course_id).first()

        asgn_groups_create = []
        asgn_groups_update = []
        for canvas_group in canvas_course.get_assignment_groups():
            id = canvas_group.__getattribute__('id')
            name = canvas_group.__getattribute__('name')
            allocation = canvas_group.__getattribute__('group_weight')
            asgn_group = AssignmentGroup.objects.filter(pk=id)
            if not asgn_group.exists():
                asgn_groups_create.append(
                    AssignmentGroup(
                        id=id,
                        name=name,
                        course=model_course,
                        allocation=allocation))
            else:
                asgn_groups_update.append(
                    AssignmentGroup(
                        id=id,
                        name=name,
                        course=model_course,
                        allocation=allocation))
        AssignmentGroup.objects.bulk_create(asgn_groups_create)
        AssignmentGroup.objects.bulk_update(
            asgn_groups_update, [
                'name', 'course', 'allocation'])

        assessment_fields = {}
        for assessment in assessments:
            if assessment.group is not None:
                initial = assessment.group
            else:
                initial = None
            assessment_fields[assessment.id.hex] = forms.ModelChoiceField(
                AssignmentGroup.objects.filter(course_id=course_id), label=assessment.title, initial=initial)
        self.fields.update(assessment_fields)


class StudentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user_id = kwargs.pop('user_id')
        course_id = kwargs.pop('course_id')
        super().__init__(*args, **kwargs)

        if not user_id or not course_id:
            raise PermissionDenied

        flex_assessments = FlexAssessment.objects.filter(
            user__user_id=user_id, assessment__course_id=course_id)
        user_comment = UserComment.objects.filter(
            user__user_id=user_id, course__id=course_id).first()

        flex_fields = {}
        for fa in flex_assessments:
            if fa.flex is not None:
                initial_flex = fa.flex
            else:
                initial_flex = None
            flex_fields[fa.assessment.id.hex] = forms.DecimalField(max_digits=5,
                                                                   decimal_places=2,
                                                                   initial=initial_flex,
                                                                   max_value=100,
                                                                   min_value=0,
                                                                   label=fa.assessment.title,
                                                                   widget=forms.NumberInput(attrs={'size': 3}))

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
                    'rows': 3,
                    'cols': 25}),
            required=False)

        self.fields.update(flex_fields)
        self.fields.update(comment_field)

        deadline = Course.objects.get(pk=course_id).deadline
        if datetime.now(ZoneInfo('America/Vancouver')) > deadline:
            for field in self.fields.values():
                field.disabled = True
