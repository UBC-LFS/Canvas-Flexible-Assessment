from datetime import datetime
from zoneinfo import ZoneInfo
from canvasapi import Canvas
from django import forms
from django.core.exceptions import ValidationError, PermissionDenied
from django.forms import BaseFormSet, BaseModelFormSet, ModelForm, formset_factory, modelform_factory, modelformset_factory
from .models import Assessment, Course, FlexAssessment, UserComment, AssignmentGroup
import os

CANVAS_API_URL = os.getenv('CANVAS_API_URL')
CANVAS_API_KEY = os.getenv('CANVAS_API_KEY')


class DateForm(ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        open = cleaned_data.get('open')
        close = cleaned_data.get('close')

        if open > close:
            self.add_error(None, ValidationError('Close date should be after open date'))


    class Meta:
        model = Course
        fields = ['open', 'close']
        widgets = {
            'open': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'close': forms.DateTimeInput(attrs={'type': 'datetime-local'})}


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
            asgn_group = AssignmentGroup.objects.filter(pk=id)
            if not asgn_group.exists():
                asgn_groups_create.append(
                    AssignmentGroup(
                        id=id,
                        name=name,
                        course=model_course))
            else:
                asgn_groups_update.append(
                    AssignmentGroup(
                        id=id,
                        name=name,
                        course=model_course))
        AssignmentGroup.objects.bulk_create(asgn_groups_create)
        AssignmentGroup.objects.bulk_update(
            asgn_groups_update, ['name', 'course'])

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
                initial_flex = int(fa.flex)
            else:
                initial_flex = None
            flex_fields[fa.assessment.id.hex] = forms.IntegerField(initial=initial_flex,
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

        course = Course.objects.get(pk=course_id)
        open = course.open
        close = course.close
        now = datetime.now(ZoneInfo('America/Vancouver'))
        if now > close or now < open:
            for field in self.fields.values():
                field.disabled = True


class AssessmentBaseFormSet(BaseModelFormSet):
    def clean(self):
        if any(self.errors):
            return

        for form in self.forms:
            if not form.cleaned_data or set(form.cleaned_data.keys()) != set(
                    ('title', 'default', 'min', 'max', 'id')):
                self.forms.remove(form)

        default_sum = sum([form.cleaned_data.get('default', 0)
                          for form in self.forms])
        if default_sum != 100:
            raise ValidationError(
                'Default assessments should add up to 100%, currently it is {}%'.format(default_sum))

        for form in self.forms:
            cleaned_data = form.cleaned_data
            default = cleaned_data.get('default')
            min = cleaned_data.get('min')
            max = cleaned_data.get('max')

            allocations = [('default', default),
                           ('max', max),
                           ('min', min)]
            labels = {'default': 'Default', 'max': 'Maximum', 'min': 'Minimum'}

            for field, allocation in allocations:
                if allocation and (allocation > 100.0 or allocation < 0.0):
                    form.add_error(
                        field, ValidationError(
                            '{} must be within 0.0 and 100.0'.format(
                                labels[field])))

            if default and min and max:
                if min > default:
                    form.add_error('min', ValidationError(
                        'Minimum must be lower than default'))
                if default > max:
                    form.add_error('max', ValidationError(
                        'Maximum must be higher than default'))
                if min > max:
                    form.add_error(None, ValidationError(
                        'Maximum must be higher than minimum'))


AssessmentFormSet = modelformset_factory(Assessment,
                                         fields=(
                                             'title', 'default', 'min', 'max'),
                                         extra=0,
                                         widgets={'title': forms.TextInput(attrs={'size': 15}),
                                                  'default': forms.NumberInput(attrs={'size': 3}),
                                                  'min': forms.NumberInput(attrs={'size': 3}),
                                                  'max': forms.NumberInput(attrs={'size': 3})},
                                         formset=AssessmentBaseFormSet)
