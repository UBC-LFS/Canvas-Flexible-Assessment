from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms import BaseModelFormSet, ModelForm, modelformset_factory
from django.utils import timezone
from flexible_assessment.models import Assessment, Course, FlexAssessment
import flexible_assessment.utils as utils

class StudentAssessmentBaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop('user_id')
        self.course_id = kwargs.pop('course_id')
        super().__init__(*args, **kwargs)

        if not self.user_id or not self.course_id:
            raise PermissionDenied

        flex_assessments = FlexAssessment.objects.filter(
            user__user_id=self.user_id, assessment__course_id=self.course_id)

        flex_fields = {}
        for fa in flex_assessments:
            if fa.flex is not None:
                initial_flex = fa.flex
            else:
                initial_flex = None
            flex_fields[fa.assessment.id.hex] = forms.DecimalField(
                initial=initial_flex,
                max_value=100,
                min_value=0,
                max_digits=5,
                decimal_places=2,
                label=fa.assessment.title,
                widget=forms.NumberInput(attrs={'size': 5})
                )

        self.fields.update(flex_fields)

    def clean(self):
        flex_fields = dict(
            filter(
                lambda field: field[0] not in ['comment', 'agreement'],
                self.cleaned_data.items()))

        flex_total = sum(flex_fields.values())
        if flex_total != 100:
            self.add_error(
                None, ValidationError(
                    'Total flex has to add up to 100%, currently it is ({})%'
                    .format(flex_total)))


class OptionsForm(forms.Form):
    hide_total = forms.BooleanField(
        required=False,
        label='Hide totals in Student Grades Summary')
    ignore_conflicts = forms.BooleanField(
        required=False)
    hide_weights = forms.BooleanField(
        required=False,
        label='Hide Assignment Group Weights in Canvas')

    def __init__(self, *args, **kwargs):
        hide_total = kwargs.pop('hide_total', False)
        hide_weights = kwargs.pop('hide_weights', True)
        super().__init__(*args, **kwargs)
        self.initial['hide_total'] = hide_total
        self.initial['hide_weights'] = hide_weights


class CourseSettingsForm(ModelForm):
    """Form to set flexible assessment availability for students."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.open:
            self.initial['open'] = self.instance.open
        else:
            self.initial['open'] = timezone.localtime().replace(
                hour=9, minute=0, second=0)
        
        self.fields['close'].required = False
        self.fields['open'].required = False

    def clean(self):
        cleaned_data = super().clean()
        open_datetime = cleaned_data.get('open')
        close_datetime = cleaned_data.get('close')

        if open_datetime is None:
            self.add_error('open', ValidationError('Please enter a date'))
        
        if close_datetime is None:
            self.add_error('close', ValidationError('Please enter a date'))
        
        if open_datetime is None or close_datetime is None:
            return 

        if open_datetime > close_datetime:
            self.add_error(None, ValidationError(
                'Close date should be after open date'))
            self.add_error('open', ValidationError(''))
            self.add_error('close', ValidationError(''))

    class Meta:
        model = Course
        fields = ['open', 'close', 'welcome_instructions', 'comment_instructions']
        widgets = {
            'open': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'),
            'close': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'),
            'welcome_instructions': forms.Textarea(
                attrs={'rows':2,
                    'placeholder': 'Example: Welcome to Flexible Assessment, the system that allows students to decide how their final grades will be weighted. Please enter your desired weights in the fields below, agree to the terms, and click Submit.'}),
            'comment_instructions': forms.Textarea(
                attrs={'rows':2,
                    'placeholder': 'Example: Please enter your reasons for the choices you made.'})
        }


class AssessmentGroupForm(forms.Form):
    """Form for matching assessments to Canvas assignment groups. Each course
    assessment is a field and Canvas assignment groups are the options.
    """

    def __init__(self, *args, **kwargs):
        canvas_course = kwargs.pop('canvas_course')
        assessments = kwargs.pop('assessments')
        super().__init__(*args, **kwargs)

        choices = [(None, '---------')]
        id_map = {}
        canvas_assignment_groups = sorted(canvas_course.get_assignment_groups(), key=lambda group: group.name)

        for canvas_group in canvas_assignment_groups:
            id = canvas_group.__getattribute__('id')
            name = canvas_group.__getattribute__('name')
            choices.append((id, name))
            id_map[id] = len(choices) - 1

        assessment_fields = {}
        for assessment in assessments:
            if assessment.group is not None and assessment.group in id_map:
                index = id_map[assessment.group]
            else:
                index = 0
                # This occurs if the assessment group was previously matched to a canvas group that was deleted. Reset the group to None
                if assessment.group is not None:
                    assessment.group = None
                    assessment.save()
            initial = choices[index][0]
            assessment_fields[assessment.id.hex] = forms.ChoiceField(
                choices=choices,
                label='{} ({}%)'.format(assessment.title, assessment.default),
                initial=initial)

        self.fields.update(assessment_fields)

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
            self.non_form_errors().append(
                ValidationError('Default assessments should add up to 100%.')
            )
        
        if len(self.forms) < 2:
            self.non_form_errors().append("You must enter at least two assessments.")

        # They must have at least 2 assessments flexible (or else students can't actually make choices)
        num_assessments_flexible = 0

        # These are used to determine if the flex ranges are possible for students to select
        all_assessments = [] # Example: {'title': 'assignment1', 'default': Decimal('20.00'), 'min': Decimal('10.00'), 'max': Decimal('30.00'), 'id': <Assessment: assignment1, test_course1>}
        total_min = 0
        total_max = 0
        
        for form in self.forms:
            cleaned_data = form.cleaned_data
            default = cleaned_data.get('default')
            min_value = cleaned_data.get('min')
            max_value = cleaned_data.get('max')
            title = cleaned_data.get('title')
            cleaned_data['form'] = form

            all_assessments.append(cleaned_data)
            total_min += min_value
            total_max += max_value

            if min_value != max_value:
                num_assessments_flexible += 1

            allocations = [('default', default),
                           ('max', max_value),
                           ('min', min_value)]
            labels = {'default': 'Default', 'max': 'Maximum', 'min': 'Minimum'}

            for field, allocation in allocations:
                if allocation and (allocation > 100.0 or allocation < 0.0):
                    form.add_error(
                        field,
                        ValidationError('{} must be within 0.0 and 100.0'.format(labels[field]))
                    )
            if '<' in title or '>' in title:
                form.add_error(
                    'title',
                    ValidationError('Invalid special character in title')
                )
            if min_value > default:
                form.add_error(
                    'min',
                    ValidationError('Minimum must be lower than default')
                )
            if default > max_value:
                form.add_error(
                    'max',
                    ValidationError('Maximum must be higher than default')
                )
            if min_value > max_value:
                form.add_error(
                    'max',
                    ValidationError('Maximum must be higher than minimum')
                )
                form.add_error(
                    'min',
                    ValidationError('Minimum must be lower than maximum')
                )

        if default_sum == 100: # Don't check ranges if doesn't add to 100
            utils.find_invalid_flex_ranges(all_assessments, total_min, total_max)
        if num_assessments_flexible < 2 and len(self.forms) > 1:
            self.non_form_errors().append("You must make at least two assessments flexible.")


class AssessmentFileForm(forms.Form):
    file = forms.FileField(required=False)


def get_assessment_formset(extra=0):
    AssessmentFormSet = modelformset_factory(
        Assessment, fields=('title', 'default', 'min', 'max'),
        extra=extra,
        widgets={'title': forms.TextInput(attrs={'size': 15}),
                 'default': forms.NumberInput(attrs={'size': 5, 'min': 0, 'max': 100}),
                 'min': forms.NumberInput(attrs={'size': 5, 'min': 0, 'max': 100}),
                 'max': forms.NumberInput(attrs={'size': 5, 'min': 0, 'max': 100})},
        formset=AssessmentBaseFormSet)
    return AssessmentFormSet
