from django.core.exceptions import ValidationError
from django.forms import ModelForm
from .models import Assessment


class AddAssessmentForm(ModelForm):
    def grade_range_check(self, data):
        if data > 100.0 or data < 0.0:
            raise ValidationError(
                'Grade allocations must be within 0.0 and 100.0')

    def clean(self):
        cleaned_data = super().clean()
        default = cleaned_data.get('default')
        min = cleaned_data.get('min')
        max = cleaned_data.get('max')

        self.grade_range_check(default)
        self.grade_range_check(min)
        self.grade_range_check(max)

        if min > default:
            raise ValidationError('Minimum must be lower than default')
        elif default > max:
            raise ValidationError('Maximum must be higher than default')
        elif min > max:
            raise ValidationError('Maximum must be higher than minimum')

    class Meta:
        model = Assessment
        fields = ['title', 'default', 'min', 'max']
        help_texts = {'title': 'Enter assessment title',
                      'default': 'Default grade allocation',
                      'min': 'Minimum possible grade allocation set by student',
                      'max': 'Maximum possible grade allocation set by student'}
